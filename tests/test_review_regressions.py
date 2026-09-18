"""Regressions for the review findings: each test fails if that defect returns."""

import asyncio
from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

import pytest

from brand_maker.brand_system.assets import AssetMissing, AssetStore
from brand_maker.brand_system.models import (
    AssetRegistration,
    BrandSection,
    BrandToken,
    LocalOwner,
    NarrativeBlock,
    WorkingDraft,
    WorkspaceBrief,
)
from brand_maker.brand_system.publication import canonical_content_hash
from brand_maker.brand_system.readiness import assess_readiness
from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
from brand_maker.compliance.deterministic import evaluate_artifact
from brand_maker.compliance.models import ArtifactInput, DeterministicRule
from brand_maker.compliance.repository import SQLiteComplianceRepository
from brand_maker.generation.orchestrator import GenerationOrchestrator, _founding_brief
from brand_maker.generation.repository import SQLiteGenerationRepository
from brand_maker.publishing.archive import InvalidArchive, create_archive, restore_archive
from brand_maker.publishing.developer_exports import export_draft_tokens
from brand_maker.publishing.markdown import export_markdown, import_markdown
from tests.generation.test_orchestrator import GoodCompleter
from tests.publishing.helpers import published_version


def _draft(**overrides: object) -> WorkingDraft:
    payload: dict[str, object] = {
        "brand_id": uuid4(),
        "brand_name": "Aura Studio",
        "brand_context": "A calm studio for focused work.",
        "owner": LocalOwner(display_name="Tester"),
        "revision": 1,
        "sections": [
            BrandSection(
                id="section.strategy",
                title="Strategy",
                status="draft",
                blocks=[NarrativeBlock(id="block.a", type="paragraph", text="We make calm tools.")],
            )
        ],
    }
    payload.update(overrides)
    return WorkingDraft(**payload)  # type: ignore[arg-type]


# 1. A brand name must never become executable code in an export.
LINE_SEPARATOR = "\u2028"


def test_tailwind_comment_cannot_be_closed_by_a_unicode_line_separator() -> None:
    draft = _draft(brand_name="Aura" + LINE_SEPARATOR + "globalThis.pwned = true;//")

    config = export_draft_tokens(draft)["tailwind.config.js"]

    comment, _, rest = config.partition("\n")
    assert LINE_SEPARATOR not in comment
    assert "pwned" not in rest
    assert comment.startswith("// ")


# 12. Distinct token ids must never collapse into one exported identifier.
def test_colliding_token_ids_do_not_produce_one_css_name() -> None:
    draft = _draft(
        sections=[
            BrandSection(
                id="section.color",
                title="Color",
                status="draft",
                tokens=[
                    BrandToken(id="token.a.b", name="Dotted", value_type="string", value="one"),
                    BrandToken(id="token.a-b", name="Dashed", value_type="string", value="two"),
                ],
            )
        ]
    )

    css = export_draft_tokens(draft)["tokens.css"]

    names = [line.split(":")[0].strip() for line in css.splitlines() if line.startswith("  --")]
    assert len(names) == len(set(names))


def test_an_ordinary_token_name_is_unchanged_by_the_disambiguation() -> None:
    draft = _draft(
        sections=[
            BrandSection(
                id="section.color",
                title="Color",
                status="draft",
                tokens=[
                    BrandToken(
                        id="token.color.primary",
                        name="Primary",
                        value_type="color",
                        value="#1e40af",
                    )
                ],
            )
        ]
    )

    assert "--brand-token-color-primary: #1e40af;" in export_draft_tokens(draft)["tokens.css"]


# 2 and 3. Owner controls must survive an in-flight provider call.
class _Completer(GoodCompleter):
    """Valid model output, with an owner action landing mid-call."""

    def __init__(self, during_call: Callable[[], None]) -> None:
        super().__init__()
        self._during_call = during_call

    async def complete(self, **kwargs: object) -> str:
        self._during_call()
        return await super().complete(**kwargs)


def _orchestrator(
    tmp_path: Path,
) -> tuple[GenerationOrchestrator, SQLiteBrandSystemRepository, SQLiteGenerationRepository]:
    workspaces = SQLiteBrandSystemRepository(tmp_path / "brands.db")
    runs = SQLiteGenerationRepository(tmp_path / "brands.db")
    return GenerationOrchestrator(workspaces=workspaces, runs=runs), workspaces, runs


