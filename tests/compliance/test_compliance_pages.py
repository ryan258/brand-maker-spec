from pathlib import Path

from fastapi.testclient import TestClient

from brand_maker.app import create_app
from brand_maker.config import Settings
from brand_maker.models import BrandResponse


class UnusedPipeline:
    async def build(self, brand_name: str, *, brand_context: str | None = None) -> BrandResponse:
        raise AssertionError("legacy generation must not run")


def test_compliance_page_and_deterministic_api_are_accessible_and_labeled(
    tmp_path: Path,
) -> None:
    settings = Settings(
        _env_file=None,
        openrouter_api_key="test-key",
        database_path=tmp_path / "brands.db",
    )
    with TestClient(create_app(settings=settings, pipeline=UnusedPipeline())) as api:
        page = api.get("/compliance")
        script = api.get("/assets/compliance.js")
        favicon = api.get("/favicon.svg")
        empty_rules_result = api.post(
            "/api/compliance/artifact-evaluations",
            json={
                "artifact": {"name": "Empty Card", "content": "An unconstrained launch card"},
                "brand_version": "1.0.0",
                "amendment_revision": 0,
                "rules": [],
            },
        )
        result = api.post(
            "/api/compliance/artifact-evaluations",
            json={
                "artifact": {"name": "Card", "content": "A long launch card"},
                "brand_version": "1.0.0",
                "amendment_revision": 0,
                "rules": [
                    {
                        "id": "rule.copy.maximum-length",
                        "kind": "maximum_length",
                        "parameter": "5",
                        "message": "Shorten the copy.",
                    }
                ],
            },
        )
        exception = api.post(
            "/api/compliance/exceptions",
            json={
                "rule_id": "rule.copy.maximum-length",
                "artifact_id": "d795ebf9-8f54-44a2-85cd-e73faacb7008",
                "rationale": "Approved launch exception.",
                "expires_at": "2027-07-23T12:00:00Z",
            },
        )
        fetched_exception = api.get(f"/api/compliance/exceptions/{exception.json()['id']}")
        untrusted_markup = api.post(
            "/api/compliance/artifact-evaluations",
            json={
                "artifact": {
                    "name": "HTML sample",
                    "content": '<img src=x onerror="alert(1)">',
                },
                "brand_version": "1.0.0",
                "rules": [
                    {
                        "id": "rule.review.html",
                        "kind": "unsupported",
                        "parameter": "HTML rendering",
                        "message": "Inspect safely.",
                    }
                ],
            },
        )
        evidence = api.post(
            "/api/compliance/evidence",
            json={
                "artifact_id": "d795ebf9-8f54-44a2-85cd-e73faacb7008",
                "evidence": {
                    "level": "owner",
                    "claim": "The copy uses the intended voice.",
                    "verifier_name": "Ryan",
                },
            },
        )

    assert page.status_code == 200
    assert favicon.headers["cache-control"] == "no-cache"
    assert favicon.headers["x-content-type-options"] == "nosniff"
    assert 'role="status"' in page.text
    assert "Exceptions and evidence" in page.text
    assert 'id="brand-id"' in page.text
    assert "/compliance-rules`" in script.text
    assert 'parameter:"280"' not in script.text
    assert empty_rules_result.status_code == 201
    assert empty_rules_result.json()["findings"] == []
    assert empty_rules_result.json()["rule_ids"] == []
    assert "nothing was checked" in script.text
    assert result.status_code == 201
    assert result.json()["findings"][0]["evaluation_type"] == "deterministic"
    assert result.json()["findings"][0]["status"] == "fail"
    assert exception.status_code == 201
    assert fetched_exception.json() == exception.json()
    assert untrusted_markup.status_code == 201
    assert evidence.status_code == 201
    assert evidence.json()["record"]["level"] == "owner"
