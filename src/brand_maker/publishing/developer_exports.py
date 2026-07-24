"""Stable developer-facing projections of canonical tokens, rules, and voice."""

import json
import re

from brand_maker.brand_system.models import PublishedVersion


def _semantic_name(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.casefold().replace(".", "-")).strip("-")


def export_developer_package(published: PublishedVersion) -> dict[str, str]:
    tokens = [token for section in published.snapshot.sections for token in section.tokens]
    rules = [rule for section in published.snapshot.sections for rule in section.rules]
    css = [f"/* brand-version: {published.version}; hash: {published.content_hash} */", ":root {"]
    for token in sorted(tokens, key=lambda item: item.id):
        css.append(f"  --brand-{_semantic_name(token.id)}: {token.value};")
    css.append("}")
    metadata = {"version": published.version, "content_hash": published.content_hash}
    token_payload = {**metadata, "tokens": [item.model_dump(mode="json") for item in tokens]}
    rule_payload = {**metadata, "rules": [item.model_dump(mode="json") for item in rules]}
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
        "voice-context.json": json.dumps(
            voice_payload, sort_keys=True, separators=(",", ":")
        )
        + "\n",
        "change-manifest.json": json.dumps(
            change_payload, sort_keys=True, separators=(",", ":")
        )
        + "\n",
    }