def test_generation_does_not_overwrite_a_section_locked_during_the_model_call(
    tmp_path: Path,
) -> None:
    orchestrator, workspaces, _ = _orchestrator(tmp_path)
    draft = workspaces.create(_draft())

    def lock_it() -> None:
        current = workspaces.get(draft.brand_id)
        assert current is not None
        payload = current.model_dump(mode="json")
        payload["sections"][0]["locked"] = True
        payload["revision"] = current.revision + 1
        workspaces.update(WorkingDraft.model_validate(payload), expected_revision=current.revision)

    run = orchestrator.start(draft, target_section_id="section.strategy", model="test-model")
    finished = asyncio.run(orchestrator.resume(run.id, completer=_Completer(lock_it)))

    after = workspaces.get(draft.brand_id)
    assert after is not None
    assert after.sections[0].locked is True
    assert after.sections[0].blocks[0].id == "block.a"
    assert finished.sections[0].status == "preserved_edited"


def test_pause_issued_during_the_model_call_is_not_overwritten(tmp_path: Path) -> None:
    orchestrator, workspaces, runs = _orchestrator(tmp_path)
    draft = workspaces.create(_draft())
    run = orchestrator.start(draft, target_section_id="section.strategy", model="test-model")

    finished = asyncio.run(
        orchestrator.resume(run.id, completer=_Completer(lambda: orchestrator.pause(run.id)))
    )

    assert finished.status == "paused"
    stored = runs.get(run.id)
    assert stored is not None and stored.status == "paused"


# 11. Every substantive brief field must reach the prompt.
def test_a_brief_of_only_constraints_is_still_sent_to_the_model() -> None:
    draft = _draft(
        brief=WorkspaceBrief(
            entry_path="raw_idea",
            constraints=["Never use stock photography."],
            differentiators=["Owner-operated."],
        )
    )

    summary = _founding_brief(draft)

    assert summary is not None
    assert summary["constraints"] == ["Never use stock photography."]
    assert summary["differentiators"] == ["Owner-operated."]


def test_token_values_are_bounded() -> None:
    with pytest.raises(ValueError):
        BrandToken(id="token.big", name="Big", value_type="string", value="x" * 2_001)


# 4. A stored compliance result must never answer for a different input.
def test_saved_evaluation_is_not_reused_for_different_colors(tmp_path: Path) -> None:
    store = SQLiteComplianceRepository(tmp_path / "compliance.db")
    rule = DeterministicRule(
        id="rule.contrast",
        kind="minimum_contrast",
        parameter="4.5",
        message="Raise the contrast.",
    )
    passing = ArtifactInput(
        name="Card", content="Same text", foreground="#000000", background="#ffffff"
    )
    failing = ArtifactInput(
        name="Card", content="Same text", foreground="#eeeeee", background="#ffffff"
    )

    first = store.save_evaluation(
        evaluate_artifact(
            passing,
            rules=[rule],
            brand_version="1.0.0",
            amendment_revision=0,
            tool_version="1",
        )
    )
    second = store.save_evaluation(
        evaluate_artifact(
            failing,
            rules=[rule],
            brand_version="1.0.0",
            amendment_revision=0,
            tool_version="1",
        )
    )

    assert first.findings[0].status == "pass"
    assert second.findings[0].status == "fail"


def test_saved_evaluation_is_not_reused_when_the_rules_change(tmp_path: Path) -> None:
    store = SQLiteComplianceRepository(tmp_path / "compliance.db")
    artifact = ArtifactInput(name="Card", content="A long launch card")
    lenient = DeterministicRule(
        id="rule.length", kind="maximum_length", parameter="500", message="Shorten it."
    )
    strict = lenient.model_copy(update={"parameter": "5"})

    first = store.save_evaluation(
        evaluate_artifact(
            artifact,
            rules=[lenient],
            brand_version="1.0.0",
            amendment_revision=0,
            tool_version="1",
        )
    )
    second = store.save_evaluation(
        evaluate_artifact(
            artifact,
            rules=[strict],
            brand_version="1.0.0",
            amendment_revision=0,
            tool_version="1",
        )
    )

    assert first.findings[0].status == "pass"
    assert second.findings[0].status == "fail"


