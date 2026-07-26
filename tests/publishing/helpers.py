from datetime import UTC, datetime
from uuid import UUID

from brand_maker.brand_system.models import (
    ApprovalRecord,
    BrandPattern,
    BrandSection,
    LocalOwner,
    NarrativeBlock,
    PatternSpecification,
    PublicationManifest,
    PublishedVersion,
    RenderedPublishedVersion,
    WorkingDraft,
)


def published_version() -> PublishedVersion:
    brand_id = UUID("d795ebf9-8f54-44a2-85cd-e73faacb7008")
    now = datetime(2026, 7, 23, tzinfo=UTC)
    draft = WorkingDraft(
        brand_id=brand_id,
        brand_name="Northstar",
        owner=LocalOwner(display_name="Ryan"),
        revision=4,
        sections=[
            BrandSection(
                id="section.strategy",
                title="Strategy",
                status="approved",
                blocks=[
                    NarrativeBlock(
                        id="block.strategy.purpose",
                        type="paragraph",
                        text="A clear purpose & durable direction.",
                    )
                ],
                patterns=[
                    BrandPattern(
                        id="pattern.voice.say-never-say",
                        name="Say / never say",
                        kind="say_never_say",
                        summary="Turn the voice into concrete language choices.",
                        specifications=[
                            PatternSpecification(label="Say", value="Lead with the reader benefit.")
                        ],
                        do_guidance=["Use specific, verifiable language."],
                        dont_guidance=["Use unsupported superlatives."],
                    )
                ],
            ),
            BrandSection(id="section.logo", title="Logo", status="approved"),
        ],
    )
    approval = ApprovalRecord(
        id=UUID("064027ac-6b11-4f86-93d4-1f5f87609ca2"),
        brand_id=brand_id,
        draft_revision=4,
        owner_id="local-owner",
        approved_at=now,
        rationale="Ready to publish.",
    )
    return PublishedVersion(
        brand_id=brand_id,
        version="1.0.0",
        published_at=now,
        publisher_id="local-owner",
        draft_revision=4,
        change_summary="Initial guide.",
        content_hash="a" * 64,
        manifest=PublicationManifest(
            schema_version="1.0", draft_revision=4, section_ids=["section.strategy", "section.logo"]
        ),
        approvals=[approval],
        snapshot=draft,
    )


def rendered_version() -> RenderedPublishedVersion:
    published = published_version()
    return RenderedPublishedVersion(
        brand_id=published.brand_id,
        version=published.version,
        amendment_revision=0,
        rendered_change_summary=published.change_summary,
        rendered_snapshot=published.snapshot,
        amendments=[],
    )
