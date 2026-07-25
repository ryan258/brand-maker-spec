# Implementation Plan: Personal Brand Operating System

## Overview

Implement the approved specification as small vertical slices. Foundations that affect
every feature—migration, evidence, lifecycle, readiness, and audit—come first. Browser
features follow their domain contracts. Existing staged workshop and documentation
changes remain untouched until they can be reconciled deliberately.

## Progress

- Complete: Phase 0 baseline verification.
- Complete: Tasks 1.1–1.3 (lifecycle/brief, evidence/decisions, generated provenance).
- Complete: Tasks 2.1–2.2 (readiness reports and approval/publication enforcement).
- Complete: Task 3.1 (unified non-parody quick start with compatibility preservation).
- Next: Task 2.3, durable audit history and revision-safe undo/redo.

## Architecture Decisions

- Use additive Pydantic fields and SQLite migrations; never rewrite existing workspace
  JSON destructively.
- Keep one canonical workspace and project quick-start results into it.
- Store immutable source/evidence records and reference them by stable ID.
- Keep generation progress event-based while persisting only validated complete fields.
- Implement readiness as deterministic findings with visible, rationale-bound overrides.
- Use progressive enhancement and dependency-free browser JavaScript unless a new
  dependency is separately approved.
- Treat imported and researched content as untrusted boundary data.
- Preserve REST compatibility and add resources rather than silently changing shapes.

## Phase 0: Reconcile and Baseline

### Task 0.1: Protect the current working state

**Acceptance:** Existing staged and unstaged changes are inventoried; implementation
does not overwrite unrelated edits; baseline failures are documented.

**Verify:** `git status --short`, `git diff --cached --check`, focused staged tests.

**Files:** None. **Dependencies:** None. **Scope:** XS.

### Task 0.2: Establish complete verification baseline

**Acceptance:** Full tests, Ruff, MyPy, and build results are recorded before behavior
changes; known failures are separated from new work.

**Verify:** Commands from the specification.

**Files:** None. **Dependencies:** 0.1. **Scope:** XS.

## Phase 1: Canonical Foundations

### Task 1.1: Add lifecycle and structured brief contracts

**Acceptance:** All entry paths validate; existing drafts load with safe defaults;
assistance and research modes are explicit.

**Verify:** New model/migration unit tests fail first, then pass.

**Files:** `brand_system/models.py`, repository migration code, model tests.
**Dependencies:** Phase 0. **Scope:** M.

### Task 1.2: Add source, evidence, and decision records

**Acceptance:** Important canonical entities can cite immutable evidence and decisions;
invalid/dangling references fail at the boundary.

**Verify:** Model and repository round-trip tests.

**Files:** models, validation, repository, focused tests. **Dependencies:** 1.1. **Scope:** M.

### Task 1.3: Persist generation provenance

**Acceptance:** Rationale, prompt/run identity, model, inference provenance, and
confidence explanation survive generation and reload.

**Verify:** Orchestrator regression test proves metadata was previously discarded.

**Files:** generation contracts, orchestrator, repository-facing tests. **Dependencies:** 1.2. **Scope:** M.

### Checkpoint 1

- Existing databases load.
- New contracts reject invalid evidence graphs.
- Full focused brand-system and generation tests pass.

## Phase 2: Readiness, Audit, and Recovery

### Task 2.1: Implement deterministic readiness reports

**Acceptance:** Concept, working, approved, and production-ready targets return stable
finding codes; empty work cannot pass approved readiness.

**Verify:** Unit matrix covering every target and override behavior.

**Files:** readiness module, models, tests. **Dependencies:** Phase 1. **Scope:** M.

### Task 2.2: Enforce readiness at approval and publication

**Acceptance:** Blank publication regression fails before implementation and passes
after; warnings can be acknowledged but blockers cannot be erased.

**Verify:** Publication integration tests and exact-revision conflict tests.

**Files:** publication service, app routes, tests. **Dependencies:** 2.1. **Scope:** M.

