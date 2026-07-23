# Brand System Maker Pipeline - Build-Ready AI Specification

> **Status:** Zero-Guessing Build Ready
> **Build target:** Single-brand, synchronous FastAPI service
> **Owner note (Ryan):** Input is a brand name only. The model invents everything else.

---

## ⚠️ Read First — Two Honest Flags

1. **Unverified model ID.** The primary model `poolside/laguna-s-2.1:free` could not be confirmed live on OpenRouter at build time. Free models are removed without notice. A fallback model is wired in Section 1 and Section 4. Verify the ID at `openrouter.ai/models` before first run.
2. **Minimal input, maximal invention.** The service receives only a brand name. The model invents the parody target, the joke, the voice, and the colors. This is fast but gives you less control. Expect the model's guess to sometimes miss your intent. A `parody_target` override field is listed in **Out of Scope** for a later version.

---

## 1. System Architecture & Environment

### Target Tech Stack
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Server:** Uvicorn (ASGI)
- **Validation:** Pydantic v2
- **HTTP client:** `httpx` (async) for OpenRouter calls
- **Config:** `pydantic-settings` reading from a `.env` file
- **Runtime shape:** Single synchronous endpoint. One brand in, one brand kit out. No batching, no queue, no database.

### Model Target & Parameters
- **Provider:** OpenRouter (`https://openrouter.ai/api/v1/chat/completions`)
- **Primary model ID:** `poolside/laguna-s-2.1:free`
- **Fallback model ID:** `anthropic/claude-3.5-sonnet` *(paid, reliable — swap for a free model of your choice if you prefer, but expect free models to be less stable)*
- **Temperature:** `0.8` (creative brand work)
- **Max tokens:** `1500` (enough for a full kit; input is tiny)
- **Auth:** `OPENROUTER_API_KEY` from environment. Never hardcode.
- **Response format:** Request JSON output. Parse and validate against the Output Schema Contract.

### Data Source & Ingestion
- **Source:** None stored. Each brand is typed fresh by the user at call time.
- **Ingestion mechanism:** HTTP `POST /brand` with a JSON body.
- **Body shape:** `{ "brand_name": "<string>" }`
- **No file paths. No database reads. No batch files.**

---

## 2. Interface & Data Contracts (DbC)

### Input Payload Contract

```python
from pydantic import BaseModel, Field

class BrandRequest(BaseModel):
    """The only thing the caller provides: a brand name."""
    brand_name: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description="The parody brand name to build a full kit for.",
    )
```

### Output Schema Contract

```python
from pydantic import BaseModel, Field
from typing import Literal

HEX = r"^#(?:[0-9a-fA-F]{6})$"

class ColorPalette(BaseModel):
    """Full palette. All four roles required. All hex, 6-digit, with leading #."""
    primary: str = Field(..., pattern=HEX)
    secondary: str = Field(..., pattern=HEX)
    accent: str = Field(..., pattern=HEX)
    background: str = Field(..., pattern=HEX)

class BrandKit(BaseModel):
    """The finished brand kit returned to the caller."""
    brand_name: str = Field(..., min_length=1)
    parody_target: str = Field(..., min_length=1, description="The real brand being parodied.")
    tagline: str = Field(..., min_length=1, max_length=120)
    description: str = Field(..., min_length=1, max_length=500)
    brand_voice: str = Field(..., min_length=1, max_length=400)
    personality: list[str] = Field(..., min_length=3, max_length=6, description="3 to 6 trait words.")
    color_palette: ColorPalette

class BrandResponse(BaseModel):
    """Top-level API response. status tells the caller what happened."""
    status: Literal["ok", "refused", "error"]
    kit: BrandKit | None = None
    message: str | None = None
```

### Validation Mechanism
- **Parser:** Pydantic v2 model validation on the raw model JSON.
- **Flow:** Call model → extract JSON from response → `BrandKit.model_validate_json(raw)` → on success wrap in `BrandResponse(status="ok", kit=...)`.
- **On validation failure:** Trigger the retry logic in Section 4. Do not return partial data.