# 5. Readiness labels must mean what they claim.
def test_an_empty_workspace_cannot_reach_approved_readiness() -> None:
    report = assess_readiness(_draft(sections=[]), "approved")

    assert report.can_advance is False
    assert any(item.code == "section.missing" for item in report.findings)


# 6. Publication must revalidate required managed assets.
def test_publication_refuses_a_required_managed_asset_that_is_gone(tmp_path: Path) -> None:
    store = AssetStore(tmp_path / "assets")
    draft = _draft(
        assets=[
            AssetRegistration(
                id="asset.logo",
                name="logo.png",
                storage="managed",
                media_type="image/png",
                size_bytes=10,
                content_hash="b" * 64,
                required=True,
            )
        ]
    )

    with pytest.raises(AssetMissing):
        store.prepare_publication(draft)


# 7. Archive checksums must not certify an inconsistent publication.
def test_archive_with_a_wrong_publication_hash_is_rejected(tmp_path: Path) -> None:
    published = published_version()
    tampered = published.model_copy(update={"content_hash": "a" * 64})
    archive = tmp_path / "tampered.brand.zip"
    create_archive(tampered, tmp_path / "assets", archive)

    with pytest.raises(InvalidArchive):
        restore_archive(archive, tmp_path / "restored")


def test_archive_round_trips_a_blob_shared_by_two_registrations(tmp_path: Path) -> None:
    source = tmp_path / "logo.png"
    source.write_bytes(b"\x89PNG\r\n\x1a\n" + b"shared bytes")
    store = AssetStore(tmp_path / "assets")
    first = store.import_managed(
        asset_id="asset.one",
        name="one.png",
        source=source,
        media_type="image/png",
        required=True,
    )
    second = first.model_copy(update={"id": "asset.two", "name": "two.png"})
    base = published_version()
    snapshot = base.snapshot.model_copy(update={"assets": [first, second]})
    published = base.model_copy(
        update={"snapshot": snapshot, "content_hash": canonical_content_hash(snapshot)}
    )
    archive = tmp_path / "shared.brand.zip"

    create_archive(published, tmp_path / "assets", archive)
    restored = restore_archive(archive, tmp_path / "restored")

    assert [item.id for item in restored.rendered.rendered_snapshot.assets] == [
        "asset.one",
        "asset.two",
    ]


# 13. Markdown interchange must survive ordinary content.
def test_markdown_round_trips_a_brand_name_containing_a_backtick() -> None:
    draft = _draft(brand_name="Aura `Studio`")

    restored = import_markdown(export_markdown(draft, version="draft", amendment_revision=0))

    assert restored.brand_name == "Aura `Studio`"


def test_markdown_renders_rules_and_tokens_outside_the_json_payload() -> None:
    draft = _draft(
        sections=[
            BrandSection(
                id="section.color",
                title="Color",
                status="draft",
                tokens=[
                    BrandToken(
                        id="token.color.primary",
                        name="Primary",
                        value_type="color",
                        value="#1e40af",
                    )
                ],
            )
        ]
    )

    readable = export_markdown(draft, version="draft", amendment_revision=0).split("```")[0]

    assert "Primary" in readable
    assert "#1e40af" in readable


# 9. Audience outputs must carry the enforceable content, not only narrative.
def test_audience_html_and_pdf_source_include_token_values() -> None:
    from brand_maker.publishing.pdf import projection_html
    from brand_maker.publishing.projections import project
    from brand_maker.publishing.web import render_projection
    from tests.publishing.helpers import rendered_version

    base = rendered_version()
    section = base.rendered_snapshot.sections[0].model_copy(
        update={
            "tokens": [
                BrandToken(
                    id="token.color.primary", name="Primary", value_type="color", value="#1e40af"
                )
            ]
        }
    )
    snapshot = base.rendered_snapshot.model_copy(update={"sections": [section]})
    rendered = base.model_copy(update={"rendered_snapshot": snapshot})
    view = project(rendered, content_hash="c" * 64, audience="designer")

    assert "#1e40af" in render_projection(view)
    assert "#1e40af" in projection_html(view)
