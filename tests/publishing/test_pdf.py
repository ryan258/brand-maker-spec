from io import BytesIO

import pdfplumber
from pypdf import PdfReader

from brand_maker.publishing.pdf import render_pdf
from brand_maker.publishing.projections import project
from tests.publishing.helpers import rendered_version


def test_pdf_is_searchable_tagged_bookmarked_and_source_bound() -> None:
    view = project(rendered_version(), content_hash="a" * 64, audience="agency")
    payload = render_pdf(view)
    reader = PdfReader(BytesIO(payload))

    with pdfplumber.open(BytesIO(payload)) as document:
        text = "\n".join(page.extract_text() or "" for page in document.pages)

    assert payload.startswith(b"%PDF-")
    assert "Northstar" in text
    assert "Version 1.0.0 - amendment 0" in text
    assert reader.outline
    assert "/StructTreeRoot" in reader.trailer["/Root"]
    assert reader.metadata is not None
    assert reader.metadata.title == "Northstar brand guide"


def test_pdf_output_is_reproducible_for_one_projection() -> None:
    view = project(rendered_version(), content_hash="a" * 64, audience="agency")

    assert render_pdf(view) == render_pdf(view)
