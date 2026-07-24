"""Escaped HTML rendering for audience projections."""

from html import escape

from brand_maker.publishing.patterns import render_pattern_html
from brand_maker.publishing.projections import AudienceProjection


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
        if section.patterns:
            parts.append("<h3>Patterns and playbooks</h3>")
            parts.extend(render_pattern_html(pattern) for pattern in section.patterns)
        parts.append("</section>")
    parts.append("</main></body></html>")
    return "".join(parts)
