import asyncio
import json
from pathlib import Path
from uuid import UUID

from brand_maker.brand_system.models import (
    BrandExample,
    BrandPattern,
    BrandRule,
    BrandSection,
    BrandToken,
    LocalOwner,
    NarrativeBlock,
    PatternSpecification,
    WorkingDraft,
    WorkspaceBrief,
)
from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
from brand_maker.generation.orchestrator import (
    GenerationOrchestrator,
    _build_accepted_context,
    _founding_brief,
)
from brand_maker.generation.repository import SQLiteGenerationRepository
from brand_maker.generation.sections import SECTION_CATALOG, prerequisite_closure
from brand_maker.openrouter import ModelUnavailable, ProviderError


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
                        for kind in request["content_requirements"]["required_pattern_kinds"]
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


class LeakyProviderFailure:
    async def complete(self, **kwargs) -> str:
        raise ProviderError("upstream payload contained secret-token-123")


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
    assert len(stored.evidence) == len(SECTION_CATALOG)
    assert len(stored.decisions) == len(SECTION_CATALOG)
    strategy_decision = stored.decisions[0]
    assert strategy_decision.rationale == "A bounded generated starting point."
    assert strategy_decision.provenance == "model-inference"
    assert strategy_decision.generation_run_id == f"run.{run.id.hex}"
    assert strategy_decision.prompt_version == "living-brand-section-v3"
    assert strategy_decision.model == "test-model"
    assert stored.sections[0].blocks[0].decision_ids == [strategy_decision.id]


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


async def test_failed_run_persists_only_a_safe_error_summary(tmp_path: Path) -> None:
    workspaces, draft = workspace(tmp_path / "brands.db")
    runs = SQLiteGenerationRepository(tmp_path / "brands.db")
    orchestrator = GenerationOrchestrator(workspaces=workspaces, runs=runs)
    run = orchestrator.start(draft, target_section_id="section.strategy", model="test-model")

    failed = await orchestrator.resume(run.id, completer=LeakyProviderFailure())

    assert failed.status == "failed"
    assert failed.sections[0].error == "Section generation failed."
    assert "secret-token-123" not in failed.model_dump_json()


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


def _draft_with_brief(brief: WorkspaceBrief) -> WorkingDraft:
    return WorkingDraft(
        brand_id=UUID("11111111-1111-1111-1111-111111111111"),
        brand_name="Acme",
        owner=LocalOwner(display_name="Owner"),
        revision=1,
        brief=brief,
        sections=[BrandSection(id="section.strategy", title="Strategy", status="draft")],
    )


def test_founding_brief_summarizes_set_fields_with_concept_and_stage() -> None:
    draft = _draft_with_brief(
        WorkspaceBrief(
            objective="Win trust",
            audience="Small farmers",
            category="Agtech",
            differentiators=["local-first"],
        )
    )
    summary = _founding_brief(draft)

    assert summary is not None
    assert summary["objective"] == "Win trust"
    assert summary["concept"] == draft.brief.entry_path
    assert summary["stage"] == draft.maturity
    assert summary["differentiators"] == ["local-first"]


def test_founding_brief_is_skipped_without_substantive_intent() -> None:
    # A brief with only constraints and no objective/audience/category is nothing to obey.
    draft = _draft_with_brief(WorkspaceBrief(constraints=["budget under 5k"]))
    assert _founding_brief(draft) is None


def test_build_accepted_context_hydrates_section_blocks_tokens_rules_and_examples() -> None:
    section_strategy = BrandSection(
        id="section.strategy",
        title="Strategy",
        status="draft",
        blocks=[
            NarrativeBlock(
                id="block.strategy.overview", type="paragraph", text="Strategic vision text."
            )
        ],
        rules=[
            BrandRule(
                id="rule.strategy.primary",
                name="Primary Rule",
                description="Stay focused.",
                enforcement="warning",
            )
        ],
    )
    section_color = BrandSection(
        id="section.color",
        title="Color",
        status="draft",
        tokens=[
            BrandToken(
                id="token.color.primary", name="Primary Color", value_type="color", value="#112233"
            )
        ],
        examples=[
            BrandExample(
                id="example.color.do", kind="do", text="Use primary color for main action."
            )
        ],
    )
    section_empty = BrandSection(id="section.voice", title="Voice", status="draft")

    context = _build_accepted_context([section_strategy, section_color, section_empty])

    assert context["section.strategy"] == {
        "status": "draft",
        "title": "Strategy",
        "blocks": [
            {"id": "block.strategy.overview", "type": "paragraph", "text": "Strategic vision text."}
        ],
        "rules": [
            {
                "id": "rule.strategy.primary",
                "name": "Primary Rule",
                "description": "Stay focused.",
                "enforcement": "warning",
            }
        ],
    }
    assert context["section.color"] == {
        "status": "draft",
        "title": "Color",
        "tokens": [
            {
                "id": "token.color.primary",
                "name": "Primary Color",
                "value_type": "color",
                "value": "#112233",
            }
        ],
        "examples": [
            {"id": "example.color.do", "kind": "do", "text": "Use primary color for main action."}
        ],
    }
    assert context["section.voice"] == {"status": "draft"}


