"""Campaign composition that preserves exact artifact revisions."""

from typing import Literal
from uuid import UUID, uuid4

from pydantic import Field

from brand_maker.compliance.models import ArtifactEvaluation, ArtifactRevision
from brand_maker.compliance.repository import SQLiteComplianceRepository
from brand_maker.models import ContractModel


class CampaignResult(ContractModel):
    id: UUID
    name: str = Field(..., min_length=1, max_length=300)
    brand_version: str
    amendment_revision: int = Field(..., ge=0)
    status: Literal["current", "stale"]
    artifacts: list[ArtifactRevision] = Field(..., min_length=1, max_length=1_000)
    atomic_evaluations: list[ArtifactEvaluation] = Field(default_factory=list)
    cross_artifact_findings: list[str] = Field(default_factory=list)


class CreateCampaignRequest(ContractModel):
    name: str = Field(..., min_length=1, max_length=300)
    brand_version: str = Field(..., min_length=1, max_length=100)
    amendment_revision: int = Field(0, ge=0)
    artifacts: list[ArtifactRevision] = Field(..., min_length=1, max_length=1_000)
    atomic_evaluations: list[ArtifactEvaluation] = Field(default_factory=list)


class CampaignService:
    def __init__(self, repository: SQLiteComplianceRepository) -> None:
        self._repository = repository

    def evaluate(
        self,
        *,
        name: str,
        artifact_revisions: list[ArtifactRevision],
        brand_version: str,
        amendment_revision: int,
        atomic_evaluations: list[ArtifactEvaluation] | None = None,
    ) -> CampaignResult:
        token_sources: dict[str, dict[str, list[str]]] = {}
        for artifact in artifact_revisions:
            for token_id, value in artifact.input.declared_tokens.items():
                token_sources.setdefault(token_id, {}).setdefault(value, []).append(artifact.name)
        cross_findings = [
            f"Token {token_id} has conflicting values across: "
            + ", ".join(sorted(name for names in values.values() for name in names))
            for token_id, values in sorted(token_sources.items())
            if len(values) > 1
        ]
        result = CampaignResult(
            id=uuid4(),
            name=name,
            brand_version=brand_version,
            amendment_revision=amendment_revision,
            status="current",
            artifacts=artifact_revisions,
            atomic_evaluations=atomic_evaluations or [],
            cross_artifact_findings=cross_findings,
        )
        self._repository.save_campaign(
            result.id, result.model_dump_json(exclude_computed_fields=True)
        )
        return result

    def get(self, campaign_id: UUID) -> CampaignResult | None:
        payload = self._repository.get_campaign(campaign_id)
        return CampaignResult.model_validate_json(payload) if payload else None
