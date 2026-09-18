# Changelog

## Unreleased

### Added

- Added canonical raw-idea, named-concept, existing-project, and quick-start entry
  paths with adaptive assistance and controlled-research metadata.
- Added durable evidence and decision records so generated guidance retains rationale,
  provenance, confidence explanation, prompt version, model, and generation-run identity.
- Added maturity-aware readiness reports that block approval and publication of brand
  systems missing a required core section, missing canonical content in a section, or
  holding sections that are not yet reviewed or approved.
- Made every successful browser quick start create a concept-stage living workspace
  while preserving the saved quick-kit record and compatibility API.
- Added keyboard-accessible creation choices for raw ideas, named concepts, and
  existing projects, with explicit advisor/copilot/autonomous and research boundaries.
- Added an incrementally autosaved structured brief with low-typing starter answers,
  plus evidence intake that preserves source type and visible privacy state.
- Made section generation obey the founding brief: the brief's objective, audience,
  category, differentiators, constraints, existing equity, and success measures, plus
  the workspace concept and maturity stage, are supplied to every section-generation
  request. The complete-draft refresh regenerates unlocked sections from the current
  brief while preserving locked sections.
- Added optional `brand_context` input to quick-start generations and API requests (`POST /api/brands`), allowing initial brand notes (up to 50,000 characters) to be passed safely into quick-start generation and automatically populated on the living workspace.

- **Idea 1:** Moved AI logo generation above the section editor.
- **Idea 2:** Added inline logo and image thumbnails to the asset list.
- **Idea 3:** Added debounced section autosave.
- **Idea 4:** Added dirty-navigation warnings for unsaved section edits.
- **Idea 5:** Added drag and button-based reordering for section content.
- **Idea 6:** Added duplication controls for existing section content.
- **Idea 7:** Added keyboard shortcuts for saving and inserting content.
- **Idea 8:** Added a per-section content-completeness meter.
- **Idea 9:** Made Prose, Rules, Tokens, Examples, and Patterns collapsible.
- **Idea 10:** Added live word and character counts to narrative fields.
- **Idea 11:** Added SSE-based live generation progress streaming.
- **Idea 12:** Added single field/block regeneration with rationale tracing.
- **Idea 15:** Added candidate section variant proposals across conservative, balanced, and bold postures.
- **Idea 21:** Added favicon and app-icon crops for raster logos.
- **Idea 22:** Added AI-generated monochrome, inverted, horizontal-lockup, and
  icon-only logo variants.
- **Idea 23:** Added local raster-to-SVG logo vectorization.
- **Idea 25:** Added validated font uploads with magic byte verification and safe `@font-face` CSS generation.
- **Idea 30:** Added automated logo color contrast analysis against brand background tokens.
- **Idea 31:** Added a reversible dark-mode bible preview derived from the brand's
  current paper and ink tokens, while keeping print output light.
- **Idea 34:** Added reduced-motion-safe active table-of-contents tracking as the
  reader moves through the brand bible.
- **Idea 58:** Added a durable local audit feed with changed fields and optional
  owner rationale for canonical edits.
- **Idea 61:** Added copy compliance checking engine against active living brand rules.
- **Idea 64:** Added cross-section token collision and duplicate key detection.
- **Idea 66:** Added WCAG AA/AAA design token contrast pair auditing.
- **Idea 68:** Added canonical validation for broken cross-section references.
- **Idea 69:** Added a browser workflow for visible, expiring compliance exceptions
  and supporting evidence.
- **Idea 71:** Added direct PDF, Markdown, and ZIP export actions to the brand bible.
- **Idea 72:** Added CSS custom-property, Tailwind, and JSON token exports.
- **Idea 76:** Added immutable, semantically versioned brand releases.
- **Idea 77:** Added downloadable brand-kit bundles with the bible, tokens, and
  registered production assets.
- **Idea 91:** Added optimistic-lock-safe undo and redo without rewriting immutable
  published versions.
- **Idea 92:** Persisted reversible before/after history for each canonical workspace
  mutation, including explicit undo and redo events.
- **Idea 93:** Added revision-checked soft deletion, a bounded recoverable trash, and
  explicit restore without silently duplicating saved-kit workspaces.
- **Idea 94:** Added portable per-brand workspace backups with bounded ZIP parsing,
  manifest checksums, asset-integrity validation, and conflict-safe restore.
- **Idea 99:** Added responsive single-column workshop layouts and wrapping controls.

### Fixed

- Stopped a brand name from injecting executable JavaScript into the exported Tailwind
  config: the name is now written as an escaped JSON string literal, so a Unicode line
  separator (U+2028/U+2029) can no longer close the comment and start a statement.
- Made exported token identifiers stable and unique: `token.a.b` and `token.a-b` no
  longer collapse into one `--brand-token-a-b` declaration, draft and published exports
  share one naming policy, and a name collision is reported instead of silently merged.
- Stopped generation from overwriting an owner's lock or edit: when the target section
  changed while the model was working, the owner's version is kept and the run reports
  that section as `preserved_edited`.
- Made pause and cancel durable: a run re-reads the persisted control state before
  committing generated output, so a finishing worker can no longer erase a pause or
  cancel that was issued during the provider call.
