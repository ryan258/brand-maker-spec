"""Canonical, versioned contracts for one local living brand system."""

from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from brand_maker.brand_system.validation import (
    reject_raw_html,
    require_acyclic_token_graph,
    require_known_references,
    require_unique_ids,
)
from brand_maker.models import ContractModel

StableId = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$"),
]
ShortText = Annotated[str, Field(min_length=1, max_length=300)]
NarrativeText = Annotated[str, Field(min_length=1, max_length=50_000)]

ReferenceKind = Literal[
    "section", "block", "rule", "token", "asset", "example", "pattern"
]
BlockType = Literal[
    "paragraph",
    "heading",
    "ordered_list",
    "unordered_list",
    "quotation",
    "table",
    "code_sample",
    "callout",
    "rule_reference",
    "token_reference",
    "asset_reference",
    "example",
    "do_dont",
]


class LocalOwner(ContractModel):
    """Attribution for the one person operating the local application."""

    id: StableId = "local-owner"
    display_name: ShortText


class CanonicalReference(ContractModel):
    """A typed semantic link to another canonical entity."""

    kind: ReferenceKind
    target_id: StableId


class NarrativeBlock(ContractModel):
    """A safe structured narrative block with a stable identity."""

    id: StableId
    type: BlockType
    text: NarrativeText
    references: list[CanonicalReference] = Field(default_factory=list, max_length=100)
    heading_level: int | None = Field(default=None, ge=1, le=6)

    _reject_html = field_validator("text")(reject_raw_html)

    @model_validator(mode="after")
    def validate_heading_level(self) -> Self:
        if self.type == "heading" and self.heading_level is None:
            raise ValueError("heading blocks require heading_level")
        if self.type != "heading" and self.heading_level is not None:
            raise ValueError("heading_level is only valid for heading blocks")
        return self


class BrandRule(ContractModel):
    """A testable or advisory brand decision."""

    id: StableId
    name: ShortText
    description: NarrativeText
    enforcement: Literal["advisory", "warning", "blocking"]
    references: list[CanonicalReference] = Field(default_factory=list, max_length=100)


class BrandToken(ContractModel):
    """A named implementation value with optional token dependencies."""

    id: StableId
    name: ShortText
    value_type: Literal["color", "string", "number", "dimension", "duration", "font", "boolean"]
    value: str | float | int | bool
    references: list[CanonicalReference] = Field(default_factory=list, max_length=100)


class BrandExample(ContractModel):
    """A structured demonstration of correct, incorrect, or contextual use."""

    id: StableId
    kind: Literal["do", "dont", "context"]
    text: NarrativeText
    references: list[CanonicalReference] = Field(default_factory=list, max_length=100)

    _reject_html = field_validator("text")(reject_raw_html)


PatternKind = Literal[
    "positioning_framework",
    "audience_profile",
    "message_hierarchy",
    "content_template",
    "say_never_say",
    "voice_scale",
    "logo_lockup",
    "logo_clear_space",
    "color_application",
    "type_scale",
    "layout_template",
    "image_art_direction",
    "icon_system",
    "motion_behavior",
    "sound_direction",
    "web_component",
    "interaction_pattern",
    "channel_playbook",
    "accessibility_checklist",
    "governance_workflow",
]


class PatternSpecification(ContractModel):
    """One labeled, implementation-facing detail within a brand pattern."""

    label: ShortText
    value: NarrativeText

    _reject_html = field_validator("value")(reject_raw_html)


class BrandPattern(ContractModel):
    """An actionable application pattern or playbook derived from the brand."""

    id: StableId
    name: ShortText
    kind: PatternKind
    summary: NarrativeText
    specifications: list[PatternSpecification] = Field(..., min_length=1, max_length=100)
    do_guidance: list[NarrativeText] = Field(..., min_length=1, max_length=100)
    dont_guidance: list[NarrativeText] = Field(..., min_length=1, max_length=100)
    references: list[CanonicalReference] = Field(default_factory=list, max_length=100)

    _reject_summary_html = field_validator("summary")(reject_raw_html)

    @field_validator("do_guidance", "dont_guidance")
    @classmethod
    def reject_guidance_html(cls, values: list[str]) -> list[str]:
        return [reject_raw_html(value) for value in values]


