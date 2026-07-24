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
    lines.extend([f"```{CANONICAL_MARKER}", canonical, "```", ""])
    return "\n".join(lines)


def import_markdown(source: str) -> WorkingDraft:
    match = re.search(rf"```{CANONICAL_MARKER}\n(?P<payload>[^`]{{1,5000000}})\n```", source)
    if match is None:
        raise ValueError("canonical JSON block is missing")
    return WorkingDraft.model_validate_json(match.group("payload"))
