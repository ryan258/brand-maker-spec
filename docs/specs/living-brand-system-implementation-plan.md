# Implementation Plan: Living Brand System

> Status: Implemented and release-verified
> Source: `docs/specs/living-brand-system.md`
> Delivery model: test-first vertical slices on the existing local FastAPI app

## 1. Overview

Build the approved Living Brand System additively beside the current parody
`BrandKit`. Existing `/brand`, `/api/brands`, saved-kit records, and browser pages
remain compatible throughout migration. New work uses strict Pydantic contracts,
JSON snapshots in SQLite, thin services and routes, safe dependency-free browser
rendering, and bounded OpenRouter calls.

The plan deliberately produces a useful local workflow early: create a workspace,
edit structured sections, approve it, and publish an immutable version. Generation,
assets, exports, compliance, and richer audience views then extend that proven path.

## 2. Protected Baseline

The current worktree already contains staged production fixes and tests plus staged
and unstaged revisions of the approved specification. Implementation must not lose,
overwrite, unstage, or silently fold unrelated changes into a slice.

Before Task 1:

1. Re-run the current verification suite.
2. Record the exact staged and unstaged file lists.
3. Keep the current index unchanged unless the owner explicitly authorizes staging
   or committing.
4. Keep all new behavior additive until the legacy compatibility tests prove that
   migration is safe.

## 3. Architecture Decisions

- **Compatibility shell:** Retain `BrandKit` and its endpoints. A living brand
  workspace can be created from a saved kit without modifying the source record.
- **Snapshot persistence:** Store validated canonical drafts and published versions
  as versioned JSON snapshots. Use relational columns only for identity, lifecycle,
  ordering, integrity, and bounded queries.
- **Optimistic revisions:** Every mutable draft has an integer revision. Updates
  require the expected revision and reject stale writes.
- **Single local owner:** Store a display identity and governance attribution, not
  authentication, permissions, invitations, or collaboration state.
- **Canonical sections:** Narrative blocks, rules, tokens, references, examples,
  evidence, and governance records use stable identifiers and strict discriminated
  contracts.
- **One generation engine:** Complete-draft and section-only generation schedule the
  same section runner. Every accepted section is persisted before the next begins.
- **Immutable publication:** Publication stores a complete content manifest and
  content hash. Clerical corrections are append-only amendments.
- **Managed publication assets:** Drafts may link files. Publication copies required
  files into content-addressed local storage and binds hashes into the snapshot.
- **Projection, not duplication:** Audience guides and export formats derive from a
  selected published version and amendment revision.
- **Deterministic first:** Contract, reference, token, contrast, terminology, and
  manifest checks are deterministic. Model judgment remains separately labeled.
- **No speculative platform:** No accounts, remote hosting, multi-user concurrency,
  plugin system, or framework rewrite.

## 4. Dependency Graph

```text
canonical contracts
  -> snapshot repository
    -> workspace API and migration
      -> workshop UI
      -> approval and publication
        -> amendments
        -> asset snapshotting
        -> audience projections and exports
        -> artifact and campaign compliance
  -> section generation contracts
    -> resumable orchestration
      -> generation API and UI
```

## 5. Task List

### Phase A: Canonical Workspace Foundation

#### Task 1: Define the minimum canonical contracts

**Description:** Add strict contracts for a local owner, structured narrative
blocks, rules, tokens, sections, references, draft lifecycle, and workspace summary.

**Acceptance:**

- Unsupported block types, raw HTML, blank identifiers, duplicate stable IDs,
  dangling references, and token cycles are rejected.
- A minimal valid workspace round-trips through versioned canonical JSON.
- Existing `BrandKit` contracts remain unchanged.

**Verify:** `uv run pytest -q tests/brand_system/test_contracts.py`

**Files:** `src/brand_maker/brand_system/models.py`,
`src/brand_maker/brand_system/validation.py`,
`src/brand_maker/brand_system/__init__.py`,
`tests/brand_system/test_contracts.py`

**Dependencies:** None. **Scope:** Medium.

#### Task 2: Persist workspaces as optimistic JSON snapshots

**Description:** Add an additive SQLite repository for workspace identity, current
draft JSON, schema version, revision, timestamps, and local-owner attribution.

**Acceptance:**

- Create, get, list, and expected-revision update operations are transactional.
- A stale update is rejected without changing stored canonical data.
- Existing `saved_brands` data and repository behavior are untouched.

**Verify:** `uv run pytest -q tests/brand_system/test_repository.py tests/test_storage.py`

**Files:** `src/brand_maker/brand_system/repository.py`,
`tests/brand_system/test_repository.py`

