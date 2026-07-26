# ruff: noqa: E501 - Keep the judge rubric readable as authored.
"""Deterministic and LLM-judge evaluation for generated brand responses."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Literal, Protocol, Self

import httpx
from pydantic import Field, model_validator

from brand_maker.config import Settings
from brand_maker.json_extract import extract_json_object
from brand_maker.models import BrandKit, BrandResponse, ContractModel
from brand_maker.openrouter import OpenRouterClient, ProviderError

JUDGE_SYSTEM_INSTRUCTION = """You are a strict brand-kit evaluator. You score ONE original brand starting point.

You are given:
- The original brand name.
- The generated brand kit JSON.

Score the kit from 1 to 5 on each of these four rubric items:

1. POSITIONING CLARITY — Is the category or convention this brand reacts against clear,
   and does the concept occupy a distinct, credible position?
2. VOICE CONSISTENCY — Do tagline, description, voice, and personality all match one clear character?
3. COLOR FIT — Does the palette suit the brand's tone? Are all four roles distinct?
4. USABILITY — Could a designer use this kit as-is with no rewrite?

Rules:
- Score each item 1 (poor) to 5 (excellent). Whole numbers only.
- Do not reward length. Reward sharpness and consistency.
- If any required field is empty or generic filler, cap that item at 2.

For API compatibility, put the positioning-clarity score in the legacy
`parody_clarity` key. Return ONLY this JSON, nothing else:
{
  "parody_clarity": <1-5>,
  "voice_consistency": <1-5>,
  "color_fit": <1-5>,
  "usability": <1-5>,
  "overall": <average of the four, one decimal>,
  "notes": "<one short sentence of critique>"
}"""


class SuccessfulBrandResponse(ContractModel):
    status: Literal["ok"]
    kit: BrandKit
    message: None = None


class JudgeScores(ContractModel):
    parody_clarity: int = Field(..., ge=1, le=5)
    voice_consistency: int = Field(..., ge=1, le=5)
    color_fit: int = Field(..., ge=1, le=5)
    usability: int = Field(..., ge=1, le=5)
    overall: float = Field(..., ge=1, le=5)
    notes: str = Field(..., min_length=1, max_length=300)

    @model_validator(mode="after")
    def validate_average(self) -> Self:
        expected = round(
            (self.parody_clarity + self.voice_consistency + self.color_fit + self.usability) / 4,
            1,
        )
        if self.overall != expected:
            raise ValueError(f"overall must be the rubric average ({expected:.1f})")
        return self

    @property
    def passes(self) -> bool:
        individual = (
            self.parody_clarity,
            self.voice_consistency,
            self.color_fit,
            self.usability,
        )
        return self.overall >= 4.0 and min(individual) >= 3


class Completer(Protocol):
    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str: ...


def validate_deterministic(payload: object) -> BrandResponse:
    """Enforce all deterministic pass criteria on a serialized response."""

    successful = SuccessfulBrandResponse.model_validate(payload)
    return BrandResponse(status="ok", kit=successful.kit)


async def judge_brand_response(
    *,
    completer: Completer,
    original_brand_name: str,
    response: BrandResponse,
    model: str,
) -> JudgeScores:
    """Run the specification's exact semantic rubric against a valid kit."""

    successful = SuccessfulBrandResponse.model_validate(response.model_dump(mode="json"))
    evaluation_input = {
        "original_brand_name": original_brand_name,
        "brand_kit": successful.kit.model_dump(mode="json"),
    }
    raw = await completer.complete(
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_INSTRUCTION},
            {
                "role": "user",
                "content": json.dumps(evaluation_input, ensure_ascii=False),
            },
        ],
        model=model,
        temperature=0.0,
        max_tokens=300,
    )
    return JudgeScores.model_validate_json(extract_json_object(raw))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and optionally judge a generated BrandResponse JSON file."
    )
    parser.add_argument("response_file", type=Path)
    parser.add_argument(
        "--brand-name",
        help="Original input name. Defaults to the validated kit's brand_name.",
    )
    parser.add_argument(
        "--deterministic-only",
        action="store_true",
        help="Skip the paid model judge and only validate the response contract.",
    )
    parser.add_argument("--judge-model", help="Override BRAND_MAKER_JUDGE_MODEL.")
    return parser


async def _run(args: argparse.Namespace) -> int:
    if args.response_file.stat().st_size > 1_000_000:
        raise ValueError("evaluation input exceeds 1 MB")
    payload = json.loads(args.response_file.read_text(encoding="utf-8"))
    response = validate_deterministic(payload)
    if response.kit is None:  # Defensive narrowing; deterministic validation requires it.
        raise ValueError("validated response did not contain a kit")
    result: dict[str, object] = {"deterministic_pass": True}

    if args.deterministic_only:
        print(json.dumps(result, indent=2))
        return 0

    settings = Settings.model_validate({})
    timeout = httpx.Timeout(settings.request_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as http:
        completer = OpenRouterClient(
            http=http,
            api_key=settings.openrouter_api_key.get_secret_value(),
        )
        scores = await judge_brand_response(
            completer=completer,
            original_brand_name=args.brand_name or response.kit.brand_name,
            response=response,
            model=args.judge_model or settings.judge_model,
        )
    result["judge_pass"] = scores.passes
    result["scores"] = scores.model_dump(mode="json")
    print(json.dumps(result, indent=2))
    return 0 if scores.passes else 1


def main() -> None:
    """Console entry point for the spec's evaluation harness."""

    args = _parser().parse_args()
    try:
        exit_code = asyncio.run(_run(args))
    except (OSError, ProviderError, ValueError) as exc:
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    raise SystemExit(exit_code)
