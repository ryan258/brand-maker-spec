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


class TokenCollisionFinding(ContractModel):
    token_id: StableId
    name: ShortText
    sections: list[str]
    collision_type: Literal["duplicate_id", "value_mismatch"]
    values_by_section: dict[str, str | float | int | bool]
    message: str


class TokenContrastFinding(ContractModel):
    foreground_token_id: StableId
    foreground_token_name: ShortText
    foreground_color: str
    background_token_id: StableId
    background_token_name: ShortText
    background_color: str
    contrast_ratio: float
    passes_aa_normal: bool
    passes_aa_large: bool
    passes_aaa: bool
    suggested_correction: str | None = None


class CopyCheckViolation(ContractModel):
    rule_id: StableId
    rule_name: ShortText
    enforcement: Literal["advisory", "warning", "blocking"]
    matched_text: str | None = None
    message: str
    suggested_correction: str | None = None


class CopyCheckReport(ContractModel):
    copy_text: str
    passed_rules_count: int
    violations: list[CopyCheckViolation]
    overall_status: Literal["pass", "warning", "fail"]


class CopyCheckRequest(ContractModel):
    copy_text: str = Field(..., min_length=1, max_length=50_000)
