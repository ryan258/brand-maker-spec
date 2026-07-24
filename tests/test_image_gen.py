import base64
import json
from uuid import UUID

import httpx
import pytest

from brand_maker.brand_system.models import BrandSection, BrandToken, LocalOwner, WorkingDraft
from brand_maker.image_gen import (
    ModelUnavailable,
    OpenRouterImageClient,
    ProviderError,
    logo_prompt,
)

_PNG = b"\x89PNG\r\n\x1a\nlogo"


@pytest.mark.asyncio
async def test_generate_decodes_base64_image_and_sends_bearer_key() -> None:
    observed: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        observed["auth"] = request.headers["authorization"]
        observed["body"] = json.loads(request.content)
        b64 = base64.b64encode(_PNG).decode()
        payload = {"data": [{"b64_json": b64, "media_type": "image/png"}]}
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = OpenRouterImageClient(http=http, api_key="secret")
        image_bytes, media_type = await client.generate(prompt="a mark", model="img/model")

    assert image_bytes == _PNG
    assert media_type == "image/png"
    assert observed["auth"] == "Bearer secret"
    assert str(observed["body"]).find("img/model") != -1


@pytest.mark.asyncio
async def test_generate_maps_rate_limit_to_model_unavailable() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "rate limit"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = OpenRouterImageClient(http=http, api_key="secret")
        with pytest.raises(ModelUnavailable):
            await client.generate(prompt="x", model="img/model")


@pytest.mark.asyncio
async def test_generate_rejects_undecodable_image_data() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        bad = {"data": [{"b64_json": "not*base64", "media_type": "image/png"}]}
        return httpx.Response(200, json=bad)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = OpenRouterImageClient(http=http, api_key="secret")
        with pytest.raises(ProviderError):
            await client.generate(prompt="x", model="img/model")


@pytest.mark.asyncio
async def test_generate_sends_reference_image_as_bounded_data_url() -> None:
    observed: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        observed.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={"data": [{"b64_json": base64.b64encode(_PNG).decode()}]},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = OpenRouterImageClient(http=http, api_key="secret")
        await client.generate(
            prompt="make an icon-only variant",
            model="img/model",
            reference=(_PNG, "image/png"),
            aspect_ratio="1:1",
            background="transparent",
        )

    reference = observed["input_references"][0]  # type: ignore[index]
    assert reference["type"] == "image_url"  # type: ignore[index]
    assert str(reference["image_url"]["url"]).startswith("data:image/png;base64,")  # type: ignore[index]
    assert observed["aspect_ratio"] == "1:1"
    assert observed["background"] == "transparent"


def test_logo_prompt_uses_brand_name_context_and_color_tokens() -> None:
    draft = WorkingDraft(
        brand_id=UUID("ea7d54dd-61f4-430e-a20e-eced89cddb37"),
        brand_name="TTipsy Hog",
        brand_context="Arkansas bar & grill.",
        owner=LocalOwner(display_name="Ryan"),
        revision=1,
        sections=[
            BrandSection(
                id="section.color",
                title="Color",
                status="draft",
                tokens=[
                    BrandToken(id="token.color.p", name="P", value_type="color", value="#997333"),
                    BrandToken(id="token.font.b", name="B", value_type="font", value="Roboto"),
                ],
            )
        ],
    )

    prompt = logo_prompt(draft, "line mark")

    assert "TTipsy Hog" in prompt
    assert "Arkansas bar & grill." in prompt
    assert "#997333" in prompt  # color token included
    assert "Roboto" not in prompt  # font tokens are not colors
    assert "line mark" in prompt
