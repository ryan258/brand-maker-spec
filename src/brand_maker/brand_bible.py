"""Complete, escaped HTML rendering for a current living-brand draft."""

# The assembled HTML remains auditable as complete fragments rather than line-by-line
# Python concatenation.
# ruff: noqa: E501

import re
from html import escape

from brand_maker.brand_bible_styles import BRAND_BIBLE_CSS
from brand_maker.brand_system.models import (
    AssetRegistration,
    BrandExample,
    BrandPattern,
    BrandRule,
    BrandSection,
    BrandToken,
    CanonicalReference,
    NarrativeBlock,
    WorkingDraft,
)
from brand_maker.google_fonts import (
    GOOGLE_FONTS,
    family_of,
    font_stack,
    google_css_url,
)
from brand_maker.workshop_web import HEADER


def _references(references: list[CanonicalReference]) -> str:
    if not references:
        return ""
    links = ", ".join(
        f'<a href="#{escape(reference.target_id)}">{escape(reference.target_id)}</a>'
        for reference in references
    )
    return f'<p class="references"><strong>References:</strong> {links}</p>'


def _block(block: NarrativeBlock) -> str:
    return (
        f'<article class="guidance-block" id="{escape(block.id)}">'
        f'<p class="content-kind">{escape(block.type.replace("_", " "))}</p>'
        f'<p class="preserve-lines" data-block-id="{escape(block.id)}">{escape(block.text)}</p>'
        f"{_references(block.references)}</article>"
    )


def _rule(rule: BrandRule) -> str:
    return (
        f'<li id="{escape(rule.id)}"><div class="item-heading">'
        f"<h4>{escape(rule.name)}</h4>"
        f'<span class="badge badge-{escape(rule.enforcement)}">'
        f"{escape(rule.enforcement)}</span></div>"
        f'<p class="preserve-lines">{escape(rule.description)}</p>'
        f"{_references(rule.references)}</li>"
    )


def _token(token: BrandToken) -> str:
    value = str(token.value).lower() if isinstance(token.value, bool) else str(token.value)
    return (
        f'<tr id="{escape(token.id)}"><th scope="row">{escape(token.name)}'
        f'<span class="canonical-id">{escape(token.id)}</span></th>'
        f"<td>{escape(token.value_type)}</td><td><code>{escape(value)}</code>"
        f"{_references(token.references)}</td></tr>"
    )


def _example(example: BrandExample) -> str:
    return (
        f'<li class="example example-{escape(example.kind)}" id="{escape(example.id)}">'
        f'<p class="content-kind">{escape(example.kind)}</p>'
        f'<p class="preserve-lines">{escape(example.text)}</p>'
        f"{_references(example.references)}</li>"
    )


def _pattern(pattern: BrandPattern) -> str:
    specifications = "".join(
        f"<div><dt>{escape(item.label)}</dt>"
        f'<dd class="preserve-lines">{escape(item.value)}</dd></div>'
        for item in pattern.specifications
    )
    do_items = "".join(f"<li>{escape(item)}</li>" for item in pattern.do_guidance)
    dont_items = "".join(f"<li>{escape(item)}</li>" for item in pattern.dont_guidance)
    return (
        f'<article class="pattern-card" id="{escape(pattern.id)}">'
        '<div class="item-heading">'
        f"<h4>{escape(pattern.name)}</h4>"
        f'<span class="badge">{escape(pattern.kind.replace("_", " "))}</span></div>'
        f'<p class="pattern-summary preserve-lines">{escape(pattern.summary)}</p>'
        f'<dl class="pattern-specifications">{specifications}</dl>'
        '<div class="guidance-pair"><section><h5>Do</h5>'
        f'<ul class="do-list">{do_items}</ul></section>'
        f'<section><h5>Do not</h5><ul class="dont-list">{dont_items}</ul></section></div>'
        f"{_references(pattern.references)}</article>"
    )


