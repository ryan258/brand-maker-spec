"""Durable SQLite ledger for resumable section-generation runs."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field

from brand_maker.models import ContractModel


class SectionRunState(ContractModel):
    section_id: str
    status: Literal["pending", "accepted", "preserved_locked", "failed"] = "pending"
    attempts: int = Field(0, ge=0)
    error: str | None = None


class GenerationRun(ContractModel):
    id: UUID
    brand_id: UUID
    source_revision: int = Field(..., ge=1)
    model: str
    fallback_model: str | None = None
    status: Literal["pending", "running", "paused", "failed", "cancelled", "completed"]
    cursor: int = Field(0, ge=0)
    sections: list[SectionRunState]
    created_at: datetime
    updated_at: datetime


class StartGenerationRequest(ContractModel):
    target_section_id: str | None = None


SCHEMA = """
CREATE TABLE IF NOT EXISTS generation_runs (
    id TEXT PRIMARY KEY, brand_id TEXT NOT NULL, status TEXT NOT NULL,
    updated_at TEXT NOT NULL, run_json TEXT NOT NULL
)
"""


class SQLiteGenerationRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def save(self, run: GenerationRun) -> GenerationRun:
        with sqlite3.connect(self._path, timeout=5.0) as connection:
            connection.execute(SCHEMA)
            connection.execute(
                """INSERT INTO generation_runs VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET status=excluded.status,
                   updated_at=excluded.updated_at, run_json=excluded.run_json""",
                (
                    str(run.id),
                    str(run.brand_id),
                    run.status,
                    run.updated_at.isoformat(),
                    run.model_dump_json(),
                ),
            )
        return run

    def get(self, run_id: UUID) -> GenerationRun | None:
        with sqlite3.connect(self._path, timeout=5.0) as connection:
            connection.execute(SCHEMA)
            row = connection.execute(
                "SELECT run_json FROM generation_runs WHERE id = ?", (str(run_id),)
            ).fetchone()
        return GenerationRun.model_validate_json(row[0]) if row else None