**Dependencies:** Task 1. **Scope:** Small.

**Boundary approval:** Approving this plan authorizes the additive SQLite tables
described here; it does not authorize destructive migration or removal of
`saved_brands`.

#### Task 3: Expose workspace creation, retrieval, listing, and editing

**Description:** Add a small service and `/api/brand-systems` endpoints, including
creation from scratch and migration from an existing saved `BrandKit`.

**Acceptance:**

- The owner can create and retrieve a draft, update one section with an expected
  revision, and list local workspaces with bounded pagination.
- Migration retains source provenance and marks missing comprehensive sections
  incomplete rather than inventing content.
- Invalid or stale writes return stable 4xx responses and preserve the prior draft.

**Verify:** `uv run pytest -q tests/brand_system/test_workspace_api.py`

**Files:** `src/brand_maker/brand_system/service.py`, `src/brand_maker/app.py`,
`tests/brand_system/test_workspace_api.py`, `src/brand_maker/models.py`

**Dependencies:** Tasks 1-2. **Scope:** Medium.

#### Task 4: Deliver the first usable workshop screen

**Description:** Add a keyboard-operable workspace page that lists section status,
opens one section, edits supported fields/blocks, and saves with conflict handling.

**Acceptance:**

- A local owner can create or migrate a workspace and edit it in the browser.
- Model/user content is rendered with text-only DOM APIs; no raw HTML insertion.
- Status, errors, save progress, landmarks, labels, focus, and narrow layouts are
  accessible.

**Verify:** `uv run pytest -q tests/brand_system/test_workshop_pages.py`; browser
check at desktop and 320 CSS pixels with keyboard-only navigation.

**Files:** `src/brand_maker/workshop_web.py`, `src/brand_maker/workshop_ui.py`,
`src/brand_maker/workshop_styles.py`, `src/brand_maker/app.py`,
`tests/brand_system/test_workshop_pages.py`

**Dependencies:** Task 3. **Scope:** Medium.

### Checkpoint A

- Full tests, Ruff, strict MyPy, and build pass.
- Existing `/brand`, `/api/brands`, home, and library flows are unchanged.
- Browser console is clean and the first workspace edit flow works end to end.

### Phase B: Governance and Reproducible Publication

#### Task 5: Add dependency-aware edits, locks, and validation

**Description:** Compute affected references, preserve locked content, classify
blocking errors/warnings/advice, and expose downstream impact before an edit lands.

**Acceptance:**

- Broken references and cycles block publication with actionable locations.
- Locked sections cannot be overwritten without explicit confirmation.
- Proposed updates report affected documents, rules, tokens, examples, and checks.

**Verify:** `uv run pytest -q tests/brand_system/test_editing.py`

**Files:** `src/brand_maker/brand_system/editing.py`,
`src/brand_maker/brand_system/validation.py`,
`src/brand_maker/brand_system/service.py`, `tests/brand_system/test_editing.py`

**Dependencies:** Tasks 1-3. **Scope:** Medium.

#### Task 6: Approve and publish immutable versions

**Description:** Add revision-bound local-owner approval and transactional
publication with semantic version, manifest, canonical hash, and change summary.

**Acceptance:**

- Publication requires a valid approved draft revision and managed required assets.
- Relevant edits invalidate prior approval.
- Published base snapshots cannot be updated or overwritten.

**Verify:** `uv run pytest -q tests/brand_system/test_publication.py`

**Files:** `src/brand_maker/brand_system/publication.py`,
`src/brand_maker/brand_system/repository.py`, `src/brand_maker/app.py`,
`tests/brand_system/test_publication.py`

**Dependencies:** Tasks 2, 5. **Scope:** Medium.

#### Task 7: Support bounded clerical amendments

**Description:** Implement the append-only amendment ledger and historical
reconstruction for metadata, spelling, grammar, and formatting corrections.

**Acceptance:**

- Meaning/rule/token/asset/approval/applicability changes are rejected as amendments.
- Every amendment records before/after, rationale, owner, time, and ordinal revision.
- Any historical amendment revision reconstructs deterministically.

**Verify:** `uv run pytest -q tests/brand_system/test_amendments.py`

**Files:** `src/brand_maker/brand_system/amendments.py`,
`src/brand_maker/brand_system/repository.py`, `src/brand_maker/app.py`,
`tests/brand_system/test_amendments.py`

**Dependencies:** Task 6. **Scope:** Medium.

#### Task 8: Register linked and managed assets

**Description:** Register asset metadata, safely import managed files, hash content,
deduplicate bytes, validate linked paths, and snapshot required linked assets during
publication.

**Acceptance:**

