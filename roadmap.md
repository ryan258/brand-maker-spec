# Personal Brand OS Roadmap

A high-level view of product direction, delivered capabilities, and upcoming priorities for Brand System Maker.

For the comprehensive specification and milestone plan, see:
- [`docs/specs/personal-brand-os.md`](docs/specs/personal-brand-os.md)
- [`docs/specs/personal-brand-os-implementation-plan.md`](docs/specs/personal-brand-os-implementation-plan.md)
- [`docs/specs/personal-brand-os-roadmap.md`](docs/specs/personal-brand-os-roadmap.md)
- [`docs/100-ideas-for-enhancement.md`](docs/100-ideas-for-enhancement.md)

---

## Current State & Delivered Capabilities

Brand System Maker is a local-first personal brand operating system for turning raw ideas, named concepts, and existing projects into researched, versioned living brands.

### 1. Workspace & Discovery
- **Multi-Path Entry**: First-class intake for raw ideas, named concepts, existing projects, and quick-start generations (`POST /api/brands`).
- **Autosaving Brief**: Structured brief with starter suggestions, low-typing answers, and persistent evidence intake (`private-local` vs `research-approved`).
- **Resilient Recovery**: Bounded undo/redo (`MAX_UNDO_DEPTH = 20`), recoverable trash with restore, and portable checksum-verified backups (`.zip`).

### 2. Resilient Generation & Anchors
- **Streaming & Controls**: Live SSE section generation progress, pause, resume, cancel, and automatic run reattachment after page reload (`GET /api/brand-systems/{id}/generation-runs/latest`).
- **Protected Anchors**: Locked sections and approved sections are preserved during complete draft regeneration and serve as immutable context.
- **Concurrent Edit Priority**: User edits and locks made while background generation is running take precedence; the generated section is dropped as `preserved_edited`.
- **Field & Posture Variants**: Single-field regeneration and posture proposals (conservative, balanced, bold).

### 3. Production Assets & Visual Identity
- **Logo Suite & Derivatives**: AI raster logo generation, favicon and app-icon crops, AI monochrome/inverted/icon variants, and local raster-to-SVG vectorization.
- **Font & Color Verification**: Magic-byte font validation, safe `@font-face` generation, and WCAG AA/AAA logo contrast analysis against brand background tokens.

### 4. Living Brand Bible & Projections
- **Interactive Brand Bible**: Navigable living source of truth, dark-mode preview derived from paper/ink tokens, active table of contents, and print/PDF optimization.
- **Audience Projections**: Creator, designer, business, and agency views rendering narrative prose alongside enforceable rules, tokens, examples, and production assets.
- **Export Formats**: Robust Markdown interchange (backtick-safe), print-ready PDF/UA, and downloadable brand-kit bundles (`.zip`) with asset integrity verification.
- **Developer Token Exports**: CSS custom properties, Tailwind configuration with injection-safe string literal escaping, and stable/unique token identifiers.

### 5. Readiness, Governance & Compliance
- **Maturity-Aware Readiness**: Readiness reports enforce required core sections (`strategy`, `messaging`, `voice`, `color`, `typography`) and flag unverified claims.
- **Decision Verification**: `POST /api/brand-systems/{id}/decision-verifications` enables owners to verify or waive factual claims to unlock production readiness.
- **Deterministic Compliance**: Results bound to exact artifact hash, full rule definitions (`rule_set_hash`), and published brand identity (`brand_id`). Expiring exceptions and evidence tracking.
- **Immutable Publication**: Semantically versioned releases with required asset verification, atomic database transactions, and canonical content hashes.

---

## Implementation Status Summary

| Capability Area | API / Engine | Browser UI | Status |
|---|---|---|---|
| Workspace creation, brief, evidence intake | Complete | Complete | Shipped |
| Streaming generation, pause/resume/cancel | Complete | Complete | Shipped |
| In-flight run reattachment after reload | Complete | Complete | Shipped |
| Section locking & approved anchor protection | Complete | Partial (API lock) | Shipped |
| Readiness assessment & gating | Complete | Complete | Shipped |
| Decision verification API | Complete | Planned | Shipped |
| In-place bible editing, dark preview, TOC | Complete | Complete | Shipped |
| Audience projections (HTML, PDF) | Complete | Complete | Shipped |
| Developer token exports (CSS, Tailwind, JSON)| Complete | Complete | Shipped |
| Brand-kit archives & portable backups | Complete | Complete | Shipped |
| Undo / redo / trash / restore | Complete | Planned | Engine Shipped |
| Deterministic compliance engine | Complete | Complete | Shipped |
| Publication-bound compliance checking | Complete | Planned | Shipped |
| Exact publication & amendment release flows | Complete | Planned | Engine Shipped |

---

## Upcoming Roadmap Priorities

1. **Phase 3.4 — Bounded Project & Document Import**:
   - Ingest existing markdown files, web pages, and local repositories into structured workspace briefs and assets.
2. **Visual Teaching Boards**:
   - Visual inspection cards for typography scales, color palettes, logo lockups, and layout grids.
3. **Browser Governance Controls**:
   - Dedicated UI actions in the workshop for section locking, draft approval, semantic publication, revision rollback, and backup restore.
4. **Local Scheduled Compliance Auditing**:
   - In-app status center for scheduled drift detection across registered artifacts without external email/SaaS dependencies.
5. **Developer SDK & CLI Sync**:
   - Revision-safe CLI for token and asset synchronization directly into local frontend projects.

---

## Out of Scope (Deferred / Non-Goals)

To preserve the local-first, single-owner focus and privacy boundaries:
- Multi-user accounts, real-time presence, and role-based permissions.
- Cloud hosting, metered API subscriptions, and third-party SaaS billing.
- Automatic publishing without explicit owner approval.
- Team comment threads (replaced by personal decision/review notes).