def _section(section: BrandSection, number: int, brand_id: object) -> str:
    parts = [
        f'<section class="bible-section" id="{escape(section.id)}" data-section-id="{escape(section.id)}" data-locked="{"1" if section.locked else "0"}">',
        '<div class="section-heading">',
        f'<p class="section-number">{number:02d}</p>',
        f"<div><h2>{escape(section.title)}</h2>",
        f'<p><span class="badge">{escape(section.status)}</span>',
        f' <span class="lock-state">{"Locked" if section.locked else "Editable"}</span></p>',
        "</div></div>",
    ]
    if section.blocks:
        parts.extend(_block(block) for block in section.blocks)
    if section.rules:
        parts.append('<div class="content-group"><h3>Rules</h3><ul class="rule-list">')
        parts.extend(_rule(rule) for rule in section.rules)
        parts.append("</ul></div>")
    if section.tokens:
        parts.append(
            '<div class="content-group"><h3>Tokens</h3><div class="table-scroll">'
            '<table><thead><tr><th scope="col">Token</th><th scope="col">Type</th>'
            '<th scope="col">Value</th></tr></thead><tbody>'
        )
        parts.extend(_token(token) for token in section.tokens)
        parts.append("</tbody></table></div></div>")
    if section.examples:
        parts.append('<div class="content-group"><h3>Examples</h3><ul class="example-list">')
        parts.extend(_example(example) for example in section.examples)
        parts.append("</ul></div>")
    if section.patterns:
        parts.append(
            '<div class="content-group"><h3>Patterns &amp; playbooks</h3><div class="pattern-list">'
        )
        parts.extend(_pattern(pattern) for pattern in section.patterns)
        parts.append("</div></div>")
    if not (
        section.blocks or section.rules or section.tokens or section.examples or section.patterns
    ):
        if section.locked:
            parts.append(
                '<p class="empty-guidance">No guidance has been added to this section yet.</p>'
            )
        else:
            parts.append(
                '<p class="empty-guidance">No guidance yet. '
                f'<a href="/brand-systems/{brand_id}#{escape(section.id)}">'
                "Add it in the workshop</a> — write a paragraph or generate this section.</p>"
            )
    parts.append("</section>")
    return "".join(parts)


def _asset(asset: AssetRegistration) -> str:
    location = asset.source_path or "Managed copy"
    return (
        f'<tr id="{escape(asset.id)}"><th scope="row">{escape(asset.name)}'
        f'<span class="canonical-id">{escape(asset.id)}</span></th>'
        f"<td>{escape(asset.media_type)}</td><td>{asset.size_bytes:,} bytes</td>"
        f"<td>{escape(asset.storage)}</td><td>{'Required' if asset.required else 'Optional'}</td>"
        f'<td class="asset-location">{escape(location)}<code>{escape(asset.content_hash)}</code></td>'
        "</tr>"
    )


# CSS var <- first token of the matching value_type whose id/name mentions a role.
_COLOR_ROLES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("--accent", ("accent", "primary", "brand", "action", "cta")),
    ("--ink", ("ink", "text", "foreground", "body", "heading")),
    ("--paper", ("paper", "background", "canvas", "base", "page")),
    ("--surface", ("surface", "card", "panel")),
    ("--muted", ("muted", "secondary", "subtle", "subdued")),
    ("--line", ("line", "border", "rule", "divider", "stroke")),
)
_FONT_ROLES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("--font-display", ("display", "heading", "headline", "title", "serif")),
    ("--font-body", ("body", "text", "paragraph", "base", "sans")),
    ("--font-mono", ("mono", "code")),
)
# Trust boundary: token values are model/user-authored and land inside <style>,
# where HTML-escaping can't stop a raw "</style>" breakout. Allow only well-formed
# colors / font stacks (font names carry spaces, commas, quotes — but never < > { } ; ).
_SAFE_COLOR = re.compile(r"^(#[0-9a-fA-F]{3,8}|[a-zA-Z]{3,20}|(rgb|hsl)a?\([0-9.,%\s/deg]+\))$")
_SAFE_FONT = re.compile(r"^[-\w\s,'\".]{1,120}$")


