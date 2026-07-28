"""Stable developer-facing projections of canonical implementation guidance."""

import io
import json
import re
import zipfile
from pathlib import Path

from brand_maker.brand_bible import render_brand_bible
from brand_maker.brand_system.assets import AssetChanged, AssetMissing, AssetStore
from brand_maker.brand_system.models import AssetRegistration, PublishedVersion, WorkingDraft
from brand_maker.publishing.archive import MAX_ARCHIVE_BYTES, MAX_ENTRIES, MAX_ENTRY_BYTES
from brand_maker.publishing.markdown import export_markdown
from brand_maker.publishing.pdf import render_html_pdf


class BrandKitLimitExceeded(ValueError):
    """A draft brand kit cannot be produced within the archive safety limits."""


class RequiredBrandKitAssetUnavailable(ValueError):
    """A required registered asset cannot be included safely."""

    def __init__(self, asset: AssetRegistration) -> None:
        self.asset = asset
        super().__init__(asset.name)


def _semantic_name(value: str) -> str:
    cleaned = value.casefold().replace(".", "-")
    cleaned = re.sub(r"[^a-z0-9_-]+", "-", cleaned).strip("-")
    return cleaned or "token"


def _css_value(value: str | float | int | bool) -> str:
    """Keep a token inside its custom-property declaration."""

    text = str(value)
    escaped = "".join(
        f"\\{ord(character):x} "
        if character in "\\;{}" or ord(character) < 32 or ord(character) == 127
        else character
        for character in text
    )
    return escaped.replace("/*", "\\2f *").replace("*/", "*\\2f ")


def export_draft_tokens(draft: WorkingDraft) -> dict[str, str]:
    safe_css_brand = re.sub(r"[\r\n]+", " ", draft.brand_name).replace("*/", "* /")
    safe_js_brand = re.sub(r"[\r\n]+", " ", draft.brand_name)

    tokens = [token for section in draft.sections for token in section.tokens]
    css = [f"/* brand-system: {safe_css_brand} (draft) */", ":root {"]
    colors: dict[str, str] = {}
    fonts: dict[str, str] = {}
    spacing: dict[str, str] = {}
    durations: dict[str, str] = {}
    seen_keys: dict[str, int] = {}

    for token in sorted(tokens, key=lambda item: item.id):
        base_key = _semantic_name(token.id)
        if base_key in seen_keys:
            seen_keys[base_key] += 1
            key = f"{base_key}_{seen_keys[base_key]}"
        else:
            seen_keys[base_key] = 0
            key = base_key

        val = str(token.value)
        css.append(f"  --brand-{key}: {_css_value(token.value)};")
        if token.value_type == "color":
            colors[key] = val
        elif token.value_type == "font":
            fonts[key] = val
        elif token.value_type == "dimension":
            spacing[key] = val
        elif token.value_type == "duration":
            durations[key] = val
    css.append("}")

    token_payload = {
        "brand_id": str(draft.brand_id),
        "brand_name": draft.brand_name,
        "revision": draft.revision,
        "tokens": [item.model_dump(mode="json") for item in tokens],
    }

    extend_theme: dict[str, dict[str, str]] = {}
    if colors:
        extend_theme["colors"] = colors
    if fonts:
        extend_theme["fontFamily"] = fonts
    if spacing:
        extend_theme["spacing"] = spacing
    if durations:
        extend_theme["transitionDuration"] = durations

    tailwind_config = {"theme": {"extend": extend_theme}}
    tailwind_js = (
        f"// Generated Tailwind CSS theme extension for {safe_js_brand}\n"
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
        css.append(f"  --brand-{_semantic_name(token.id)}: {_css_value(token.value)};")
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


def _safe_zip_filename(name: str) -> str:
    base = Path(name).name
    cleaned = re.sub(r"[^a-zA-Z0-9_ .-]", "_", base).strip(". ")
    return cleaned or "file"


def build_brand_kit_zip(draft: WorkingDraft, asset_store: AssetStore) -> bytes:
    if len(draft.assets) + 5 > MAX_ENTRIES:
        raise BrandKitLimitExceeded(f"Brand kit contains too many entries (max {MAX_ENTRIES}).")
    token_exports = export_draft_tokens(draft)
    md_content = export_markdown(draft, version="draft", amendment_revision=0)
    html_content = render_brand_bible(draft, for_pdf=True)
    pdf_bytes = render_html_pdf(html_content)

    safe_name = _safe_zip_filename(draft.brand_name)
    buffer = io.BytesIO()
    total_bytes = 0
    seen_names: set[str] = set()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        def write_entry(path: str, value: str | bytes) -> None:
            nonlocal total_bytes
            data = value.encode("utf-8") if isinstance(value, str) else value
            if len(data) > MAX_ENTRY_BYTES:
                raise BrandKitLimitExceeded(
                    f"Brand kit entry '{path}' exceeds the {MAX_ENTRY_BYTES} byte limit."
                )
            total_bytes += len(data)
            if total_bytes > MAX_ARCHIVE_BYTES:
                raise BrandKitLimitExceeded("Brand kit exceeds the 250 MB archive limit.")
            seen_names.add(path)
            zf.writestr(path, data)

        write_entry("tokens.css", token_exports["tokens.css"])
        write_entry("tokens.json", token_exports["tokens.json"])
        write_entry("tailwind.config.js", token_exports["tailwind.config.js"])
        write_entry(f"{safe_name}-bible.md", md_content)
        write_entry(f"{safe_name}-bible.pdf", pdf_bytes)

        for asset in draft.assets:
            if asset.size_bytes > MAX_ENTRY_BYTES:
                if asset.required:
                    raise BrandKitLimitExceeded(
                        f"Required asset '{asset.name}' exceeds the 25 MB entry limit."
                    )
                continue
            try:
                asset_bytes = asset_store.read(asset)
                base_name = _safe_zip_filename(asset.name)
                stem = Path(base_name).stem
                extension = Path(base_name).suffix
                candidate_name = f"assets/{base_name}"
                counter = 1
                while candidate_name in seen_names:
                    candidate_name = f"assets/{stem}_{counter}{extension}"
                    counter += 1
                write_entry(candidate_name, asset_bytes)
            except BrandKitLimitExceeded:
                raise
            except (AssetMissing, AssetChanged, ValueError) as exc:
                if asset.required:
                    raise RequiredBrandKitAssetUnavailable(asset) from exc

    return buffer.getvalue()
