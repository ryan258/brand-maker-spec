"""Pure deterministic compliance checks with explicit unsupported results."""

import re
from typing import Literal

from brand_maker.brand_system.models import BrandSection
from brand_maker.compliance.models import (
    ArtifactEvaluation,
    ArtifactInput,
    ComplianceFinding,
    DeterministicRule,
    TokenCollisionFinding,
    TokenContrastFinding,
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


def audit_token_collisions(
    workspace_sections: list[BrandSection],
) -> list[TokenCollisionFinding]:
    """Detect duplicate token keys and value mismatches across workspace sections."""
    tokens_by_id: dict[str, list[tuple[str, str | float | int | bool]]] = {}
    names_by_id: dict[str, str] = {}

    for section in workspace_sections:
        for idx, token in enumerate(section.tokens):
            matching_in_section = [t for t in section.tokens if t.id == token.id]
            section_label = f"{section.title} ({section.id})"
            if len(matching_in_section) > 1:
                section_label = f"{section.title} ({section.id} item #{idx + 1})"
            tokens_by_id.setdefault(token.id, []).append((section_label, token.value))
            names_by_id[token.id] = token.name

    collisions: list[TokenCollisionFinding] = []
    for token_id, entries in tokens_by_id.items():
        if len(entries) > 1:
            sections = [e[0] for e in entries]
            values_dict = {e[0]: e[1] for e in entries}
            unique_vals = set(values_dict.values())
            collision_type: Literal["duplicate_id", "value_mismatch"] = (
                "value_mismatch" if len(unique_vals) > 1 else "duplicate_id"
            )
            msg = (
                f"Token '{token_id}' is defined in multiple sections ({', '.join(sections)}) "
                f"with conflicting values: {values_dict}."
                if collision_type == "value_mismatch"
                else f"Token '{token_id}' is duplicated across sections ({', '.join(sections)})."
            )
            collisions.append(
                TokenCollisionFinding(
                    token_id=token_id,
                    name=names_by_id[token_id],
                    sections=sections,
                    collision_type=collision_type,
                    values_by_section=values_dict,
                    message=msg,
                )
            )
    return collisions


def audit_token_contrast_pairs(
    workspace_sections: list[BrandSection],
) -> list[TokenContrastFinding]:
    """Audit WCAG contrast ratios between color design tokens across workspace sections."""
    from brand_maker.compliance.models import TokenContrastFinding

    hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
    color_tokens: list[tuple[str, str, str]] = []  # (id, name, hex_value)

    for section in workspace_sections:
        for token in section.tokens:
            if token.value_type == "color" and isinstance(token.value, str):
                val = token.value.strip()
                if hex_pattern.match(val):
                    color_tokens.append((token.id, token.name, val))

    fg_keywords = {"ink", "text", "foreground", "primary", "secondary", "body", "heading"}
    bg_keywords = {"paper", "background", "surface", "card", "canvas", "base"}

    findings: list[TokenContrastFinding] = []
    for fg_id, fg_name, fg_val in color_tokens:
        fg_lower = fg_id.casefold() + fg_name.casefold()
        is_fg = any(k in fg_lower for k in fg_keywords)
        for bg_id, bg_name, bg_val in color_tokens:
            if fg_id == bg_id:
                continue
            bg_lower = bg_id.casefold() + bg_name.casefold()
            is_bg = any(k in bg_lower for k in bg_keywords)

            # Audit pairs where one is foreground-like and one is background-like, or default pairs
            if is_fg and is_bg:
                ratio = round(_contrast(fg_val, bg_val), 2)
                aa_normal = ratio >= 4.5
                aa_large = ratio >= 3.0
                aaa = ratio >= 7.0
                correction = None
                if not aa_normal:
                    correction = (
                        f"Contrast {ratio}:1 is below WCAG AA (4.5:1). "
                        f"Adjust '{fg_name}' ({fg_val}) or '{bg_name}' ({bg_val}) "
                        f"for better legibility."
                    )
                findings.append(
                    TokenContrastFinding(
                        foreground_token_id=fg_id,
                        foreground_token_name=fg_name,
                        foreground_color=fg_val,
                        background_token_id=bg_id,
                        background_token_name=bg_name,
                        background_color=bg_val,
                        contrast_ratio=ratio,
                        passes_aa_normal=aa_normal,
                        passes_aa_large=aa_large,
                        passes_aaa=aaa,
                        suggested_correction=correction,
                    )
                )
    return findings