- Imports enforce configured size/type/path limits and never follow unsafe archive
  paths or execute content.
- Published versions reference immutable hashes and survive removal of source paths.
- Missing or changed required linked assets block publication visibly.

**Verify:** `uv run pytest -q tests/brand_system/test_assets.py`

**Files:** `src/brand_maker/brand_system/assets.py`,
`src/brand_maker/brand_system/repository.py`,
`src/brand_maker/brand_system/publication.py`,
`tests/brand_system/test_assets.py`

**Dependencies:** Tasks 2, 6. **Scope:** Medium.

### Checkpoint B

- A workspace can be edited, validated, approved, published, amended, and restored.
- Publication failure never leaves a partial version or partial managed-asset set.
- Legacy and full verification suites pass.

### Phase C: Resumable Section Generation

#### Task 9: Define section schemas and versioned prompts

**Description:** Define the ordered section catalog, prerequisites, safe prompt
inputs, and section-specific output contracts for the comprehensive guide.

**Acceptance:**

- All approved content domains map to an explicit section contract.
- Provider output cannot redefine IDs, inject HTML, or write outside its section.
- Every prompt records version, inputs, model, rationale, and provenance.

**Verify:** `uv run pytest -q tests/generation/test_sections.py`

**Files:** `src/brand_maker/generation/sections.py`,
`src/brand_maker/generation/prompts.py`, `tests/generation/test_sections.py`

**Dependencies:** Task 1. **Scope:** Medium.

#### Task 10: Implement durable generation runs

**Description:** Persist ordered per-section state and execute bounded section calls
with validation, failover, cancellation, retry, and resume.

**Acceptance:**

- Every accepted section is saved before the next call starts.
- Failure preserves accepted/locked sections and exposes a resumable cursor.
- Complete and section-only modes share one runner and yield equivalent canonical
  results for equivalent inputs.

**Verify:** `uv run pytest -q tests/generation/test_orchestrator.py`

**Files:** `src/brand_maker/generation/orchestrator.py`,
`src/brand_maker/generation/repository.py`,
`src/brand_maker/openrouter.py`, `tests/generation/test_orchestrator.py`

**Dependencies:** Tasks 2, 5, 9. **Scope:** Medium.

#### Task 11: Expose generation controls in API and workshop

**Description:** Add start/status/pause/cancel/retry/resume routes and corresponding
accessible workshop controls and progress announcements.

**Acceptance:**

- Complete-draft and selected-section requests use the same API contract.
- The UI shows per-section progress and remains usable after pause or failure.
- Duplicate commands are idempotent and bounded.

**Verify:** `uv run pytest -q tests/generation/test_generation_api.py
tests/generation/test_generation_pages.py`; browser failure/resume check.

**Files:** `src/brand_maker/app.py`, `src/brand_maker/workshop_ui.py`,
`src/brand_maker/workshop_web.py`, `tests/generation/test_generation_api.py`,
`tests/generation/test_generation_pages.py`

**Dependencies:** Tasks 4, 10. **Scope:** Medium.

### Checkpoint C

- Complete generation can be interrupted after any section and resumed without
  repeating accepted work.
- Section-only and complete modes pass equivalence tests using deterministic fakes.
- No verification test makes a paid or live model call.

### Phase D: Publishing Views and Portable Exports

#### Task 12: Render four audience projections

**Description:** Render creator, designer, business, and agency views from one exact
published version without copied canonical decisions.

**Acceptance:**

- Every view identifies brand version and amendment revision.
- Rule/token/asset references resolve consistently in all four projections.
- Audience-specific omissions never mutate or duplicate canonical data.

**Verify:** `uv run pytest -q tests/publishing/test_projections.py`

**Files:** `src/brand_maker/publishing/projections.py`,
`src/brand_maker/publishing/web.py`, `src/brand_maker/app.py`,
`tests/publishing/test_projections.py`

**Dependencies:** Tasks 6-7. **Scope:** Medium.

#### Task 13: Implement deterministic Markdown and developer exports

**Description:** Add constrained Markdown import/export plus CSS variables, design
tokens, voice/context packages, rule packs, and change manifests.

**Acceptance:**

- Markdown round-trips every supported block and preserves unsupported safe text
  visibly while rejecting executable/raw HTML content.
- Developer exports use stable semantic names and identify their source version.
- Golden outputs are deterministic.

**Verify:** `uv run pytest -q tests/publishing/test_markdown.py
tests/publishing/test_developer_exports.py`

**Files:** `src/brand_maker/publishing/markdown.py`,
`src/brand_maker/publishing/developer_exports.py`,
`tests/publishing/test_markdown.py`,
`tests/publishing/test_developer_exports.py`

