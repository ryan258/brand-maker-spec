"""Deterministic orchestration for brand generation outcomes."""

from typing import Protocol

from pydantic import ValidationError

from brand_maker.json_extract import NoJSONObject, extract_json_object
from brand_maker.models import BrandKit, BrandResponse
from brand_maker.openrouter import (
    ContextOverflow,
    ModelUnavailable,
    ProviderError,
    ProviderRefusal,
)

INVALID_DATA_MESSAGE = "Model returned invalid data after 3 attempts."
REFUSAL_MESSAGE = "The model declined to build this brand."
PROVIDER_MESSAGE = "Model provider unavailable."
CONTEXT_MESSAGE = "Input too large."
REFUSAL_PHRASES = (
    "i cannot",
    "i can't",
    "cannot comply",
    "can't assist",
    "can't help",
    "i won't",
    "unable to assist",
    "unable to comply",
    "unable to help",
    "decline to",
)


def _contains_refusal_language(raw: str) -> bool:
    normalized = raw.casefold()
    return any(phrase in normalized for phrase in REFUSAL_PHRASES)


class Generator(Protocol):
    async def generate(
        self,
        *,
        brand_name: str,
        model: str,
        safety_rephrase: bool = False,
        brand_context: str | None = None,
    ) -> str: ...


class BrandBuilder(Protocol):
    async def build(
        self, brand_name: str, *, brand_context: str | None = None
    ) -> BrandResponse: ...


class BrandPipeline:
    """Apply bounded retry, refusal, and model-failover policy."""

    def __init__(self, *, generator: Generator, primary_model: str, fallback_model: str) -> None:
        self._generator = generator
        self._primary_model = primary_model
        self._fallback_model = fallback_model

    async def build(self, brand_name: str, *, brand_context: str | None = None) -> BrandResponse:
        model = self._primary_model
        failover_used = False
        safety_rephrase = False
        invalid_attempts = 0

        while invalid_attempts < 3:
            try:
                raw = await self._generator.generate(
                    brand_name=brand_name,
                    model=model,
                    safety_rephrase=safety_rephrase,
                    brand_context=brand_context,
                )
            except ModelUnavailable:
                if (
                    not failover_used
                    and model == self._primary_model
                    and self._fallback_model != self._primary_model
                ):
                    model = self._fallback_model
                    failover_used = True
                    continue
                return BrandResponse(status="error", message=PROVIDER_MESSAGE)
            except ContextOverflow:
                return BrandResponse(status="error", message=CONTEXT_MESSAGE)
            except ProviderRefusal:
                if safety_rephrase:
                    return BrandResponse(status="refused", message=REFUSAL_MESSAGE)
                safety_rephrase = True
                continue
            except ProviderError:
                return BrandResponse(status="error", message=PROVIDER_MESSAGE)

            try:
                json_text = extract_json_object(raw)
            except NoJSONObject:
                if safety_rephrase:
                    return BrandResponse(status="refused", message=REFUSAL_MESSAGE)
                safety_rephrase = True
                continue

            try:
                kit = BrandKit.model_validate_json(json_text)
                if kit.brand_name != brand_name:
                    raise ValueError("model changed the requested brand name")
            except (ValidationError, ValueError):
                if _contains_refusal_language(raw):
                    if safety_rephrase:
                        return BrandResponse(status="refused", message=REFUSAL_MESSAGE)
                    safety_rephrase = True
                    continue
                invalid_attempts += 1
                continue

            return BrandResponse(status="ok", kit=kit)

        return BrandResponse(status="error", message=INVALID_DATA_MESSAGE)