class AssetRegistration(ContractModel):
    """Integrity-bound metadata for one linked or managed production asset."""

    id: StableId
    name: ShortText
    storage: Literal["linked", "managed"]
    media_type: ShortText
    size_bytes: int = Field(..., ge=1)
    content_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    source_path: str | None = Field(default=None, max_length=4096)
    required: bool = True

    @model_validator(mode="after")
    def validate_storage_location(self) -> Self:
        if self.storage == "linked" and not self.source_path:
            raise ValueError("linked assets require source_path")
        if self.storage == "managed" and self.source_path is not None:
            raise ValueError("managed assets cannot depend on source_path")
        return self


class RegisterAssetRequest(ContractModel):
    expected_revision: int = Field(..., ge=1)
    id: StableId
    name: ShortText
    storage: Literal["linked", "managed"]
    media_type: ShortText
    source_path: str = Field(..., min_length=1, max_length=4096)
    required: bool = True


SectionStatus = Literal["incomplete", "draft", "reviewed", "approved"]


class BrandSection(ContractModel):
    """One independently editable and lockable part of a working draft."""

    id: StableId
    title: ShortText
    status: SectionStatus = "incomplete"
    locked: bool = False
    blocks: list[NarrativeBlock] = Field(default_factory=list, max_length=1_000)
    rules: list[BrandRule] = Field(default_factory=list, max_length=1_000)
    tokens: list[BrandToken] = Field(default_factory=list, max_length=1_000)
    examples: list[BrandExample] = Field(default_factory=list, max_length=1_000)
    patterns: list[BrandPattern] = Field(default_factory=list, max_length=1_000)


class WorkingDraft(ContractModel):
    """The mutable canonical authoring state for one local brand."""

    schema_version: Literal["1.0"] = "1.0"
    brand_id: UUID
    source_brand_id: UUID | None = None
    brand_name: ShortText
    brand_context: NarrativeText | None = None
    owner: LocalOwner
    revision: int = Field(..., ge=1)
    status: Literal["draft", "reviewed", "approved"] = "draft"
    sections: list[BrandSection] = Field(default_factory=list, max_length=100)
    assets: list[AssetRegistration] = Field(default_factory=list, max_length=1_000)

    @model_validator(mode="after")
    def validate_canonical_graph(self) -> Self:
        entities: dict[str, list[str]] = {
            "section": [section.id for section in self.sections],
            "block": [block.id for section in self.sections for block in section.blocks],
            "rule": [rule.id for section in self.sections for rule in section.rules],
            "token": [token.id for section in self.sections for token in section.tokens],
            "example": [example.id for section in self.sections for example in section.examples],
            "pattern": [pattern.id for section in self.sections for pattern in section.patterns],
            "asset": [asset.id for asset in self.assets],
        }
        require_unique_ids(canonical_id for ids in entities.values() for canonical_id in ids)
        known_by_kind = {kind: set(ids) for kind, ids in entities.items()}

        referents = [
            reference
            for section in self.sections
            for block in section.blocks
            for reference in block.references
        ]
        referents.extend(
            reference
            for section in self.sections
            for rule in section.rules
            for reference in rule.references
        )
        referents.extend(
            reference
            for section in self.sections
            for token in section.tokens
            for reference in token.references
        )
        referents.extend(
            reference
            for section in self.sections
            for example in section.examples
            for reference in example.references
        )
        referents.extend(
            reference
            for section in self.sections
            for pattern in section.patterns
            for reference in pattern.references
        )
        require_known_references(
            ((reference.kind, reference.target_id) for reference in referents), known_by_kind
        )

        token_graph = {
            token.id: {
                reference.target_id for reference in token.references if reference.kind == "token"
            }
            for section in self.sections
            for token in section.tokens
        }
        require_acyclic_token_graph(token_graph)
        return self


