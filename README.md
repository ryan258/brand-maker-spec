# Brand System Maker

A local-first personal brand operating system for turning raw ideas, named concepts,
and existing projects into researched, versioned living brands. It supports structured
editing, resumable generation, approval and immutable publication, audience guides,
portable exports, and evidence-rich brand compliance. The fast one-name generator is
a quick entry path into the same durable workspace.

The approved product direction and implementation sequence live in
[`docs/specs/personal-brand-os.md`](docs/specs/personal-brand-os.md) and
[`docs/specs/personal-brand-os-implementation-plan.md`](docs/specs/personal-brand-os-implementation-plan.md).
For a browser walkthrough, see [`docs/happy-path.md`](docs/happy-path.md), and for
100 copy-and-paste example briefs see
[`docs/100-awesome-brand-demos.md`](docs/100-awesome-brand-demos.md) and
[`docs/100-parody-brand-demos.md`](docs/100-parody-brand-demos.md).

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
  -d '{"brand_name":"Fieldwell"}'
```

Open `http://127.0.0.1:8000/brand-systems` to create and edit a living brand, or
`http://127.0.0.1:8000/compliance` to check an artifact. The legacy generator is at
the homepage and its saved library is at `/brands`. Interactive API documentation is
available at `/docs`.

The living-brand workflow is:

1. Create a workspace from a raw idea, named concept, existing project, or saved quick
   kit, then add whatever founding context is already known. The structured brief saves
   incrementally and offers starter answers to reduce typing.
2. Edit sections manually or generate a complete/selected starting point. Generation
   obeys the founding brief; **Generate or refresh complete draft** regenerates
   unlocked sections from the current brief while preserving locked ones.
3. Open **View complete brand bible** for the live, navigable source of truth across
   context, guidance, rules, tokens, examples, patterns/playbooks, and registered
   assets; preview its brand-token dark mode, follow the active table of contents,
   print it, or save it as PDF directly from the browser. Patterns include
   say/never-say guidance, message systems, web-component specifications and states,
   type scales, layout templates, channel playbooks, and governance workflows.
4. Review dependencies and the local audit feed, undo or redo revision-safe edits,
   lock settled sections, approve an exact draft revision, and publish an immutable
   semantic version.
5. Render creator, designer, business, or agency views; export Markdown, developer
   tokens/rules, canonical archives, or tagged PDF/UA.
6. Register artifact revisions and run deterministic compliance checks. Unsupported
   checks, model judgment, evidence, and expiring exceptions remain visibly distinct.

Evidence intake records whether a source is an owner statement, project material, or
external source. Its visible privacy state is either `private-local` or explicitly
`research-approved`; private-local content does not grant permission for external use.

Saved quick kits remain available in the kit library. Use **Build complete brand
bible** on a saved kit to preserve it as the exact source of a new living workspace.
New quick-start generations create a concept-stage living workspace automatically.
The older quick-kit schema retains a `parody_target` field for stored-data and API
compatibility, but parody is no longer the product's positioning or creative limit.

The original `POST /brand` endpoint remains stateless and backward-compatible. The
browser uses the persistent library API:

- `POST /api/brands`: generate and save a successful kit (accepts optional `brand_name` and `brand_context` up to 50k chars).
- `GET /api/brands?page=1&pageSize=12`: list saved brands newest first.
- `GET /api/brands/{id}`: retrieve one complete saved brand.

Living workspaces expose bounded audit history at
`GET /api/brand-systems/{id}/audit`. Revision-safe `POST` requests to the sibling
`/undo` and `/redo` endpoints require the current `expected_revision`; a new edit
after undo deliberately closes the abandoned redo branch.