### Task 2.3: Persist audit history and undo/redo

**Acceptance:** Meaningful mutations create reversible audit records; undo/redo uses
optimistic revision checks and cannot rewrite published snapshots.

**Verify:** Repository and API integration tests.

**Files:** audit module, repository, routes, tests. **Dependencies:** 1.2. **Scope:** M.

### Task 2.4: Add soft delete, backup, and restore

**Acceptance:** Trash is recoverable, backups bind database content and managed assets,
and restore validates hashes before mutation.

**Verify:** Tamper, stale revision, missing asset, and successful restore tests.

**Files:** backup module, repository/routes, tests. **Dependencies:** 2.3. **Scope:** M.

### Checkpoint 2

- Empty approval/publication is impossible.
- Audit and recovery tests pass.
- Archive/path/security probes pass.

## Phase 3: Unified Entry and Discovery

### Task 3.1: Replace parody positioning with unified quick start

**Acceptance:** Homepage describes the personal brand OS; quick generation creates a
concept workspace; legacy `POST /brand` remains compatible.

**Verify:** Page contract, API compatibility, and migration tests.

**Files:** homepage, quick-start client, routes/service, tests. **Dependencies:** 1.1. **Scope:** M.

### Task 3.2: Add entry-path and assistance-mode UI

**Acceptance:** Raw idea, named concept, and existing project are keyboard-accessible
creation choices; advisor/copilot/autonomous mode is explained and saved.

**Verify:** Browser-shell tests and DevTools creation walkthrough.

**Files:** workshop shell/client/styles, page tests. **Dependencies:** 3.1. **Scope:** M.

### Task 3.3: Add structured brief and evidence intake

**Acceptance:** Brief fields save incrementally; suggested answers reduce typing;
source type and privacy state are visible.

**Verify:** API autosave, stale revision, accessibility, and reload tests.

**Files:** service/routes, workshop client/shell, tests. **Dependencies:** 1.2, 3.2. **Scope:** M.

### Task 3.4: Add explicit project and document import

**Acceptance:** Only selected paths/URLs are read; PDF/document/site/assets become
bounded source records; hostile content cannot become instructions or raw HTML.

**Verify:** Boundary, traversal, size, type, timeout, and provenance tests.

**Files:** importing module, routes, contracts, tests. **Dependencies:** 3.3. **Scope:** M.

### Checkpoint 3

- All four entry paths create canonical workspaces.
- No user-facing parody positioning remains.
- Import threat-model probes pass.

## Phase 4: Adaptive Generation

### Task 4.1: Stream validated generation progress and estimates

**Acceptance:** Users see section/field progress and estimated cost before execution;
partial invalid model output is never saved as canonical content.

**Verify:** Event sequence, cancellation, reconnect, and estimate tests.

**Files:** generation service/contracts, routes, client, tests. **Dependencies:** 1.3. **Scope:** M.

### Task 4.2: Add field regeneration and posture controls

**Acceptance:** One field can be regenerated in conservative/balanced/bold posture;
the proposal does not overwrite accepted content.

**Verify:** Proposal identity and merge tests.

**Files:** prompts/orchestrator, routes/client, tests. **Dependencies:** 4.1. **Scope:** M.

### Task 4.3: Add alternatives, comparison, merge, and prompt view

**Acceptance:** Two or three variants can be compared and selectively merged; exact
prompt and model provenance remain visible; power-user edits are versioned.

**Verify:** Contract, merge, escaping, and browser interaction tests.

**Files:** generation models/service, client/shell, tests. **Dependencies:** 4.2. **Scope:** M.

### Task 4.4: Add critique, token suggestion, and explicit fallback

**Acceptance:** Critique reports contradictions without mutation; token suggestions are
proposals; model failure exposes a safe retry/fallback choice.

**Verify:** Contradiction fixtures, provider error matrix, browser flow.

**Files:** critique module, generation service/client, tests. **Dependencies:** 4.3. **Scope:** M.

