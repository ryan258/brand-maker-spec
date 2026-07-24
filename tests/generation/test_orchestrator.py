import asyncio
import json
from pathlib import Path
from uuid import UUID

from brand_maker.brand_system.models import BrandSection, LocalOwner, WorkingDraft
from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
from brand_maker.generation.orchestrator import GenerationOrchestrator
from brand_maker.generation.repository import SQLiteGenerationRepository
from brand_maker.generation.sections import SECTION_CATALOG
from brand_maker.openrouter import ModelUnavailable


class GoodCompleter:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.requests: list[dict[str, object]] = []

    async def complete(self, *, messages, model, temperature, max_tokens) -> str:
        request = json.loads(messages[1]["content"])
        self.requests.append(request)
        section_id = request["section_id"]
        slug = section_id.removeprefix("section.")
        self.calls.append(section_id)
        return json.dumps(
            {
                "prompt_version": request["prompt_version"],
                "section_id": section_id,
                "rationale": "A bounded generated starting point.",
                "section": {
                    "id": section_id,
                    "title": request["section_title"],
                    "status": "draft",
                    "locked": False,
                    "blocks": [
                        {
                            "id": f"block.{slug}.overview",
                            "type": "paragraph",
                            "text": "A specific strategic overview.",
                            "references": [],
                        },
                        {
                            "id": f"block.{slug}.application",
                            "type": "paragraph",
                            "text": "Practical application guidance.",
                            "references": [],
                        },
                    ],
                    "rules": [
                        {
                            "id": f"rule.{slug}.primary",
                            "name": "Primary rule",
                            "description": "Apply this decision consistently.",
                            "enforcement": "warning",
                            "references": [],
                        }
                    ],
                    "tokens": (
                        [
                            {
                                "id": f"token.{slug}.base",
                                "name": "Base value",
                                "value_type": "string",
                                "value": "brand-default",
                                "references": [],
                            }
                        ]
                        if request["content_requirements"]["tokens_required"]
                        else []
                    ),
                    "examples": [
                        {
                            "id": f"example.{slug}.do",
                            "kind": "do",
                            "text": "Follow the guidance in a concrete way.",
                            "references": [],
                        },
                        {
                            "id": f"example.{slug}.dont",
                            "kind": "dont",
                            "text": "Do not contradict the guidance.",
                            "references": [],
                        },
                    ],
                    "patterns": [
                        {
                            "id": f"pattern.{slug}.{kind}",
                            "name": kind.replace("_", " ").title(),
                            "kind": kind,
                            "summary": "A concrete application pattern.",
                            "specifications": [
                                {
                                    "label": "Default",
                                    "value": "Apply the documented specification.",
                                }
                            ],
                            "do_guidance": ["Use this approved pattern."],
                            "dont_guidance": ["Do not invent an unsupported variant."],
                            "references": [],
                        }
                        for kind in request["content_requirements"][
                            "required_pattern_kinds"
                        ]
                    ],
                },
            }
        )


class FailsAfterOne(GoodCompleter):
    async def complete(self, **kwargs) -> str:
        if self.calls:
            self.calls.append("invalid")
            return "not json"
        return await super().complete(**kwargs)


class PrimaryUnavailable(GoodCompleter):
    async def complete(self, **kwargs) -> str:
        if kwargs["model"] == "primary-model":
            raise ModelUnavailable("unavailable")
        return await super().complete(**kwargs)


def workspace(path: Path) -> tuple[SQLiteBrandSystemRepository, WorkingDraft]:
    store = SQLiteBrandSystemRepository(path)
    draft = WorkingDraft(
        brand_id=UUID("d795ebf9-8f54-44a2-85cd-e73faacb7008"),
        brand_name="Northstar",
        brand_context="Independent bookstores serving curious local readers.",
        owner=LocalOwner(display_name="Ryan"),
        revision=1,
        sections=[BrandSection(id=item.id, title=item.title) for item in SECTION_CATALOG.values()],
    )
    store.create(draft)
    return store, draft


async def test_complete_run_persists_every_section_and_finishes(tmp_path: Path) -> None:
    workspaces, draft = workspace(tmp_path / "brands.db")
    runs = SQLiteGenerationRepository(tmp_path / "brands.db")
    orchestrator = GenerationOrchestrator(workspaces=workspaces, runs=runs)
    completer = GoodCompleter()
    run = orchestrator.start(draft, target_section_id=None, model="test-model")

    completed = await orchestrator.resume(run.id, completer=completer)
    stored = workspaces.get(draft.brand_id)

    assert completed.status == "completed"
    assert completed.cursor == len(SECTION_CATALOG)
    assert completer.calls == list(SECTION_CATALOG)
    assert all(
        request["brand_context"] == "Independent bookstores serving curious local readers."
        for request in completer.requests
    )
    assert stored is not None
    assert stored.revision == 1 + len(SECTION_CATALOG)
    assert all(section.status == "draft" for section in stored.sections)


async def test_failed_run_resumes_without_repeating_accepted_work(tmp_path: Path) -> None:
    workspaces, draft = workspace(tmp_path / "brands.db")
    runs = SQLiteGenerationRepository(tmp_path / "brands.db")
    orchestrator = GenerationOrchestrator(workspaces=workspaces, runs=runs)
    run = orchestrator.start(draft, target_section_id=None, model="test-model")
    failed = await orchestrator.resume(run.id, completer=FailsAfterOne())

    assert failed.status == "failed"
    assert failed.cursor == 1
    assert workspaces.get(draft.brand_id).revision == 2  # type: ignore[union-attr]

    good = GoodCompleter()
    completed = await orchestrator.resume(run.id, completer=good)

    assert completed.status == "completed"
    assert "section.strategy" not in good.calls
    assert good.calls[0] == "section.messaging"


async def test_generation_preserves_locked_sections_and_fails_over(tmp_path: Path) -> None:
    workspaces, draft = workspace(tmp_path / "brands.db")
    payload = draft.model_dump(mode="json")
    payload["sections"][0]["locked"] = True
    payload["sections"][0]["status"] = "approved"
    payload["revision"] = 2
    locked = WorkingDraft.model_validate(payload)
    workspaces.update(locked, expected_revision=1)
    runs = SQLiteGenerationRepository(tmp_path / "brands.db")
    orchestrator = GenerationOrchestrator(workspaces=workspaces, runs=runs)
    run = orchestrator.start(
        locked,
        target_section_id="section.messaging",
        model="primary-model",
        fallback_model="fallback-model",
    )

    completed = await orchestrator.resume(run.id, completer=PrimaryUnavailable())
    stored = workspaces.get(draft.brand_id)

    assert completed.status == "completed"
    assert completed.sections[0].status == "preserved_locked"
    assert completed.sections[1].status == "accepted"
    assert stored is not None
    assert stored.sections[0].locked is True
    assert stored.sections[0].status == "approved"


async def test_duplicate_resume_commands_share_one_bounded_run(tmp_path: Path) -> None:
    workspaces, draft = workspace(tmp_path / "brands.db")
    runs = SQLiteGenerationRepository(tmp_path / "brands.db")
    orchestrator = GenerationOrchestrator(workspaces=workspaces, runs=runs)
    completer = GoodCompleter()
    run = orchestrator.start(draft, target_section_id="section.strategy", model="test-model")

    first, second = await asyncio.gather(
        orchestrator.resume(run.id, completer=completer),
        orchestrator.resume(run.id, completer=completer),
    )

    assert first.status == second.status == "completed"
    assert completer.calls == ["section.strategy"]
