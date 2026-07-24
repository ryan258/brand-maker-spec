# Brand System Maker

A local-first FastAPI workshop for building comprehensive, versioned living brand
systems. It supports structured editing, resumable section generation, approval and
immutable publication, audience guides, portable exports, and evidence-rich brand
compliance. The original parody-kit generator remains available as a compatible
starting point and can be migrated into a living workspace.

## Quick start

Requirements: Python 3.11+ and [uv](https://docs.astral.sh/uv/).

Tagged PDF export uses WeasyPrint. On macOS, install its native runtime with
`brew install weasyprint`; follow the WeasyPrint installation guide for equivalent
Linux packages.

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

Open `http://127.0.0.1:8000/brand-systems` to create and edit a living brand, or
`http://127.0.0.1:8000/compliance` to check an artifact. The legacy generator is at
the homepage and its saved library is at `/brands`. Interactive API documentation is
available at `/docs`.

The living-brand workflow is:

1. Create a blank workspace, optionally pasting background context for the brand, or
   migrate a saved parody kit.
2. Edit sections manually or generate a complete/selected starting point.
3. Review dependencies, lock settled sections, approve an exact draft revision,
   and publish an immutable semantic version.
4. Render creator, designer, business, or agency views; export Markdown, developer
   tokens/rules, canonical archives, or tagged PDF/UA.
5. Register artifact revisions and run deterministic compliance checks. Unsupported
   checks, model judgment, evidence, and expiring exceptions remain visibly distinct.

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

The database and managed-asset directory are created on first use and excluded from
Git. Back up both the configured database file and its sibling `assets/` directory.
To restore on another machine, stop the app, replace those two items from the same
backup generation, and restart. Canonical publication archives are independently
checksum-bound and can restore their managed assets without original source paths.

Legacy records are never destructively migrated. Creating a living workspace from a
saved kit copies its content and provenance; the source kit remains unchanged.

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

- `brand_system/`: canonical workspaces, validation, assets, publication, and amendments.
- `generation/`: versioned section prompts and resumable generation runs.
- `publishing/`: audience projections, Markdown/developer/archive/PDF exports.
- `compliance/`: artifact revisions, deterministic checks, campaigns, evidence, and exceptions.
- `models.py`: retained parody-kit public contracts.
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
- `workshop_web.py` / `workshop_ui.py` / `workshop_styles.py`: living-brand workspace HTML shells, dependency-free behavior, and styles.
- `compliance_web.py` / `compliance_ui.py`: local compliance workflow shell and text-only DOM behavior.
- `evaluation.py`: deterministic checks and the exact LLM judge rubric.

Framework patterns follow the official documentation for
[FastAPI lifespan testing](https://fastapi.tiangolo.com/advanced/testing-events/),
[Pydantic settings and dotenv files](https://docs.pydantic.dev/latest/concepts/pydantic_settings/#dotenv-env-support),
[HTTPX async client pooling](https://www.python-httpx.org/async/#opening-and-closing-clients),
and [OpenRouter error handling](https://openrouter.ai/docs/api/reference/errors-and-debugging).
