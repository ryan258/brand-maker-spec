from pathlib import Path

from brand_maker.compliance.deterministic import evaluate_artifact
from brand_maker.compliance.models import ArtifactInput, DeterministicRule
from brand_maker.compliance.repository import SQLiteComplianceRepository


def test_deterministic_findings_bind_exact_inputs_and_never_silently_pass() -> None:
    artifact = ArtifactInput(
        name="Launch card",
        content="A free offer",
        foreground="#777777",
        background="#FFFFFF",
        width=1200,
        height=630,
    )
    rules = [
        DeterministicRule(
            id="rule.term.free",
            kind="forbidden_term",
            parameter="free",
            message="Avoid unqualified free claims.",
        ),
        DeterministicRule(
            id="rule.contrast.body",
            kind="minimum_contrast",
            parameter="4.5",
            message="Body text needs 4.5:1 contrast.",
        ),
        DeterministicRule(
            id="rule.unsupported.logo-clearspace",
            kind="unsupported",
            parameter="visual geometry",
            message="Requires visual inspection.",
        ),
    ]

    result = evaluate_artifact(
        artifact,
        rules=rules,
        brand_version="1.0.0",
        amendment_revision=0,
        tool_version="1.0",
    )

    assert result.artifact_hash == artifact.content_hash
    assert result.rule_ids == [rule.id for rule in rules]
    assert [finding.status for finding in result.findings] == [
        "fail",
        "fail",
        "unsupported",
    ]
    assert all(finding.evaluation_type == "deterministic" for finding in result.findings)


def test_artifact_revisions_and_results_are_append_only(tmp_path: Path) -> None:
    repository = SQLiteComplianceRepository(tmp_path / "brands.db")
    artifact = ArtifactInput(name="Card", content="Hello")
    first = repository.register_artifact(artifact)
    repeated = repository.register_artifact(artifact)

    assert first == repeated
    assert first.revision == 1
    changed = repository.register_artifact(ArtifactInput(name="Card", content="Hello again"))
    assert changed.revision == 2
