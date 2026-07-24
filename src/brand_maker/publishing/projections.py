"""Audience-specific projections derived from one immutable publication."""

from typing import Literal

from pydantic import Field

from brand_maker.brand_system.models import BrandSection, RenderedPublishedVersion
from brand_maker.models import ContractModel

Audience = Literal["creator", "designer", "business", "agency"]

AUDIENCE_SECTIONS: dict[Audience, frozenset[str]] = {
    "creator": frozenset(
        {"section.strategy", "section.messaging", "section.voice", "section.imagery"}
    ),
    "designer": frozenset(
        {
            "section.strategy",
            "section.logo",
            "section.color",
            "section.typography",
            "section.imagery",
            "section.motion",
            "section.accessibility",
        }
    ),
    "business": frozenset(
        {"section.strategy", "section.audience", "section.messaging", "section.governance"}
    ),
    "agency": frozenset(),
}


class AudienceProjection(ContractModel):
    brand_id: str
    brand_name: str
    version: str
    amendment_revision: int = Field(..., ge=0)
    audience: Audience
    source_content_hash: str
    sections: list[BrandSection]


def project(
    rendered: RenderedPublishedVersion, *, content_hash: str, audience: Audience
) -> AudienceProjection:
    included = AUDIENCE_SECTIONS[audience]
    sections = [
        section
        for section in rendered.rendered_snapshot.sections
        if not included or section.id in included
    ]
    return AudienceProjection(
        brand_id=str(rendered.brand_id),
        brand_name=rendered.rendered_snapshot.brand_name,
        version=rendered.version,
        amendment_revision=rendered.amendment_revision,
        audience=audience,
        source_content_hash=content_hash,
        sections=sections,
    )