- Made an approved section an anchor for generation, as the walkthrough promised;
  previously only an explicit lock protected content.
- Bound compliance results to the exact evaluated input: the artifact hash now covers
  declared tokens, foreground/background colors, and dimensions, and a stored result is
  keyed by the rule definitions, brand identity, and publication content hash, so a
  saved pass can no longer be returned for an artifact that now fails.
- Made readiness enforce the completeness it claims: an approved brand system must
  contain its core sections, and unverified decisions are reported (blocking for
  production-ready). Added `POST /api/brand-systems/{id}/decision-verifications` so the
  owner can record verification.
- Made publication revalidate required managed assets, so a draft whose required managed
  blob is missing or altered can no longer be published.
- Made archive import verify what the publication claims, not just the ZIP: the
  canonical content hash, manifest/snapshot agreement, approval and amendment ownership,
  and the reapplied amendment result are all checked before the archive is accepted.
- Fixed publication archives failing to round-trip when two asset registrations share
  one blob, and stopped archive creation from assuming an optional linked asset lives
  under the managed root.
- Made archive import atomic: the asset tree is replaced inside the database
  transaction, so a database conflict no longer leaves replaced assets behind.
- Fixed Markdown interchange breaking on a backtick in the brand name or prose, and
  rendered rules, tokens, examples, and assets in the readable Markdown instead of
  leaving them only inside the embedded JSON.
- Added rules, tokens, examples, and assets to the HTML and PDF audience outputs, and
  removed the audience mapping's reference to a `section.audience` that does not exist.
- Stopped autosave from retrying a permanent failure forever: a 409 or 422 keeps the
  unsaved section, stops the automatic retry loop, offers an explicit Retry save, and
  no longer blocks brief saving.
- Restored every substantive brief field to the generation prompt; a brief holding only
  constraints and differentiators previously reached the model as nothing at all.
- Bounded token values to 2,000 characters so an unbounded string cannot reach a prompt
  or an export.
- Moved published PDF and archive generation off the event loop, and checked the brand
  kit size estimate before rendering rather than after.
- Fixed complete-draft generation that could never finish: the section-generation
  prompt now shows the model the section container and its block, rule, example, token,
  and pattern contracts, so schema-conforming sections are produced instead of failing
  `extra="forbid"` validation on every retry.
- Made the generation envelope strip known prompt-scaffolding keys models echo back
  (at the envelope root and inside the section) while still rejecting genuine injected
  keys, so an otherwise-correct section is no longer rejected for an echoed field.
- Surfaced the real per-attempt validation error on a failed generation section instead
  of a generic message, and logged it, so generation failures are diagnosable.
- Excluded target section's own pre-brief/stale content from `accepted_context` during section generation and brief-matching reruns, avoiding self-contradictory prompt instructions.
- Expanded `accepted_context` filtering to transitive prerequisite closures (`prerequisite_closure`), ensuring downstream sections receive necessary color palette, typography, and layout rules.
- Hydrated pattern metadata in `accepted_context`, capped narrative prose/rules/examples/patterns text length to 1,000 characters, and capped item array bounds to keep prompt context size bounded.
- Bumped section generation prompt version to `living-brand-section-v3` and optimized section generation by hoisting prompt construction outside completion retry loops.

### Changed

- Added a Resume control to the workshop's generation panel and reattachment to an
  in-flight or paused run after reload (`GET /api/brand-systems/{id}/generation-runs/latest`),
  so reloading no longer strands a run or starts a second one.
- Corrected the happy-path walkthrough: hand-editing alone does not protect a section
  (lock or approve it), and generating one section also regenerates its unlocked
  prerequisites.
- Corrected the root architecture document: the application is local-first but not
  offline-capable — startup requires an OpenRouter key, generation is remote, and some
  browser pages load fonts from a public CDN.
- Reframed the product as a personal brand operating system rather than a parody-only
  generator; legacy quick-kit fields remain available for compatibility.
- Replaced parody-oriented homepage, library, generation, and evaluation language with
  broad original-brand positioning.
- Modularized application routes from monolithic `app.py` into dedicated sub-routers under `src/brand_maker/routes/` (`workspaces`, `assets`, `publication`, `exports`, `generation`, `compliance`, and `pages`).
- Replaced Python-embedded CSS/JS string modules (`ui.py`, `workshop_ui.py`, `library_ui.py`, `compliance_ui.py`) with static asset files served at `/assets`.
- Bounded undo audit history storage in SQLite (`MAX_UNDO_DEPTH = 20`) via `_prune_audit_snapshots` to prevent database size bloat.
- Optimized paginated workspace list queries with SQLite `json_extract` to eliminate full JSON model deserialization overhead.
- Ensured thread-safe queue event notifications in `GenerationOrchestrator` using `event_loop.call_soon_threadsafe`.
- Added optimistic draft locking conflict retries (up to 3 attempts) in `_persist_generated_section` for concurrent generation runs.
- Enforced zip entry (25 MB) and total archive (250 MB) safety limits in developer brand-kit exports and early `Content-Length` checks on file upload streams.
- Guarded managed asset file unlinking with `is_referenced` content-hash verification to protect shared content blobs.
