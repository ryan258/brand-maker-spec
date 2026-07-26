# Product Specification: Living Brand System

> Status: Product decisions resolved; awaiting final specification approval
> Product: Brand System Maker  
> Scope: Next-generation comprehensive style-guide system  
> Last updated: 2026-07-23

## 1. Objective

Evolve Brand System Maker from a generator of small, immutable brand kits into a
local-first brand operating system: one editable source of truth that produces a
browsable style guide, portable exports, audience-specific guidance, reusable AI
context, and explainable compliance results.

The product serves four equally weighted audiences:

1. Solo creators who need approachable guidance and useful defaults.
2. Professional designers who need exact specifications and implementation rules.
3. Small businesses that need practical messaging and channel playbooks.
4. Agencies that need rationale, governance, review, and client-ready handoff.

Success requires all three of these outcomes:

- A polished, accessible, browsable style-guide website.
- Downloadable documents and machine-readable exports.
- Actionable rules that keep future content and design work consistent.

## 2. Product Thesis

A comprehensive brand guide should not be one long AI-authored document. It should
be a hybrid system with two canonical layers:

- **Narrative documents** hold strategy, reasoning, interpretation, and creative
  direction where nuance matters.
- **Structured rules and tokens** hold measurable or enforceable decisions such as
  colors, typography roles, spacing, terminology, accessibility constraints, and
  channel requirements.

Documents may reference and explain rules, but may not silently redefine them.
Web guides, PDFs, audience views, prompts, token files, and compliance checks are
generated projections of the same approved brand version.

## 3. Assumptions

This draft proceeds with the following assumptions. Open questions in Section 20
may change them before implementation planning.

1. The product remains local-first and privacy-aware.
2. A single brand is the initial unit of authoring, publication, and export.
3. The existing `POST /brand` contract remains available during migration.
4. Every generated brand system begins as an editable draft.
5. A published version's base snapshot is immutable. Non-semantic metadata,
   spelling, grammar, and formatting corrections may be applied through an
   append-only amendment ledger; all meaning-changing edits require a new version.
6. Strategy is document-first; execution rules are structure-first.
7. Every important recommendation records rationale, provenance, confidence, and
   any professional-verification requirement.
8. The product may generate concept artwork and governed derivatives. Generated work
   remains a concept until the production-readiness checks defined by
   `personal-brand-os.md` are recorded. Publication snapshots every required asset into
   managed, content-addressed local storage.
9. Deterministic and judgment-based compliance results remain visibly distinct.
10. Multi-brand inheritance and sub-brand overrides are deferred until the
    single-brand system is proven.
11. The foundation product has one local owner. That owner may author, review,
    approve, publish, amend, and retire content without accounts, roles, invitations,
    or collaboration permissions. Governance actions still retain timestamps,
    rationale, and revision attribution for history and portable handoff.
12. Compliance supports both independently evaluable artifacts and campaigns that
    compose artifacts for cross-channel and cross-artifact evaluation.
13. Creative exceptions are narrowly scoped, time-bounded, explicitly approved,
    and visible in compliance results rather than silently suppressing rules.
14. Approval and verification are distinct: subjective recommendations may be
    approved, while objective or professional claims require claim-appropriate
    evidence before they are marked verified.
15. Portability uses a two-layer contract: versioned JSON is the normative logical
    representation, and a checksum-bound archive is the normative self-contained
    transport for JSON, managed assets, and embedded evidence.
16. Narrative documents use a constrained block model as canonical content, with
    documented Markdown import and export as a portable human-readable projection.
17. Complete-draft and section-by-section generation are two entry points into one
    ordered, resumable section pipeline; neither uses a separate monolithic model
    request or a competing generation contract.

## 4. User Jobs

### Solo creator

When I have a brand idea but limited design experience, I want guided decisions and
plain-language examples so I can create coherent work without learning an entire
professional vocabulary first.

### Professional designer

When I receive or develop a brand direction, I want exact, editable rules and
portable tokens so I can implement the system without reverse-engineering prose.

### Small business

When my team creates customer-facing material, I want practical messaging and
channel guidance so our work sounds and feels consistent without constant review.

### Agency

When I create and hand off a client brand, I want rationale, approvals, versions,
exceptions, and audience-appropriate publications so the system remains usable
after delivery.

## 5. Product Principles

1. **One decision, one owner.** A value has one canonical location.
2. **Rules over repetition.** Publications reference shared decisions instead of
   copying them.
3. **Editable by default.** Generation begins the work; it does not end it.
4. **Explain the recommendation.** Important decisions include rationale.
5. **Expose uncertainty.** Unverified guidance must not masquerade as fact.
6. **Preview consequences.** Users see downstream effects before applying changes.
7. **Publish deliberately.** Draft work never silently changes an approved guide.
8. **Compliance must be explainable.** No opaque brand score.
9. **Accessibility is part of the brand.** It is not a separate checklist added at
   export time.
10. **Portable by design.** Users can leave with a complete representation of their
    work.

## 6. Scope

### 6.1 Brand foundation

- Purpose, vision, mission, and values
- Brand promise
- Positioning and competitive frame
- Audience segments and needs
- Differentiators and reasons to believe
- Brand story
- Personality and archetype rationale
- Experience principles
- Naming architecture
- Short, medium, and full brand descriptions
- Explicit anti-positioning: what the brand is not

### 6.2 Messaging system

