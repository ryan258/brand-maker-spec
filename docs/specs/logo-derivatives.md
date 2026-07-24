# Spec: Logo Derivatives

## Objective

Let a brand owner select an uploaded or AI-generated raster logo and create three
production-ready derivative sets without replacing the source asset:

- favicon/app-icon PNGs at 16, 32, 48, 180, 192, and 512 pixels;
- AI-edited monochrome, inverted, horizontal-lockup, and icon-only variants;
- a local SVG trace containing editable vector paths and no embedded raster data.

Every derivative is an optional, content-addressed managed asset. A set is added
to the working draft atomically at one expected revision.

## Tech Stack and Commands

- Python 3.11+, FastAPI, Pydantic, Pillow.
- Test: `uv run pytest -q`
- Lint: `uv run ruff check .`
- Format check: `uv run ruff format --check .`
- Type check: `uv run mypy`
- Build: `uv build`

## Project Structure

- `src/brand_maker/logo_derivatives.py`: bounded local raster transforms and SVG tracing.
- `src/brand_maker/image_gen.py`: OpenRouter reference-image request support.
- `src/brand_maker/app.py`: derivative resource endpoints and atomic persistence.
- `src/brand_maker/workshop_*`: accessible source selection and actions.
- `tests/`: unit, provider-contract, API, and page-contract coverage.

## Interface Contract

- `POST .../assets/{asset_id}/favicon-sets` accepts `expected_revision`.
- `POST .../assets/{asset_id}/logo-variant-sets` accepts `expected_revision`, an
  optional subset of the four supported variants, and optional extra instructions.
- `POST .../assets/{asset_id}/vectorizations` accepts `expected_revision`.
- Success returns the complete next `WorkingDraft` at HTTP 201.
- Unknown assets return 404; stale revisions return 409; unsupported or malformed
  source images return 422; provider refusal returns 422; temporary provider
  unavailability returns 503; other provider failures return 502.

## Testing Strategy

- Unit tests prove crop sizes, alpha preservation, and path-only SVG output.
- Provider tests prove the source is sent as a base64 `input_references` data URL.
- API tests prove atomic revision bumps, managed registration, variant naming, and
  source-asset selection.
- Page tests prove the controls are labelled, keyboard-native, and status-announced.

## Boundaries

- Always: preserve source bytes; verify source size/hash before reading; cap decoded
  dimensions; strip metadata from local derivatives; keep outputs optional.
- Ask first: add another provider, expose public asset URLs, or change publication rules.
- Never: embed the source raster in SVG, mutate/overwrite source assets, fetch remote
  source URLs, or claim semantic AI edits were produced by deterministic cropping.

## Success Criteria

- One action produces all six square icon sizes from a raster logo.
- Each requested AI variant uses the selected logo as an image reference and is stored
  only if the entire requested set succeeds.
- Vectorization emits valid SVG with one or more `<path>` elements and no `<image>` or
  data URL.
- Invalid raster inputs and decompression-bomb-sized images fail safely.
- Focused and full verification commands pass.
