"""Bounded, resumable orchestration for canonical section generation."""

import asyncio
import json
import logging
from collections.abc import Callable, Collection, Sequence
from datetime import UTC, datetime
from typing import Literal, Protocol
from uuid import UUID, uuid4

from pydantic import ValidationError

from brand_maker.brand_system.models import (
    BrandSection,
    DecisionRecord,
    EvidenceSource,
    WorkingDraft,
)
from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
from brand_maker.generation.prompts import PROMPT_VERSION, section_messages
from brand_maker.generation.repository import (
    GenerationRun,
    SectionRunState,
    SQLiteGenerationRepository,
)
from brand_maker.generation.sections import (
    SECTION_CATALOG,
    GeneratedSectionEnvelope,
    prerequisite_closure,
)
from brand_maker.json_extract import NoJSONObject, extract_json_object
from brand_maker.openrouter import ModelUnavailable, ProviderError

_logger = logging.getLogger(__name__)


class Completer(Protocol):
    async def complete(
        self, *, messages: list[dict[str, str]], model: str, temperature: float, max_tokens: int
    ) -> str: ...


class GenerationRunNotFound(LookupError):
    pass


def _record_generated_decision(
    envelope: GeneratedSectionEnvelope,
    *,
    run: GenerationRun,
    model: str,
    recorded_at: datetime,
) -> tuple[BrandSection, EvidenceSource, DecisionRecord]:
    """Bind validated model output to durable rationale and provenance records."""

    slug = envelope.section_id.removeprefix("section.")
    evidence_id = f"evidence.generation.{run.id.hex}.{slug}"
    decision_id = f"decision.generation.{run.id.hex}.{slug}"
    evidence = EvidenceSource(
        id=evidence_id,
        kind="model-inference",
        title=f"Generated {envelope.section.title} rationale",
        summary=envelope.rationale,
        locator=f"generation-run:{run.id}",
        retrieved_at=recorded_at,
    )
    decision = DecisionRecord(
        id=decision_id,
        decision_type=f"generated.{slug}",
        rationale=envelope.rationale,
        provenance="model-inference",
        source_ids=[evidence_id],
        confidence="medium",
        confidence_explanation=(
            "This is a validated generated starting point that still requires owner review."
        ),
        verification_requirement="owner-review",
        verification_status="unverified",
        generation_run_id=f"run.{run.id.hex}",
        prompt_version=envelope.prompt_version,
        model=model,
    )

    section = envelope.section.model_copy(
        update={
            "blocks": [
                item.model_copy(update={"decision_ids": [*item.decision_ids, decision_id]})
                for item in envelope.section.blocks
            ],
            "rules": [
                item.model_copy(update={"decision_ids": [*item.decision_ids, decision_id]})
                for item in envelope.section.rules
            ],
            "tokens": [
                item.model_copy(update={"decision_ids": [*item.decision_ids, decision_id]})
                for item in envelope.section.tokens
            ],
            "examples": [
                item.model_copy(update={"decision_ids": [*item.decision_ids, decision_id]})
                for item in envelope.section.examples
            ],
            "patterns": [
                item.model_copy(update={"decision_ids": [*item.decision_ids, decision_id]})
                for item in envelope.section.patterns
            ],
        }
    )
    return section, evidence, decision


# Prompt budget per section: the context carries every prerequisite, and blocks hold up to
# 50k characters each, so an edited draft would otherwise blow the model's context window.
_MAX_CONTEXT_ITEMS = 20
_MAX_CONTEXT_CHARS = 1_000


def _clip(text: str) -> str:
    """Bound one field, marking the cut so the model does not read it as complete."""
    return text if len(text) <= _MAX_CONTEXT_CHARS else text[:_MAX_CONTEXT_CHARS] + "…"


