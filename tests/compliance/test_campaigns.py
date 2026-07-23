from pathlib import Path

from brand_maker.compliance.campaigns import CampaignService
from brand_maker.compliance.models import ArtifactInput
from brand_maker.compliance.repository import SQLiteComplianceRepository


def test_campaign_keeps_atomic_artifacts_and_marks_old_result_stale(tmp_path: Path) -> None:
    repository = SQLiteComplianceRepository(tmp_path / "brands.db")
    first = repository.register_artifact(
        ArtifactInput(
            name="Card",
            content="Launch now",
            declared_tokens={"token.color.primary": "#000000"},
        )
    )
    second = repository.register_artifact(
        ArtifactInput(
            name="Email",
            content="Launch now",
            declared_tokens={"token.color.primary": "#FFFFFF"},
        )
    )
    campaigns = CampaignService(repository)
    result = campaigns.evaluate(
        name="Launch",
        artifact_revisions=[first, second],
        brand_version="1.0.0",
        amendment_revision=0,
    )

    assert result.status == "current"
    assert result.artifacts == [first, second]
    assert result.cross_artifact_findings == [
        "Token token.color.primary has conflicting values across: Card, Email"
    ]

    repository.register_artifact(ArtifactInput(name="Card", content="Launch tomorrow"))
    assert campaigns.get(result.id).status == "stale"  # type: ignore[union-attr]
