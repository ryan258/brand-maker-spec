"""Bounded, resumable orchestration for canonical section generation."""

import asyncio
from collections.abc import Callable
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
from brand_maker.generation.sections import SECTION_CATALOG, GeneratedSectionEnvelope
from brand_maker.json_extract import NoJSONObject, extract_json_object
from brand_maker.openrouter import ModelUnavailable, ProviderError


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
            try:
                definition = SECTION_CATALOG[target_section_id]
            except KeyError as exc:
                raise ValueError("unknown generation section") from exc
            needed = set(definition.prerequisites) | {target_section_id}
            requested = [section_id for section_id in SECTION_CATALOG if section_id in needed]
        now = self._clock()
        return self._runs.save(
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
        self._runs.save(run)
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
            current_section = next(
                item for item in draft.sections if item.id == state.section_id
            )
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
                self._runs.save(run)
                continue
            accepted = False
            last_error = "Section generation failed validation."
            selected_model = run.model
            for _ in range(3):
                state = state.model_copy(update={"attempts": state.attempts + 1})
                try:
                    raw = await completer.complete(
                        messages=section_messages(
                            definition=definition,
                            brand_name=draft.brand_name,
                            brand_context=draft.brand_context,
                            accepted_context={
                                section.id: section.status for section in draft.sections
                            },
                        ),
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
                except ModelUnavailable:
                    if run.fallback_model and selected_model != run.fallback_model:
                        selected_model = run.fallback_model
                    continue
                except (NoJSONObject, ProviderError, ValidationError, ValueError):
                    continue
            states = list(run.sections)
            if not accepted:
                states[run.cursor] = state.model_copy(
                    update={"status": "failed", "error": last_error}
                )
                run = run.model_copy(
                    update={"sections": states, "status": "failed", "updated_at": self._clock()}
                )
                return self._runs.save(run)
            states[run.cursor] = state.model_copy(update={"status": "accepted", "error": None})
            run = run.model_copy(
                update={
                    "sections": states,
                    "cursor": run.cursor + 1,
                    "updated_at": self._clock(),
                }
            )
            self._runs.save(run)
        run = run.model_copy(update={"status": "completed", "updated_at": self._clock()})
        return self._runs.save(run)

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
        return self._runs.save(controlled)