class WorkspaceSummary(ContractModel):
    """A compact, bounded-list projection of a working draft."""

    brand_id: UUID
    brand_name: str
    revision: int = Field(..., ge=1)
    status: Literal["draft", "reviewed", "approved"]
    section_count: int = Field(..., ge=0)
    complete_section_count: int = Field(..., ge=0)

    @classmethod
    def from_draft(cls, draft: WorkingDraft) -> Self:
        return cls(
            brand_id=draft.brand_id,
            brand_name=draft.brand_name,
            revision=draft.revision,
            status=draft.status,
            section_count=len(draft.sections),
            complete_section_count=sum(
                section.status in {"reviewed", "approved"} for section in draft.sections
            ),
        )


class CreateWorkspaceRequest(ContractModel):
    """Create a blank workspace or migrate one immutable legacy kit."""

    brand_name: ShortText | None = None
    brand_context: NarrativeText | None = None
    owner_name: ShortText
    source_brand_id: UUID | None = None

    @model_validator(mode="after")
    def require_one_source(self) -> Self:
        if (self.brand_name is None) == (self.source_brand_id is None):
            raise ValueError("provide exactly one of brand_name or source_brand_id")
        return self


class UpdateSectionRequest(ContractModel):
    """Revision-safe replacement of one canonical section."""

    expected_revision: int = Field(..., ge=1)
    section: BrandSection
    confirm_locked: bool = False


class ValidationIssue(ContractModel):
    location: str
    message: str


class EditImpact(ContractModel):
    changed_ids: list[StableId]
    affected_ids: list[StableId]
    blocking_errors: list[ValidationIssue]
    warnings: list[ValidationIssue] = Field(default_factory=list)
    advice: list[ValidationIssue] = Field(default_factory=list)
    can_apply: bool


class WorkspacePage(ContractModel):
    """A bounded page of local living-brand workspaces."""

    items: list[WorkspaceSummary]
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_items: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)


class ApprovalRequest(ContractModel):
    expected_revision: int = Field(..., ge=1)
    rationale: ShortText


class ApprovalRecord(ContractModel):
    id: UUID
    brand_id: UUID
    draft_revision: int = Field(..., ge=1)
    owner_id: StableId
    approved_at: datetime
    rationale: ShortText
    outcome: Literal["approved"] = "approved"


SemanticVersion = Annotated[
    str, Field(pattern=r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
]


class PublicationRequest(ContractModel):
    expected_revision: int = Field(..., ge=1)
    version: SemanticVersion
    change_summary: ShortText


class PublicationManifest(ContractModel):
    schema_version: Literal["1.0"]
    draft_revision: int = Field(..., ge=1)
    section_ids: list[StableId]


class PublishedVersion(ContractModel):
    brand_id: UUID
    version: SemanticVersion
    published_at: datetime
    publisher_id: StableId
    draft_revision: int = Field(..., ge=1)
    change_summary: ShortText
    content_hash: str = Field(..., pattern=r"^[0-9a-f]{64}$")
    manifest: PublicationManifest
    approvals: list[ApprovalRecord] = Field(..., min_length=1)
    snapshot: WorkingDraft


class AmendmentRequest(ContractModel):
    target_id: StableId
    field: Literal["text", "change_summary"]
    category: Literal["metadata", "spelling", "grammar", "formatting"]
    before: NarrativeText
    after: NarrativeText
    rationale: ShortText

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if self.before == self.after:
            raise ValueError("amendment must change a value")
        return self


class PublicationAmendment(ContractModel):
    id: UUID
    brand_id: UUID
    version: SemanticVersion
    amendment_revision: int = Field(..., ge=1)
    target_id: StableId
    field: Literal["text", "change_summary"]
    category: Literal["metadata", "spelling", "grammar", "formatting"]
    before: NarrativeText
    after: NarrativeText
    rationale: ShortText
    owner_id: StableId
    approved_at: datetime


class RenderedPublishedVersion(ContractModel):
    brand_id: UUID
    version: SemanticVersion
    amendment_revision: int = Field(..., ge=0)
    rendered_change_summary: ShortText
    rendered_snapshot: WorkingDraft
    amendments: list[PublicationAmendment]
