"""Strict contracts for reproducible artifact compliance."""

import hashlib
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from brand_maker.brand_system.models import ShortText, StableId
from brand_maker.models import ContractModel


class ArtifactInput(ContractModel):
    name: ShortText
    content: str = Field(..., min_length=1, max_length=1_000_000)
    declared_tokens: dict[StableId, str] = Field(default_factory=dict, max_length=1_000)
    foreground: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    background: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    width: int | None = Field(default=None, ge=1, le=100_000)
    height: int | None = Field(default=None, ge=1, le=100_000)

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content.encode()).hexdigest()


class ArtifactRevision(ContractModel):
    id: UUID
    name: ShortText
    revision: int = Field(..., ge=1)
    content_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    input: ArtifactInput
    registered_at: datetime


class DeterministicRule(ContractModel):
    id: StableId
    kind: Literal[
        "forbidden_term",
        "maximum_length",
        "required_disclosure",
        "allowed_token",
        "minimum_contrast",
        "required_dimensions",
        "unsupported",
    ]
    parameter: str = Field(..., min_length=1, max_length=1_000)
    message: ShortText


class ComplianceFinding(ContractModel):
    rule_id: StableId
    status: Literal["pass", "fail", "unsupported"]
    evaluation_type: Literal["deterministic"] = "deterministic"
    evidence: str = Field(..., min_length=1, max_length=10_000)
    suggested_correction: str | None = Field(default=None, max_length=10_000)


class ArtifactEvaluation(ContractModel):
    artifact_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    brand_version: str
    amendment_revision: int = Field(..., ge=0)
    tool_version: str
    rule_ids: list[StableId]
    findings: list[ComplianceFinding]


class EvaluateArtifactRequest(ContractModel):
    artifact: ArtifactInput
    rules: list[DeterministicRule] = Field(..., min_length=1, max_length=1_000)
    brand_version: str = Field(..., min_length=1, max_length=100)
    amendment_revision: int = Field(0, ge=0)