- Core message and elevator pitch
- Messaging pillars and supporting proof
- Audience-specific value propositions
- Taglines and approved alternatives
- Campaign themes
- Boilerplate copy
- Headline and call-to-action patterns
- Product-description formulas
- Objection-handling language
- Claims that require evidence
- Approved, discouraged, and prohibited phrases

### 6.3 Verbal identity

- Voice attributes with behavioral definitions
- Tone dimensions and context-specific settings
- Vocabulary and terminology
- Grammar, punctuation, capitalization, and number rules
- Sentence and paragraph guidance
- Humor boundaries
- Inclusive-language requirements
- Sensitive-message guidance
- Microcopy patterns
- Positive and negative examples

### 6.4 Logo and signature guidance

- Creative brief and intended meaning
- Mark and lockup taxonomy
- Clear-space and minimum-size principles
- Background, contrast, and monochrome behavior
- Co-branding relationships
- Placement and motion principles
- Misuse examples
- Required production formats

Exact measurements remain unavailable until a production logo is registered.

### 6.5 Color system

- Brand, neutral, support, and utility palettes
- Semantic color roles
- Background and surface hierarchy
- Text, icon, and interaction-state colors
- Light and dark themes
- Approved combinations
- Accessibility contrast matrix
- Gradient rules
- Data-visualization palette
- HEX, RGB, and HSL values
- Print values marked for professional verification
- Stable semantic token names

### 6.6 Typography

- Typeface roles and verified fallback stacks
- Licensing and sourcing notes
- Type scale, weights, line heights, and tracking
- Heading, body, caption, label, quotation, and data styles
- Responsive behavior
- Numeral and tabular-data guidance
- International-character requirements
- Accessibility constraints
- Substitution guidance

### 6.7 Layout and composition

- Grid, container, column, and gutter systems
- Spacing scale
- Alignment, density, and hierarchy principles
- Shape language
- Borders, radii, shadows, and elevation
- Responsive and print composition
- Correct and incorrect examples

### 6.8 Imagery and art direction

- Subject, composition, perspective, lighting, and depth
- Color treatment, cropping, and focal-point rules
- Representation and inclusion
- Product and environmental photography
- Texture and material language
- AI-image boundaries and disclosure guidance
- Stock-image selection criteria
- Alt-text voice

### 6.9 Illustration, iconography, and graphics

- Illustration personality and dimensionality
- Line, shape, stroke, corner, and terminal principles
- Icon grid and filled-versus-outlined guidance
- Decorative motifs and patterns
- Charts, diagrams, and data visualization
- Rules for combining illustration and photography

### 6.10 Motion, sound, and interaction

- Motion personality
- Duration and easing tokens
- Entrance, exit, and transition behavior
- Reduced-motion requirements
- Logo-motion brief
- Microinteraction and progress behavior
- Notification style
- Sonic personality and voiceover direction

### 6.11 Digital product guidance

- Semantic design tokens
- Guidance for buttons, links, inputs, cards, navigation, and alerts
- Interaction and component states
- Form and validation behavior
- Content hierarchy and density
- Empty, loading, success, and error states
- Focus and keyboard behavior
- Accessible data display

This scope defines guidance and tokens, not a maintained UI component library.

### 6.12 Channel playbooks

- Website and landing pages
- Email
- Organic and paid social
- Advertising
- Presentations
- Documents and reports
- Packaging
- Environmental signage
- Events and merchandise
- Press and public relations
- Customer support
- Internal communications
- Partner and co-branded work

Each playbook derives tone, hierarchy, color balance, typography, imagery, calls to
action, accessibility, and common mistakes from the canonical system.

### 6.13 Accessibility and inclusion

- WCAG contrast requirements
- Keyboard and focus principles
- Reduced-motion behavior
- Typography readability
- Color-independent communication
- Alt text, captions, and transcripts
- Plain-language targets
- Inclusive language and imagery
- Cognitive-load guidance
- Localization and text expansion
- Exceptions and approval requirements

### 6.14 Governance

- Draft, reviewed, approved, published, superseded, and retired states
- Decision owners and rationale
- Version history and comparisons
- Section-level locking
- Review and approval workflow
- Explicit local-owner confirmation for approval and publication
- Approval records bound to exact revisions
- Deprecation and migration guidance
- Time-bounded exceptions
- Asset and rule provenance
- Review schedules
- Import, export, backup, and restoration

## 7. Canonical Domain Model

### BrandSystem

The durable identity and metadata for one brand. It points to one working draft and
zero or more immutable published versions.

### WorkingDraft

The mutable authoring state. It contains narrative documents, structured rules,
tokens, examples, asset registrations, unresolved decisions, and validation state.
It may also contain up to 50,000 characters of owner-supplied `brand_context` pasted
when the workspace is created. This context is trimmed, stored as canonical draft
data, and supplied as untrusted JSON data to every section-generation request; it
must never be interpreted as prompt instructions. The founding brief's substantive
fields (objective, audience, category, differentiators, constraints, existing equity,
success measures) plus the workspace concept and maturity stage are likewise supplied
as untrusted JSON to every section-generation request so generated sections obey the
brief; they must never be interpreted as prompt instructions.

### PublishedVersion

An immutable snapshot with a semantic version, publication time, publisher,
change summary, complete content manifest, reproducible export manifest, and the
approval records that authorized publication. Its rendered current state is the
base snapshot plus an ordered amendment ledger.

### PublicationAmendment