def _build_accepted_context(
    sections: list[BrandSection], *, prerequisites: Collection[str] | None = None
) -> dict[str, object]:
    """Hydrate prerequisite section context with blocks, tokens, rules, examples, and patterns."""
    context: dict[str, object] = {}
    for section in sections:
        if prerequisites is not None and section.id not in prerequisites:
            continue
        if not (
            section.blocks
            or section.rules
            or section.tokens
            or section.examples
            or section.patterns
        ):
            context[section.id] = {"status": section.status}
            continue
        data: dict[str, object] = {"status": section.status, "title": section.title}
        if section.blocks:
            data["blocks"] = [
                {"id": b.id, "type": b.type, "text": _clip(b.text)}
                for b in section.blocks[:_MAX_CONTEXT_ITEMS]
            ]
        if section.tokens:
            data["tokens"] = [
                {"id": t.id, "name": t.name, "value_type": t.value_type, "value": t.value}
                for t in section.tokens[:_MAX_CONTEXT_ITEMS]
            ]
        if section.rules:
            data["rules"] = [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": _clip(r.description),
                    "enforcement": r.enforcement,
                }
                for r in section.rules[:_MAX_CONTEXT_ITEMS]
            ]
        if section.examples:
            data["examples"] = [
                {"id": e.id, "kind": e.kind, "text": _clip(e.text)}
                for e in section.examples[:_MAX_CONTEXT_ITEMS]
            ]
        if section.patterns:
            data["patterns"] = [
                {"id": p.id, "name": p.name, "kind": p.kind, "summary": _clip(p.summary)}
                for p in section.patterns[:_MAX_CONTEXT_ITEMS]
            ]
        context[section.id] = data
    return context


def _founding_brief(draft: WorkingDraft) -> dict[str, object] | None:
    """Compact set-only view of the founding brief for brief-obeying generation."""
    brief = draft.brief
    summary: dict[str, object] = {"concept": brief.entry_path, "stage": draft.maturity}
    for name in ("objective", "audience", "category", "existing_equity"):
        value = getattr(brief, name)
        if value:
            summary[name] = value
    for name in ("differentiators", "constraints", "success_measures"):
        value = getattr(brief, name)
        if value:
            summary[name] = list(value)
    # Only objective/audience/category carry the brief's intent; without them there is
    # nothing substantive to obey, so skip the field entirely.
    if not any(k in summary for k in ("objective", "audience", "category")):
        return None
    return summary


def _safe_put(queue: asyncio.Queue[dict[str, object]], event: dict[str, object]) -> None:
    try:
        if queue.full():
            queue.get_nowait()
        queue.put_nowait(event)
    except (asyncio.QueueEmpty, asyncio.QueueFull):
        pass


