"""Tests for Personal Brand OS enhancements (Ideas 11, 12, 15, 25, 30, 61, 64, 66)."""

import asyncio
from io import BytesIO
from uuid import uuid4

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

from brand_maker.brand_system.assets import (
    generate_font_face_css,
    validate_font_file_header,
)
from brand_maker.brand_system.models import (
    BrandPattern,
    BrandRule,
    BrandSection,
    BrandToken,
    LocalOwner,
    NarrativeBlock,
    PatternSpecification,
    WorkingDraft,
)
from brand_maker.compliance.copy_checker import (
    check_copy_against_brand_rules,
    deterministic_copy_rules,
)
from brand_maker.compliance.deterministic import (
    audit_token_collisions,
    audit_token_contrast_pairs,
)
from brand_maker.generation.orchestrator import (
    GenerationOrchestrator,
    GenerationRunNotFound,
)
from brand_maker.generation.prompts import variant_generation_messages
from brand_maker.generation.sections import SECTION_CATALOG
from brand_maker.logo_derivatives import (
    check_logo_contrast_against_backgrounds,
    extract_dominant_logo_color,
)


def create_sample_workspace() -> WorkingDraft:
    return WorkingDraft(
        brand_id=uuid4(),
        brand_name="Fieldwell",
        brand_context="Living brand system for organic farming software.",
        owner=LocalOwner(display_name="Test Owner"),
        revision=1,
        sections=[
            BrandSection(
                id="section.identity",
                title="Brand Identity",
                status="draft",
                blocks=[
                    NarrativeBlock(
                        id="block.id.1",
                        type="paragraph",
                        text="Fieldwell is modern, sustainable, and reliable.",
                    )
                ],
                rules=[
                    BrandRule(
                        id="rule.id.1",
                        name="No Parody Language",
                        description="Never say parody in marketing copy.",
                        enforcement="blocking",
                    )
                ],
                tokens=[
                    BrandToken(
                        id="token.color.primary",
                        name="Primary Green",
                        value_type="color",
                        value="#1b4d3e",
                    ),
                    BrandToken(
                        id="token.color.paper.light",
                        name="Paper Light",
                        value_type="color",
                        value="#ffffff",
                    ),
                ],
            ),
            BrandSection(
                id="section.typography",
                title="Typography & Design",
                status="draft",
                tokens=[
                    BrandToken(
                        id="token.color.secondary",
                        name="Secondary Accent",
                        value_type="color",
                        value="#2a6e59",
                    ),
                    BrandToken(
                        id="token.color.paper.dark",
                        name="Paper Dark",
                        value_type="color",
                        value="#111827",
                    ),
                ],
            ),
        ],
    )


def create_test_font(*, flavor: str | None = None) -> bytes:
    builder = FontBuilder(1024, isTTF=True)
    builder.setupGlyphOrder([".notdef"])
    pen = TTGlyphPen(None)
    builder.setupGlyf({".notdef": pen.glyph()})
    builder.setupHorizontalMetrics({".notdef": (500, 0)})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupCharacterMap({})
    builder.setupNameTable(
        {
            "familyName": "Test Font",
            "styleName": "Regular",
            "uniqueFontIdentifier": "Test Font Regular",
            "fullName": "Test Font Regular",
            "psName": "Test-Font-Regular",
        }
    )
    builder.setupOS2(
        sTypoAscender=800,
        sTypoDescender=-200,
        usWinAscent=800,
        usWinDescent=200,
    )
    builder.setupPost()
    builder.setupMaxp()
    builder.font.flavor = flavor
    output = BytesIO()
    builder.save(output)
    return output.getvalue()


def test_font_header_validation():
    woff_data = create_test_font(flavor="woff")
    woff2_data = create_test_font(flavor="woff2")
    ttf_data = create_test_font()

    assert validate_font_file_header(woff_data) == "woff"
    assert validate_font_file_header(woff2_data) == "woff2"
    assert validate_font_file_header(ttf_data) == "truetype"

    with pytest.raises(ValueError, match="Invalid font magic bytes"):
        validate_font_file_header(b"BADHEADER")

    with pytest.raises(ValueError, match="could not be parsed"):
        validate_font_file_header(b"wOF2\x00\x01\x00\x00")

    oversized_woff2 = bytearray(48)
    oversized_woff2[:4] = b"wOF2"
    oversized_woff2[16:20] = (30_000_000).to_bytes(4, "big")
    with pytest.raises(ValueError, match="decoded size"):
        validate_font_file_header(bytes(oversized_woff2))