An append-only correction to a published version. It records a monotonically
increasing amendment revision, exact field or content-block targets, before and
after values, correction category, rationale, author, approval, and time. Allowed
categories are metadata, spelling, grammar, and formatting. An amendment must not
change meaning, rules, tokens, asset content, approvals, or applicability.

### ApprovalRecord

An immutable decision binding the local owner, time, rationale, and approval outcome
to an exact draft revision or section revision. Revisions invalidate prior approvals
when an approved value or dependent rule changes. It is governance history, not an
authorization or multi-user permission record.

### NarrativeDocument

A typed document containing editorial content and references to canonical rules.
Required metadata:

- Stable identifier
- Document type and title
- Body represented as safe structured content
- Rule and asset references
- Draft and review state
- Rationale and provenance
- Confidence and verification notes
- Revision history

### NarrativeBlock

A safe, typed content block with a stable identifier. Supported block types include
paragraph, heading, ordered list, unordered list, quotation, table, code sample,
callout, rule reference, token reference, asset reference, example, and paired
"do"/"don't" guidance. Inline content supports plain text, emphasis, strong text,
code, safe links, and semantic references.

The canonical block representation lives in versioned JSON. Markdown import maps
supported syntax and documented extensions into blocks; unsupported executable or
unsafe content is rejected, while unsupported non-executable content is preserved
as clearly labeled plain text or code for review. Markdown export is deterministic
and human-readable. Arbitrary HTML, scripts, embedded styles, event handlers, and
unknown executable content are never canonical narrative content.

### Rule

A testable or advisory brand decision. Required metadata:

- Stable identifier and category
- Human-readable name and description
- Severity: required, recommended, or advisory
- Typed value or constraint
- Applicability conditions
- Rationale
- Positive and negative examples
- Verification method
- Dependencies
- Approval and verification state

### VerificationClaim and EvidenceRecord

A verification claim identifies an exact recommendation, asserted fact, required
evidence class, scope, and status. Evidence records are immutable references to one
of these supported classes:

- Reproducible automated measurement with tool, version, inputs, and result
- Registered asset with integrity hash and measured properties
- Primary-source license, specification, or official documentation
- Human attestation with identity, role, qualifications, scope, and date
- Qualified professional review for legal, trademark, accessibility, print,
  typography, or other specialist claims

Statuses are generated, reviewed, approved, verified, and professionally verified.
Subjective brand decisions may reach approved but not verified status. Model output
or agreement among multiple models is supporting analysis, not verification.

### Token

A named, typed implementation value such as a color, spacing unit, type role,
duration, or elevation. Tokens may reference other tokens but must not form cycles.

### AssetRegistration

Metadata and an integrity reference for a production asset supplied outside the
product. A draft registration is either:

- **Managed:** copied into content-addressed local storage and addressed by its
  integrity hash.
- **Linked:** referenced at its current filesystem location and monitored for
  disappearance or content changes.

Managed import is the default. Linked assets are permitted during drafting, but
every required linked asset is copied into managed storage when a version is
published. Published versions refer only to immutable asset hashes. Identical
content is deduplicated without merging distinct asset metadata or usage roles.

### Example

A structured demonstration of correct, incorrect, or contextual usage. Examples
may be text, safe markup, configuration, or references to registered assets.

### Pattern and Playbook

An actionable, typed brand application specification. It bridges strategic prose
and production work without pretending to be a maintained component library. Every
pattern has a stable ID, name, enumerated kind, summary, one or more labeled
specifications, do guidance, do-not guidance, and canonical references. Examples
include say/never-say lists, message hierarchies, web-component anatomy and states,
type scales, layout templates, channel playbooks, and governance workflows.

Generated sections must satisfy this deliverables matrix. These entries are minimums,
not limits; the model may add applicable patterns but may not omit required ones.

| Section | Required patterns and playbooks |
|---|---|
| Strategy | Positioning framework; audience profile |
| Messaging | Message hierarchy; content template |
| Voice | Say/never-say; voice scale |
| Logo | Lockup system; clear-space and minimum-size specification |
| Color | Color application matrix |
| Typography | Responsive type scale |
| Layout | Layout template and responsive composition |
| Imagery | Image art-direction brief |
| Illustration | Icon and illustration system |
| Motion and sound | Motion behavior; sound and voiceover direction |
| Digital products | Web-component specification; interaction pattern |
| Channels | Channel playbook; content template |
| Accessibility | Accessibility checklist |
| Governance | Governance workflow |

A web-component specification covers anatomy, variants, interactive states, content
rules, responsive behavior, keyboard and focus behavior, validation, empty/loading/
success/error states where applicable, and accessibility requirements. It does not
contain executable production component code.

### Exception

A documented, narrowly scoped, time-bounded departure from one or more rules. It
records affected artifacts, campaigns, channels, audiences, locales, or dates;
business or creative rationale; known risks; compensating measures; requester;
owner; reviewer; effective and expiration times; approval history; and closure or
renewal outcome. Renewals create new approval records. A recurring exception must
prompt a proposed rule change rather than become undeclared permanent policy.

### Artifact

One independently evaluable piece of work with a stable identity, artifact type,
channel, audience, objective, content or managed asset references, metadata, and
integrity hash. Examples include an advertisement, email, landing page, social post,
presentation, packaging panel, copy document, or design-token package.

### Campaign

A named collection of versioned artifact references with a shared objective,
audience, message, schedule, channels, required elements, disclosures, and approved
campaign-level exceptions. An artifact may participate in more than one campaign
without duplicating its content or artifact-level findings.

