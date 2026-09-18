"""Append-only SQLite storage for artifact and campaign revisions."""

import json
import sqlite3
from contextlib import AbstractContextManager
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
CREATE TABLE IF NOT EXISTS compliance_evaluations_v2 (
 artifact_hash TEXT NOT NULL, brand_version TEXT NOT NULL,
 amendment_revision INTEGER NOT NULL, tool_version TEXT NOT NULL,
 rule_set_hash TEXT NOT NULL, brand_id TEXT NOT NULL, source_content_hash TEXT NOT NULL,
 evaluation_json TEXT NOT NULL,
 PRIMARY KEY(artifact_hash, brand_version, amendment_revision, tool_version,
             rule_set_hash, brand_id, source_content_hash)
)
"""


class SQLiteComplianceRepository:
    def __init__(self, path: Path) -> None:
        self._path = path
        initialize_database(path, SCHEMA)

    def _connect(self) -> AbstractContextManager[sqlite3.Connection]:
        return database_connection(self._path)

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
        # Every input that can change a finding is part of the key, so a stored result is
        # only ever returned for the exact artifact, brand state, and rules that produced it.
        key = (
            evaluation.artifact_hash,
            evaluation.brand_version,
            evaluation.amendment_revision,
            evaluation.tool_version,
            evaluation.rule_set_hash,
            str(evaluation.brand_id or ""),
            evaluation.source_content_hash or "",
        )
        with self._connect() as connection:
            connection.execute(
                """INSERT OR IGNORE INTO compliance_evaluations_v2
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (*key, evaluation.model_dump_json()),
            )
            row = connection.execute(
                """SELECT evaluation_json FROM compliance_evaluations_v2
                   WHERE artifact_hash=? AND brand_version=? AND amendment_revision=?
                   AND tool_version=? AND rule_set_hash=? AND brand_id=?
                   AND source_content_hash=?""",
                key,
            ).fetchone()
        return ArtifactEvaluation.model_validate_json(row[0])