### Checkpoint 4

- Advisor, copilot, and autonomous workflows pass focused end-to-end tests.
- Generated-versus-edited diffs and provenance are visible.

## Phase 5: Asset Studio and Qualification

### Task 5.1: Extend asset metadata and qualification

**Acceptance:** Existing assets migrate; generated/derived files default to concept;
production-ready requires recorded rights, format, accessibility, and visual checks.

**Verify:** Lifecycle and publication-readiness tests.

**Files:** asset models/service, repository, tests. **Dependencies:** 2.1. **Scope:** M.

### Task 5.2: Add asset validation and palette extraction

**Acceptance:** Resolution/size warnings, metadata extraction, palette proposals, and
logo/background contrast results are deterministic and visible.

**Verify:** Image fixtures, malformed media, and contrast tests.

**Files:** asset processing, service/routes, tests. **Dependencies:** 5.1. **Scope:** M.

### Task 5.3: Add background removal and font wiring

**Acceptance:** Originals remain unchanged; derivatives retain lineage; uploaded fonts
use validated formats and safe generated `@font-face` declarations.

**Verify:** Media processing, font escaping, and browser rendering tests.

**Files:** asset processing, bible theme, routes, tests. **Dependencies:** 5.1. **Scope:** M.

### Task 5.4: Add versioned comparison gallery

**Acceptance:** All logo versions and derivatives can be compared, restored, and
qualified without overwriting their source.

**Verify:** API ordering, lineage, restore, and browser gallery tests.

**Files:** asset service/routes, workshop client/styles, tests. **Dependencies:** 5.2. **Scope:** M.

### Checkpoint 5

- No generated asset is mislabeled production-ready.
- Asset transformation and malicious-file probes pass.

## Phase 6: Brand-Connected Quality and Compliance

### Task 6.1: Bind evaluations to an exact brand revision

**Acceptance:** Compliance selects a workspace/publication and loads its real supported
rules/tokens; generic rules appear only in sandbox mode.

**Verify:** Regression test reproduces the current hard-coded-rule behavior first.

**Files:** compliance models/service, routes/client, tests. **Dependencies:** 2.1. **Scope:** M.

### Task 6.2: Add brand health and deterministic quality checks

**Acceptance:** Coverage, contradictions, duplicate/conflicting tokens, rules without
examples, contrast pairs, and readability produce stable explainable findings.

**Verify:** Focused rule fixtures and score-boundary tests.

**Files:** compliance checks/models, tests. **Dependencies:** 6.1. **Scope:** M.

### Task 6.3: Add local status center and scheduled drift checks

**Acceptance:** Asset drift and stale verification appear locally; schedules are
disabled by default, reversible, and do not require email.

**Verify:** Clock-controlled scheduler and browser status tests.

**Files:** compliance scheduler/store, routes/UI, tests. **Dependencies:** 6.2. **Scope:** M.

### Checkpoint 6

- Fieldwell-style rules alter compliance results.
- Deterministic, judgment, unsupported, and evidence labels remain distinct.

## Phase 7: Governance Browser Workflow

### Task 7.1: Surface impact, review, locking, and personal notes

**Acceptance:** Section changes preview downstream impact; AI proposals and personal
review notes are visible; decision locks are understandable and reversible.

**Verify:** API and browser state-transition tests.

**Files:** workshop shell/client/styles, routes/tests. **Dependencies:** 2.3, 4.3. **Scope:** M.

### Task 7.2: Surface readiness, approval, and publication

**Acceptance:** The browser displays every readiness finding, captures exact-revision
rationale, and cannot publish until the chosen target passes.

**Verify:** DevTools happy path plus blocker/override/stale-revision paths.

**Files:** governance UI/client, routes, tests. **Dependencies:** 2.2. **Scope:** M.

### Task 7.3: Surface history, amendments, backups, and restore

**Acceptance:** Users can compare revisions, view audit history, apply allowed
corrections, download backups, and perform validated restores.

