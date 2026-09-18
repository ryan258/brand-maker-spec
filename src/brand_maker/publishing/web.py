"""Escaped HTML rendering for audience projections."""

from html import escape

from brand_maker.brand_system.models import BrandSection
from brand_maker.publishing.patterns import render_pattern_html
from brand_maker.publishing.projections import AudienceProjection


def section_detail_html(section: BrandSection) -> list[str]:
    """Every audience needs the enforceable content, not only the narrative."""

    parts: list[str] = []
    if section.rules:
        parts.append("<h3>Rules</h3><ul>")
        parts.extend(
            f"<li><strong>{escape(rule.name)}</strong> ({escape(rule.enforcement)}): "
            f"{escape(rule.description)}</li>"
            for rule in section.rules
        )
        parts.append("</ul>")
    if section.tokens:
        parts.append("<h3>Tokens</h3><ul>")
        parts.extend(
            f"<li><strong>{escape(token.name)}</strong> "
            f"(<code>{escape(token.id)}</code>, {escape(token.value_type)}): "
            f"{escape(str(token.value))}</li>"
            for token in section.tokens
        )
        parts.append("</ul>")
    if section.examples:
        parts.append("<h3>Examples</h3><ul>")
        parts.extend(
            f"<li><strong>{escape(example.kind)}:</strong> {escape(example.text)}</li>"
            for example in section.examples
        )
        parts.append("</ul>")
    return parts


def render_projection(view: AudienceProjection) -> str:
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        f"<title>{escape(view.brand_name)} - {escape(view.audience)} guide</title></head><body>",
        f"<main><h1>{escape(view.brand_name)}</h1>",
        f"<p>Version {escape(view.version)}, amendment {view.amendment_revision}</p>",
    ]
    for section in view.sections:
        parts.append(f'<section id="{escape(section.id)}"><h2>{escape(section.title)}</h2>')
        parts.extend(f"<p>{escape(block.text)}</p>" for block in section.blocks)
        parts.extend(section_detail_html(section))
        if section.patterns:
            parts.append("<h3>Patterns and playbooks</h3>")
            parts.extend(render_pattern_html(pattern) for pattern in section.patterns)
        parts.append("</section>")
    if view.assets:
        parts.append('<section id="assets"><h2>Production assets</h2><ul>')
        parts.extend(
            f"<li><strong>{escape(asset.name)}</strong> ({escape(asset.media_type)}, "
            f"{asset.size_bytes} bytes, "
            f"{'required' if asset.required else 'optional'}) — "
            f"<code>{escape(asset.content_hash)}</code></li>"
            for asset in view.assets
        )
        parts.append("</ul></section>")
    parts.append("</main></body></html>")
    return "".join(parts)
