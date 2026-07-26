"""Visible, expiring exceptions with append-only renewal approvals."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Self
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from brand_maker.brand_system.models import ShortText, StableId
from brand_maker.models import ContractModel
from brand_maker.sqlite import database_connection, initialize_database

SCHEMA = """CREATE TABLE IF NOT EXISTS compliance_exceptions (
    id TEXT PRIMARY KEY, exception_json TEXT NOT NULL
)"""


class ExceptionRequest(ContractModel):
    rule_id: StableId
    artifact_id: UUID
    rationale: ShortText
    expires_at: datetime

    @model_validator(mode="after")
    def require_timezone(self) -> Self:
        if self.expires_at.tzinfo is None:
            raise ValueError("exception expiration must include a timezone")
        return self


class ExceptionApproval(ContractModel):
    owner_id: StableId
    approved_at: datetime
    expires_at: datetime


class RenewExceptionRequest(ContractModel):
    expires_at: datetime

    @model_validator(mode="after")
    def require_timezone(self) -> Self:
        if self.expires_at.tzinfo is None:
            raise ValueError("exception expiration must include a timezone")
        return self


class ComplianceException(ContractModel):
    id: UUID
    rule_id: StableId
    artifact_id: UUID
    rationale: ShortText
    approvals: list[ExceptionApproval] = Field(..., min_length=1)
    recommend_rule_change: bool = False


class ExceptionLedger:
    def __init__(
        self,
        *,
        clock: Callable[[], datetime] | None = None,
        path: Path | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._path = path
        self._records: dict[UUID, ComplianceException] = {}
        self._lock = RLock()
        if path is not None:
            initialize_database(path, SCHEMA)

    def _save(self, record: ComplianceException) -> None:
        self._records[record.id] = record
        if self._path is not None:
            with database_connection(self._path) as connection:
                connection.execute(
                    """INSERT INTO compliance_exceptions VALUES (?, ?)
                       ON CONFLICT(id) DO UPDATE SET exception_json=excluded.exception_json""",
                    (str(record.id), record.model_dump_json()),
                )

    def get(self, exception_id: UUID) -> ComplianceException | None:
        with self._lock:
            if exception_id in self._records:
                return self._records[exception_id]
            if self._path is None:
                return None
            with database_connection(self._path) as connection:
                row = connection.execute(
                    "SELECT exception_json FROM compliance_exceptions WHERE id=?",
                    (str(exception_id),),
                ).fetchone()
            if row is None:
                return None
            record = ComplianceException.model_validate_json(row[0])
            self._records[record.id] = record
            return record

    def approve(self, request: ExceptionRequest, *, owner_id: str) -> ComplianceException:
        with self._lock:
            if request.expires_at <= self._clock():
                raise ValueError("exception expiration must be in the future")
            record = ComplianceException(
                id=uuid4(),
                rule_id=request.rule_id,
                artifact_id=request.artifact_id,
                rationale=request.rationale,
                approvals=[
                    ExceptionApproval(
                        owner_id=owner_id,
                        approved_at=self._clock(),
                        expires_at=request.expires_at,
                    )
                ],
            )
            self._save(record)
            return record

    def applicable(self, exception_id: UUID, *, at: datetime | None = None) -> bool:
        record = self.get(exception_id)
        if record is None:
            raise KeyError(exception_id)
        observed = at or self._clock()
        return record.approvals[-1].expires_at > observed

    def renew(self, exception_id: UUID, *, expires_at: datetime) -> ComplianceException:
        with self._lock:
            record = self.get(exception_id)
            if record is None:
                raise KeyError(exception_id)
            if expires_at <= record.approvals[-1].expires_at:
                raise ValueError("renewal must extend the expiration")
            approvals = [
                *record.approvals,
                ExceptionApproval(
                    owner_id=record.approvals[-1].owner_id,
                    approved_at=self._clock(),
                    expires_at=expires_at,
                ),
            ]
            updated = ComplianceException.model_validate(
                {
                    **record.model_dump(mode="json"),
                    "approvals": [item.model_dump(mode="json") for item in approvals],
                    "recommend_rule_change": len(approvals) >= 3,
                }
            )
            self._save(updated)
            return updated
