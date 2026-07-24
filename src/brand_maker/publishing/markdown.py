"""Deterministic, constrained Markdown interchange."""

import json
import re

from brand_maker.brand_system.models import WorkingDraft

CANONICAL_MARKER = "brand-system-canonical-json-v1"


def export_markdown(draft: WorkingDraft, *, version: str, amendment_revision: int) -> str:
    canonical = json.dumps(draft.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    lines = [
        f"# {draft.brand_name}",
        "",
        f"Source version: {version}; amendment revision: {amendment_revision}",
        "",
    ]
    for section in draft.sections:
        lines.extend([f"## {section.title}", ""])
        for block in section.blocks:
            lines.extend([block.text, ""])
        if section.patterns:
            lines.extend(["### Patterns and playbooks", ""])
        for pattern in section.patterns:
            lines.extend(
                [
                    f"#### {pattern.name}",
                    "",
                    f"Kind: {pattern.kind}",
                    "",
                    pattern.summary,
                    "",
                ]
            )
            lines.extend(
                f"- **{item.label}:** {item.value}" for item in pattern.specifications
            )
            lines.extend(["", "**Do**", ""])
            lines.extend(f"- {item}" for item in pattern.do_guidance)
            lines.extend(["", "**Do not**", ""])
            lines.extend(f"- {item}" for item in pattern.dont_guidance)
            lines.append("")
    lines.extend([f"```{CANONICAL_MARKER}", canonical, "```", ""])
    return "\n".join(lines)


def import_markdown(source: str) -> WorkingDraft:
    match = re.search(rf"```{CANONICAL_MARKER}\n(?P<payload>[^`]{{1,5000000}})\n```", source)
    if match is None:
        raise ValueError("canonical JSON block is missing")
    return WorkingDraft.model_validate_json(match.group("payload"))
