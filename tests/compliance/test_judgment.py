from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from brand_maker.compliance.judgment import (
    EvidenceRecord,
    JudgmentFinding,
    SQLiteEvidenceRepository,
)


def test_model_judgment_can_never_claim_verified_status() -> None:
    with pytest.raises(ValidationError):
        JudgmentFinding(
            rule_id="rule.voice.warm",
            evidence="The copy feels warm.",
            confidence=0.8,
            status="verified",
        )


def test_professional_evidence_requires_identity_qualifications_scope_and_date() -> None:
    with pytest.raises(ValidationError):
        EvidenceRecord(
            level="professional",
            claim="The logo is legally clear.",
            verifier_name="Counsel",
        )


def test_scoped_evidence_is_persisted_without_upgrading_model_judgment(
    tmp_path: Path,
) -> None:
    repository = SQLiteEvidenceRepository(tmp_path / "brands.db")
    evidence = EvidenceRecord(
        level="owner",
        claim="The approved campaign uses the intended voice.",
        verifier_name="Ryan",
    )
    registered = repository.register(
        UUID("d795ebf9-8f54-44a2-85cd-e73faacb7008"), evidence
    )

    assert repository.get(registered.id) == registered
