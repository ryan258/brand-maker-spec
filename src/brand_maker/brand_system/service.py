"""Application service for local living-brand workspace operations."""

from collections.abc import Callable
from uuid import UUID, uuid4

from brand_maker.brand_system.editing import preview_section_edit
from brand_maker.brand_system.models import (
    BrandSection,
    BrandToken,
    CreateWorkspaceRequest,
    EditImpact,
    LocalOwner,
    NarrativeBlock,
    WorkingDraft,
    WorkspaceBrief,
)
from brand_maker.brand_system.repository import (
    SQLiteBrandSystemRepository,
    StaleDraftRevision,
    WorkspaceAlreadyTrashed,
)
from brand_maker.models import BrandKit
from brand_maker.storage import SQLiteBrandRepository

SECTION_CATALOG = (
    ("strategy", "Strategy"),
    ("messaging", "Messaging"),
    ("voice", "Voice"),
    ("logo", "Logo guidance"),
    ("color", "Color"),
    ("typography", "Typography"),
    ("layout", "Layout"),
    ("imagery", "Imagery"),
    ("illustration", "Illustration and iconography"),
    ("motion", "Motion and sound"),
    ("digital", "Digital products"),
    ("channels", "Channels"),
    ("accessibility", "Accessibility and inclusion"),
    ("governance", "Governance"),
)


class SourceBrandNotFound(LookupError):
    """The requested immutable legacy kit does not exist."""


class WorkspaceNotFound(LookupError):
    """The requested living-brand workspace does not exist."""


class SectionNotFound(LookupError):
    """The requested canonical section does not exist."""


class LockedSection(RuntimeError):
    """A locked section requires explicit overwrite confirmation."""


class InvalidSectionEdit(ValueError):
    """A proposed section breaks canonical validation."""


def _blank_sections() -> list[BrandSection]:
    return [
        BrandSection(id=f"section.{section_id}", title=title)
        for section_id, title in SECTION_CATALOG
    ]


def _migrated_sections(kit: BrandKit) -> list[BrandSection]:
    sections = {section.id: section for section in _blank_sections()}
    sections["section.strategy"] = sections["section.strategy"].model_copy(
        update={
            "status": "draft",
            "blocks": [
                NarrativeBlock(
                    id="block.strategy.description",
                    type="paragraph",
                    text=kit.description,
                )
            ],
        }
    )
    sections["section.messaging"] = sections["section.messaging"].model_copy(
        update={
            "status": "draft",
            "blocks": [
                NarrativeBlock(id="block.messaging.tagline", type="quotation", text=kit.tagline)
            ],
        }
    )
    sections["section.voice"] = sections["section.voice"].model_copy(
        update={
            "status": "draft",
            "blocks": [
                NarrativeBlock(id="block.voice.summary", type="paragraph", text=kit.brand_voice),
                NarrativeBlock(
                    id="block.voice.personality",
                    type="unordered_list",
                    text="\n".join(kit.personality),
                ),
            ],
        }
    )
    sections["section.color"] = sections["section.color"].model_copy(
        update={
            "status": "draft",
            "tokens": [
                BrandToken(
                    id=f"token.color.{role}",
                    name=f"{role.title()} color",
                    value_type="color",
                    value=value,
                )
                for role, value in kit.color_palette.model_dump().items()
            ],
        }
    )
    return list(sections.values())


class BrandSystemService:
    """Coordinate validated workspace operations across legacy and new stores."""

    def __init__(
        self,
        *,
        workspaces: SQLiteBrandSystemRepository,
        legacy: SQLiteBrandRepository,
        id_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        self._workspaces = workspaces
        self._legacy = legacy
        self._id_factory = id_factory

    def create(self, request: CreateWorkspaceRequest) -> WorkingDraft:
        source: BrandKit | None = None
        if request.source_brand_id is not None:
            saved = self._legacy.get(request.source_brand_id)
            if saved is None:
                raise SourceBrandNotFound
            existing = self._workspaces.get_by_source_brand_id(
                request.source_brand_id, include_trashed=True
            )
            if existing is not None:
                if self._workspaces.get(existing.brand_id) is None:
                    raise WorkspaceAlreadyTrashed("source workspace is in trash")
                return existing
            source = saved.kit
        if source is not None:
            brand_name = source.brand_name
        else:
            if request.brand_name is None:  # Contract validation makes this unreachable.
                raise ValueError("brand_name is required without a source brand")
            brand_name = request.brand_name
        draft = WorkingDraft(
            brand_id=self._id_factory(),
            source_brand_id=request.source_brand_id,
            brand_name=brand_name,
            brand_context=(
                request.brand_context
                if request.brand_context is not None
                else (source.description if source is not None else None)
            ),
            owner=LocalOwner(display_name=request.owner_name),
            revision=1,
            maturity=(
                "concept" if request.entry_path in {"raw_idea", "quick_start"} else "working"
            ),
            brief=WorkspaceBrief(
                entry_path=request.entry_path,
                assistance_mode=request.assistance_mode,
                research_mode=request.research_mode,
            ),
            sections=_migrated_sections(source) if source is not None else _blank_sections(),
        )
        return self._workspaces.create(draft)

    def replace_section(
        self,
        brand_id: UUID,
        section_id: str,
        section: BrandSection,
        expected_revision: int,
        *,
        confirm_locked: bool = False,
        change_note: str | None = None,
    ) -> WorkingDraft:
        current = self._workspaces.get(brand_id)
        if current is None:
            raise WorkspaceNotFound
        if current.revision != expected_revision:
            raise StaleDraftRevision("draft revision conflict")
        if section.id != section_id:
            raise SectionNotFound
        existing = next((item for item in current.sections if item.id == section_id), None)
        if existing is None:
            raise SectionNotFound
        if existing.locked and not confirm_locked:
            raise LockedSection
        impact, candidate = preview_section_edit(current, section)
        if candidate is None or not impact.can_apply:
            raise InvalidSectionEdit
        payload = candidate.model_dump(mode="json")
        payload.update({"revision": expected_revision + 1, "status": "draft"})
        updated = WorkingDraft.model_validate(payload)
        return self._workspaces.update(
            updated,
            expected_revision=expected_revision,
            action="section.replaced",
            reason=change_note,
        )

    def preview_section(
        self, brand_id: UUID, section_id: str, section: BrandSection, expected_revision: int
    ) -> EditImpact:
        current = self._workspaces.get(brand_id)
        if current is None:
            raise WorkspaceNotFound
        if current.revision != expected_revision:
            raise StaleDraftRevision("draft revision conflict")
        if section.id != section_id:
            raise SectionNotFound
        try:
            impact, _ = preview_section_edit(current, section)
        except LookupError as exc:
            raise SectionNotFound from exc
        return impact
