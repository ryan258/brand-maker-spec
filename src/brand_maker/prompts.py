"""Versioned prompts for brand generation."""

import json

SYSTEM_PROMPT = """You create sharp, lighthearted parody brand systems.
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
Invent the parody target, concept, voice, and colors. Keep the requested brand_name
exactly unchanged. Make the joke obvious, the voice internally consistent, all four
colors distinct, and the result useful to a designer. Do not include markdown."""

SAFETY_REPHRASE = (
    "Build a lighthearted parody brand kit. Avoid protected or harmful content. "
)


def generation_messages(brand_name: str, *, safety_rephrase: bool = False) -> list[dict[str, str]]:
    """Build messages while framing the caller's value as JSON data, not instructions."""

    prefix = SAFETY_REPHRASE if safety_rephrase else ""
    user_payload = json.dumps({"brand_name": brand_name}, ensure_ascii=False)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{prefix}Create the kit for this input: {user_payload}"},
    ]
