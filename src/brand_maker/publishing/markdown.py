"""Deterministic, constrained Markdown interchange."""

import json

from brand_maker.brand_system.models import BrandSection, WorkingDraft

CANONICAL_MARKER = "brand-system-canonical-json-v1"


def _section_detail(section: BrandSection) -> list[str]:
    """Render the guidance that otherwise survives only inside the embedded JSON."""

    lines: list[str] = []
    if section.rules:
        lines.extend(["### Rules", ""])
        lines.extend(
            f"- **{rule.name}** ({rule.enforcement}): {rule.description}" for rule in section.rules
        )
        lines.append("")
    if section.tokens:
        lines.extend(["### Tokens", ""])
        lines.extend(
            f"- **{token.name}** (`{token.id}`, {token.value_type}): {token.value}"
            for token in section.tokens
        )
        lines.append("")
    if section.examples:
        lines.extend(["### Examples", ""])
        lines.extend(f"- **{example.kind}:** {example.text}" for example in section.examples)
        lines.append("")
    return lines


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
        lines.extend(_section_detail(section))
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
            lines.extend(f"- **{item.label}:** {item.value}" for item in pattern.specifications)
            lines.extend(["", "**Do**", ""])
            lines.extend(f"- {item}" for item in pattern.do_guidance)
            lines.extend(["", "**Do not**", ""])
            lines.extend(f"- {item}" for item in pattern.dont_guidance)
            lines.append("")
    if draft.assets:
        lines.extend(["## Production assets", ""])
        lines.extend(
            f"- **{asset.name}** ({asset.media_type}, {asset.size_bytes} bytes, "
            f"{'required' if asset.required else 'optional'}) — `{asset.content_hash}`"
            for asset in draft.assets
        )
        lines.append("")
    lines.extend([f"```{CANONICAL_MARKER}", canonical, "```", ""])
    return "\n".join(lines)


def import_markdown(source: str) -> WorkingDraft:
    # The payload is one compact JSON line, so read it by position: a pattern that excludes
    # backticks loses every brand whose name or prose contains one.
    opening = f"```{CANONICAL_MARKER}\n"
    start = source.rfind(opening)
    if start == -1:
        raise ValueError("canonical JSON block is missing")
    payload_start = start + len(opening)
    end = source.find("\n```", payload_start)
    if end == -1:
        raise ValueError("canonical JSON block is unterminated")
    return WorkingDraft.model_validate_json(source[payload_start:end])
