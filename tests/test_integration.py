import json

import httpx
import pytest
from fastapi.testclient import TestClient

from brand_maker.app import create_app
from brand_maker.config import Settings
from brand_maker.openrouter import OpenRouterClient
from brand_maker.pipeline import BrandPipeline


@pytest.mark.asyncio
async def test_brand_request_runs_end_to_end_through_provider_boundary() -> None:
    kit = {
        "brand_name": "Floogle",
        "parody_target": "Google",
        "tagline": "Search less. Guess more.",
        "description": "A search engine that confidently indexes vibes.",
        "brand_voice": "Cheerful, certain, playful, and wrong on purpose.",
        "personality": ["Playful", "Chaotic", "Helpful"],
        "color_palette": {
            "primary": "#4285F4",
            "secondary": "#EA4335",
            "accent": "#FBBC05",
            "background": "#FFFFFF",
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": json.dumps(kit)},
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        generator = OpenRouterClient(http=http, api_key="test-key")
        pipeline = BrandPipeline(
            generator=generator,
            primary_model="test/primary",
            fallback_model="test/fallback",
        )
        settings = Settings(_env_file=None, openrouter_api_key="test-key")
        with TestClient(create_app(settings=settings, pipeline=pipeline)) as client:
            response = client.post("/brand", json={"brand_name": "Floogle"})

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["kit"] == kit
