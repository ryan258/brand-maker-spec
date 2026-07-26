# Changelog

## Unreleased

### Added

- Added canonical raw-idea, named-concept, existing-project, and quick-start entry
  paths with adaptive assistance and controlled-research metadata.
- Added durable evidence and decision records so generated guidance retains rationale,
  provenance, confidence explanation, prompt version, model, and generation-run identity.
- Added maturity-aware readiness reports and blocked approval/publication of empty or
  materially incomplete brand systems.
- Made every successful browser quick start create a concept-stage living workspace
  while preserving the saved quick-kit record and compatibility API.
- Added keyboard-accessible creation choices for raw ideas, named concepts, and
  existing projects, with explicit advisor/copilot/autonomous and research boundaries.
- Added an incrementally autosaved structured brief with low-typing starter answers,
  plus evidence intake that preserves source type and visible privacy state.
- Made section generation obey the founding brief: the brief's objective, audience,
  category, differentiators, constraints, existing equity, and success measures, plus
  the workspace concept and maturity stage, are supplied to every section-generation
  request. Added an **Update to match brief** control that regenerates unlocked
  sections to obey the current brief while preserving locked sections.

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

- Fixed complete-draft generation that could never finish: the section-generation
  prompt now shows the model the section container and its block, rule, example, token,
  and pattern contracts, so schema-conforming sections are produced instead of failing
  `extra="forbid"` validation on every retry.
- Made the generation envelope strip known prompt-scaffolding keys models echo back
  (at the envelope root and inside the section) while still rejecting genuine injected
  keys, so an otherwise-correct section is no longer rejected for an echoed field.
- Surfaced the real per-attempt validation error on a failed generation section instead
  of a generic message, and logged it, so generation failures are diagnosable.

### Changed

- Reframed the product as a personal brand operating system rather than a parody-only
  generator; legacy quick-kit fields remain available for compatibility.
- Replaced parody-oriented homepage, library, generation, and evaluation language with
  broad original-brand positioning.
