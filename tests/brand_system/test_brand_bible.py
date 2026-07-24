from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

from brand_maker.app import create_app
from brand_maker.brand_bible import _brand_theme, render_brand_bible
from brand_maker.brand_system.models import (
    AssetRegistration,
    BrandExample,
    BrandPattern,
    BrandRule,
    BrandSection,
    BrandToken,
    LocalOwner,
    NarrativeBlock,
    PatternSpecification,
    WorkingDraft,
)
from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
from brand_maker.config import Settings
from brand_maker.models import BrandResponse
from brand_maker.storage import SQLiteBrandRepository


class UnusedPipeline:
    async def build(self, brand_name: str) -> BrandResponse:
        raise AssertionError("brand bible pages must not invoke generation")


def complete_draft() -> WorkingDraft:
    return WorkingDraft(
        brand_id=UUID("ea7d54dd-61f4-430e-a20e-eced89cddb37"),
        brand_name="Northstar & Co.",
        brand_context='<script>alert("context")</script>\nIndependent bookstores.',
        owner=LocalOwner(display_name="Ryan & team"),
        revision=7,
        status="reviewed",
        sections=[
            BrandSection(
                id="section.strategy",
                title="Strategy & purpose",
                status="approved",
                locked=True,
                blocks=[
                    NarrativeBlock(
                        id="block.strategy.purpose",
                        type="paragraph",
                        text="Build trust & durable recognition.",
                    )
                ],
                rules=[
                    BrandRule(
                        id="rule.strategy.truth",
                        name="Tell the truth",
                        description="Never overstate evidence & outcomes.",
                        enforcement="blocking",
                    )
                ],
                tokens=[
                    BrandToken(
                        id="token.color.ink",
                        name="Ink",
                        value_type="color",
                        value="#17201c",
                    )
                ],
                examples=[
                    BrandExample(
                        id="example.strategy.do",
                        kind="do",
                        text="Use concrete, verifiable language.",
                    )
                ],
                patterns=[
                    BrandPattern(
                        id="pattern.voice.say-never-say",
                        name="Say / never say",
                        kind="say_never_say",
                        summary="Turn the voice into concrete language choices.",
                        specifications=[
                            PatternSpecification(
                                label="Say",
                                value="Your neighborhood guide to books that matter.",
                            ),
                            PatternSpecification(
                                label="Never say",
                                value="The ultimate revolutionary content destination.",
                            ),
                        ],
                        do_guidance=["Lead with a specific reader benefit."],
                        dont_guidance=["Use unsupported superlatives & hype."],
                    ),
                    BrandPattern(
                        id="pattern.digital.primary-button",
                        name="Primary web button",
                        kind="web_component",
                        summary="The highest-priority action in a page or flow.",
                        specifications=[
                            PatternSpecification(
                                label="Anatomy",
                                value="Action label, focus ring, and optional leading icon.",
                            ),
                            PatternSpecification(
                                label="States",
                                value="Default, hover, focus, active, loading, and disabled.",
                            ),
                            PatternSpecification(
                                label="Accessibility",
                                value="Native button semantics and a 44 by 44 pixel target.",
                            ),
                        ],
                        do_guidance=["Use one primary action per decision area."],
                        dont_guidance=["Use color alone to communicate state."],
                    ),
                ],
            ),
            BrandSection(
                id="section.messaging",
                title="Messaging",
                status="incomplete",
            ),
        ],
        assets=[
            AssetRegistration(
                id="asset.logo.primary",
                name="Primary logo",
                storage="linked",
                media_type="image/svg+xml",
                size_bytes=2_048,
                content_hash="a" * 64,
                source_path="/tmp/Northstar & Co/logo.svg",
                required=True,
            )
        ],
    )


def test_complete_brand_bible_renders_every_canonical_content_kind_safely() -> None:
    page = render_brand_bible(complete_draft())

    assert page.count("<h1") == 1
    assert "Northstar &amp; Co." in page
    assert "Ryan &amp; team" in page
    assert "&lt;script&gt;alert" in page
    assert '<script>alert("context")</script>' not in page
    assert 'href="#section.strategy"' in page
    assert "Build trust &amp; durable recognition." in page
    assert "Never overstate evidence &amp; outcomes." in page
    assert "#17201c" in page
    assert "Use concrete, verifiable language." in page
    assert "Patterns &amp; playbooks" in page
    assert "Say / never say" in page
    assert "Your neighborhood guide to books that matter." in page
    assert "Primary web button" in page
    assert "Default, hover, focus, active, loading, and disabled." in page
    assert "Use unsupported superlatives &amp; hype." in page
    assert "/tmp/Northstar &amp; Co/logo.svg" in page
    # section.messaging is empty and editable, so its empty state links into the workshop.
    assert 'href="/brand-systems/ea7d54dd-61f4-430e-a20e-eced89cddb37#section.messaging"' in page
    assert "Add it in the workshop" in page
    assert "Print or save PDF" in page


