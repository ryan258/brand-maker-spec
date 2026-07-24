import json

from brand_maker.publishing.developer_exports import export_developer_package
from tests.publishing.helpers import published_version


def test_developer_exports_are_deterministic_and_source_bound() -> None:
    published = published_version()
    package = export_developer_package(published)

    assert package == export_developer_package(published)
    assert "brand-version: 1.0.0" in package["tokens.css"]
    assert json.loads(package["tokens.json"])["content_hash"] == "a" * 64
    assert json.loads(package["rules.json"])["version"] == "1.0.0"
    assert json.loads(package["voice-context.json"])["version"] == "1.0.0"
    assert json.loads(package["patterns.json"])["patterns"][0]["kind"] == "say_never_say"
    assert json.loads(package["change-manifest.json"])["change_summary"] == "Initial guide."
