import pytest

from brand_maker.json_extract import NoJSONObject, extract_json_object


def test_extracts_exact_json_object() -> None:
    raw = '{"brand_name":"Floogle","description":"A {surprising} brand"}'

    assert extract_json_object(raw) == raw


def test_extracts_json_from_markdown_fence() -> None:
    raw = 'Here is the kit:\n```json\n{"brand_name":"Floogle"}\n```'

    assert extract_json_object(raw) == '{"brand_name":"Floogle"}'


def test_extracts_balanced_object_from_surrounding_prose() -> None:
    raw = 'Result follows: {"nested":{"value":"}"},"ok":true} Thanks.'

    assert extract_json_object(raw) == '{"nested":{"value":"}"},"ok":true}'


def test_preserves_malformed_json_like_object_for_schema_validation() -> None:
    raw = "Model output: {brand_name: 'Floogle'}"

    assert extract_json_object(raw) == "{brand_name: 'Floogle'}"


@pytest.mark.parametrize("raw", ["", "I cannot help with that.", "```json\nno object\n```"])
def test_raises_when_no_json_object_is_present(raw: str) -> None:
    with pytest.raises(NoJSONObject):
        extract_json_object(raw)