def test_build_accepted_context_filters_prerequisites_and_hydrates_patterns() -> None:
    section_strategy = BrandSection(
        id="section.strategy",
        title="Strategy",
        status="draft",
        blocks=[NarrativeBlock(id="block.strategy.overview", type="paragraph", text="A" * 1500)],
    )
    section_messaging = BrandSection(
        id="section.messaging",
        title="Messaging",
        status="draft",
        patterns=[
            BrandPattern(
                id="pattern.messaging.framework",
                name="Framework",
                kind="positioning_framework",
                summary="A positioning framework pattern.",
                specifications=[PatternSpecification(label="Core", value="Value")],
                do_guidance=["Do X"],
                dont_guidance=["Dont Y"],
            )
        ],
    )
    section_color = BrandSection(
        id="section.color",
        title="Color",
        status="draft",
        tokens=[
            BrandToken(id="token.color.primary", name="Primary", value_type="color", value="#000")
        ],
    )

    context = _build_accepted_context(
        [section_strategy, section_messaging, section_color],
        prerequisites={"section.strategy"},
    )

    assert "section.messaging" not in context
    assert "section.color" not in context
    assert "section.strategy" in context
    # Clipped to the budget, with a marker so the model does not read it as complete.
    assert context["section.strategy"]["blocks"][0]["text"] == "A" * 1000 + "…"

    context_messaging = _build_accepted_context(
        [section_messaging], prerequisites={"section.messaging"}
    )
    assert context_messaging["section.messaging"]["patterns"] == [
        {
            "id": "pattern.messaging.framework",
            "name": "Framework",
            "kind": "positioning_framework",
            "summary": "A positioning framework pattern.",
        }
    ]


def test_prerequisite_closure_reaches_indirect_dependencies() -> None:
    # section.digital depends only on layout, but must still see the palette and type roles.
    assert prerequisite_closure("section.digital") == {
        "section.layout",
        "section.color",
        "section.typography",
        "section.strategy",
    }
    assert prerequisite_closure("section.strategy") == set()


async def test_regenerated_section_never_sees_its_own_prior_content(tmp_path: Path) -> None:
    # "Update to match brief" reruns every unlocked section over a populated draft. Feeding a
    # section its own stale content under "do not contradict accepted context" would pin it to
    # the output the rerun is meant to replace.
    workspaces, draft = workspace(tmp_path / "brands.db")
    runs = SQLiteGenerationRepository(tmp_path / "brands.db")
    orchestrator = GenerationOrchestrator(workspaces=workspaces, runs=runs)

    first = orchestrator.start(draft, target_section_id=None, model="test-model")
    await orchestrator.resume(first.id, completer=GoodCompleter())
    populated = workspaces.get(draft.brand_id)
    assert populated is not None
    assert populated.sections[0].blocks  # every section now carries prior content

    rerun_completer = GoodCompleter()
    second = orchestrator.start(populated, target_section_id=None, model="test-model")
    await orchestrator.resume(second.id, completer=rerun_completer)

    by_section = {
        request["section_id"]: request["accepted_context"] for request in rerun_completer.requests
    }
    assert all(section_id not in context for section_id, context in by_section.items()), (
        "a section was handed its own prior content as accepted context"
    )
    # Prerequisites arrive hydrated, transitively.
    assert by_section["section.strategy"] == {}
    assert set(by_section["section.digital"]) == prerequisite_closure("section.digital")
    assert by_section["section.digital"]["section.color"]["tokens"]
