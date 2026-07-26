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
    # 1. Matches quoted phrases: never say "fake claims"
    quoted = re.findall(
        r"(?:never say|do not use|avoid|forbidden:?)\s+['\"]([^'\"]+)['\"]",
        text,
        re.IGNORECASE,
    )
    for q in quoted:
        q_clean = q.strip()
        if q_clean and q_clean.lower() not in STOPWORDS:
            terms.append(q_clean)

    # 2. Matches single unquoted words: never say parody
    unquoted = re.findall(
        r"(?:never say|do not use|avoid|forbidden:?)\s+([a-zA-Z0-9_-]+)",
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


def deterministic_copy_rules(workspace: WorkingDraft) -> list[DeterministicRule]:
    """Project canonical copy guidance into explicit deterministic checks."""

    result: list[DeterministicRule] = []
    for section in workspace.sections:
        for rule in section.rules:
            terms = _extract_forbidden_terms(f"{rule.name} {rule.description}")
            if terms:
                result.extend(
                    DeterministicRule(
                        id=_derived_rule_id(rule.id, index),
                        kind="forbidden_term",
                        parameter=term[:1_000],
                        message=f"Follow the published rule: {rule.name}."[:300],
                    )
                    for index, term in enumerate(terms, start=1)
                )
            else:
                result.append(
                    DeterministicRule(
                        id=rule.id,
                        kind="unsupported",
                        parameter=rule.description[:1_000],
                        message=f"Review the published rule manually: {rule.name}."[:300],
                    )
                )
        for pattern in section.patterns:
            result.extend(
                DeterministicRule(
                    id=_derived_rule_id(pattern.id, index),
                    kind="forbidden_term",
                    parameter=term[:1_000],
                    message=f"Use an approved alternative from {pattern.name}."[:300],
                )
                for index, term in enumerate(_structured_forbidden_terms(pattern), start=1)
            )
    return result


def check_copy_against_brand_rules(copy_text: str, workspace: WorkingDraft) -> CopyCheckReport:
    """Evaluate candidate text against brand rules across all sections."""
    violations: list[CopyCheckViolation] = []
    total_rules = 0

    for section in workspace.sections:
        for rule in section.rules:
            total_rules += 1
            rule_desc = f"{rule.name} {rule.description}"
            forbidden_terms = _extract_forbidden_terms(rule_desc)
            for term in forbidden_terms:
                match = re.search(rf"\b{re.escape(term)}\b", copy_text, re.IGNORECASE)
                if match:
                    violations.append(
                        CopyCheckViolation(
                            rule_id=rule.id,
                            rule_name=rule.name,
                            enforcement=rule.enforcement,
                            matched_text=match.group(0),
                            message=(
                                f"Copy contains forbidden term '{match.group(0)}' "
                                f"violating rule '{rule.name}'."
                            ),
                            suggested_correction=(
                                f"Replace or remove '{match.group(0)}' according to brand guidance."
                            ),
                        )
                    )
                    break

        for pattern in section.patterns:
            total_rules += 1
            pattern_text = f"{pattern.name} {pattern.summary} {' '.join(pattern.dont_guidance)}"
            forbidden_terms = _structured_forbidden_terms(pattern)
            if not forbidden_terms:
                forbidden_terms = _extract_forbidden_terms(pattern_text)
            for term in forbidden_terms:
                found = re.search(rf"\b{re.escape(term)}\b", copy_text, re.IGNORECASE)
                if found:
                    violations.append(
                        CopyCheckViolation(
                            rule_id=pattern.id,
                            rule_name=pattern.name,
                            enforcement="warning",
                            matched_text=found.group(0),
                            message=(
                                f"Copy contains discouraged phrasing '{found.group(0)}' "
                                f"in '{pattern.name}'."
                            ),
                            suggested_correction="Use approved messaging alternatives.",
                        )
                    )
                    break

    passed_count = max(0, total_rules - len(violations))
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