### ComplianceRun and Finding

A reproducible artifact or campaign evaluation against one published brand version
and amendment revision. Artifact runs evaluate one item independently. Campaign
runs retain each artifact's findings and add cross-artifact findings for consistency,
adaptation, completeness, disclosure, and drift. Every finding records the
applicable rule, evidence, severity, explanation, suggested correction, confidence,
evaluation type, and review requirement.

### GenerationRun

A durable orchestration record for one initial-generation or regeneration request.
It records the requested sections, their dependency-respecting order, source draft
revision, per-section status, bounded provider attempts, accepted outputs, errors,
resume cursor, and completion state. A complete-draft run schedules every applicable
section; a section-by-section run schedules only the selected section and unmet
prerequisites. Both execute the same section generator and validation contract.

## 8. Guided Workshop

The authoring experience shall provide:

- Section navigation and completion state
- Complete-draft and section-by-section generation entry points
- Per-section generation progress, retry, pause, resume, and cancellation controls
- A live complete-brand-bible view of the current draft, with navigable sections,
  founding context, narrative guidance, rules, tokens, examples, patterns and
  playbooks, registered assets, canonical identifiers, revision state, responsive
  layout, and print styling
- A clear action on every saved legacy kit to continue into the living-brand workflow
- Direct narrative editing
- Typed editors for rules and tokens
- Section-level regeneration
- Alternative comparison
- Rationale and provenance display
- Locking and approval controls
- Undo and version restoration
- Dependency warnings
- Contradiction detection
- Downstream-impact previews
- Professional-verification markers
- Comments and review notes
- Audience-view previews

Generation must never overwrite approved or locked content without explicit user
confirmation.

## 9. Validation and Consistency

Validation operates at four levels:

1. **Field validation:** types, ranges, formats, lengths, and required values.
2. **Relational validation:** references exist, token graphs are acyclic, and
   dependent values remain compatible.
3. **Cross-domain validation:** narrative claims and examples do not contradict
   structured rules.
4. **Professional validation:** font licensing, print conversions, trademark
   matters, production dimensions, and similar claims remain marked unverified
   until evidence is registered.

Approval records answer whether the brand accepts a decision. Verification claims
answer whether evidence supports an objective or professional assertion. The UI,
exports, and compliance results must not conflate these concepts.

Blocking errors prevent publication. Warnings require acknowledgment. Advice does
not prevent publication.

## 10. Publishing

One published version produces multiple views without duplicating canonical data.

### Creator guide

Plain language, guided examples, practical decisions, and limited jargon.

### Designer specification

Exact tokens, measurements, states, constraints, and implementation notes.

### Business playbook

Positioning, messaging, customer experience, campaigns, and channel usage.

### Agency package

Strategy, rationale, governance, review state, handoff, exceptions, and client-ready
presentation.

### Output formats

- Responsive web guide
- Print-ready PDF
- Complete structured JSON
- Portable brand archive
- CSS custom properties
- Tool-neutral design tokens
- AI context and prompt package
- Voice and messaging reference
- Condensed channel guides
- Deterministic Markdown projections of narrative documents
- Compliance rule pack
- Version manifest and change log

Every export identifies the source brand version and export schema version.

### Portability contract

The canonical JSON representation defines documents, rules, tokens, relationships,
governance, approvals, verification claims, evidence metadata, versions, amendments,
asset hashes, campaigns, exceptions, and compliance configuration. It is the
normative logical contract for APIs, diffs, migration, and interoperability.

The self-contained archive is the normative transport for complete restoration. It
contains a manifest, the canonical JSON, every required managed asset, embedded
evidence, and checksums binding binary content to JSON references. Derived PDFs,
websites, and token projections are reproducible outputs and need not be authoritative
archive contents.

## 11. Compliance Engine

Compliance supports two compositional evaluation units:

- **Artifact evaluation** checks one independently versioned item.
- **Campaign evaluation** evaluates a declared set of artifact revisions, retains
  their individual findings, and adds cross-artifact and cross-channel findings.

Campaign evaluation must not collapse or replace artifact evidence. A campaign
status is a projection over its artifact and campaign findings, not a separate
opaque score.

An approved exception changes the disposition of an applicable finding but does
not erase the rule, evidence, or original finding. Reports identify the exception,
scope, owner confirmation, and expiration. Expired exceptions no longer alter
finding disposition. The local owner may approve their own exceptions.

### Deterministic evaluation

- Color values and contrast
- Token usage
- Typography roles
- Character and length constraints
- Required and prohibited terminology
- Required disclosures
- Registered logo measurements
- Component and accessibility rules

### Judgment-based evaluation

- Voice consistency
- Strategic alignment
- Imagery fit
- Message hierarchy
- Personality fit
- Audience and channel suitability

Judgment-based results must be labeled as model assessments and include confidence.
They must never be presented as deterministic failures.

Each finding shall include:

- Submitted material and evaluation scope
- Published version used
- Applicable rule
- Deterministic or judgment-based classification
- Severity and evidence
- Explanation and suggested correction
- Confidence and human-review requirement

The system shall not reduce compliance to one unexplained aggregate score.

## 12. Versioning and Publication

- Working drafts are mutable.
- A published version's base snapshot and amendment history are immutable.
- Publishing creates a complete reproducible base snapshot at amendment revision
  zero.
- Permitted clerical corrections append amendment records without rewriting the
  base snapshot or prior amendments.