def test_font_face_css_generation():
    css = generate_font_face_css("Inter Custom", "font/woff2", "/api/assets/123")
    assert "@font-face" in css
    assert "font-family: 'Inter Custom';" in css
    assert "url('/api/assets/123')" in css
    assert "format('woff2');" in css


def test_copy_compliance_checker():
    workspace = create_sample_workspace()
    clean_copy = "Fieldwell provides high yield harvest insights."
    clean_report = check_copy_against_brand_rules(clean_copy, workspace)
    assert clean_report.overall_status == "pass"
    assert len(clean_report.violations) == 0

    bad_copy = "This is a parody joke system for farming."
    bad_report = check_copy_against_brand_rules(bad_copy, workspace)
    assert bad_report.overall_status == "fail"
    assert len(bad_report.violations) >= 1
    assert any("parody" in v.message.lower() for v in bad_report.violations)


def test_copy_compliance_uses_structured_never_say_specifications() -> None:
    workspace = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Fieldwell",
        owner=LocalOwner(display_name="Owner"),
        revision=1,
        sections=[
            BrandSection(
                id="section.voice",
                title="Voice",
                patterns=[
                    BrandPattern(
                        id="pattern.voice.language",
                        name="Language choices",
                        kind="say_never_say",
                        summary="Approved language boundaries.",
                        specifications=[
                            PatternSpecification(label="Never say", value="game-changing")
                        ],
                        do_guidance=["Use concrete outcomes."],
                        dont_guidance=["Avoid unsupported language."],
                    )
                ],
            )
        ],
    )

    report = check_copy_against_brand_rules("A game-changing platform.", workspace)

    assert report.overall_status == "warning"
    assert report.violations[0].matched_text == "game-changing"
    rules = deterministic_copy_rules(workspace)
    assert [(rule.kind, rule.parameter) for rule in rules] == [
        ("forbidden_term", "game-changing")
    ]


def test_published_compliance_rule_ids_remain_within_contract_limits() -> None:
    pattern = BrandPattern(
        id="pattern." + "x" * 120,
        name="Language choices",
        kind="say_never_say",
        summary="Approved language boundaries.",
        specifications=[PatternSpecification(label="Never say", value="game-changing")],
        do_guidance=["Use concrete outcomes."],
        dont_guidance=["Avoid unsupported language."],
    )
    workspace = WorkingDraft(
        brand_id=uuid4(),
        brand_name="Fieldwell",
        owner=LocalOwner(display_name="Owner"),
        revision=1,
        sections=[BrandSection(id="section.voice", title="Voice", patterns=[pattern])],
    )

    rules = deterministic_copy_rules(workspace)

    assert len(rules[0].id) <= 128


def test_token_collision_audit():
    section1 = BrandSection(
        id="section.identity",
        title="Brand Identity",
        status="draft",
        tokens=[
            BrandToken(
                id="token.color.primary",
                name="Primary Green",
                value_type="color",
                value="#1b4d3e",
            )
        ],
    )
    section2 = BrandSection(
        id="section.typography",
        title="Typography",
        status="draft",
        tokens=[
            BrandToken(
                id="token.color.primary",
                name="Primary Green (Duplicate)",
                value_type="color",
                value="#2a6e59",
            )
        ],
    )
    collisions = audit_token_collisions([section1, section2])
    assert len(collisions) == 1
    c = collisions[0]
    assert c.token_id == "token.color.primary"
    assert c.collision_type == "value_mismatch"
    assert any("Brand Identity" in s for s in c.sections)
    assert any("Typography" in s for s in c.sections)


def test_wcag_token_contrast_pairs_audit():
    workspace = create_sample_workspace()
    findings = audit_token_contrast_pairs(workspace.sections)
    # Check contrast between Primary Green (#1b4d3e) and Paper Light (#ffffff)
    fg_bg_pair = next((f for f in findings if f.foreground_token_id == "token.color.primary"), None)
    assert fg_bg_pair is not None
    assert fg_bg_pair.contrast_ratio >= 4.5
    assert fg_bg_pair.passes_aa_normal is True


