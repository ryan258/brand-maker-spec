from collections.abc import Sequence

import pytest

from brand_maker.models import BrandResponse
from brand_maker.openrouter import (
    ContextOverflow,
    ModelUnavailable,
    ProviderError,
    ProviderRefusal,
)
from brand_maker.pipeline import BrandPipeline

PRIMARY = "primary/model"
FALLBACK = "fallback/model"
VALID_KIT = """{
  "brand_name": "Floogle",
  "parody_target": "Google",
  "tagline": "Search less. Guess more.",
  "description": "A search engine that indexes vibes instead of facts.",
  "brand_voice": "Cheerful, over-confident, and technically wrong on purpose.",
  "personality": ["Playful", "Chaotic", "Helpful"],
  "color_palette": {
    "primary": "#4285F4",
    "secondary": "#EA4335",
    "accent": "#FBBC05",
    "background": "#FFFFFF"
  }
}"""


class ScriptedGenerator:
    def __init__(self, outcomes: Sequence[str | Exception]) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[tuple[str, str, bool]] = []
        self.contexts: list[str | None] = []

    async def generate(
        self,
        *,
        brand_name: str,
        model: str,
        safety_rephrase: bool = False,
        brand_context: str | None = None,
    ) -> str:
        self.calls.append((brand_name, model, safety_rephrase))
        self.contexts.append(brand_context)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def pipeline(generator: ScriptedGenerator) -> BrandPipeline:
    return BrandPipeline(generator=generator, primary_model=PRIMARY, fallback_model=FALLBACK)


@pytest.mark.asyncio
async def test_build_returns_valid_kit_on_first_attempt() -> None:
    generator = ScriptedGenerator([VALID_KIT])

    response = await pipeline(generator).build("Floogle")

    assert response.status == "ok"
    assert response.kit is not None
    assert response.kit.brand_name == "Floogle"
    assert generator.calls == [("Floogle", PRIMARY, False)]


@pytest.mark.asyncio
async def test_build_retries_invalid_data_up_to_three_total_attempts() -> None:
    generator = ScriptedGenerator(["{}", "{}", "{}"])

    response = await pipeline(generator).build("Floogle")

    assert response == BrandResponse(
        status="error",
        message="Model returned invalid data after 3 attempts.",
    )
    assert len(generator.calls) == 3


@pytest.mark.asyncio
async def test_build_can_recover_on_third_schema_attempt() -> None:
    generator = ScriptedGenerator(["{}", "{malformed}", VALID_KIT])

    response = await pipeline(generator).build("Floogle")

    assert response.status == "ok"
    assert len(generator.calls) == 3


@pytest.mark.asyncio
async def test_build_rephrases_once_after_plain_text_refusal() -> None:
    generator = ScriptedGenerator(["I cannot help with that.", VALID_KIT])

    response = await pipeline(generator).build("Floogle")

    assert response.status == "ok"
    assert generator.calls == [
        ("Floogle", PRIMARY, False),
        ("Floogle", PRIMARY, True),
    ]


@pytest.mark.asyncio
async def test_build_rephrases_refusal_language_wrapped_in_json() -> None:
    generator = ScriptedGenerator(['{"message":"I cannot build this brand."}', VALID_KIT])

    response = await pipeline(generator).build("Floogle")

    assert response.status == "ok"
    assert generator.calls[-1] == ("Floogle", PRIMARY, True)


@pytest.mark.asyncio
async def test_build_rephrases_once_after_provider_refusal() -> None:
    generator = ScriptedGenerator([ProviderRefusal("declined"), VALID_KIT])

    response = await pipeline(generator).build("Floogle")

    assert response.status == "ok"
    assert generator.calls[-1] == ("Floogle", PRIMARY, True)


@pytest.mark.asyncio
async def test_build_returns_refused_after_second_refusal() -> None:
    generator = ScriptedGenerator(["No JSON here.", ProviderRefusal("declined")])

    response = await pipeline(generator).build("Floogle")

    assert response == BrandResponse(
        status="refused",
        message="The model declined to build this brand.",
    )
    assert len(generator.calls) == 2


@pytest.mark.asyncio
async def test_build_fails_over_once_when_primary_is_unavailable() -> None:
    generator = ScriptedGenerator([ModelUnavailable("down"), VALID_KIT])

    response = await pipeline(generator).build("Floogle")

    assert response.status == "ok"
    assert generator.calls == [
        ("Floogle", PRIMARY, False),
        ("Floogle", FALLBACK, False),
    ]


@pytest.mark.asyncio
async def test_schema_retries_stay_on_fallback_after_failover() -> None:
    generator = ScriptedGenerator([ModelUnavailable("down"), "{}", VALID_KIT])

    response = await pipeline(generator).build("Floogle")

    assert response.status == "ok"
    assert [call[1] for call in generator.calls] == [PRIMARY, FALLBACK, FALLBACK]


@pytest.mark.asyncio
async def test_build_returns_provider_error_when_fallback_is_unavailable() -> None:
    generator = ScriptedGenerator(
        [ModelUnavailable("primary down"), ModelUnavailable("fallback down")]
    )

    response = await pipeline(generator).build("Floogle")

    assert response == BrandResponse(status="error", message="Model provider unavailable.")
    assert len(generator.calls) == 2


@pytest.mark.asyncio
async def test_build_returns_input_too_large_for_context_overflow() -> None:
    response = await pipeline(ScriptedGenerator([ContextOverflow("too long")])).build("Floogle")

    assert response == BrandResponse(status="error", message="Input too large.")


@pytest.mark.asyncio
async def test_build_hides_unclassified_provider_error() -> None:
    response = await pipeline(ScriptedGenerator([ProviderError("account details")])).build(
        "Floogle"
    )

    assert response == BrandResponse(status="error", message="Model provider unavailable.")


@pytest.mark.asyncio
async def test_build_retries_when_model_changes_requested_brand_name() -> None:
    wrong_name = VALID_KIT.replace('"Floogle"', '"Other"', 1)
    generator = ScriptedGenerator([wrong_name, VALID_KIT])

    response = await pipeline(generator).build("Floogle")

    assert response.status == "ok"
    assert len(generator.calls) == 2
