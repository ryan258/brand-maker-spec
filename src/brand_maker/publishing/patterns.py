"""Shared escaped HTML projection for canonical patterns and playbooks."""

from html import escape

from brand_maker.brand_system.models import BrandPattern


def render_pattern_html(pattern: BrandPattern) -> str:
    specifications = "".join(
        f"<div><dt>{escape(item.label)}</dt><dd>{escape(item.value)}</dd></div>"
        for item in pattern.specifications
    )
    do_items = "".join(f"<li>{escape(item)}</li>" for item in pattern.do_guidance)
    dont_items = "".join(f"<li>{escape(item)}</li>" for item in pattern.dont_guidance)
    return (
        f'<article class="brand-pattern" id="{escape(pattern.id)}">'
        f"<h3>{escape(pattern.name)}</h3>"
        f'<p class="pattern-kind">{escape(pattern.kind.replace("_", " "))}</p>'
        f"<p>{escape(pattern.summary)}</p>"
        f"<dl>{specifications}</dl>"
        f"<h4>Do</h4><ul>{do_items}</ul>"
        f"<h4>Do not</h4><ul>{dont_items}</ul>"
        "</article>"
    )