class GenerationOrchestrator:
    def __init__(
        self,
        *,
        workspaces: SQLiteBrandSystemRepository,
        runs: SQLiteGenerationRepository,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        self._workspaces = workspaces
        self._runs = runs
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory
        self._run_locks: dict[UUID, asyncio.Lock] = {}
        self._listeners: dict[UUID, list[asyncio.Queue[dict[str, object]]]] = {}

    def subscribe(self, run_id: UUID) -> asyncio.Queue[dict[str, object]]:
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue(maxsize=1)
        self._listeners.setdefault(run_id, []).append(queue)
        run = self._runs.get(run_id)
        if run is None:
            self.unsubscribe(run_id, queue)
            raise GenerationRunNotFound
        _safe_put(queue, self._event(run))
        return queue

    def unsubscribe(self, run_id: UUID, queue: asyncio.Queue[dict[str, object]]) -> None:
        if run_id in self._listeners:
            try:
                self._listeners[run_id].remove(queue)
            except ValueError:
                pass
            if not self._listeners[run_id]:
                del self._listeners[run_id]

    def _notify(self, run: GenerationRun) -> None:
        if run.id in self._listeners:
            event = self._event(run)
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            for queue in list(self._listeners[run.id]):
                if loop and loop.is_running():
                    loop.call_soon_threadsafe(_safe_put, queue, event)
                else:
                    _safe_put(queue, event)

    @staticmethod
    def _event(run: GenerationRun) -> dict[str, object]:
        return {
            "run_id": str(run.id),
            "status": run.status,
            "cursor": run.cursor,
            "total_sections": len(run.sections),
            "sections": [section.model_dump(mode="json") for section in run.sections],
            "updated_at": run.updated_at.isoformat(),
        }

    def _save_and_notify(self, run: GenerationRun) -> GenerationRun:
        saved = self._runs.save(run)
        self._notify(saved)
        return saved

    def start(
        self,
        draft: WorkingDraft,
        *,
        target_section_id: str | None,
        model: str,
        fallback_model: str | None = None,
    ) -> GenerationRun:
        if target_section_id is None:
            requested = list(SECTION_CATALOG)
        else:
            if target_section_id not in SECTION_CATALOG:
                raise ValueError("unknown generation section")
            needed = prerequisite_closure(target_section_id) | {target_section_id}
            requested = [section_id for section_id in SECTION_CATALOG if section_id in needed]
        now = self._clock()
        return self._save_and_notify(
            GenerationRun(
                id=self._id_factory(),
                brand_id=draft.brand_id,
                source_revision=draft.revision,
                model=model,
                fallback_model=fallback_model,
                status="pending",
                cursor=0,
                sections=[SectionRunState(section_id=item, attempts=0) for item in requested],
                created_at=now,
                updated_at=now,
            )
        )

    async def resume(self, run_id: UUID, *, completer: Completer) -> GenerationRun:
        lock = self._run_locks.setdefault(run_id, asyncio.Lock())
        async with lock:
            return await self._resume(run_id, completer=completer)

    async def _resume(self, run_id: UUID, *, completer: Completer) -> GenerationRun:
        run = self._runs.get(run_id)
        if run is None:
            raise GenerationRunNotFound
        if run.status in {"cancelled", "completed"}:
            return run
        run = run.model_copy(update={"status": "running", "updated_at": self._clock()})
        self._save_and_notify(run)
        while run.cursor < len(run.sections):
            persisted = self._runs.get(run.id)
            if persisted is None:
                raise GenerationRunNotFound
            if persisted.status in {"paused", "cancelled"}:
                return persisted
            state = run.sections[run.cursor]
            draft = self._workspaces.get(run.brand_id)
            if draft is None:
                raise GenerationRunNotFound
            definition = SECTION_CATALOG[state.section_id]
            current_section = next(item for item in draft.sections if item.id == state.section_id)
            if current_section.locked:
                states = list(run.sections)
                states[run.cursor] = state.model_copy(
                    update={"status": "preserved_locked", "error": None}
                )
                run = run.model_copy(
                    update={
                        "sections": states,
                        "cursor": run.cursor + 1,
                        "updated_at": self._clock(),
                    }
                )
                self._save_and_notify(run)
                continue
            accepted = False
            last_error = "Section generation failed validation."
            selected_model = run.model
            messages = section_messages(
                definition=definition,
                brand_name=draft.brand_name,
                brand_context=draft.brand_context,
                founding_brief=_founding_brief(draft),
                accepted_context=_build_accepted_context(
                    draft.sections, prerequisites=prerequisite_closure(state.section_id)
                ),
            )
            for _ in range(3):
                state = state.model_copy(update={"attempts": state.attempts + 1})
                try:
                    raw = await completer.complete(
                        messages=messages,
                        model=selected_model,
                        temperature=0.5,
                        max_tokens=2_500,
                    )
                    envelope = GeneratedSectionEnvelope.model_validate_json(
                        extract_json_object(raw)
                    )
                    if envelope.prompt_version != PROMPT_VERSION:
                        raise ValueError("prompt version mismatch")
                    if envelope.section_id != state.section_id:
                        raise ValueError("section identity mismatch")
                    generated, evidence, decision = _record_generated_decision(
                        envelope,
                        run=run,
                        model=selected_model,
                        recorded_at=self._clock(),
                    )
                    sections = [
                        generated if item.id == state.section_id else item
                        for item in draft.sections
                    ]
                    payload = draft.model_dump(mode="json")
                    payload.update(
                        {
                            "sections": [item.model_dump(mode="json") for item in sections],
                            "evidence": [
                                *[item.model_dump(mode="json") for item in draft.evidence],
                                evidence.model_dump(mode="json"),
                            ],
                            "decisions": [
                                *[item.model_dump(mode="json") for item in draft.decisions],
                                decision.model_dump(mode="json"),
                            ],
                            "revision": draft.revision + 1,
                        }
                    )
                    updated = WorkingDraft.model_validate(payload)
                    self._workspaces.update(updated, expected_revision=draft.revision)
                    accepted = True
                    break
                except ModelUnavailable as exc:
                    last_error = f"model unavailable ({selected_model}): {exc}"
                    if run.fallback_model and selected_model != run.fallback_model:
                        selected_model = run.fallback_model
                    continue
                except (NoJSONObject, ProviderError, ValidationError, ValueError) as exc:
                    last_error = f"{type(exc).__name__}: {exc}"
                    _logger.warning(
                        "section %s attempt failed: %s", state.section_id, last_error
                    )
                    continue
            states = list(run.sections)
            if not accepted:
                states[run.cursor] = state.model_copy(
                    update={"status": "failed", "error": last_error}
                )
                run = run.model_copy(
                    update={"sections": states, "status": "failed", "updated_at": self._clock()}
                )
                return self._save_and_notify(run)
            states[run.cursor] = state.model_copy(update={"status": "accepted", "error": None})
            run = run.model_copy(
                update={
                    "sections": states,
                    "cursor": run.cursor + 1,
                    "updated_at": self._clock(),
                }
            )
            self._save_and_notify(run)
        run = run.model_copy(update={"status": "completed", "updated_at": self._clock()})
        return self._save_and_notify(run)

    def pause(self, run_id: UUID) -> GenerationRun:
        return self._set_terminal_control(run_id, "paused")

    def cancel(self, run_id: UUID) -> GenerationRun:
        return self._set_terminal_control(run_id, "cancelled")

    def _set_terminal_control(
        self, run_id: UUID, status: Literal["paused", "cancelled"]
    ) -> GenerationRun:
        run = self._runs.get(run_id)
        if run is None:
            raise GenerationRunNotFound
        if run.status in {"completed", "cancelled"}:
            return run
        controlled = GenerationRun.model_validate(
            {**run.model_dump(mode="json"), "status": status, "updated_at": self._clock()}
        )
        return self._save_and_notify(controlled)

    async def regenerate_field(
        self,
        *,
        draft: WorkingDraft,
        section_id: str,
        field_label: str,
        current_text: str,
        instruction: str | None = None,
        model: str,
        completer: Completer,
    ) -> dict[str, str]:
        """Regenerate a single narrative field/block using LLM assistance (Idea 12)."""
        from brand_maker.generation.prompts import field_regeneration_messages

        section = next((s for s in draft.sections if s.id == section_id), None)
        section_title = section.title if section else section_id
        messages = field_regeneration_messages(
            brand_name=draft.brand_name,
            brand_context=draft.brand_context,
            section_title=section_title,
            field_label=field_label,
            current_text=current_text,
            instruction=instruction,
        )
        raw = await completer.complete(
            messages=messages, model=model, temperature=0.7, max_tokens=1000
        )
        try:
            parsed = extract_json_object(raw)
            data = json.loads(parsed)
            if not isinstance(data, dict):
                raise ValueError("Expected JSON object")
            return {
                "rationale": str(
                    data.get("rationale", "Field regenerated based on owner instruction.")
                ),
                "text": str(data.get("text", current_text)),
            }
        except (NoJSONObject, json.JSONDecodeError, ValueError):
            return {
                "rationale": "Field regeneration fell back to original text.",
                "text": current_text,
            }

    async def generate_section_variants(
        self,
        *,
        draft: WorkingDraft,
        section_id: str,
        postures: Sequence[str] | None = None,
        model: str,
        completer: Completer,
    ) -> list[dict[str, object]]:
        """Generate 2-3 candidate section variants for user comparison (Idea 15)."""
        from brand_maker.generation.prompts import variant_generation_messages

        definition = SECTION_CATALOG.get(section_id)
        if definition is None:
            raise ValueError("unknown generation section")

        postures = postures or ["conservative", "balanced", "bold"]
        variants: list[dict[str, object]] = []
        for posture in postures:
            messages = variant_generation_messages(
                definition=definition,
                brand_name=draft.brand_name,
                brand_context=draft.brand_context,
                postures=[posture],
            )
            try:
                raw = await completer.complete(
                    messages=messages, model=model, temperature=0.7, max_tokens=2500
                )
                envelope = GeneratedSectionEnvelope.model_validate_json(extract_json_object(raw))
                variants.append(
                    {
                        "posture": posture,
                        "rationale": envelope.rationale,
                        "section": envelope.section.model_dump(mode="json"),
                    }
                )
            except (NoJSONObject, ValidationError, ValueError):
                continue
        return variants
