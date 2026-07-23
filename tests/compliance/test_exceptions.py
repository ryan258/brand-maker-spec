from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from brand_maker.compliance.exceptions import ExceptionLedger, ExceptionRequest


def test_expired_exception_does_not_alter_new_results_and_renewals_append() -> None:
    now = datetime(2026, 7, 23, tzinfo=UTC)
    ledger = ExceptionLedger(clock=lambda: now)
    request = ExceptionRequest(
        rule_id="rule.term.free",
        artifact_id=UUID("d795ebf9-8f54-44a2-85cd-e73faacb7008"),
        rationale="Approved launch wording.",
        expires_at=now + timedelta(days=1),
    )
    exception = ledger.approve(request, owner_id="local-owner")

    assert ledger.applicable(exception.id, at=now) is True
    assert ledger.applicable(exception.id, at=now + timedelta(days=2)) is False

    renewed = ledger.renew(exception.id, expires_at=now + timedelta(days=3))
    assert len(renewed.approvals) == 2
    ledger.renew(exception.id, expires_at=now + timedelta(days=4))
    recurring = ledger.renew(exception.id, expires_at=now + timedelta(days=5))
    assert recurring.recommend_rule_change is True


def test_exception_ledger_survives_a_local_restart(tmp_path: Path) -> None:
    now = datetime(2026, 7, 23, tzinfo=UTC)
    path = tmp_path / "brands.db"
    first = ExceptionLedger(clock=lambda: now, path=path)
    approved = first.approve(
        ExceptionRequest(
            rule_id="rule.term.free",
            artifact_id=UUID("d795ebf9-8f54-44a2-85cd-e73faacb7008"),
            rationale="Approved wording.",
            expires_at=now + timedelta(days=1),
        ),
        owner_id="local-owner",
    )

    restarted = ExceptionLedger(clock=lambda: now, path=path)
    assert restarted.get(approved.id) == approved
