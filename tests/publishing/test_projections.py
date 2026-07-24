from brand_maker.publishing.projections import project
from brand_maker.publishing.web import render_projection
from tests.publishing.helpers import rendered_version


def test_four_views_share_exact_source_identity_without_mutating_snapshot() -> None:
    rendered = rendered_version()
    original = rendered.model_dump_json()

    creator = project(rendered, content_hash="a" * 64, audience="creator")
    designer = project(rendered, content_hash="a" * 64, audience="designer")
    business = project(rendered, content_hash="a" * 64, audience="business")
    agency = project(rendered, content_hash="a" * 64, audience="agency")

    assert [item.id for item in creator.sections] == ["section.strategy"]
    assert [item.id for item in designer.sections] == ["section.strategy", "section.logo"]
    assert [item.id for item in business.sections] == ["section.strategy"]
    assert [item.id for item in agency.sections] == ["section.strategy", "section.logo"]
    assert rendered.model_dump_json() == original


def test_projection_html_escapes_canonical_text_and_identifies_revision() -> None:
    view = project(rendered_version(), content_hash="a" * 64, audience="agency")
    page = render_projection(view)

    assert "Version 1.0.0, amendment 0" in page
    assert "purpose &amp; durable" in page