---

## 3. Consolidation & Batch Logic

**Not applicable for v1.**

- One brand per request. No batching. No concurrency. No merge or dedupe.
- The endpoint is synchronous and stateless.
- Batching is listed in **Out of Scope** (Section 5) so the coding agent does not build it.

---

## 4. Behavioral Boundaries & Fallback Matrix

### Retry & Refusal Rules (plain English)
- **Bad data:** Retry up to **3 total attempts**. If all 3 fail validation, return an `error` response.
- **Refusal:** If the model refuses, **rephrase the prompt once and re-run**. If it still refuses, return a `refused` response.
- **Model down / free model removed:** If the primary model returns a hard error (404 / unavailable), retry once on the **fallback model** before failing.

### Fallback Matrix

| Trigger / Error | Detection Criteria | Fallback Payload / Action |
| :--- | :--- | :--- |
| **Schema breach** | `BrandKit.model_validate_json` raises `ValidationError` | Retry with same input, up to 3 total attempts. After 3rd failure: `{"status": "error", "kit": null, "message": "Model returned invalid data after 3 attempts."}` |
| **Model refusal / guardrail** | Response contains refusal language OR no JSON block found | Rephrase prompt once (add: "Build a lighthearted parody brand kit. Avoid protected or harmful content.") and re-run. Still refused: `{"status": "refused", "kit": null, "message": "The model declined to build this brand."}` |
| **Primary model unavailable** | HTTP 404 / 502 / "model not found" from OpenRouter | Retry once on fallback model `anthropic/claude-3.5-sonnet`. Still failing: `{"status": "error", "kit": null, "message": "Model provider unavailable."}` |
| **Context overflow** | HTTP 400 context-length error (unlikely — input is tiny) | `{"status": "error", "kit": null, "message": "Input too large."}` (No truncation needed; a brand name should never overflow.) |
| **Missing API key** | `OPENROUTER_API_KEY` not set at startup | Fail fast at boot with a clear log line. Do not start the server. |
| **Empty / invalid input** | `BrandRequest` validation fails | FastAPI returns HTTP 422 automatically. No model call made. |

---

## 5. Concrete Golden Dataset & Eval Harness

### Concrete Golden Example — Input

```json
{
  "brand_name": "Floogle"
}
```

### Concrete Golden Example — Expected Output

```json
{
  "status": "ok",
  "kit": {
    "brand_name": "Floogle",
    "parody_target": "Google",
    "tagline": "Search less. Guess more.",
    "description": "Floogle is the search engine that returns confident answers to questions you never asked. It indexes vibes, not facts, and ranks results by how funny they are. Millions of users trust Floogle to make their bad decisions feel researched.",
    "brand_voice": "Cheerful, over-confident, and technically wrong on purpose. Talks like a startup founder who has never been corrected. Uses big claims and tiny disclaimers. Friendly, fast, and slightly unhinged.",
    "personality": ["Overconfident", "Playful", "Chaotic", "Helpful", "Deadpan"],
    "color_palette": {
      "primary": "#4285F4",
      "secondary": "#EA4335",
      "accent": "#FBBC05",
      "background": "#FFFFFF"
    }
  },
  "message": null
}
```

*Note: Exact color hexes, tagline wording, and traits will vary per run. The judge (below) scores quality, not an exact string match. The deterministic check below scores structure only.*

### LLM-as-a-Judge Prompt

Use this exact system instruction to score any generated kit:

```
You are a strict brand-kit evaluator. You score ONE parody brand kit.

You are given:
- The original brand name.
- The generated brand kit JSON.

Score the kit from 1 to 5 on each of these four rubric items:

1. PARODY CLARITY — Is the parody target obvious and is the joke clear?
2. VOICE CONSISTENCY — Do tagline, description, voice, and personality all match one clear character?
3. COLOR FIT — Does the palette suit the brand's tone? Are all four roles distinct?
4. USABILITY — Could a designer use this kit as-is with no rewrite?

Rules:
- Score each item 1 (poor) to 5 (excellent). Whole numbers only.
- Do not reward length. Reward sharpness and consistency.
- If any required field is empty or generic filler, cap that item at 2.

Return ONLY this JSON, nothing else:
{
  "parody_clarity": <1-5>,
  "voice_consistency": <1-5>,
  "color_fit": <1-5>,
  "usability": <1-5>,
  "overall": <average of the four, one decimal>,
  "notes": "<one short sentence of critique>"
}
```