- The default published view applies all amendments in order.
- Historical state remains reproducible from the version and amendment revision.
- Meaning-changing edits create a new version.
- Version comparisons identify changed documents, rules, tokens, assets, examples,
  exceptions, and clerical amendments.
- Exports record both their source version and amendment revision.
- Retiring a version does not delete it.
- Deleting a brand or version is outside the initial scope and requires a separate
  retention and recovery policy.

## 13. Functional Requirements

1. **WHEN** a brand system is generated, the system **SHALL** create an editable
   working draft rather than an immutable published guide.
2. **WHEN** a user edits narrative content, the system **SHALL** preserve valid rule
   references and surface broken references.
3. **WHEN** a user edits a rule or token, the system **SHALL** show affected
   documents, examples, exports, and compliance checks before applying the change.
4. **IF** an edit introduces a blocking contradiction, the system **SHALL NOT**
   publish the draft until it is resolved.
5. **WHEN** a section is regenerated, the system **SHALL** preserve locked content
   and present proposed changes for review.
6. **WHEN** a draft is published, the system **SHALL** create an immutable,
   versioned snapshot with a complete manifest.
7. **WHEN** an audience view is rendered, the system **SHALL** derive it from one
   published version without copying canonical decisions.
8. **WHEN** an export is created, the system **SHALL** identify the brand version
   and export schema version.
9. **WHEN** compliance is evaluated, the system **SHALL** record the exact published
   version and rules used.
10. **IF** a compliance result depends on model judgment, the system **SHALL** label
    it separately from deterministic findings.
11. **IF** a recommendation requires professional verification, the system
    **SHALL** retain that status until supporting evidence is registered.
12. **WHEN** a registered asset changes, the system **SHALL** identify all dependent
    rules and examples requiring review.
13. **WHEN** a draft with required linked assets is published, the system **SHALL**
    copy those assets into managed content-addressed storage and bind the published
    version to their immutable hashes.
14. **IF** a required linked asset is missing or unreadable, the system **SHALL NOT**
    publish the draft and **SHALL** identify the blocking registration.
15. **WHEN** a user exports the complete brand, the system **SHALL** produce a
    portable representation sufficient to restore the published version.
16. **IF** generation or evaluation fails, the system **SHALL** retain the last
    valid draft and expose a sanitized, recoverable error state.
17. **WHEN** a brand is published, the local owner **MAY** author, review, approve,
    and publish the same revision.
18. **WHEN** a governance action is persisted, the system **SHALL** attribute it to
    the local owner and retain its time, rationale, and exact target revision without
    requiring an account, role, invitation, or permission model.
19. **IF** an approved section or one of its dependencies changes, the system
    **SHALL** invalidate the affected approval before publication.
20. **WHEN** publication succeeds, the published version **SHALL** retain the exact
    approval records and local-owner identity that authorized it.
21. **WHEN** the local owner corrects published metadata, spelling, grammar, or
    formatting without changing meaning, the system **SHALL** append an amendment
    record rather than rewrite the base snapshot.
22. **IF** a proposed amendment changes meaning, a rule, a token, asset content, an
    approval, or applicability, the system **SHALL** reject the amendment and
    require a new draft version.
23. **WHEN** published content is rendered or exported, the system **SHALL** identify
    the exact brand version and amendment revision used.
24. **WHEN** a historical amendment revision is requested, the system **SHALL**
    reconstruct that state from the base snapshot and ordered amendment ledger.
25. **WHEN** an artifact is evaluated, the system **SHALL** bind the run to the
    artifact's exact revision or integrity hash and retain independently actionable
    findings.
26. **WHEN** a campaign is evaluated, the system **SHALL** evaluate or reuse the
    declared artifact revisions and then add cross-artifact findings without hiding
    individual artifact results.
27. **IF** an artifact changes after a campaign run, the system **SHALL** mark the
    affected campaign result stale until the new artifact revision is evaluated.
28. **WHEN** a campaign finding is reported, the system **SHALL** identify all
    affected artifacts, channels, campaign requirements, and applicable brand rules.
29. **WHEN** an exception is requested, the system **SHALL** require explicit rule,
    scope, rationale, risk, owner confirmation, effective time, and expiration time.
30. **WHEN** an approved exception applies to a finding, the system **SHALL** retain
    the underlying rule and evidence while displaying the exception's disposition,
    scope, approval, and expiration.
31. **WHEN** an exception expires, the system **SHALL** stop applying it to new or
    refreshed compliance results without deleting its historical decisions.
32. **WHEN** an exception is renewed, the system **SHALL** create a new approval
    record rather than extend or overwrite the prior decision.
33. **IF** substantially equivalent exceptions recur, the system **SHALL** surface a
    recommendation to revise the canonical rule through a new brand version.
34. **WHEN** a recommendation is generated, the system **SHALL** initialize its
    verification state as generated and unverified.
35. **WHEN** the local owner accepts a subjective recommendation, the system
    **SHALL** mark it approved without representing it as objectively verified.
36. **WHEN** an objective claim is marked verified, the system **SHALL** retain
    evidence appropriate to the claim, including provenance and reproducibility
    metadata.
37. **WHEN** a claim requires specialist judgment, the system **SHALL NOT** mark it
    professionally verified without an attestation that records qualifications,
    scope, identity, and date.
38. **IF** multiple models agree on a claim, the system **MAY** retain that agreement
    as analysis but **SHALL NOT** treat it as verification evidence.
