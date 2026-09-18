"""Deterministic maturity checks for honest brand-system status labels."""

from typing import Literal

from pydantic import Field

from brand_maker.brand_system.models import StableId, WorkingDraft
from brand_maker.models import ContractModel

ReadinessTarget = Literal["concept", "working", "approved", "production-ready"]
FindingSeverity = Literal["warning", "blocking"]

# A schema-valid workspace can hold any set of sections, so the sections an approved brand
# must actually contain are named here rather than assumed from how creation happens to work.
CORE_SECTION_IDS = (
    "section.strategy",
    "section.messaging",
    "section.voice",
    "section.color",
    "section.typography",
)
PRODUCTION_SECTION_IDS = (
    *CORE_SECTION_IDS,
    "section.logo",
    "section.layout",
    "section.accessibility",
    "section.governance",
)


class ReadinessFinding(ContractModel):
    code: StableId
    severity: FindingSeverity
    message: str = Field(..., min_length=1, max_length=1_000)
    target_id: StableId | None = None


class ReadinessReport(ContractModel):
    target: ReadinessTarget
    draft_revision: int = Field(..., ge=1)
    can_advance: bool
    findings: list[ReadinessFinding]


class ReadinessRequest(ContractModel):
    target: ReadinessTarget
    expected_revision: int = Field(..., ge=1)


def assess_readiness(draft: WorkingDraft, target: ReadinessTarget) -> ReadinessReport:
    """Return visible findings without mutating or silently waiving them."""

    findings: list[ReadinessFinding] = []
    if not draft.brand_context:
        findings.append(
            ReadinessFinding(
                code="brand.context.required",
                severity="blocking" if target != "working" else "warning",
                message="Add founding context before assigning this maturity.",
            )
        )

    if target in {"approved", "production-ready"}:
        required_ids = PRODUCTION_SECTION_IDS if target == "production-ready" else CORE_SECTION_IDS
        present = {section.id for section in draft.sections}
        for section_id in required_ids:
            if section_id not in present:
                findings.append(
                    ReadinessFinding(
                        code="section.missing",
                        severity="blocking",
                        target_id=section_id,
                        message=f"{section_id.removeprefix('section.')} is missing from this "
                        "brand system and is required before this maturity.",
                    )
                )
        for decision in draft.decisions:
            if decision.verification_requirement == "none":
                continue
            if decision.verification_status != "unverified":
                continue
            findings.append(
                ReadinessFinding(
                    code="decision.unverified",
                    # Approval records that the owner accepted the content; production use
                    # is where an unverified professional or legal claim becomes a risk.
                    severity="blocking" if target == "production-ready" else "warning",
                    target_id=decision.id,
                    message=(
                        f"{decision.decision_type} still needs "
                        f"{decision.verification_requirement.replace('-', ' ')}."
                    ),
                )
            )
        for section in draft.sections:
            if section.status not in {"reviewed", "approved"}:
                findings.append(
                    ReadinessFinding(
                        code="section.incomplete",
                        severity="blocking",
                        target_id=section.id,
                        message=f"{section.title} must be reviewed or approved.",
                    )
                )
            if not any(
                (section.blocks, section.rules, section.tokens, section.examples, section.patterns)
            ):
                findings.append(
                    ReadinessFinding(
                        code="section.content.required",
                        severity="blocking",
                        target_id=section.id,
                        message=f"{section.title} needs canonical guidance before approval.",
                    )
                )

    if target == "production-ready":
        required_assets = [asset for asset in draft.assets if asset.required]
        if not required_assets:
            findings.append(
                ReadinessFinding(
                    code="asset.required",
                    severity="blocking",
                    message="Register at least one required production asset.",
                )
            )
        for asset in required_assets:
            if asset.storage != "managed":
                findings.append(
                    ReadinessFinding(
                        code="asset.managed.required",
                        severity="blocking",
                        target_id=asset.id,
                        message=f"{asset.name} must be stored as a managed asset.",
                    )
                )

    return ReadinessReport(
        target=target,
        draft_revision=draft.revision,
        can_advance=not any(item.severity == "blocking" for item in findings),
        findings=findings,
    )
