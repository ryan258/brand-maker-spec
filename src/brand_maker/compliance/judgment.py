"""Explicitly non-authoritative model judgment and scoped evidence records."""

import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal, Self
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from brand_maker.brand_system.models import ShortText, StableId
from brand_maker.models import ContractModel


class JudgmentFinding(ContractModel):
    rule_id: StableId
    evidence: str = Field(..., min_length=1, max_length=10_000)
    confidence: float = Field(..., ge=0, le=1)
    status: Literal["suggestion", "needs_review"]
    evaluation_type: Literal["model_judgment"] = "model_judgment"


class EvidenceRecord(ContractModel):
    level: Literal["owner", "professional"]
    claim: str = Field(..., min_length=1, max_length=10_000)
    verifier_name: ShortText
    qualifications: ShortText | None = None
    scope: ShortText | None = None
    verified_on: date | None = None

    @model_validator(mode="after")
    def require_professional_attribution(self) -> Self:
        if self.level == "professional" and not all(
            (self.qualifications, self.scope, self.verified_on)
        ):
            raise ValueError("professional evidence requires qualifications, scope, and date")
        return self


class RegisteredEvidence(ContractModel):
    id: UUID
    artifact_id: UUID
    record: EvidenceRecord
    registered_at: datetime


class RegisterEvidenceRequest(ContractModel):
    artifact_id: UUID
    evidence: EvidenceRecord


class SQLiteEvidenceRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def register(self, artifact_id: UUID, record: EvidenceRecord) -> RegisteredEvidence:
        registered = RegisteredEvidence(
            id=uuid4(),
            artifact_id=artifact_id,
            record=record,
            registered_at=datetime.now(UTC),
        )
        with sqlite3.connect(self._path, timeout=5.0) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS compliance_evidence (
                   id TEXT PRIMARY KEY, artifact_id TEXT NOT NULL,
                   evidence_json TEXT NOT NULL)"""
            )
            connection.execute(
                "INSERT INTO compliance_evidence VALUES (?, ?, ?)",
                (str(registered.id), str(artifact_id), registered.model_dump_json()),
            )
        return registered

    def get(self, evidence_id: UUID) -> RegisteredEvidence | None:
        with sqlite3.connect(self._path, timeout=5.0) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS compliance_evidence (
                   id TEXT PRIMARY KEY, artifact_id TEXT NOT NULL,
                   evidence_json TEXT NOT NULL)"""
            )
            row = connection.execute(
                "SELECT evidence_json FROM compliance_evidence WHERE id=?",
                (str(evidence_id),),
            ).fetchone()
        return RegisteredEvidence.model_validate_json(row[0]) if row else None
