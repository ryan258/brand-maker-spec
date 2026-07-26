import json
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from brand_maker.evaluation import (
    JUDGE_SYSTEM_INSTRUCTION,
    JudgeScores,
    judge_brand_response,
    validate_deterministic,
)
from brand_maker.models import BrandResponse
from brand_maker.openrouter import ProviderError


def valid_kit_data() -> dict[str, object]:
    return {
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
            "background": "#FFFFFF",
        },
    }


class FakeCompleter:
    def __init__(self, raw: str) -> None:
        self.raw = raw
        self.calls: list[dict[str, Any]] = []

    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        self.calls.append(
            {
                "messages": messages,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return self.raw


def successful_response() -> BrandResponse:
    return BrandResponse.model_validate({"status": "ok", "kit": valid_kit_data(), "message": None})


def test_deterministic_validation_accepts_complete_ok_response() -> None:
    response = validate_deterministic(successful_response().model_dump(mode="json"))

    assert response.status == "ok"


def test_spec_golden_fixture_passes_deterministic_validation() -> None:
    fixture = Path(__file__).parent / "fixtures" / "golden_response.json"

    response = validate_deterministic(json.loads(fixture.read_text(encoding="utf-8")))

    assert response.kit is not None
    assert response.kit.brand_name == "Floogle"


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "error", "kit": None, "message": "failed"},
        {"status": "ok", "kit": None, "message": None},
    ],
)
def test_deterministic_validation_rejects_non_kit_payload(payload: object) -> None:
    with pytest.raises(ValidationError):
        validate_deterministic(payload)


def test_judge_scores_require_valid_range_and_correct_average() -> None:
    with pytest.raises(ValidationError):
        JudgeScores(
            parody_clarity=5,
            voice_consistency=5,
            color_fit=5,
            usability=5,
            overall=4.9,
            notes="Strong work.",
        )


def test_judge_pass_requires_overall_four_and_no_item_below_three() -> None:
    passing = JudgeScores(
        parody_clarity=4,
        voice_consistency=4,
        color_fit=4,
        usability=4,
        overall=4.0,
        notes="Ready to use.",
    )
    failing = JudgeScores(
        parody_clarity=5,
        voice_consistency=5,
        color_fit=5,
        usability=2,
        overall=4.2,
        notes="Not usable yet.",
    )

    assert passing.passes is True
    assert failing.passes is False


@pytest.mark.asyncio
async def test_judge_uses_exact_rubric_and_validates_json_response() -> None:
    completer = FakeCompleter(
        """```json
        {"parody_clarity":5,"voice_consistency":4,"color_fit":4,
         "usability":4,"overall":4.2,"notes":"A clear and cohesive kit."}
        ```"""
    )

    scores = await judge_brand_response(
        completer=completer,
        original_brand_name="Floogle",
        response=successful_response(),
        model="judge/model",
    )

    assert scores.passes is True
    assert completer.calls[0]["messages"][0] == {
        "role": "system",
        "content": JUDGE_SYSTEM_INSTRUCTION,
    }
    assert completer.calls[0]["model"] == "judge/model"
    assert completer.calls[0]["temperature"] == 0.0


def test_cli_reports_provider_failure_without_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from brand_maker import evaluation

    async def fail(args: object) -> int:
        raise ProviderError("model provider unavailable")

    monkeypatch.setattr(evaluation, "_run", fail)
    monkeypatch.setattr(sys, "argv", ["brand-maker-eval", "response.json"])

    with pytest.raises(SystemExit) as raised:
        evaluation.main()

    assert raised.value.code == 2
    assert capsys.readouterr().err == "Evaluation failed: model provider unavailable\n"
