"""Append-only SQLite storage for artifact and campaign revisions."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from brand_maker.compliance.models import ArtifactEvaluation, ArtifactInput, ArtifactRevision
from brand_maker.sqlite import database_connection, initialize_database

SCHEMA = """
CREATE TABLE IF NOT EXISTS compliance_artifacts (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, revision INTEGER NOT NULL,
 content_hash TEXT NOT NULL, registered_at TEXT NOT NULL, artifact_json TEXT NOT NULL,
 UNIQUE(name, revision), UNIQUE(name, content_hash)
);
CREATE TABLE IF NOT EXISTS compliance_campaigns (
 id TEXT PRIMARY KEY, status TEXT NOT NULL, result_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS compliance_evaluations (
 artifact_hash TEXT NOT NULL, brand_version TEXT NOT NULL,
 amendment_revision INTEGER NOT NULL, tool_version TEXT NOT NULL,
 evaluation_json TEXT NOT NULL,
 PRIMARY KEY(artifact_hash, brand_version, amendment_revision, tool_version)
)
"""


class SQLiteComplianceRepository:
    def __init__(self, path: Path) -> None:
        self._path = path
        initialize_database(path, SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        with database_connection(self._path) as connection:
            yield connection

    def register_artifact(self, artifact: ArtifactInput) -> ArtifactRevision:
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT artifact_json FROM compliance_artifacts WHERE name=? AND content_hash=?",
                (artifact.name, artifact.content_hash),
            ).fetchone()
            if existing:
                return ArtifactRevision.model_validate_json(existing[0])
            row = connection.execute(
                "SELECT COALESCE(MAX(revision), 0) FROM compliance_artifacts WHERE name=?",
                (artifact.name,),
            ).fetchone()
            revision = int(row[0]) + 1
            record = ArtifactRevision(
                id=uuid4(),
                name=artifact.name,
                revision=revision,
                content_hash=artifact.content_hash,
                input=artifact,
                registered_at=datetime.now(UTC),
            )
            connection.execute(
                "INSERT INTO compliance_artifacts VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(record.id),
                    record.name,
                    record.revision,
                    record.content_hash,
                    record.registered_at.isoformat(),
                    record.model_dump_json(exclude_computed_fields=True),
                ),
            )
            if revision > 1:
                rows = connection.execute(
                    "SELECT id, result_json FROM compliance_campaigns WHERE status='current'"
                ).fetchall()
                for campaign_id, payload in rows:
                    result = json.loads(payload)
                    if any(
                        item["name"] == artifact.name and item["revision"] < revision
                        for item in result["artifacts"]
                    ):
                        result["status"] = "stale"
                        connection.execute(
                            "UPDATE compliance_campaigns SET status='stale', "
                            "result_json=? WHERE id=?",
                            (json.dumps(result), campaign_id),
                        )
        return record

    def save_campaign(self, campaign_id: UUID, payload: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO compliance_campaigns VALUES (?, 'current', ?)",
                (str(campaign_id), payload),
            )

    def get_campaign(self, campaign_id: UUID) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT result_json FROM compliance_campaigns WHERE id=?", (str(campaign_id),)
            ).fetchone()
        return str(row[0]) if row else None

    def save_evaluation(self, evaluation: ArtifactEvaluation) -> ArtifactEvaluation:
        with self._connect() as connection:
            connection.execute(
                """INSERT OR IGNORE INTO compliance_evaluations
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    evaluation.artifact_hash,
                    evaluation.brand_version,
                    evaluation.amendment_revision,
                    evaluation.tool_version,
                    evaluation.model_dump_json(),
                ),
            )
            row = connection.execute(
                """SELECT evaluation_json FROM compliance_evaluations
                   WHERE artifact_hash=? AND brand_version=?
                   AND amendment_revision=? AND tool_version=?""",
                (
                    evaluation.artifact_hash,
                    evaluation.brand_version,
                    evaluation.amendment_revision,
                    evaluation.tool_version,
                ),
            ).fetchone()
        return ArtifactEvaluation.model_validate_json(row[0])