**Verify:** Browser workflow and destructive-action confirmation tests.

**Files:** governance UI/client, routes, tests. **Dependencies:** 2.3–2.4. **Scope:** M.

### Checkpoint 7

- The README workflow is possible without opening API documentation.

## Phase 8: Visual Bible and Purpose-Built Outputs

### Task 8.1: Add token specimens and accessibility boards

**Acceptance:** Color chips, contrast pairs, font specimens, type scales, dark preview,
and non-color labels render from canonical tokens.

**Verify:** Semantic HTML, contrast logic, print, and browser visual checks.

**Files:** bible renderer/styles, tests. **Dependencies:** 5.1, 6.2. **Scope:** M.

### Task 8.2: Add logo, layout, imagery, and channel boards

**Acceptance:** Canonical patterns/assets render as clear-space, misuse, layout,
component-state, image-direction, and channel examples where data exists.

**Verify:** Golden semantic fixtures and mobile/print screenshots.

**Files:** bible renderer/styles, pattern tests. **Dependencies:** 5.4. **Scope:** M.

### Task 8.3: Add active navigation, notes, and revision changes

**Acceptance:** Current section highlights on scroll; anchored personal notes and exact
revision differences are accessible and print-safe.

**Verify:** Browser scroll, keyboard, reduced-motion, and print tests.

**Files:** bible renderer/client/styles, tests. **Dependencies:** 7.3. **Scope:** M.

### Task 8.4: Rebuild audience projections

**Acceptance:** Each audience contract includes its required rules, tokens, examples,
patterns, assets, evidence, and tailored explanatory structure; no nonexistent section
IDs remain.

**Verify:** Projection completeness matrix and export tests.

**Files:** projections, web/PDF renderers, tests. **Dependencies:** 8.1–8.2. **Scope:** M.

### Checkpoint 8

- Populated desktop, mobile, and print outputs visually teach the brand system.
- Accessibility and export semantics pass.

## Phase 9: Guidance and Low-Typing Experience

### Task 9.1: Add guided tour, glossary, and sample workspaces

**Acceptance:** First run teaches the core lifecycle; sample brands are cloneable;
terminology is available in context without blocking work.

**Verify:** First-run and returning-user browser tests.

**Files:** onboarding UI/data, workshop integration, tests. **Dependencies:** Phase 7. **Scope:** M.

### Task 9.2: Add checklists, validation, nudges, and next-step guidance

**Acceptance:** Empty states and progress use readiness data; suggestions are selectable
and dismissible; validation is announced accessibly.

**Verify:** State matrix and keyboard/browser tests.

**Files:** workshop client/shell/styles, tests. **Dependencies:** 2.1, 3.3. **Scope:** M.

### Task 9.3: Reorder and refine mobile workflow

**Acceptance:** Status and section navigation precede secondary asset tooling; touch and
keyboard targets remain usable; no horizontal overflow exists at 320 CSS pixels.

**Verify:** DevTools at 320, 390, tablet, and desktop widths; Lighthouse accessibility.

**Files:** workshop shell/styles/client, tests. **Dependencies:** 9.2. **Scope:** M.

## Phase 10: Imports, Exports, and Project Automation

### Task 10.1: Add DTCG tokens and starter components

**Acceptance:** Exports are deterministic, syntax-safe, semantically named, and include
metadata binding them to exact versions.

**Verify:** Parser/compile tests for JSON, CSS, HTML, and JavaScript outputs.

**Files:** publishing exporters, routes, tests. **Dependencies:** 8.1. **Scope:** M.

### Task 10.2: Add SDK snippets, CLI sync, and local read API

**Acceptance:** Python/JS snippets and CLI pull/push use documented stable contracts,
optimistic revisions, and safe local defaults.

**Verify:** CLI subprocess and OpenAPI contract tests.

**Files:** CLI module, routes/contracts, tests. **Dependencies:** 10.1. **Scope:** M.

