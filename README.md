# Brand System Maker

A local-first FastAPI application that turns one parody brand name into a complete,
validated brand kit through OpenRouter. Successful kits are saved to a local SQLite
library. The generation pipeline implements the product contract in `spec.md`,
including bounded schema retries, one refusal rephrase, and one model failover.

## Quick start

Requirements: Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev
cp .env.example .env
# Add your OpenRouter key to .env
uv run brand-maker
```

The service fails during startup if `OPENROUTER_API_KEY` is missing. It listens on
`127.0.0.1:8000` by default; use `--host` and `--port` to override them.

```bash
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/brand \
  -H 'Content-Type: application/json' \
  -d '{"brand_name":"Floogle"}'
```

Opening `http://127.0.0.1:8000/` shows the browser workspace: enter a parody name,
generate a kit, and review or copy the identity, voice, personality, and palette.
Every successful generation is saved locally. Open `http://127.0.0.1:8000/brands`
to browse the collection; each card links to its complete brand page. The homepage
also includes a plain-language first-run guide. Interactive OpenAPI documentation is
available at `http://127.0.0.1:8000/docs`.

The original `POST /brand` endpoint remains stateless and backward-compatible. The
browser uses the persistent library API:

- `POST /api/brands`: generate and save a successful kit.
- `GET /api/brands?page=1&pageSize=12`: list saved brands newest first.
- `GET /api/brands/{id}`: retrieve one complete saved brand.

## API outcomes

- `ok`: a complete, contract-valid kit is present.
- `refused`: the model declined both the original and safety-rephrased request.
- `error`: validation retries were exhausted, the provider was unavailable, or
  the context limit was exceeded.
- HTTP 422: the request was invalid; OpenRouter is not called.

Provider and model failures intentionally return stable, sanitized messages. The
service does not expose provider payloads, credentials, or partial model output.

## Configuration

| Variable | Required | Default |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | Yes | — |
| `BRAND_MAKER_PRIMARY_MODEL` | No | `poolside/laguna-s-2.1:free` |
| `BRAND_MAKER_FALLBACK_MODEL` | No | `anthropic/claude-sonnet-4.5` |
| `BRAND_MAKER_JUDGE_MODEL` | No | `anthropic/claude-sonnet-4.5` |
| `BRAND_MAKER_REQUEST_TIMEOUT_SECONDS` | No | `45` |
| `BRAND_MAKER_DATABASE_PATH` | No | `.brand-maker/brands.db` |

The database is created on the first library operation and is excluded from Git.
Back up the configured database file if the generated collection matters to you.

The spec's original `anthropic/claude-3.5-sonnet` fallback is retired. The shipped
default is the currently available Sonnet 4.5 slug; every model remains overridable
without a code change.

## Verification

```bash
uv run pytest
uv run ruff check src tests
uv run mypy src
uv build
```

To run only the deterministic golden checks against a saved API response:

```bash
uv run brand-maker-eval response.json --deterministic-only
```

To run the exact semantic judge rubric from `spec.md` (this makes one paid model
call):

```bash
uv run brand-maker-eval response.json --brand-name Floogle
```

The evaluator exits `0` on pass, `1` when the semantic score misses the threshold,
and `2` for invalid input or evaluation failure.

## Architecture

- `models.py`: strict public data contracts.
- `openrouter.py`: bounded HTTP adapter and provider-envelope validation.
- `json_extract.py`: defensive extraction of object-shaped model output.
- `pipeline.py`: retry, refusal, failover, and terminal-outcome state machine.
- `app.py`: lifespan-owned HTTP client and FastAPI routes.
- `web.py`: dependency-free homepage, favicon, and documentation navigation.
- `ui.py`: safe browser-side generation and result rendering behavior.
- `storage.py`: parameterized SQLite persistence and bounded pagination.
- `library_web.py`: collection and full-detail HTML shells.
- `library_ui.py`: safe collection/detail loading and rendering behavior.
- `library_styles.py`: shared responsive library design system.
- `evaluation.py`: deterministic checks and the exact LLM judge rubric.

Framework patterns follow the official documentation for
[FastAPI lifespan testing](https://fastapi.tiangolo.com/advanced/testing-events/),
[Pydantic settings and dotenv files](https://docs.pydantic.dev/latest/concepts/pydantic_settings/#dotenv-env-support),
[HTTPX async client pooling](https://www.python-httpx.org/async/#opening-and-closing-clients),
and [OpenRouter error handling](https://openrouter.ai/docs/api/reference/errors-and-debugging).