**Dependencies:** Tasks 1, 6. **Scope:** Medium.

#### Task 14: Export and restore canonical JSON archives

**Description:** Produce versioned canonical JSON and a checksum-bound ZIP containing
managed assets/evidence; validate completely before atomic import.

**Acceptance:**

- Archive paths, sizes, types, schema versions, references, and checksums are bounded
  and validated before canonical state changes.
- A valid archive restores without the original database or source paths.
- Invalid archives remain available for diagnosis and do not partially import.

**Verify:** `uv run pytest -q tests/publishing/test_archives.py`

**Files:** `src/brand_maker/publishing/archive.py`,
`src/brand_maker/brand_system/repository.py`, `src/brand_maker/app.py`,
`tests/publishing/test_archives.py`

**Dependencies:** Tasks 7-8, 13. **Scope:** Medium.

#### Task 15: Add print-ready PDF output

**Description:** Generate a tagged, navigable PDF projection from the same published
content and visually verify representative long and narrow cases.

**Acceptance:**

- PDF identifies source version, has correct heading order/bookmarks, legible color
  contrast, page numbers, unbroken critical tables, and no clipped content.
- Generated text remains searchable and the output is reproducible.
- Rendering failures preserve canonical state and return a sanitized report.

**Verify:** focused PDF tests, text extraction, page rendering, and visual inspection.

**Files:** `src/brand_maker/publishing/pdf.py`, `src/brand_maker/app.py`,
`tests/publishing/test_pdf.py`, `pyproject.toml`, `uv.lock`

**Dependencies:** Task 12. **Scope:** Medium.

**Boundary approval:** Approving this plan authorizes selecting one maintained PDF
library during Task 15 after a source-backed comparison. No dependency is added
earlier, and the selected package and lockfile change will be reported explicitly.

### Checkpoint D

- Web, Markdown, JSON, archive, token, prompt/context, rule-pack, and PDF outputs all
  identify and reproduce one source version.
- Archive restoration and PDF visual verification pass.

### Phase E: Compliance, Exceptions, and Evidence

#### Task 16: Evaluate artifacts deterministically

**Description:** Register bounded artifact revisions/hashes and produce findings for
applicable deterministic rules with exact evidence and suggested corrections.

**Acceptance:**

- Runs bind artifact revision/hash, brand version, amendment revision, tool version,
  and applicable rule IDs.
- Deterministic findings cover supported contrast, token, terminology, length,
  disclosure, and registered-dimension rules without model calls.
- Unsupported checks are explicit, never silently passed.

**Verify:** `uv run pytest -q tests/compliance/test_artifacts.py`

**Files:** `src/brand_maker/compliance/models.py`,
`src/brand_maker/compliance/deterministic.py`,
`src/brand_maker/compliance/repository.py`,
`tests/compliance/test_artifacts.py`

**Dependencies:** Tasks 6, 13. **Scope:** Medium.

#### Task 17: Compose campaigns and stale-result tracking

**Description:** Evaluate campaigns from exact artifact revisions, retain atomic
findings, add cross-artifact/channel checks, and mark affected results stale.

**Acceptance:**

- Campaign results never hide or rewrite artifact findings.
- Cross-artifact findings identify every affected artifact and rule.
- Changed artifacts mark dependent campaign results stale until reevaluated.

**Verify:** `uv run pytest -q tests/compliance/test_campaigns.py`

**Files:** `src/brand_maker/compliance/campaigns.py`,
`src/brand_maker/compliance/repository.py`, `src/brand_maker/app.py`,
`tests/compliance/test_campaigns.py`

**Dependencies:** Task 16. **Scope:** Medium.

#### Task 18: Add judgment, evidence, and time-bounded exceptions

**Description:** Keep model judgment distinct, register claim-appropriate evidence,
track verification levels, and apply visible expiring exceptions without erasing
findings.

**Acceptance:**

- Model agreement cannot produce verified status.
- Professional verification requires scoped identity, qualifications, and date.
- Expired exceptions stop altering new results; renewals append approval records;
  recurring exceptions prompt a versioned rule-change recommendation.

**Verify:** `uv run pytest -q tests/compliance/test_judgment.py
tests/compliance/test_exceptions.py`

**Files:** `src/brand_maker/compliance/judgment.py`,
`src/brand_maker/compliance/exceptions.py`,
`tests/compliance/test_judgment.py`,
`tests/compliance/test_exceptions.py`

**Dependencies:** Tasks 6, 16-17. **Scope:** Medium.

#### Task 19: Deliver the compliance browser workflow