`DELETE /api/brand-systems/{id}` moves a workspace into recoverable trash; list it at
`GET /api/brand-system-trash` and restore it through the item-level `/restore` route.
Download a checksum-bound portable backup from
`GET /api/brand-systems/{id}/backup`. Restore a new workspace through
`POST /api/brand-system-backups`, or pass the current `expectedRevision` to replace an
existing or trashed workspace as a new revision. Restore validates the complete
manifest and every managed asset before changing workspace state.

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
| `BRAND_MAKER_PRIMARY_MODEL` | No | `google/gemini-3.5-flash-lite` |
| `BRAND_MAKER_FALLBACK_MODEL` | No | `google/gemini-2.5-flash` |
| `BRAND_MAKER_JUDGE_MODEL` | No | `anthropic/claude-sonnet-4.5` |
| `BRAND_MAKER_IMAGE_MODEL` | No | `google/gemini-2.5-flash-image-preview` |
| `BRAND_MAKER_REQUEST_TIMEOUT_SECONDS` | No | `45` |
| `BRAND_MAKER_DATABASE_PATH` | No | `.brand-maker/brands.db` |
| `BRAND_MAKER_ASSET_SOURCE_ROOTS` | No | Database directory only |

The database and managed-asset directory are created on first use and excluded from
Git. Back up both the configured database file and its sibling `assets/` directory.
To restore on another machine, stop the app, replace those two items from the same
backup generation, and restart. Canonical publication archives are independently
checksum-bound and can restore their managed assets without original source paths.

Legacy records are never destructively migrated. Creating a living workspace from a
saved kit copies its content and provenance; the source kit remains unchanged.

The primary, fallback, judge, and image-model defaults are defined once in `Settings`
and mirrored here and in `.env.example`; every model remains overridable without a
code change. Keep the primary and fallback models distinct if you want provider
failover to select a second model.

## Local security boundary

This is an unauthenticated, single-owner local application. The CLI binds to
`127.0.0.1` by default and refuses non-loopback hosts unless
`--allow-network-bind` is supplied explicitly. Only use that override behind an
authentication and TLS gate. `owner_id` records attribution; it is not access
control.

The path-based asset registration API may read only from
`BRAND_MAKER_ASSET_SOURCE_ROOTS` (a JSON list of directories), or from the database
directory when the variable is omitted. Prefer browser uploads for ordinary use.

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

- `routes/`: modular API endpoints (`workspaces`, `assets`, `publication`, `exports`,
  `generation`, `compliance`, and `pages`).
- `brand_system/`: canonical workspaces, validation, assets, publication, and amendments.
- `generation/`: versioned section prompts and resumable generation runs.
- `publishing/`: audience projections, Markdown/developer/archive/PDF exports.
- `compliance/`: artifact revisions, deterministic checks, campaigns, evidence, and exceptions.
- `models.py`: retained quick-kit compatibility contracts.
- `openrouter.py`: bounded HTTP adapter and provider-envelope validation.
- `json_extract.py`: defensive extraction of object-shaped model output.
- `pipeline.py`: retry, refusal, failover, and terminal-outcome state machine.
- `app.py`: FastAPI application factory, lifespan management, and router orchestration.
- `web.py`: dependency-free homepage, favicon, and documentation navigation.
- `storage.py`: parameterized SQLite persistence and bounded pagination.
- `library_web.py`: collection and full-detail HTML shells.
- `static/`: shared browser scripts and responsive styles for brand bible, library, workshop, and compliance pages (`brand-bible.css`, `library.css`, `workshop.css`, `app.js`, `workshop.js`).
- `workshop_web.py`: living-brand workspace HTML shells.
- `compliance_web.py`: local compliance workflow shell.
- `evaluation.py`: deterministic checks and the exact LLM judge rubric.

Framework patterns follow the official documentation for
[FastAPI lifespan testing](https://fastapi.tiangolo.com/advanced/testing-events/),
[Pydantic settings and dotenv files](https://docs.pydantic.dev/latest/concepts/pydantic_settings/#dotenv-env-support),
[HTTPX async client pooling](https://www.python-httpx.org/async/#opening-and-closing-clients),
and [OpenRouter error handling](https://openrouter.ai/docs/api/reference/errors-and-debugging).
