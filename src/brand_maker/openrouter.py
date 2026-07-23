"""Narrow, validated adapter for OpenRouter chat completions."""

import json
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from brand_maker.prompts import generation_messages

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_RESPONSE_BYTES = 1_000_000


class ProviderError(RuntimeError):
    """Base class for safe, classified provider failures."""


class ModelUnavailable(ProviderError):
    """The requested model or its provider cannot serve the request."""


class ContextOverflow(ProviderError):
    """The provider rejected the request for exceeding its context window."""


class ProviderRefusal(ProviderError):
    """The provider explicitly classified the generation as a refusal."""


class _EnvelopeModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class _ErrorMetadata(_EnvelopeModel):
    error_type: str | None = None


class _ErrorDetail(_EnvelopeModel):
    code: int | str | None = None
    message: str = ""
    metadata: _ErrorMetadata | None = None


class _Message(_EnvelopeModel):
    content: str


class _Choice(_EnvelopeModel):
    message: _Message | None = None
    finish_reason: str | None = None
    error: _ErrorDetail | None = None


class _Completion(_EnvelopeModel):
    choices: list[_Choice] = Field(..., min_length=1)


class OpenRouterClient:
    """Call OpenRouter and return only validated assistant text."""

    def __init__(self, *, http: httpx.AsyncClient, api_key: str) -> None:
        self._http = http
        self._api_key = api_key

    async def generate(
        self,
        *,
        brand_name: str,
        model: str,
        safety_rephrase: bool = False,
    ) -> str:
        return await self.complete(
            messages=generation_messages(brand_name, safety_rephrase=safety_rephrase),
            model=model,
            temperature=0.8,
            max_tokens=1500,
        )

    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Send a bounded JSON completion request and return assistant content."""

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        try:
            async with self._http.stream(
                "POST",
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as response:
                status_code = response.status_code
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > MAX_RESPONSE_BYTES:
                        raise ProviderError("provider response exceeded the safety limit")
        except httpx.RequestError as exc:
            raise ModelUnavailable("model provider unavailable") from exc

        parsed = self._parse_json(bytes(content))
        top_error = parsed.get("error") if isinstance(parsed, dict) else None
        if status_code >= 400 or isinstance(top_error, dict):
            self._raise_classified(status_code, top_error)

        try:
            completion = _Completion.model_validate(parsed)
        except ValidationError as exc:
            raise ProviderError("provider returned a malformed response") from exc

        choice = completion.choices[0]
        if choice.error is not None or choice.finish_reason == "error":
            self._raise_classified(status_code, choice.error)
        if choice.message is None:
            raise ProviderError("provider returned a malformed response")
        return choice.message.content

    @staticmethod
    def _parse_json(content: bytes) -> dict[str, Any]:
        try:
            parsed = json.loads(content)
        except (UnicodeDecodeError, ValueError) as exc:
            raise ProviderError("provider returned a malformed response") from exc
        if not isinstance(parsed, dict):
            raise ProviderError("provider returned a malformed response")
        return parsed

    @staticmethod
    def _raise_classified(status: int, raw_error: object) -> None:
        try:
            error = _ErrorDetail.model_validate(raw_error)
        except ValidationError:
            error = _ErrorDetail(code=status, message="")

        error_type = error.metadata.error_type if error.metadata else None
        message = error.message.casefold()
        model_missing = "model" in message and "not found" in message
        if status in {404, 502, 503} or model_missing or error_type in {
            "not_found",
            "provider_unavailable",
            "provider_overloaded",
        }:
            raise ModelUnavailable("model provider unavailable")
        if error_type == "context_length_exceeded" or "context length" in message:
            raise ContextOverflow("input too large")
        if error_type in {"refusal", "content_policy_violation"} or status == 403:
            raise ProviderRefusal("model declined the request")
        raise ProviderError("model provider request failed")