39. **WHEN** canonical JSON is exported, the system **SHALL** include its schema
    version, source brand version, amendment revision, and integrity metadata.
40. **WHEN** a complete archive is exported, the system **SHALL** include canonical
    JSON, all required managed assets and embedded evidence, and checksums that bind
    every binary to its JSON reference.
41. **WHEN** canonical JSON is imported without its referenced binaries, the system
    **SHALL** preserve the logical data and explicitly report unresolved asset or
    evidence references rather than invent or discard content.
42. **WHEN** a complete archive is imported, the system **SHALL** verify its manifest,
    paths, sizes, types, checksums, schema compatibility, and referential integrity
    before changing canonical state.
43. **IF** an archive import fails, the system **SHALL** preserve the archive and the
    existing brand state unchanged and provide a sanitized failure report.
44. **WHEN** narrative content is authored or generated, the system **SHALL** store
    it as validated, stable-identity blocks rather than raw HTML.
45. **WHEN** a narrative block references a rule, token, or asset, the system
    **SHALL** store a semantic identifier rather than copy the referenced value into
    prose.
46. **WHEN** Markdown is imported, the system **SHALL** map supported syntax and
    documented extensions into canonical blocks and reject executable content.
47. **IF** Markdown contains unsupported non-executable content, the system **SHALL**
    preserve it visibly for review rather than silently discard or execute it.
48. **WHEN** Markdown is exported, the system **SHALL** produce a deterministic,
    human-readable projection that retains semantic references through documented
    portable syntax.
49. **WHEN** block content is amended, commented on, or dependency-checked, the
    system **SHALL** address stable block identifiers rather than display positions.
50. **WHEN** the local owner requests a complete initial draft, the system **SHALL**
    schedule all applicable sections through the same section-generation pipeline
    used by individual section requests.
51. **WHEN** the local owner requests one section, the system **SHALL** generate only
    that section and any explicitly identified unmet prerequisites.
52. **WHEN** a generation run advances, the system **SHALL** persist each accepted
    section result and its validation state before starting the next section.
53. **IF** a section fails generation or validation, the system **SHALL** retain all
    previously accepted sections, stop or isolate dependent work, and offer a bounded
    retry or resume from the failed section.
54. **WHEN** a generation run resumes, the system **SHALL NOT** regenerate accepted
    or locked sections unless the local owner explicitly selects them.
55. **WHEN** the same inputs, dependencies, and accepted section outputs reach the
    pipeline through either generation entry point, the resulting canonical draft
    **SHALL** have the same structure and validation semantics.
56. **WHEN** the local owner pauses or cancels generation, the system **SHALL** keep
    the last valid draft usable and record which sections remain incomplete.

## 14. Non-Functional Requirements

### Data integrity

- Canonical identifiers remain stable across edits and exports.
- Published versions are transactionally complete.
- Publication amendments are append-only, ordered, and retain before-and-after
  values sufficient for historical reconstruction.
- Token and reference graphs reject cycles and dangling dependencies.
- Failed writes do not leave partial published versions.

### Security and privacy

- The local-first default binds only to loopback.
- Model and imported content are treated as untrusted.
- Rendered content uses safe structured rendering rather than raw HTML injection.
- Narrative import and rendering prohibit arbitrary HTML, scripts, styles, event
  handlers, and executable embedded content.
- Secrets never enter brand documents, exports, logs, or model-visible metadata.
- Asset archives validate paths, types, sizes, and integrity before extraction.
- Linked asset paths remain local metadata and are never sent to a model or exposed
  in published guides or portable exports.

### Accessibility

- Authoring and published web experiences target WCAG 2.2 AA.
- All core workflows are keyboard operable.
- Dynamic validation and publication state is announced accessibly.
- Published guidance documents their own accessibility status and exceptions.

### Performance

- A normal brand opens without loading every historical version or export.
- List and history endpoints remain paginated.
- Compliance runs are bounded by artifact size and rule count.
- Campaign runs are bounded by artifact count, total artifact size, and applicable
  cross-artifact rule count.
- Long-running generation, export, or evaluation operations expose progress and may
  be cancelled without corrupting canonical state.

### Portability

- Complete exports use documented, versioned schemas.
- Canonical JSON is the normative logical contract; the checksum-bound archive is
  the normative self-contained transport.
- Unknown future fields do not silently corrupt older imports.
- Migration failures preserve the original import unchanged.

## 15. Information Architecture

1. Brand library
2. Brand overview and completion state
3. Workshop
   - Foundation
   - Messaging
   - Voice
   - Visual identity
   - Digital system
   - Channels
   - Accessibility
   - Governance
4. Decisions and unresolved issues
5. Validation
6. Audience previews
7. Publish
8. Exports
9. Compliance
10. Versions and change history
11. Assets
12. Settings

## 16. Compatibility and Migration

- Existing `BrandKit` records remain readable.
- A migration creates a working draft from an existing kit without modifying the
  source record.
- Migrated values retain provenance linking them to the original generation.
- Missing comprehensive sections begin explicitly incomplete; they are not filled
  with silent generic defaults.
- Existing `/brand` and library endpoints remain stable until a documented
  deprecation process is approved.

## 17. Technical Context

### Current stack

- Python 3.11+
- FastAPI and Uvicorn
- Pydantic v2 contracts
- SQLite persistence
- Async HTTPX provider client
- Dependency-free browser UI
- Pytest, Ruff, strict MyPy, and Hatchling/uv builds

