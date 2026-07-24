"""Print-ready PDF/UA rendering from canonical audience projections."""

# The embedded print stylesheet stays readable as CSS rather than Python fragments.
# ruff: noqa: E501

import os
from html import escape
from pathlib import Path

from brand_maker.publishing.projections import AudienceProjection


def projection_html(view: AudienceProjection) -> str:
    sections: list[str] = []
    for section in view.sections:
        blocks = "".join(f"<p>{escape(block.text)}</p>" for block in section.blocks)
        rules = "".join(
            f"<li><strong>{escape(rule.name)}:</strong> {escape(rule.description)}</li>"
            for rule in section.rules
        )
        rule_list = f"<h3>Rules</h3><ul>{rules}</ul>" if rules else ""
        sections.append(
            f'<section id="{escape(section.id)}"><h2>{escape(section.title)}</h2>'
            f"{blocks}{rule_list}</section>"
        )
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{escape(view.brand_name)} brand guide</title><meta name="author" content="Brand System Maker"><style>
@page {{ size: letter; margin: 0.7in 0.7in 0.75in; @bottom-right {{ content: "Page " counter(page) " of " counter(pages); color: #44546a; font-size: 9pt; }} }}
html {{ font: 10.5pt/1.55 system-ui, sans-serif; color: #172033; }}
body {{ margin: 0; }} header {{ border-bottom: 3px solid #3157d5; margin-bottom: 24pt; padding-bottom: 16pt; }}
h1 {{ color: #172033; font-size: 28pt; margin: 0 0 8pt; }} h2 {{ color: #2448b8; font-size: 18pt; margin: 22pt 0 8pt; break-after: avoid; }}
h3 {{ font-size: 12pt; break-after: avoid; }} p, li {{ orphans: 3; widows: 3; }} section {{ break-inside: auto; }}
.source {{ color: #44546a; }} strong {{ color: #172033; }}
</style></head><body><main><header><h1>{escape(view.brand_name)}</h1><p>{escape(view.audience.title())} brand guide</p><p class="source">Version {escape(view.version)} - amendment {view.amendment_revision}<br>Content hash {escape(view.source_content_hash)}</p></header>{''.join(sections)}</main></body></html>'''


def render_pdf(view: AudienceProjection) -> bytes:
    # Homebrew installs the native macOS libraries here; setting the fallback before
    # the lazy import keeps the wheel portable on Linux and self-contained on macOS.
    homebrew_lib = Path("/opt/homebrew/lib")
    if homebrew_lib.exists():
        current = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
        paths = [item for item in current.split(":") if item]
        if str(homebrew_lib) not in paths:
            os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = ":".join(
                [str(homebrew_lib), *paths]
            )
    from weasyprint import HTML  # type: ignore[import-untyped]

    output = HTML(string=projection_html(view)).write_pdf(
        pdf_variant="pdf/ua-1",
        pdf_tags=True,
        pdf_identifier=view.source_content_hash,
        full_fonts=True,
    )
    if not isinstance(output, bytes):
        raise RuntimeError("PDF renderer did not return bytes")
    return output
