# ADR-001: One Personal Brand Operating System

## Status

Accepted

## Date

2026-07-25

## Context

The repository began with a fast parody-brand kit and later added a much broader living
brand system. The two browser experiences, data paths, and product messages diverged.
The living system can now support strategy, visual direction, governance, compliance,
assets, and publishing, so parody is an unnecessary product constraint.

The primary user is one local owner working across personal projects and ideas. Those
projects may begin as raw ideas, named concepts, or existing bodies of work. The owner
needs both low-effort autonomous generation and careful, evidence-backed control.

## Decision

Use one canonical living-brand workspace for every entry path. Retain the quick
one-name experience, but make its successful output a concept-stage workspace rather
than a separate dead-end product. Preserve legacy records and `POST /brand` behavior
additively during migration.

Generated recommendations retain rationale, provenance, source references, confidence
explanation, and verification status. Generated artwork begins as a concept asset.
Only recorded rights, accessibility, format, and visual-quality checks can promote an
asset to production-ready.

Use maturity-aware readiness: concept and working outputs may expose incompleteness,
while approved and production-ready states enforce deterministic gates.

## Alternatives Considered

### Keep parody as the primary quick-generator identity

Rejected because it limits serious projects and conflicts with the living system's
professional scope.

### Remove the quick generator immediately

Rejected because one-name generation remains a valuable low-effort entry path and its
public API is already observable behavior.

### Build a multi-user brand SaaS

Rejected for current scope. Accounts, roles, billing, real-time presence, and public
hosting add friction without serving the owner's personal workflow.

## Consequences

- Homepage, library, documentation, and prompts migrate away from parody positioning.
- Older schemas remain readable; migrations are additive and reversible.
- Quick generation must eventually create or link a canonical workspace.
- Approval and production labels become stricter, which intentionally invalidates the
  old behavior where a blank workspace could be published as complete.
- Collaboration extension points remain possible, but no team administration is built
  under the current specification.