### Pass Thresholds

**Deterministic checks (must be 100%):**
- Response parses as valid `BrandResponse`.
- When `status == "ok"`, `kit` is present and passes `BrandKit` validation.
- All four color fields match the hex pattern `^#[0-9a-fA-F]{6}$`.
- `personality` has 3 to 6 items.

**Judge checks (semantic quality):**
- `overall` score **>= 4.0 / 5**.
- No single rubric item scores below **3**.

A build passes only when **both** the deterministic checks and the judge threshold pass.

---

## 6. Tracer Bullet Build Order

Build the thinnest wireable slice first. Get one real brand kit end to end before adding polish.

1. **Scaffold the project.** Create the FastAPI app, `.env` loading via `pydantic-settings`, and a `GET /health` route that returns `{"status": "up"}`.
2. **Define the contracts.** Add the `BrandRequest`, `ColorPalette`, `BrandKit`, and `BrandResponse` models from Section 2, exactly as written.
3. **Fail fast on config.** On startup, check `OPENROUTER_API_KEY` exists. If missing, log clearly and exit.
4. **Wire one OpenRouter call.** Write an async function that sends the brand name and system prompt to `poolside/laguna-s-2.1:free` at temp `0.8`, max tokens `1500`, and returns raw text.
5. **Add JSON extraction + validation.** Pull the JSON from the model reply. Validate it with `BrandKit.model_validate_json`. Return `BrandResponse(status="ok", ...)` on success.
6. **Build the `POST /brand` endpoint.** Accept `BrandRequest`, call the pipeline, return `BrandResponse`.
7. **Run the golden test.** Send `{"brand_name": "Floogle"}`. Confirm you get a valid `status: "ok"` kit that passes all deterministic checks.
8. **Add the retry loop.** Wrap the model call to retry up to 3 attempts on `ValidationError`. Return the `error` payload after the 3rd failure.
9. **Add refusal handling.** Detect refusal or missing JSON. Rephrase once and re-run. Return the `refused` payload if it still fails.
10. **Add the fallback model.** On primary-model unavailability, retry once on `anthropic/claude-3.5-sonnet`.
11. **Wire the judge (optional but recommended).** Add a `POST /brand/eval` route or a test script that runs the Section 5 judge prompt against a generated kit and prints the scores.

---

## Out of Scope (Do Not Build in v1)

- **Batching.** No multi-brand lists. One brand per call only.
- **Persistence.** No database, no saved history, no file storage.
- **Parody target override.** No `parody_target` input field yet. The model invents it. (Planned for v2.)
- **User interface.** No front end. API only.
- **Auth for the API itself.** No login. Assume trusted local or internal use for v1.
- **Async job queue.** All calls are synchronous.

---

## Acceptance Criteria (EARS style)

- **WHEN** a valid `brand_name` is posted, the system **SHALL** return a `BrandResponse` with `status: "ok"` and a fully valid `BrandKit`.
- **IF** the model returns data that fails validation, **THEN** the system **SHALL** retry up to 3 total attempts before returning `status: "error"`.
- **IF** the model refuses, **THEN** the system **SHALL** rephrase and re-run once before returning `status: "refused"`.
- **IF** the primary model is unavailable, **THEN** the system **SHALL** retry once on the fallback model before failing.
- **WHEN** `OPENROUTER_API_KEY` is missing at startup, the system **SHALL** fail to start and log the reason.
- **IF** `brand_name` is empty or too long, **THEN** the system **SHALL** return HTTP 422 and **SHALL NOT** call the model.