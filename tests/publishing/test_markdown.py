from brand_maker.publishing.markdown import export_markdown, import_markdown
from tests.publishing.helpers import published_version


def test_markdown_is_deterministic_and_round_trips_canonical_draft() -> None:
    draft = published_version().snapshot
    first = export_markdown(draft, version="1.0.0", amendment_revision=0)

    assert first == export_markdown(draft, version="1.0.0", amendment_revision=0)
    assert import_markdown(first) == draft
    assert "Source version: 1.0.0; amendment revision: 0" in first


def test_markdown_import_requires_constrained_canonical_payload() -> None:
    try:
        import_markdown("# Not a canonical archive\n<script>alert(1)</script>")
    except ValueError as error:
        assert str(error) == "canonical JSON block is missing"
    else:
        raise AssertionError("unsafe free-form Markdown must not become canonical state")