This specification does not yet authorize a framework migration or new dependency.

### Commands

```bash
# Install
uv sync --extra dev

# Run
uv run brand-maker

# Test
uv run pytest -q

# Lint
uv run ruff check src tests

# Type-check
uv run mypy src

# Package
uv build
```

### Proposed project structure

```text
src/brand_maker/
  brand_system/       Canonical domain models and validation
  workshop/           Draft editing and dependency analysis
  publishing/         Audience projections and export orchestration
  compliance/         Deterministic and judgment-based evaluation
  assets/             Asset registration and integrity metadata
  migrations/         Legacy BrandKit and schema migrations
  storage.py          Persistence boundary
  app.py              HTTP composition root
tests/
  brand_system/       Domain and contract tests
  workshop/           Editing and dependency tests
  publishing/         Projection and export tests
  compliance/         Rule-evaluation tests
  migrations/         Compatibility tests
docs/specs/           Product and technical specifications
```

The final structure remains subject to implementation planning and should not be
created wholesale before the first vertical slice requires it.

## 18. Code and Testing Standards

### Code style

Public boundaries use strict typed contracts with explicit validation:

```python
class BrandRule(ContractModel):
    id: UUID
    name: str = Field(..., min_length=1, max_length=120)
    severity: Literal["required", "recommended", "advisory"]
    rationale: str = Field(..., min_length=1, max_length=1_000)
```

- Prefer small domain modules and explicit names.
- Keep provider transport separate from product policy.
- Store raw canonical data; derive publications and indexes.
- Avoid generic abstractions until repeated use proves their value.
- Treat every import, model response, and user-authored reference as untrusted.

### Testing strategy

- Unit tests for contract validation, token graphs, rules, and version semantics.
- Integration tests for persistence, publication transactions, migrations, export
  round trips, generation resume/retry, and equivalence between complete-draft and
  section-by-section orchestration.
- Golden tests for audience projections and portable schemas.
- Adversarial tests for malformed imports, reference cycles, oversized artifacts,
  conflicting rules, and model/provider failures.
- Browser tests for authoring, validation, keyboard use, responsive layouts, and
  accessible status announcements.
- Deterministic compliance tests never call a model.
- Judgment-evaluation tests use bounded fakes; paid live evaluation is opt-in.

## 19. Delivery Boundaries

### Always

- Update this specification before changing an approved product contract.
- Add regression tests for every behavior change.
- Validate all external and model-produced data at the boundary.
- Preserve canonical data when derived generation or export fails.
- Run tests, lint, strict typing, and packaging before each delivery checkpoint.
- Keep accessibility requirements in the acceptance criteria.

### Ask first

- Add or change dependencies.
- Change the database schema or migration policy.
- Change published-version semantics.
- Add authentication, remote collaboration, or network exposure.
- Introduce destructive deletion or retention behavior.
- Change the portable export contract.
- Replace the dependency-free UI architecture.

### Never

- Commit secrets or user-provided private assets.
- Overwrite a published version.
- Treat model judgment as deterministic compliance.
- Silently discard unknown imported data.
- Publish generated recommendations as professionally verified without evidence.
- Regenerate locked content without explicit confirmation.

## 20. Product Decisions

### OQ-1: Asset storage and ownership — Resolved

Use a hybrid model. Drafts may contain managed or linked assets, with managed import
as the default. Publication snapshots every required linked asset into managed,
content-addressed storage; published versions and portable archives use immutable
asset hashes rather than external paths.

Entries marked **Resolved** are approved product decisions; all other entries remain
open.

### OQ-2: Approval and publishing authority — Resolved

Use one local owner who may author, review, approve, publish, amend, and retire the
same brand content. Approval remains an explicit, revision-bound governance action
for auditability and intentional publication, but it is not backed by accounts,
roles, or separation-of-duty permissions. Relevant changes invalidate approvals.

### OQ-3: Published-version correction — Resolved

Permit controlled in-place clerical correction through an append-only amendment
ledger. Amendments may correct metadata, spelling, grammar, and formatting only
when meaning is unchanged. The original snapshot and every amendment remain
available; exports identify both version and amendment revision. Any semantic,
rule, token, asset-content, approval, or applicability change requires a new
version.

### OQ-4: Compliance evaluation unit — Resolved

Support both. Artifacts are independently versioned and evaluated atomic units.
Campaigns compose exact artifact revisions and add cross-artifact and cross-channel
checks while retaining every artifact's underlying findings. Changed artifacts mark
affected campaign results stale until reevaluation.

### OQ-5: Subjective exceptions — Resolved

Use approved, narrowly scoped, time-bounded exceptions. Compliance retains the
underlying rule and finding while showing the exception's effect, owner confirmation,
and expiration. The local owner may self-approve. Renewals create new approval
records, and recurring exceptions prompt a proposed versioned rule change.

### OQ-6: Verification evidence — Resolved

Separate approval from verification. Subjective brand decisions may be reviewed and
approved but not objectively verified. Objective and professional claims require
claim-appropriate evidence: reproducible measurements, integrity-bound assets,
primary sources, scoped human attestations, or qualified professional review.
Multiple-model agreement remains supporting analysis rather than evidence.

### OQ-7: Portability contract — Resolved

Use canonical versioned JSON plus a self-contained checksum-bound archive. JSON is
the normative logical representation. The archive is the normative complete
transport and contains the JSON, required managed assets, embedded evidence, and
integrity checks. Derived publications are regenerated rather than treated as
competing sources of truth.

