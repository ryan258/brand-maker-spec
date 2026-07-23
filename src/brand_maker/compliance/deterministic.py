"""Pure deterministic compliance checks with explicit unsupported results."""

import re
from typing import Literal

from brand_maker.compliance.models import (
    ArtifactEvaluation,
    ArtifactInput,
    ComplianceFinding,
    DeterministicRule,
)


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(foreground: str, background: str) -> float:
    first, second = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)), reverse=True
    )
    return (first + 0.05) / (second + 0.05)


def _finding(rule: DeterministicRule, artifact: ArtifactInput) -> ComplianceFinding:
    status: Literal["pass", "fail", "unsupported"]
    evidence: str
    if rule.kind == "forbidden_term":
        found = re.search(rf"\b{re.escape(rule.parameter)}\b", artifact.content, re.I)
        status, evidence = (
            ("fail", f"Found forbidden term: {found.group(0)}")
            if found
            else ("pass", "Forbidden term not found.")
        )
    elif rule.kind == "maximum_length":
        maximum = int(rule.parameter)
        status = "pass" if len(artifact.content) <= maximum else "fail"
        evidence = f"Observed {len(artifact.content)} characters; maximum is {maximum}."
    elif rule.kind == "required_disclosure":
        present = rule.parameter.casefold() in artifact.content.casefold()
        status, evidence = (
            ("pass", "Required disclosure is present.")
            if present
            else ("fail", "Required disclosure is missing.")
        )
    elif rule.kind == "allowed_token":
        allowed = set(rule.parameter.split(","))
        unexpected = sorted(set(artifact.declared_tokens.values()) - allowed)
        status = "fail" if unexpected else "pass"
        evidence = (
            f"Unexpected token values: {', '.join(unexpected)}"
            if unexpected
            else "All declared token values are allowed."
        )
    elif rule.kind == "minimum_contrast":
        if artifact.foreground is None or artifact.background is None:
            return ComplianceFinding(
                rule_id=rule.id,
                status="unsupported",
                evidence="Foreground and background colors were not registered.",
            )
        observed = _contrast(artifact.foreground, artifact.background)
        minimum = float(rule.parameter)
        status = "pass" if observed >= minimum else "fail"
        evidence = f"Observed contrast {observed:.2f}:1; minimum is {minimum:.2f}:1."
    elif rule.kind == "required_dimensions":
        expected_width, expected_height = (int(item) for item in rule.parameter.split("x", 1))
        status = (
            "pass"
            if (artifact.width, artifact.height) == (expected_width, expected_height)
            else "fail"
        )
        evidence = (
            f"Observed {artifact.width}x{artifact.height}; "
            f"required {expected_width}x{expected_height}."
        )
    else:
        return ComplianceFinding(
            rule_id=rule.id,
            status="unsupported",
            evidence=f"Unsupported deterministic check: {rule.parameter}",
        )
    return ComplianceFinding(
        rule_id=rule.id,
        status=status,
        evidence=evidence,
        suggested_correction=rule.message if status == "fail" else None,
    )


def evaluate_artifact(
    artifact: ArtifactInput,
    *,
    rules: list[DeterministicRule],
    brand_version: str,
    amendment_revision: int,
    tool_version: str,
) -> ArtifactEvaluation:
    return ArtifactEvaluation(
        artifact_hash=artifact.content_hash,
        brand_version=brand_version,
        amendment_revision=amendment_revision,
        tool_version=tool_version,
        rule_ids=[rule.id for rule in rules],
        findings=[_finding(rule, artifact) for rule in rules],
    )
