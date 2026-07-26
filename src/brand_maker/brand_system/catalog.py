"""Canonical ordered catalog for every living-brand section."""

from dataclasses import dataclass

from brand_maker.brand_system.models import PatternKind


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

TOKEN_SECTIONS = frozenset(
    {"section.color", "section.typography", "section.layout", "section.motion", "section.digital"}
)

REQUIRED_PATTERN_KINDS: dict[str, tuple[PatternKind, ...]] = {
    "section.strategy": ("positioning_framework", "audience_profile"),
    "section.messaging": ("message_hierarchy", "content_template"),
    "section.voice": ("say_never_say", "voice_scale"),
    "section.logo": ("logo_lockup", "logo_clear_space"),
    "section.color": ("color_application",),
    "section.typography": ("type_scale",),
    "section.layout": ("layout_template",),
    "section.imagery": ("image_art_direction",),
    "section.illustration": ("icon_system",),
    "section.motion": ("motion_behavior", "sound_direction"),
    "section.digital": ("web_component", "interaction_pattern"),
    "section.channels": ("channel_playbook", "content_template"),
    "section.accessibility": ("accessibility_checklist",),
    "section.governance": ("governance_workflow",),
}

assert SECTION_CATALOG.keys() == REQUIRED_PATTERN_KINDS.keys(), (
    "every catalog section needs required pattern kinds: "
    f"{sorted(SECTION_CATALOG.keys() ^ REQUIRED_PATTERN_KINDS.keys())}"
)


def prerequisite_closure(section_id: str) -> set[str]:
    """Return every transitive prerequisite, excluding the requested section."""

    closure: set[str] = set()
    pending = list(SECTION_CATALOG[section_id].prerequisites)
    while pending:
        current = pending.pop()
        if current in closure:
            continue
        closure.add(current)
        pending.extend(SECTION_CATALOG[current].prerequisites)
    closure.discard(section_id)
    return closure


def content_requirements(section_id: str) -> dict[str, object]:
    return {
        "minimum_narrative_blocks": 2,
        "minimum_rules": 1,
        "minimum_examples": 2,
        "tokens_required": section_id in TOKEN_SECTIONS,
        "required_pattern_kinds": list(REQUIRED_PATTERN_KINDS[section_id]),
    }
