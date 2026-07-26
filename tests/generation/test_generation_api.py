import asyncio
import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from brand_maker.app import create_app
from brand_maker.config import Settings
from brand_maker.models import BrandResponse


class UnusedPipeline:
    async def build(self, brand_name: str, *, brand_context: str | None = None) -> BrandResponse:
        raise AssertionError("legacy generation must not be called")


class SectionCompleter:
    async def complete(self, *, messages, model, temperature, max_tokens) -> str:
        request = json.loads(messages[1]["content"])
        slug = request["section_id"].removeprefix("section.")
        return json.dumps(
            {
                "prompt_version": request["prompt_version"],
                "section_id": request["section_id"],
                "rationale": "A deterministic test section.",
                "section": {
                    "id": request["section_id"],
                    "title": request["section_title"],
                    "status": "draft",
                    "locked": False,
                    "blocks": [
                        {
                            "id": f"block.{slug}.overview",
                            "type": "paragraph",
                            "text": "A specific strategic overview.",
                            "references": [],
                        },
                        {
                            "id": f"block.{slug}.application",
                            "type": "paragraph",
                            "text": "Practical application guidance.",
                            "references": [],
                        },
                    ],
                    "rules": [
                        {
                            "id": f"rule.{slug}.primary",
                            "name": "Primary rule",
                            "description": "Apply this decision consistently.",
                            "enforcement": "warning",
                            "references": [],
                        }
                    ],
                    "tokens": (
                        [
                            {
                                "id": f"token.{slug}.base",
                                "name": "Base value",
                                "value_type": "string",
                                "value": "brand-default",
                                "references": [],
                            }
                        ]
                        if request["content_requirements"]["tokens_required"]
                        else []
                    ),
                    "examples": [
                        {
                            "id": f"example.{slug}.do",
                            "kind": "do",
                            "text": "Follow the guidance in a concrete way.",
                            "references": [],
                        },
                        {
                            "id": f"example.{slug}.dont",
                            "kind": "dont",
                            "text": "Do not contradict the guidance.",
                            "references": [],
                        },
                    ],
                    "patterns": [
                        {
                            "id": f"pattern.{slug}.{kind}",
                            "name": kind.replace("_", " ").title(),
                            "kind": kind,
                            "summary": "A concrete application pattern.",
                            "specifications": [
                                {
                                    "label": "Default",
                                    "value": "Apply the documented specification.",
                                }
                            ],
                            "do_guidance": ["Use this approved pattern."],
                            "dont_guidance": ["Do not invent an unsupported variant."],
                            "references": [],
                        }
                        for kind in request["content_requirements"]["required_pattern_kinds"]
                    ],
                },
            }
        )


class SlowSectionCompleter(SectionCompleter):
    async def complete(self, *, messages, model, temperature, max_tokens) -> str:
        await asyncio.sleep(0.2)
        return await super().complete(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )


def client(tmp_path: Path) -> TestClient:
    settings = Settings(
        _env_file=None,
        openrouter_api_key="test-key",
        database_path=tmp_path / "brands.db",
    )
    return TestClient(
        create_app(
            settings=settings,
            pipeline=UnusedPipeline(),
            generation_completer=SectionCompleter(),
        )
    )


def slow_client(tmp_path: Path) -> TestClient:
    settings = Settings(
        _env_file=None,
        openrouter_api_key="test-key",
        database_path=tmp_path / "brands.db",
    )
    return TestClient(
        create_app(
            settings=settings,
            pipeline=UnusedPipeline(),
            generation_completer=SlowSectionCompleter(),
        )
    )


def test_section_generation_run_can_start_resume_and_be_read(tmp_path: Path) -> None:
    with client(tmp_path) as api:
        draft = api.post(
            "/api/brand-systems",
            json={"brand_name": "Northstar", "owner_name": "Ryan"},
        ).json()
        started = api.post(
            f"/api/brand-systems/{draft['brand_id']}/generation-runs",
            json={"target_section_id": "section.messaging"},
        )
        run_id = started.json()["id"]
        accepted = api.post(f"/api/generation-runs/{run_id}/resume")
        for _ in range(100):
            fetched = api.get(f"/api/generation-runs/{run_id}")
            if fetched.json()["status"] == "completed":
                break
            time.sleep(0.01)
        updated = api.get(f"/api/brand-systems/{draft['brand_id']}").json()

    assert started.status_code == 201
    assert started.json()["status"] == "pending"
    assert accepted.status_code == 202
    assert accepted.json()["status"] in {"pending", "running"}
    assert fetched.json()["status"] == "completed"
    assert updated["revision"] == 3  # strategy prerequisite plus messaging


def test_second_resume_does_not_queue_another_task_for_the_same_run(tmp_path: Path) -> None:
    with slow_client(tmp_path) as api:
        draft = api.post(
            "/api/brand-systems",
            json={"brand_name": "Northstar", "owner_name": "Ryan"},
        ).json()
        run = api.post(f"/api/brand-systems/{draft['brand_id']}/generation-runs", json={}).json()

        first = api.post(f"/api/generation-runs/{run['id']}/resume")
        second = api.post(f"/api/generation-runs/{run['id']}/resume")

        assert first.status_code == second.status_code == 202
        assert len(api.app.state.generation_tasks) == 1


def test_generation_controls_are_idempotent_and_errors_are_bounded(tmp_path: Path) -> None:
    with client(tmp_path) as api:
        draft = api.post(
            "/api/brand-systems",
            json={"brand_name": "Northstar", "owner_name": "Ryan"},
        ).json()
        missing_workspace = api.post(
            "/api/brand-systems/00000000-0000-0000-0000-000000000000/generation-runs",
            json={},
        )
        invalid_section = api.post(
            f"/api/brand-systems/{draft['brand_id']}/generation-runs",
            json={"target_section_id": "section.unknown"},
        )
        run = api.post(f"/api/brand-systems/{draft['brand_id']}/generation-runs", json={}).json()
        paused = api.post(f"/api/generation-runs/{run['id']}/pause")
        paused_again = api.post(f"/api/generation-runs/{run['id']}/pause")
        cancelled = api.post(f"/api/generation-runs/{run['id']}/cancel")
        cancelled_again = api.post(f"/api/generation-runs/{run['id']}/cancel")
        missing_run = api.get("/api/generation-runs/00000000-0000-0000-0000-000000000000")

    assert missing_workspace.status_code == 404
    assert invalid_section.status_code == 422
    assert paused.json()["status"] == paused_again.json()["status"] == "paused"
    assert cancelled.json()["status"] == cancelled_again.json()["status"] == "cancelled"
    assert missing_run.status_code == 404
