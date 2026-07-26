"""Copy compliance checking engine against active brand system rules."""

import re
from typing import Literal

from brand_maker.brand_system.models import WorkingDraft
from brand_maker.compliance.models import (
    CopyCheckReport,
    CopyCheckViolation,
)

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
    "is", "it", "of", "on", "or", "our", "that", "the", "this", "to", "with",
    "your", "copy", "marketing", "text", "phrase", "words", "language"
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


def check_copy_against_brand_rules(
    copy_text: str, workspace: WorkingDraft
) -> CopyCheckReport:
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
                                f"Replace or remove '{match.group(0)}' "
                                f"according to brand guidance."
                            ),
                        )
                    )
                    break

        for pattern in section.patterns:
            total_rules += 1
            pattern_text = f"{pattern.name} {pattern.summary} {' '.join(pattern.dont_guidance)}"
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
