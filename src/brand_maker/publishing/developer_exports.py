"""Stable developer-facing projections of canonical implementation guidance."""

import json
import re

from brand_maker.brand_system.models import PublishedVersion, WorkingDraft


def _semantic_name(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.casefold().replace(".", "-")).strip("-")


def export_draft_tokens(draft: WorkingDraft) -> dict[str, str]:
    tokens = [token for section in draft.sections for token in section.tokens]
    css = [f"/* brand-system: {draft.brand_name} (draft) */", ":root {"]
    colors: dict[str, str] = {}
    fonts: dict[str, str] = {}
    other_tokens: dict[str, str] = {}

    for token in sorted(tokens, key=lambda item: item.id):
        key = _semantic_name(token.id)
        val = str(token.value)
        css.append(f"  --brand-{key}: {val};")
        if token.value_type == "color":
            colors[key] = val
        elif token.value_type == "font":
            fonts[key] = val
        else:
            other_tokens[key] = val
    css.append("}")

    token_payload = {
        "brand_id": str(draft.brand_id),
        "brand_name": draft.brand_name,
        "revision": draft.revision,
        "tokens": [item.model_dump(mode="json") for item in tokens],
    }

    tailwind_config = {
        "theme": {
            "extend": {
                "colors": colors,
                "fontFamily": fonts,
                "spacing": other_tokens,
            }
        }
    }
    tailwind_js = (
        f"// Generated Tailwind CSS theme extension for {draft.brand_name}\n"
        f"module.exports = {json.dumps(tailwind_config, indent=2)};\n"
    )

    return {
        "tokens.css": "\n".join(css) + "\n",
        "tokens.json": json.dumps(token_payload, indent=2) + "\n",
        "tailwind.config.js": tailwind_js,
    }


def export_developer_package(published: PublishedVersion) -> dict[str, str]:
    tokens = [token for section in published.snapshot.sections for token in section.tokens]
    rules = [rule for section in published.snapshot.sections for rule in section.rules]
    patterns = [pattern for section in published.snapshot.sections for pattern in section.patterns]
    css = [f"/* brand-version: {published.version}; hash: {published.content_hash} */", ":root {"]
    for token in sorted(tokens, key=lambda item: item.id):
        css.append(f"  --brand-{_semantic_name(token.id)}: {token.value};")
    css.append("}")
    metadata = {"version": published.version, "content_hash": published.content_hash}
    token_payload = {**metadata, "tokens": [item.model_dump(mode="json") for item in tokens]}
    rule_payload = {**metadata, "rules": [item.model_dump(mode="json") for item in rules]}
    pattern_payload = {
        **metadata,
        "patterns": [item.model_dump(mode="json") for item in patterns],
    }
    voice_sections = [
        section
        for section in published.snapshot.sections
        if section.id in {"section.voice", "section.messaging", "section.audience"}
    ]
    voice_payload = {
        **metadata,
        "sections": [item.model_dump(mode="json") for item in voice_sections],
    }
    change_payload = {
        **metadata,
        "change_summary": published.change_summary,
        "manifest": published.manifest.model_dump(mode="json"),
        "approval_ids": [str(item.id) for item in published.approvals],
    }
    return {
        "tokens.css": "\n".join(css) + "\n",
        "tokens.json": json.dumps(token_payload, sort_keys=True, separators=(",", ":")) + "\n",
        "rules.json": json.dumps(rule_payload, sort_keys=True, separators=(",", ":")) + "\n",
        "patterns.json": json.dumps(pattern_payload, sort_keys=True, separators=(",", ":")) + "\n",
        "voice-context.json": json.dumps(voice_payload, sort_keys=True, separators=(",", ":"))
        + "\n",
        "change-manifest.json": json.dumps(change_payload, sort_keys=True, separators=(",", ":"))
        + "\n",
    }