def _map_roles(
    tokens: list[BrandToken],
    roles: tuple[tuple[str, tuple[str, ...]], ...],
) -> dict[str, str]:
    """One token per role and one role per token: greedy in role order, no reuse."""

    overrides: dict[str, str] = {}
    used: set[str] = set()
    for var, keywords in roles:
        for token in tokens:
            if token.id in used:
                continue
            haystack = f"{token.id} {token.name}".lower()
            if any(word in haystack for word in keywords):
                overrides[var] = str(token.value)
                used.add(token.id)
                break
    return overrides


_DEFAULT_INK = (23, 32, 28)  # --ink from brand_bible_styles.py; the surface/line fallback base
_WHITE = (255, 255, 255)


def _parse_hex(value: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", value.strip())
    if not match:
        return None
    digits = match.group(1)
    if len(digits) == 3:
        digits = "".join(c * 2 for c in digits)
    return int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        *(round(x + (y - x) * t) for x, y in zip(a, b, strict=True))
    )


def _font_links(draft: WorkingDraft) -> str:
    """Preconnect + stylesheet for whatever curated Google families the brand uses."""

    families: list[str] = []
    for section in draft.sections:
        for token in section.tokens:
            if token.value_type == "font":
                family = family_of(str(token.value))
                if family and family not in families:
                    families.append(family)
    if not families:
        return ""
    return (
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        f'<link rel="stylesheet" href="{escape(google_css_url(families))}">'
    )


def _current_font(draft: WorkingDraft, keywords: tuple[str, ...]) -> str:
    for section in draft.sections:
        for token in section.tokens:
            if token.value_type == "font" and any(
                word in f"{token.id} {token.name}".lower() for word in keywords
            ):
                return str(token.value)
    return ""


def _font_options(current: str) -> str:
    labels = (("serif", "Serif"), ("sans-serif", "Sans-serif"), ("monospace", "Monospace"))
    out = ['<option value="">Default</option>']
    for generic, label in labels:
        options = "".join(
            f'<option value="{escape(font_stack(name))}"'
            f"{' selected' if font_stack(name) == current else ''}>{escape(name)}</option>"
            for name, family_generic in GOOGLE_FONTS
            if family_generic == generic
        )
        out.append(f'<optgroup label="{label}">{options}</optgroup>')
    return "".join(out)


def _font_picker(draft: WorkingDraft) -> str:
    """Edit-mode dropdowns that write display/body font tokens (revealed by the client)."""

    display = _font_options(_current_font(draft, ("display", "heading", "headline", "title")))
    body = _font_options(_current_font(draft, ("body", "text", "paragraph", "base")))
    return (
        '<div class="font-picker" id="font-picker" hidden>'
        '<label>Display font <select data-var="--font-display" '
        f'data-token-id="token.font.display" data-token-name="Display font">{display}</select></label>'
        '<label>Body font <select data-var="--font-body" '
        f'data-token-id="token.font.body" data-token-name="Body font">{body}</select></label>'
        "</div>"
    )


def _brand_theme(draft: WorkingDraft) -> str:
    """Override the fixed theme with the brand's own color/font tokens where defined."""

    tokens = [token for section in draft.sections for token in section.tokens]
    colors = [t for t in tokens if t.value_type == "color" and _SAFE_COLOR.match(str(t.value))]
    fonts = [t for t in tokens if t.value_type == "font" and _SAFE_FONT.match(str(t.value))]
    overrides = _map_roles(colors, _COLOR_ROLES) | _map_roles(fonts, _FONT_ROLES)
    if not overrides:
        return ""
    # Derive the neutral card/border roles from the brand's page color so the whole
    # surface shifts, not only the three slots a brand usually names. Only when the
    # brand redefined --paper (else the fixed theme's neutrals already agree).
    paper = _parse_hex(overrides["--paper"]) if "--paper" in overrides else None
    if paper:
        ink = _parse_hex(overrides["--ink"]) if "--ink" in overrides else _DEFAULT_INK
        overrides.setdefault("--surface", _mix(paper, _WHITE, 0.5))
        overrides.setdefault("--line", _mix(paper, ink or _DEFAULT_INK, 0.30))
    body = ";".join(f"{var}:{value}" for var, value in overrides.items())
    # ponytail: greedy keyword heuristic on token id/name; a brand color with no
    # matching role word (e.g. a 2nd "accent" pop) simply has no slot in this
    # 6-neutral+1-accent theme. Add an explicit token->role picker if that bites.
    return f"<style>:root{{{body}}}</style>"


