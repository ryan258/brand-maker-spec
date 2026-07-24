"""OpenRouter image-generation adapter for brand logo assets."""

import base64
import binascii
import json
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from brand_maker.brand_system.models import WorkingDraft
from brand_maker.openrouter import ModelUnavailable, ProviderError, ProviderRefusal

OPENROUTER_IMAGES_URL = "https://openrouter.ai/api/v1/images"
# Base64 inflates ~4/3; cap the JSON envelope so a runaway response can't exhaust memory.
# A ~18 MB image stays under the AssetStore's 25 MB managed-copy limit downstream.
MAX_RESPONSE_BYTES = 26_000_000


class _Image(BaseModel):
    model_config = ConfigDict(extra="ignore")

    b64_json: str
    media_type: str | None = None


class _ImagesResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    data: list[_Image] = Field(..., min_length=1)


class OpenRouterImageClient:
    """Call OpenRouter's image API and return validated image bytes."""

    def __init__(self, *, http: httpx.AsyncClient, api_key: str) -> None:
        self._http = http
        self._api_key = api_key

    async def generate(self, *, prompt: str, model: str) -> tuple[bytes, str]:
        """Return (image_bytes, media_type) for one generated image."""

        payload = {"model": model, "prompt": prompt, "output_format": "png"}
        try:
            async with self._http.stream(
                "POST",
                OPENROUTER_IMAGES_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as response:
                status_code = response.status_code
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_RESPONSE_BYTES:
                        raise ProviderError("image response exceeded the safety limit")
        except httpx.RequestError as exc:
            raise ModelUnavailable("image provider unavailable") from exc

        parsed = self._parse_json(bytes(body))
        if status_code >= 400:
            _raise_classified(status_code, parsed.get("error"))
        try:
            result = _ImagesResponse.model_validate(parsed)
        except ValidationError as exc:
            raise ProviderError("image provider returned a malformed response") from exc

        image = result.data[0]
        try:
            image_bytes = base64.b64decode(image.b64_json, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ProviderError("image provider returned undecodable image data") from exc
        if not image_bytes:
            raise ProviderError("image provider returned an empty image")
        return image_bytes, image.media_type or "image/png"

    @staticmethod
    def _parse_json(content: bytes) -> dict[str, Any]:
        try:
            parsed = json.loads(content)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ProviderError("image provider returned a malformed response") from exc
        if not isinstance(parsed, dict):
            raise ProviderError("image provider returned a malformed response")
        return parsed


def _raise_classified(status: int, raw_error: object) -> None:
    message = ""
    if isinstance(raw_error, dict):
        message = str(raw_error.get("message", "")).casefold()
    if status in {404, 429, 502, 503}:
        raise ModelUnavailable("image provider unavailable")
    if "policy" in message or "safety" in message:
        raise ProviderRefusal("image model declined the request")
    raise ProviderError("image provider request failed")


def logo_prompt(draft: WorkingDraft, instructions: str = "") -> str:
    """Build an image prompt from the brand's own name, context, and color tokens."""

    colors = [
        str(token.value)
        for section in draft.sections
        for token in section.tokens
        if token.value_type == "color"
    ][:6]
    parts = [
        f'Design a clean, iconic, memorable logo for the brand "{draft.brand_name}".',
        "Vector-style, high contrast, centered on a plain white background, no photorealism.",
    ]
    if draft.brand_context:
        parts.append(f"Brand context: {draft.brand_context[:600]}")
    if colors:
        parts.append(f"Use this color palette: {', '.join(colors)}.")
    if instructions.strip():
        parts.append(instructions.strip()[:2000])
    return " ".join(parts)