**Description:** Add artifact/campaign setup, run progress, evidence-rich findings,
exception management, and deterministic-versus-judgment labeling to the local UI.

**Acceptance:**

- The full workflow is keyboard operable, responsive, and uses accessible live
  status/error semantics.
- Every finding exposes rule, evidence, evaluation type, confidence, status,
  suggested correction, and applicable exception.
- No raw artifact or model content is inserted as HTML.

**Verify:** `uv run pytest -q tests/compliance/test_compliance_pages.py`; browser
checks for artifact, campaign, exception, error, and stale-result flows.

**Files:** `src/brand_maker/compliance_web.py`,
`src/brand_maker/compliance_ui.py`, `src/brand_maker/app.py`,
`tests/compliance/test_compliance_pages.py`

**Dependencies:** Tasks 16-18. **Scope:** Medium.

### Phase F: Migration, Documentation, and Release Proof

#### Task 20: Complete navigation, migration guidance, and recovery docs

**Description:** Unify browser navigation, document local backup/restore and legacy
migration, update API descriptions, and remove obsolete parody-only product claims
without removing the legacy feature.

**Acceptance:**

- A new local owner can create, generate, edit, publish, export, restore, and check a
  brand using documented steps.
- Current and next-generation contracts are clearly distinguished.
- No documentation claims statelessness or parody-only scope for the whole product.

**Verify:** documentation link checks plus existing page/API tests.

**Files:** `README.md`, `pyproject.toml`, `src/brand_maker/app.py`,
`docs/specs/living-brand-system.md`,
`docs/specs/living-brand-system-implementation-plan.md`

**Dependencies:** Tasks 1-19. **Scope:** Medium.

#### Task 21: Run adversarial review and release-quality verification

**Description:** Review the complete diff across correctness, security, privacy,
accessibility, failure recovery, compatibility, performance bounds, and spec
coverage; add only evidence-backed regression fixes.

**Acceptance:**

- Every requirement has test or inspection evidence, or is explicitly deferred in
  an approved spec revision.
- Import, archive, provider, oversized-input, stale-revision, interrupted-generation,
  partial-publication, and browser injection probes pass.
- No P1/P2 review findings remain.

**Verify:** `uv run pytest -q`; `uv run ruff check src tests`;
`uv run mypy src`; `uv build`; browser and PDF verification checklists.

**Files:** Only files implicated by review findings; each correction remains a
separate test-first increment.

**Dependencies:** Tasks 1-20. **Scope:** Medium per correction.

## 6. Checkpoint Commit Policy

- Do not commit or stage over the protected baseline without explicit owner
  authorization.
- Once authorized, use one descriptive commit per completed, green vertical slice.
- Never combine an unrelated cleanup with a feature slice.
- Before each commit: inspect the exact staged diff, scan for secrets, and run the
  focused verification for that slice.
- At every phase checkpoint: run the full suite, Ruff, strict MyPy, and build.

## 7. Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| The comprehensive schema becomes uneditable | High | Begin with minimum contracts; add each domain only with a complete workflow. |
| Legacy data or routes regress | High | Additive tables/routes and compatibility tests at every checkpoint. |
| SQLite JSON snapshots hide corruption | High | Validate on every read/write, hash publications, and use transactional replacement. |
| Complete generation loses partial work | High | Persist every accepted section and test interruption at every transition. |
| Provider output crosses trust boundaries | High | Section-specific contracts, byte/token bounds, no raw HTML, sanitized errors. |
| Linked assets break reproducibility | High | Hash before publication and copy required bytes into managed storage transactionally. |
| Archive import enables traversal or partial state | High | Validate paths, sizes, types, checksums, schema, and references before atomic import. |
| Subjective checks appear authoritative | High | Separate finding types and require evidence for verified/professional statuses. |
| Dependency-free UI becomes hard to maintain | Medium | Keep pages small and route-specific; no framework migration without a new decision. |
| PDF work expands unpredictably | Medium | Delay dependency choice until canonical projections are stable; use render-and-inspect gates. |
| Existing dirty index obscures ownership | High | Preserve it exactly until explicit staging/commit authorization. |

## 8. Approval Gate

Approval of this plan authorizes:

- The implementation order and vertical slices above.
- Additive SQLite schema changes for new living-brand records.
- A source-backed PDF-library selection and dependency addition at Task 15.
- Incremental product-code, test, documentation, and lockfile changes within the
  specified files and boundaries.

It does not authorize destructive migration, deleting legacy endpoints or data,
remote hosting, authentication, paid live test calls, committing secrets/private
assets, or publishing externally.

Implementation starts with Task 1 only after this plan is approved.
