# Implementation Plan

## Decisions

- Package code under `src/brand_maker` with small modules for contracts, provider I/O,
  orchestration, prompts, HTTP routes, and evaluation.
- Use FastAPI lifespan to validate configuration once and own one shared
  `httpx.AsyncClient` for connection pooling.
- Keep provider transport separate from retry policy so every state transition is
  deterministic and unit-testable without network access.
- Treat both user input and model/provider output as untrusted. Validate request,
  provider envelope, extracted JSON, and the final brand contract.
- Preserve the specified primary model. Replace the retired fallback default with
  `anthropic/claude-sonnet-4.5`; both remain environment-configurable.
- Keep API outcomes (`ok`, `refused`, `error`) at HTTP 200, except FastAPI request
  validation errors, which remain HTTP 422 as specified.

## Threat model

- A caller can submit adversarial text: cap it at 80 characters and interpolate it
  only as data in the user message.
- A model/provider can emit malformed envelopes, prose, hostile instructions, or
  oversized content: cap response bytes, parse defensively, and validate with
  Pydantic before returning any content.
- A slow or failing provider can consume resources: use one bounded HTTP timeout,
  a maximum of three validation attempts, one refusal retry, and one failover.
- Credentials can leak through logs or source control: load only from the
  environment, ignore `.env`, and never include request headers in errors.

## Vertical slices

1. Configuration, exact public contracts, app lifespan, and `GET /health`.
2. OpenRouter request/response adapter and defensive JSON extraction.
3. Brand pipeline success path and `POST /brand`.
4. Schema retry, refusal retry, provider fallback, and terminal errors.
5. Deterministic evaluation harness, operational docs, and final quality gates.

Each slice requires focused tests first, then full tests, lint, typing, packaging,
and a manual API smoke check at the final checkpoint.
