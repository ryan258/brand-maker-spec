"""Ordered comprehensive section catalog and provider output envelope."""

from typing import Self

from pydantic import model_validator

from brand_maker.brand_system.catalog import (
    REQUIRED_PATTERN_KINDS,
    SECTION_CATALOG,
    TOKEN_SECTIONS,
    SectionDefinition,
    content_requirements,
    prerequisite_closure,
)
from brand_maker.brand_system.models import (
    BrandSection,
    NarrativeText,
    StableId,
)
from brand_maker.models import ContractModel

__all__ = [
    "REQUIRED_PATTERN_KINDS",
    "SECTION_CATALOG",
    "GeneratedSectionEnvelope",
    "SectionDefinition",
    "content_requirements",
    "prerequisite_closure",
]


# Keys placed in the generation prompt that models tend to echo back into their output.
# extra="forbid" then rejects an otherwise-correct section on every retry. We strip only
# these known scaffolding echoes (at envelope root and in the section); genuine injected
# keys still fail validation.
_SCAFFOLD_ECHOES = frozenset(
    {
        "purpose",
        "section_purpose",
        "section_title",
        "brand_name",
        "brand_context",
        "founding_brief",
        "content_requirements",
        "shape_rules",
        "section_contract",
        "block_contract",
        "rule_contract",
        "example_contract",
        "token_contract",
        "pattern_contract",
        "prerequisites",
        "accepted_context",
    }
)


class GeneratedSectionEnvelope(ContractModel):
    prompt_version: str
    section_id: StableId
    rationale: NarrativeText
    section: BrandSection

    @model_validator(mode="before")
    @classmethod
    def drop_echoed_scaffolding(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        # Envelope root: never touch real envelope fields (e.g. section_id).
        for key in _SCAFFOLD_ECHOES - set(cls.model_fields):
            data.pop(key, None)
        # Section object: never touch real BrandSection fields.
        section = data.get("section")
        if isinstance(section, dict):
            for key in _SCAFFOLD_ECHOES - set(BrandSection.model_fields):
                section.pop(key, None)
        return data

    @model_validator(mode="after")
    def bind_section_identity(self) -> Self:
        if self.section_id != self.section.id:
            raise ValueError("generated section cannot redefine section identity")
        if len(self.section.blocks) < 2 or not self.section.rules or len(self.section.examples) < 2:
            raise ValueError(
                "generated section must contain comprehensive guidance: two narrative "
                "blocks, one rule, and two examples"
            )
        if self.section_id in TOKEN_SECTIONS and not self.section.tokens:
            raise ValueError("generated technical section requires an implementation token")
        required_patterns = set(REQUIRED_PATTERN_KINDS[self.section_id])
        present_patterns = {pattern.kind for pattern in self.section.patterns}
        missing_patterns = sorted(required_patterns - present_patterns)
        if missing_patterns:
            raise ValueError(
                "generated section missing required brand patterns: " + ", ".join(missing_patterns)
            )
        return self