def test_logo_contrast_against_backgrounds():
    import io

    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 80, 80], fill=(27, 77, 62, 255))  # #1b4d3e
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    dominant = extract_dominant_logo_color(png_bytes, "image/png")
    assert dominant.startswith("#")

    results = check_logo_contrast_against_backgrounds(
        png_bytes, "image/png", [("Paper Light", "#ffffff"), ("Dark Paper", "#111827")]
    )
    assert len(results) == 2
    assert results[0]["contrast_ratio"] > 1.0


def test_logo_contrast_ignores_opaque_canvas_background():
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (100, 100), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([35, 35, 65, 65], fill="black")
    buf = BytesIO()
    img.save(buf, format="PNG")

    dominant = extract_dominant_logo_color(buf.getvalue(), "image/png")
    results = check_logo_contrast_against_backgrounds(
        buf.getvalue(), "image/png", [("Paper Light", "#ffffff")]
    )

    assert dominant == "#000000"
    assert results[0]["contrast_ratio"] == 21.0


@pytest.mark.asyncio
async def test_generation_orchestrator_streaming(tmp_path):
    from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
    from brand_maker.generation.repository import SQLiteGenerationRepository

    db_path = tmp_path / "test.db"
    workspaces = SQLiteBrandSystemRepository(db_path)
    runs = SQLiteGenerationRepository(db_path)
    orchestrator = GenerationOrchestrator(workspaces=workspaces, runs=runs)

    workspace = create_sample_workspace()
    workspaces.create(workspace)

    run = orchestrator.start(workspace, target_section_id="section.strategy", model="test-model")
    queue = orchestrator.subscribe(run.id)
    initial = queue.get_nowait()
    assert initial["status"] == "pending"

    # Pause run to trigger event notification
    orchestrator.pause(run.id)

    event = await asyncio.wait_for(queue.get(), timeout=2.0)
    assert event["run_id"] == str(run.id)
    assert event["status"] == "paused"


def test_generation_subscriber_receives_existing_terminal_state(tmp_path):
    from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
    from brand_maker.generation.repository import SQLiteGenerationRepository

    db_path = tmp_path / "test.db"
    workspaces = SQLiteBrandSystemRepository(db_path)
    runs = SQLiteGenerationRepository(db_path)
    orchestrator = GenerationOrchestrator(workspaces=workspaces, runs=runs)
    workspace = create_sample_workspace()
    workspaces.create(workspace)
    run = orchestrator.start(workspace, target_section_id="section.strategy", model="test-model")
    orchestrator.cancel(run.id)

    event = orchestrator.subscribe(run.id).get_nowait()

    assert event["status"] == "cancelled"


def test_generation_subscriber_rejects_unknown_run(tmp_path):
    from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
    from brand_maker.generation.repository import SQLiteGenerationRepository

    db_path = tmp_path / "test.db"
    orchestrator = GenerationOrchestrator(
        workspaces=SQLiteBrandSystemRepository(db_path),
        runs=SQLiteGenerationRepository(db_path),
    )

    with pytest.raises(GenerationRunNotFound):
        orchestrator.subscribe(uuid4())


def test_generation_subscriber_keeps_latest_unread_state(tmp_path):
    from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
    from brand_maker.generation.repository import SQLiteGenerationRepository

    db_path = tmp_path / "test.db"
    workspaces = SQLiteBrandSystemRepository(db_path)
    orchestrator = GenerationOrchestrator(
        workspaces=workspaces,
        runs=SQLiteGenerationRepository(db_path),
    )
    workspace = create_sample_workspace()
    workspaces.create(workspace)
    run = orchestrator.start(workspace, target_section_id="section.strategy", model="test-model")
    queue = orchestrator.subscribe(run.id)

    orchestrator.pause(run.id)

    assert queue.get_nowait()["status"] == "paused"


def test_variant_prompt_requests_one_envelope_per_provider_call():
    messages = variant_generation_messages(
        definition=SECTION_CATALOG["section.strategy"],
        brand_name="Fieldwell",
        postures=["balanced"],
    )

    system_prompt = messages[0]["content"].lower()
    assert "single" in system_prompt
    assert "key 'variants'" not in system_prompt