### Task 10.3: Add signed webhooks and rate-limit contract

**Acceptance:** Opt-in webhooks are signed, timestamped, replay-protected, redacted,
and retry with bounded backoff; 429 semantics are documented and tested.

**Verify:** Signature, replay, timeout, retry, SSRF, and secret-redaction tests.

**Files:** webhook module, routes/settings, tests. **Dependencies:** 7.2. **Scope:** M.

### Task 10.4: Add sandbox, truthful examples, and API policy

**Acceptance:** A seeded example brand powers OpenAPI/SDK examples without contaminating
real data; deprecation and changelog policy is visible.

**Verify:** Sandbox isolation and docs contract tests.

**Files:** sandbox data/service, app/docs, tests. **Dependencies:** 10.2. **Scope:** M.

### Checkpoint 10

- Export syntax/security probes pass.
- CLI and webhook integration tests pass without external network dependency.

## Phase 11: Portfolio Intelligence

### Task 11.1: Add local usage and workflow analytics

**Acceptance:** Local-only metrics identify stalled sections and generation outcomes;
collection is transparent, bounded, and erasable.

**Verify:** Aggregation and privacy tests.

**Files:** analytics store/service, status UI, tests. **Dependencies:** audit history. **Scope:** M.

### Task 11.2: Add multilingual bible projections

**Acceptance:** Translations reference one canonical source revision, share non-language
tokens, retain provenance, and visibly mark unverified language output.

**Verify:** Locale, fallback, drift, and export tests.

**Files:** localization models/service, publishing, tests. **Dependencies:** 8.4. **Scope:** M.

### Task 11.3: Add competitor positioning report

**Acceptance:** Owner-selected projects or cited public sources produce an evidence-bound
comparison that distinguishes facts from inference and avoids unsupported superiority
claims.

**Verify:** Source, citation, injection, and claim-label tests.

**Files:** research/report module, generation integration, tests. **Dependencies:** 3.4, 6.2. **Scope:** M.

## Phase 12: Documentation and Release Verification

### Task 12.1: Update product and API documentation

**Acceptance:** README, API examples, migration guidance, privacy model, maturity labels,
and operational commands match the implemented product; parody is historical only.

**Verify:** Documentation links/examples and OpenAPI tests.

**Files:** README, specs/ADRs, API docs tests. **Dependencies:** prior phases. **Scope:** M.

### Task 12.2: Complete end-to-end release verification

**Acceptance:** All success criteria pass; included roadmap items move to the changelog;
deferred items remain documented; no staged review blocker is unresolved.

**Verify:** Full tests, Ruff, MyPy, build, `git diff --check`, desktop/mobile DevTools,
console/network inspection, Lighthouse, PDF render inspection, and archive restore.

**Files:** roadmap/changelog and necessary test evidence only. **Dependencies:** all. **Scope:** M.

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Scope is too large for one safe patch | High | Land vertical slices with explicit checkpoints and keep incomplete surfaces hidden. |
| Existing staged changes overlap workshop files | High | Inventory and reconcile before edits; never reset or overwrite user work. |
| Schema evolution breaks stored brands | High | Additive defaults, migration fixtures, round-trip old snapshots. |
| Research/import leaks private material | High | Explicit selection, opt-in external use, provenance, redaction, and adversarial boundary tests. |
| Generated output implies unsupported authority | High | Enforced maturity labels and immutable qualification evidence. |
| Browser HTML/JS becomes monolithic | Medium | Extract domain renderers only after repeated patterns justify them; retain contract tests. |
| Export surface expands injection risk | High | Parser-based tests, strict serialization, bounded archives, and no raw template interpolation. |
| Local background jobs surprise the owner | Medium | Disabled by default, visible schedules, bounded work, and one-click disable/clear. |

## Human Review Gate

Implementation begins only after explicit approval of:

1. `personal-brand-os.md`;
2. `personal-brand-os-roadmap.md`; and
3. this dependency-ordered plan.
