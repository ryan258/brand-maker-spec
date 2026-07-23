"""Ordered comprehensive section catalog and provider output envelope."""

from dataclasses import dataclass
from typing import Self

from pydantic import model_validator

from brand_maker.brand_system.models import BrandSection, NarrativeText, StableId
from brand_maker.models import ContractModel


@dataclass(frozen=True)
class SectionDefinition:
    id: str
    title: str
    purpose: str
    prerequisites: tuple[str, ...] = ()


def _definition(key: str, title: str, purpose: str, *prerequisites: str) -> SectionDefinition:
    return SectionDefinition(
        id=f"section.{key}",
        title=title,
        purpose=purpose,
        prerequisites=tuple(f"section.{item}" for item in prerequisites),
    )


SECTION_CATALOG = {
    item.id: item
    for item in (
        _definition("strategy", "Strategy", "Define purpose, audience, positioning, and promise."),
        _definition(
            "messaging", "Messaging", "Define message hierarchy and reusable claims.", "strategy"
        ),
        _definition(
            "voice", "Voice", "Define voice traits, language rules, and examples.", "strategy"
        ),
        _definition(
            "logo", "Logo guidance", "Govern supplied logo variants and usage.", "strategy"
        ),
        _definition("color", "Color", "Define semantic palettes and combinations.", "strategy"),
        _definition(
            "typography", "Typography", "Define type roles, scale, and fallbacks.", "strategy"
        ),
        _definition(
            "layout", "Layout", "Define spacing, grids, and composition.", "color", "typography"
        ),
        _definition(
            "imagery", "Imagery", "Define photographic and art direction.", "strategy", "color"
        ),
        _definition(
            "illustration",
            "Illustration and iconography",
            "Define illustration and icon rules.",
            "imagery",
        ),
        _definition(
            "motion",
            "Motion and sound",
            "Define motion, timing, sound, and reduced-motion rules.",
            "voice",
        ),
        _definition(
            "digital", "Digital products", "Define interaction and component guidance.", "layout"
        ),
        _definition(
            "channels",
            "Channels",
            "Adapt the system for key communication channels.",
            "messaging",
            "voice",
        ),
        _definition(
            "accessibility",
            "Accessibility and inclusion",
            "Define inclusive and testable constraints.",
            "color",
            "typography",
            "digital",
        ),
        _definition(
            "governance",
            "Governance",
            "Define approval, version, exception, and review policy.",
            "strategy",
        ),
    )
}


class GeneratedSectionEnvelope(ContractModel):
    prompt_version: str
    section_id: StableId
    rationale: NarrativeText
    section: BrandSection

    @model_validator(mode="after")
    def bind_section_identity(self) -> Self:
        if self.section_id != self.section.id:
            raise ValueError("generated section cannot redefine section identity")
        return self
