from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from brand_maker.brand_system.models import (
    BrandSection,
    CreateWorkspaceRequest,
    DecisionRecord,
    EvidenceSource,
    LocalOwner,
    NarrativeBlock,
    WorkingDraft,
    WorkspaceBrief,
)
from brand_maker.brand_system.readiness import assess_readiness


def test_existing_workspace_payload_loads_with_personal_os_defaults() -> None:
    draft = WorkingDraft.model_validate(
        {
            "brand_id": str(uuid4()),
            "brand_name": "Northstar",
            "owner": {"display_name": "Ryan"},
            "revision": 1,
            "sections": [],
        }
    )

    assert draft.maturity == "working"
    assert draft.brief.entry_path == "named_concept"
    assert draft.brief.assistance_mode == "copilot"
    assert draft.brief.research_mode == "controlled"
    assert draft.evidence == []
    assert draft.decisions == []


def test_workspace_request_accepts_all_confirmed_entry_paths() -> None:
    for entry_path in ("raw_idea", "named_concept", "existing_project", "quick_start"):
        request = CreateWorkspaceRequest(
            brand_name="Northstar",
            owner_name="Ryan",
            entry_path=entry_path,
            assistance_mode="autonomous",
            research_mode="controlled",
        )

        assert request.entry_path == entry_path
        assert request.assistance_mode == "autonomous"


def test_decisions_must_reference_known_evidence() -> None:
    evidence = EvidenceSource(
        id="evidence.owner.brief",
        kind="owner",
        title="Founding brief",
        summary="The owner's description of the project and intended audience.",
        retrieved_at=datetime(2026, 7, 25, tzinfo=UTC),
    )
    decision = DecisionRecord(
        id="decision.strategy.positioning",
        decision_type="positioning",
        rationale="Focus on attainable outdoor care rather than adventure prestige.",
        provenance="owner",
        source_ids=[evidence.id],
        confidence="high",
        confidence_explanation="The choice directly reflects the founding brief.",
        verification_requirement="owner-review",
        verification_status="verified",
    )
    section = BrandSection(
        id="section.strategy",
        title="Strategy",
        status="reviewed",
        blocks=[
            NarrativeBlock(
                id="block.strategy.positioning",
                type="paragraph",
                text="Nearby nature is enough to begin.",
                decision_ids=[decision.id],
            )
        ],
    )

    valid = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Fieldwell",
        brand_context="Outdoor care for apartment dwellers.",
        owner=LocalOwner(display_name="Ryan"),
        revision=1,
        brief=WorkspaceBrief(entry_path="raw_idea"),
        evidence=[evidence],
        decisions=[decision],
        sections=[section],
    )
    assert valid.sections[0].blocks[0].decision_ids == [decision.id]

    with pytest.raises(ValidationError, match="unknown evidence source"):
        WorkingDraft(
            brand_id=uuid4(),
            brand_name="Fieldwell",
            owner=LocalOwner(display_name="Ryan"),
            revision=1,
            decisions=[decision.model_copy(update={"source_ids": ["evidence.missing"]})],
        )


def test_empty_workspace_fails_approved_readiness() -> None:
    draft = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Fieldwell",
        owner=LocalOwner(display_name="Ryan"),
        revision=1,
        sections=[BrandSection(id="section.strategy", title="Strategy")],
    )

    report = assess_readiness(draft, "approved")

    assert report.can_advance is False
    assert {finding.code for finding in report.findings} >= {
        "brand.context.required",
        "section.incomplete",
        "section.content.required",
    }