def render_brand_bible(draft: WorkingDraft, *, for_pdf: bool = False) -> str:
    """Render every canonical draft content type without trusting stored text as markup."""

    complete = sum(section.status in {"reviewed", "approved"} for section in draft.sections)
    context = (
        f'<p class="brand-context preserve-lines">{escape(draft.brand_context)}</p>'
        if draft.brand_context
        else '<p class="brand-context empty-guidance">No additional brand context supplied.</p>'
    )
    navigation = "".join(
        f'<li><a href="#{escape(section.id)}"><span>{index:02d}</span> '
        f"{escape(section.title)}</a></li>"
        for index, section in enumerate(draft.sections, start=1)
    )
    sections = "".join(
        _section(section, index, draft.brand_id)
        for index, section in enumerate(draft.sections, start=1)
    )
    if draft.assets:
        assets = (
            '<section class="bible-section" id="assets"><div class="section-heading">'
            '<p class="section-number">A</p><div><h2>Asset registry</h2>'
            "<p>Integrity-bound production files and source locations.</p></div></div>"
            '<div class="table-scroll"><table><thead><tr><th scope="col">Asset</th>'
            '<th scope="col">Media type</th><th scope="col">Size</th>'
            '<th scope="col">Storage</th><th scope="col">Use</th>'
            '<th scope="col">Location and SHA-256</th></tr></thead><tbody>'
            f"{''.join(_asset(asset) for asset in draft.assets)}"
            "</tbody></table></div></section>"
        )
    else:
        assets = (
            '<section class="bible-section" id="assets"><div class="section-heading">'
            '<p class="section-number">A</p><div><h2>Asset registry</h2></div></div>'
            '<p class="empty-guidance">No production assets yet.</p>'
            "</section>"
        )

    css_block = f"<style>{BRAND_BIBLE_CSS}</style>"
    if for_pdf:
        pdf_style = (
            "<style>"
            "@page { size: letter; margin: 0.7in 0.7in 0.75in; @bottom-right { content: 'Page ' counter(page) ' of ' counter(pages); color: #526058; font-size: 9pt; } }"
            "header, .cover-actions, .edit-status, .font-picker, script { display: none !important; }"
            "</style>"
        )
        return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">{css_block}{pdf_style}{_font_links(draft)}{_brand_theme(draft)}<title>{escape(draft.brand_name)} — complete brand bible</title></head><body data-page="bible" data-brand-id="{draft.brand_id}"><main id="main-content"><section class="bible-cover" aria-labelledby="bible-title"><p class="eyebrow">Complete living brand bible</p><h1 id="bible-title">{escape(draft.brand_name)}</h1><p class="cover-deck">A single source of truth for how the brand thinks, speaks, looks, behaves, and stays coherent.</p><dl class="brand-meta"><div><dt>Owner</dt><dd>{escape(draft.owner.display_name)}</dd></div><div><dt>Draft revision</dt><dd>{draft.revision}</dd></div><div><dt>System status</dt><dd>{escape(draft.status)}</dd></div><div><dt>Reviewed sections</dt><dd>{complete} of {len(draft.sections)}</dd></div><div><dt>Schema</dt><dd>{escape(draft.schema_version)}</dd></div></dl></section><section class="context-panel" aria-labelledby="context-title"><p class="eyebrow">Founding context</p><h2 id="context-title">What this brand needs to hold</h2>{context}</section><div class="bible-layout"><nav class="bible-nav" aria-label="Brand bible contents"><p class="nav-title">Contents</p><ol>{navigation}<li><a href="#assets"><span>A</span> Asset registry</a></li></ol></nav><article class="bible-content">{sections}{assets}</article></div></main><footer><p>{escape(draft.brand_name)} · Living draft revision {draft.revision} · Canonical ID {draft.brand_id}</p></footer></body></html>'''

    export_menu = (
        f'<div class="export-dropdown" style="display:inline-block;position:relative;">'
        f'<button id="export-menu-btn" type="button">Export ▾</button>'
        f'<div id="export-menu" hidden style="position:absolute;right:0;top:100%;background:var(--surface,#fff);border:1px solid var(--line,#ccc);padding:0.5rem;z-index:100;min-width:180px;box-shadow:0 4px 12px rgba(0,0,0,0.15);border-radius:4px;">'
        f'<a class="action-link" style="display:block;margin:0.25rem 0;" href="/api/brand-systems/{draft.brand_id}/draft-exports/pdf" download="{escape(draft.brand_name)}-bible.pdf">📄 PDF Document</a>'
        f'<a class="action-link" style="display:block;margin:0.25rem 0;" href="/api/brand-systems/{draft.brand_id}/draft-exports/markdown" download="{escape(draft.brand_name)}-bible.md">📝 Markdown</a>'
        f'<a class="action-link" style="display:block;margin:0.25rem 0;" href="/api/brand-systems/{draft.brand_id}/draft-exports/tokens-css" download="tokens.css">🎨 CSS Custom Properties</a>'
        f'<a class="action-link" style="display:block;margin:0.25rem 0;" href="/api/brand-systems/{draft.brand_id}/draft-exports/tokens-json" download="tokens.json">🔣 JSON Tokens</a>'
        f'<a class="action-link" style="display:block;margin:0.25rem 0;" href="/api/brand-systems/{draft.brand_id}/draft-exports/tailwind" download="tailwind.config.js">💨 Tailwind Config</a>'
        f'<a class="action-link" style="display:block;margin:0.25rem 0;" href="/api/brand-systems/{draft.brand_id}/draft-exports/kit" download="{escape(draft.brand_name)}-brand-kit.zip">📦 Brand Kit (.zip)</a>'
        f"</div></div>"
    )

    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/brand-bible.css">{css_block}{_font_links(draft)}{_brand_theme(draft)}<script src="/assets/workshop.js" defer></script><title>{escape(draft.brand_name)} — complete brand bible</title></head><body data-page="bible" data-brand-id="{draft.brand_id}">{HEADER}<main id="main-content"><section class="bible-cover" aria-labelledby="bible-title"><p class="eyebrow">Complete living brand bible</p><h1 id="bible-title">{escape(draft.brand_name)}</h1><p class="cover-deck">A single source of truth for how the brand thinks, speaks, looks, behaves, and stays coherent.</p><div class="cover-actions"><a class="action-link" href="/brand-systems/{draft.brand_id}">Edit workspace</a><button id="edit-bible" type="button" aria-pressed="false">Edit in place</button><button id="toggle-bible-theme" type="button" aria-pressed="false">Preview dark mode</button><button id="print-bible" type="button">Print or save PDF</button>{export_menu}</div><p id="edit-status" class="edit-status" role="status" aria-live="polite"></p>{_font_picker(draft)}<dl class="brand-meta"><div><dt>Owner</dt><dd>{escape(draft.owner.display_name)}</dd></div><div><dt>Draft revision</dt><dd>{draft.revision}</dd></div><div><dt>System status</dt><dd>{escape(draft.status)}</dd></div><div><dt>Reviewed sections</dt><dd>{complete} of {len(draft.sections)}</dd></div><div><dt>Schema</dt><dd>{escape(draft.schema_version)}</dd></div></dl></section><section class="context-panel" aria-labelledby="context-title"><p class="eyebrow">Founding context</p><h2 id="context-title">What this brand needs to hold</h2>{context}</section><div class="bible-layout"><nav class="bible-nav" aria-label="Brand bible contents"><p class="nav-title">Contents</p><ol>{navigation}<li><a href="#assets"><span>A</span> Asset registry</a></li></ol></nav><article class="bible-content">{sections}{assets}</article></div></main><footer><p>{escape(draft.brand_name)} · Living draft revision {draft.revision} · Canonical ID {draft.brand_id}</p></footer></body></html>'''
