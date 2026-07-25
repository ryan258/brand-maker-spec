"""Versioned prompts for brand generation."""

import json

SYSTEM_PROMPT = """You create sharp, original brand starting points.
Return ONLY one JSON object with exactly these fields:
{
  "brand_name": "string",
  "parody_target": "string",
  "tagline": "1-120 characters",
  "description": "1-500 characters",
  "brand_voice": "1-400 characters",
  "personality": ["3 to 6 concise trait words"],
  "color_palette": {
    "primary": "#RRGGBB",
    "secondary": "#RRGGBB",
    "accent": "#RRGGBB",
    "background": "#RRGGBB"
  }
}
The legacy parody_target field must contain a concise positioning reference: the
category, convention, or alternative this brand reacts against. It may be a category,
behavior, assumption, or company. Invent a specific concept, voice, and colors. Keep the
requested brand_name exactly unchanged. Make the positioning clear, the voice internally
consistent, all four colors distinct, and the result useful as a concept-stage draft.
Do not include markdown."""

SAFETY_REPHRASE = (
    "Build an original, non-infringing brand starting point. Avoid protected or harmful content. "
)


def generation_messages(brand_name: str, *, safety_rephrase: bool = False) -> list[dict[str, str]]:
    """Build messages while framing the caller's value as JSON data, not instructions."""

    prefix = SAFETY_REPHRASE if safety_rephrase else ""
    user_payload = json.dumps({"brand_name": brand_name}, ensure_ascii=False)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{prefix}Create the kit for this input: {user_payload}"},
    ]