### OQ-8: Narrative content representation — Resolved

Use constrained block JSON as canonical narrative content, with stable block
identities and semantic rule, token, and asset references. Support deterministic
Markdown import and export through documented syntax and extensions. Prohibit raw
HTML and executable embedded content; preserve unsupported safe material visibly
for review rather than silently discarding it.

### OQ-9: Collaboration horizon — Resolved

Design the foundation for one person using it locally. Do not introduce user
accounts, invitations, roles, permission checks, separation-of-duty rules, remote
presence, or concurrent editing. Retain lightweight owner attribution, timestamps,
revision history, and portable exports so another system can interpret provenance
later. Any collaborative or hosted mode requires a new approved specification and
an explicit data migration rather than speculative complexity in this model.

### OQ-10: Generation granularity — Resolved

Offer both complete-draft and section-by-section workflows through one canonical,
ordered section pipeline. Complete-draft generation is an orchestration convenience,
not one monolithic model call. Persist validated results after every section; expose
progress; support pause, bounded retry, cancellation, and resume; preserve accepted
and locked work; and ensure both entry points produce the same canonical structure
and validation behavior.

## 21. Success Criteria

The foundation is successful when:

1. A user can migrate or generate a brand into an editable hybrid draft.
2. Strategy documents can reference structured rules without duplicating values.
3. Rule changes expose their downstream impact before application.
4. Blocking contradictions prevent publication with actionable explanations.
5. A published base snapshot and amendment history are immutable, reproducible at
   every amendment revision, and comparable with later versions.
6. Creator and designer views render from the same published source.
7. Web, PDF, JSON, and design-token exports identify and reproduce their source
   version.
8. Deterministic compliance findings cite exact rules and evidence.
9. Model-based findings remain explainable and visibly subjective.
10. Existing BrandKit records and API consumers continue to work during migration.
11. The complete system is keyboard operable and meets the agreed accessibility
    verification gates.
12. A portable export can restore the published version without access to the
    original database.
13. Drafts may use linked assets, while every published version remains reproducible
    from managed, integrity-checked assets without depending on original paths.
14. The local owner can complete the full workflow independently, while explicit
    revision-bound approvals keep publication intentional and auditable without
    accounts or role machinery.
15. The local owner can correct non-semantic published mistakes without losing the
    original state or weakening version-level reproducibility.
16. Users can evaluate one artifact independently or evaluate a campaign without
    losing artifact-level evidence, reproducibility, or actionable corrections.
17. Users can authorize exceptional creative work without hiding violated rules or
    allowing temporary waivers to become invisible permanent policy.
18. Every recommendation communicates whether it is generated, reviewed, approved,
    verified, or professionally verified and retains the evidence required for that
    status.
19. Canonical JSON supports integration and migration, while a verified archive can
    restore the complete published system without its original database or file
    locations.
20. Narrative content is safely editable and addressable as structured blocks while
    remaining portable and human-readable through deterministic Markdown.
21. A fresh local installation supports the complete workflow with one owner and no
    authentication or collaboration setup, while exported history retains clear
    attribution and timestamps.
22. The local owner can generate a complete draft or work section by section, pause
    or recover from failure without losing accepted work, and obtain the same
    canonical structure and validation semantics through either entry point.
23. Workspace creation accepts optional multiline brand context, preserves its line
    breaks after trimming outer whitespace, rejects empty or over-limit values, and
    applies the stored context consistently to every generated section.
24. The local owner can open one complete brand bible directly from the workshop
    without publishing first; it safely renders every canonical draft content type,
    identifies empty areas, works at mobile widths, and prints without authoring UI.
25. Generated sections contain at least two narrative blocks, one actionable rule,
    and contrasting examples; technical implementation sections also contain tokens.
26. Generated sections include every required pattern kind in the deliverables
    matrix; a missing kind fails validation and triggers the existing bounded retry.
27. The complete bible renders each pattern with its labeled specifications, do and
    do-not guidance, and canonical identity, including explicit say/never-say and
    web-component content when their sections are generated.
28. A saved legacy kit clearly identifies itself as a quick concept and offers a
    keyboard-accessible path to create a living workspace from that exact source kit.

## 22. Explicit Non-Goals

- Creating production logos, illustrations, templates, or campaign artwork
- Replacing Figma, Illustrator, Canva, or general-purpose document editors
- Maintaining a production UI component library
- Automatically publishing draft edits
- Hiding uncertainty behind one brand score
- Structuring all strategic prose into rigid fields
- Supporting brand families or inherited sub-brands in the foundation release
- User accounts, invitations, team roles, permission systems, comments assigned to
  other users, presence indicators, and concurrent multi-user editing
- Hosting a remote multi-tenant service without a separately approved security and
  privacy specification

## 23. Principal Risks

1. Authoring becomes an exhausting form rather than a guided workshop.
2. Narrative guidance contradicts structured rules.
3. Audience views drift into duplicated content.
4. Generated guidance appears more authoritative than its evidence permits.
5. Compliance creates false certainty.
6. Versioning records labels but fails to preserve reproducible state.
7. Asset-dependent guidance remains vague because assets are not generated.
8. The schema becomes too broad to migrate or evolve safely.
9. A comprehensive initial generation exceeds model reliability and context limits.
10. Later collaboration requests are mistaken for foundation scope and reintroduce
    accounts, permissions, or concurrency before a separate migration is justified.

Implementation planning must address these risks before coding begins.