def _color(role: str, value: str) -> BrandToken:
    return BrandToken(
        id=f"token.color.{role}", name=f"{role} color", value_type="color", value=value
    )


def _draft_with_tokens(tokens: list[BrandToken]) -> WorkingDraft:
    return WorkingDraft(
        brand_id=UUID("ea7d54dd-61f4-430e-a20e-eced89cddb37"),
        brand_name="Themed",
        owner=LocalOwner(display_name="Owner"),
        revision=1,
        sections=[BrandSection(id="section.visual", title="Visual", status="draft", tokens=tokens)],
    )


def test_empty_locked_section_shows_no_workshop_link() -> None:
    draft = _draft_with_tokens([])
    draft.sections[0].locked = True
    page = render_brand_bible(draft)

    assert "No guidance has been added to this section yet." in page
    assert "Add it in the workshop" not in page


def test_brand_theme_maps_color_and_font_tokens_to_css_roles_by_keyword() -> None:
    font = BrandToken(
        id="token.font.display", name="Display", value_type="font", value="Georgia, serif"
    )
    tokens = [_color("ink", "#17201c"), _color("accent", "#a93624"), font]
    style = _brand_theme(_draft_with_tokens(tokens))

    expected = "<style>:root{--accent:#a93624;--ink:#17201c;--font-display:Georgia, serif}</style>"
    assert style == expected


def test_brand_theme_assigns_each_token_one_role_and_derives_neutrals_from_paper() -> None:
    # Primary and Accent both match the --accent keywords; the earlier token wins it
    # once (no collision), and defining a background derives surface + line too.
    style = _brand_theme(
        _draft_with_tokens(
            [
                _color("primary", "#997333"),
                _color("secondary", "#524837"),
                _color("accent", "#044843"),
                _color("background", "#f5f5e3"),
            ]
        )
    )

    assert style.count("--accent:") == 1
    assert "--accent:#997333" in style  # primary claims accent; no second assignment
    assert "--paper:#f5f5e3" in style
    assert "--muted:#524837" in style
    assert "--surface:" in style and "--line:" in style  # derived from paper


def test_brand_theme_rejects_unsafe_token_values_that_could_break_out_of_style() -> None:
    style = _brand_theme(_draft_with_tokens([_color("ink", "red}</style><script>x")]))

    assert style == ""


def test_brand_theme_is_empty_when_no_token_names_match_a_role() -> None:
    style = _brand_theme(
        _draft_with_tokens(
            [BrandToken(id="token.color.unnamed", name="Zzz", value_type="color", value="#000000")]
        )
    )

    assert style == ""


def test_brand_bible_route_reads_current_draft_and_workshop_links_to_it(
    tmp_path: Path,
) -> None:
    database = tmp_path / "brands.db"
    workspaces = SQLiteBrandSystemRepository(database)
    draft = complete_draft()
    workspaces.create(draft)
    app = create_app(
        settings=Settings(
            _env_file=None,
            openrouter_api_key="test-key",
            database_path=database,
        ),
        pipeline=UnusedPipeline(),
        repository=SQLiteBrandRepository(database),
        brand_system_repository=workspaces,
    )

    with TestClient(app) as client:
        bible = client.get(f"/brand-systems/{draft.brand_id}/bible")
        workshop = client.get(f"/brand-systems/{draft.brand_id}")
        workshop_script = client.get("/assets/workshop.js")
        bible_styles = client.get("/assets/brand-bible.css")
        missing = client.get("/brand-systems/11111111-1111-4111-8111-111111111111/bible")

    assert bible.status_code == 200
    assert bible.headers["content-security-policy"]
    assert f'data-brand-id="{draft.brand_id}"' in bible.text
    assert workshop.status_code == 200
    assert "View complete brand bible" in workshop_script.text
    assert "/bible`" in workshop_script.text
    assert bible_styles.status_code == 200
    assert "@media(max-width:40rem)" in bible_styles.text
    assert "@media print" in bible_styles.text
    assert 'document.getElementById("print-bible")' in workshop_script.text
    assert missing.status_code == 404
