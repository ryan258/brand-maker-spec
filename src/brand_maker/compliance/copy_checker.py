"""Copy compliance checking engine against active brand system rules."""

import hashlib
import re
from typing import Literal

from brand_maker.brand_system.models import WorkingDraft
from brand_maker.compliance.models import (
    CopyCheckReport,
    CopyCheckViolation,
    DeterministicRule,
)

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "this",
    "to",
    "with",
    "your",
    "copy",
    "marketing",
    "text",
    "phrase",
    "words",
    "language",
}


def _extract_forbidden_terms(text: str) -> list[str]:
    terms: list[str] = []
    # 1. Matches quoted phrases: never say "fake claims", avoid "formal"
    quoted = re.findall(
        r"(?:never say|do not use|avoid|forbidden:?)\s+['\"]([^'\"]+)['\"]",
        text,
        re.IGNORECASE,
    )
    for q in quoted:
        q_clean = q.strip()
        if q_clean and q_clean.lower() not in STOPWORDS:
            terms.append(q_clean)

    # 2. Matches single unquoted words: never say parody, do not use clickbait
    # ponytail: unquoted 'avoid' captures single adverbs like 'overly' in
    # 'Avoid overly formal language'; require quotes for 'avoid'
    unquoted = re.findall(
        r"(?:never say|do not use|forbidden:?)\s+([a-zA-Z0-9_-]+)",
        text,
        re.IGNORECASE,
    )
    for u in unquoted:
        u_clean = u.strip()
        if u_clean and u_clean.lower() not in STOPWORDS and u_clean not in terms:
            terms.append(u_clean)

    return terms


def _structured_forbidden_terms(pattern: object) -> list[str]:
    kind = getattr(pattern, "kind", None)
    if kind != "say_never_say":
        return []
    terms: list[str] = []
    for specification in getattr(pattern, "specifications", []):
        label = specification.label.casefold().replace("/", " ").replace("_", " ")
        if "never say" not in label and "forbidden" not in label and "avoid" not in label:
            continue
        terms.extend(
            item.strip() for item in re.split(r"[\n,;]+", specification.value) if item.strip()
        )
    return terms


def _derived_rule_id(base: str, index: int) -> str:
    suffix = f".term.{index}"
    if len(base) + len(suffix) <= 128:
        return f"{base}{suffix}"
    digest = hashlib.sha256(base.encode()).hexdigest()[:12]
    stem = base[: 128 - len(digest) - len(suffix) - 1].rstrip("._-")
    return f"{stem}.{digest}{suffix}"


def _deterministic_copy_rule_sources(
    workspace: WorkingDraft,
) -> list[tuple[DeterministicRule, str]]:
    result: list[tuple[DeterministicRule, str]] = []
    for section in workspace.sections:
        for rule in section.rules:
            terms = _extract_forbidden_terms(f"{rule.name} {rule.description}")
            if terms:
                result.extend(
                    (
                        DeterministicRule(
                            id=_derived_rule_id(rule.id, index),
                            kind="forbidden_term",
                            parameter=term[:1_000],
                            message=f"Follow the published rule: {rule.name}."[:300],
                        ),
                        rule.id,
                    )
                    for index, term in enumerate(terms, start=1)
                )
            else:
                result.append(
                    (
                        DeterministicRule(
                            id=rule.id,
                            kind="unsupported",
                            parameter=rule.description[:1_000],
                            message=f"Review the published rule manually: {rule.name}."[:300],
                        ),
                        rule.id,
                    )
                )
        for pattern in section.patterns:
            forbidden_terms = _structured_forbidden_terms(pattern)
            if not forbidden_terms:
                pattern_text = f"{pattern.name} {pattern.summary} {' '.join(pattern.dont_guidance)}"
                forbidden_terms = _extract_forbidden_terms(pattern_text)
            result.extend(
                (
                    DeterministicRule(
                        id=_derived_rule_id(pattern.id, index),
                        kind="forbidden_term",
                        parameter=term[:1_000],
                        message=f"Use an approved alternative from {pattern.name}."[:300],
                    ),
                    pattern.id,
                )
                for index, term in enumerate(forbidden_terms, start=1)
            )
    return result


def deterministic_copy_rules(workspace: WorkingDraft) -> list[DeterministicRule]:
    """Project canonical copy guidance into explicit deterministic checks."""

    return [rule for rule, _ in _deterministic_copy_rule_sources(workspace)]


def check_copy_against_brand_rules(copy_text: str, workspace: WorkingDraft) -> CopyCheckReport:
    """Evaluate candidate text against brand rules across all sections."""
    violations: list[CopyCheckViolation] = []

    rule_map: dict[str, tuple[str, Literal["advisory", "warning", "blocking"]]] = {}
    total_rules = 0
    for section in workspace.sections:
        total_rules += len(section.rules) + len(section.patterns)
        for r in section.rules:
            rule_map[r.id] = (r.name, r.enforcement)
        for p in section.patterns:
            rule_map[p.id] = (p.name, "warning")

    rules = _deterministic_copy_rule_sources(workspace)
    seen_rules: set[str] = set()

    for rule, base_id in rules:
        if rule.kind != "forbidden_term":
            continue
        term = rule.parameter
        if base_id in seen_rules:
            continue
        match = re.search(rf"\b{re.escape(term)}\b", copy_text, re.IGNORECASE)
        if match:
            seen_rules.add(base_id)
            rule_name, enforcement = rule_map.get(base_id, (rule.message, "warning"))
            violations.append(
                CopyCheckViolation(
                    rule_id=rule.id,
                    rule_name=rule_name,
                    enforcement=enforcement,
                    matched_text=match.group(0),
                    message=(
                        f"Copy contains forbidden term '{match.group(0)}' "
                        f"violating rule '{rule_name}'."
                    ),
                    suggested_correction=(
                        f"Replace or remove '{match.group(0)}' according to brand guidance."
                    ),
                )
            )

    passed_count = max(0, total_rules - len(seen_rules))
    has_blocking = any(v.enforcement == "blocking" for v in violations)
    has_warning = any(v.enforcement == "warning" for v in violations)

    status: Literal["pass", "warning", "fail"]
    if has_blocking:
        status = "fail"
    elif has_warning or len(violations) > 0:
        status = "warning"
    else:
        status = "pass"

    return CopyCheckReport(
        copy_text=copy_text,
        passed_rules_count=passed_count,
        violations=violations,
        overall_status=status,
    )
