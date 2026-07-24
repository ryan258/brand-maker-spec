from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

from brand_maker.app import create_app
from brand_maker.brand_bible import render_brand_bible
from brand_maker.brand_system.models import (
    BrandSection,
    BrandToken,
    LocalOwner,
    NarrativeBlock,
    WorkingDraft,
)
from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
from brand_maker.config import Settings
from brand_maker.models import BrandResponse
from brand_maker.storage import SQLiteBrandRepository


class UnusedPipeline:
    async def build(self, brand_name: str) -> BrandResponse:
        raise AssertionError("bible pages must not invoke generation")


def _draft() -> WorkingDraft:
    return WorkingDraft(
        brand_id=UUID("ea7d54dd-61f4-430e-a20e-eced89cddb37"),
        brand_name="Northstar",
        owner=LocalOwner(display_name="Ryan"),
        revision=1,
        sections=[
            BrandSection(
                id="section.voice",
                title="Voice",
                locked=False,
                blocks=[NarrativeBlock(id="block.voice.tone", type="paragraph", text="Warm.")],
            ),
            BrandSection(
                id="section.legal",
                title="Legal",
                locked=True,
                blocks=[NarrativeBlock(id="block.legal.note", type="paragraph", text="Fixed.")],
            ),
        ],
    )


def test_bible_marks_editable_prose_and_leaves_locked_sections_static() -> None:
    html = render_brand_bible(_draft())
    assert 'id="edit-bible"' in html
    # Editable section carries its id and an unlocked flag; its block is targetable.
    assert 'data-section-id="section.voice" data-locked="0"' in html
    assert 'data-block-id="block.voice.tone"' in html
    # Locked section is flagged so the client skips it.
    assert 'data-section-id="section.legal" data-locked="1"' in html


def test_bible_links_and_preselects_only_known_google_font_tokens() -> None:
    draft = _draft()
    plain = render_brand_bible(draft)
    assert "fonts.googleapis.com" not in plain  # no font tokens -> no external link

    draft.sections[0].tokens.append(
        BrandToken(
            id="token.font.display",
            name="Display font",
            value_type="font",
            value="'Playfair Display', serif",
        )
    )
    themed = render_brand_bible(draft)
    assert "css2?family=Playfair+Display" in themed
    assert "--font-display:'Playfair Display', serif" in themed
    # the matching picker option is preselected
    assert " selected>Playfair Display</option>" in themed


def _client(tmp_path: Path) -> TestClient:
    app = create_app(
        settings=Settings(openrouter_api_key="test-key", database_path=tmp_path / "b.db"),
        pipeline=UnusedPipeline(),
        brand_system_repository=SQLiteBrandSystemRepository(tmp_path / "b.db"),
        repository=SQLiteBrandRepository(tmp_path / "b.db"),
    )
    return TestClient(app)


def test_inplace_block_edit_saves_via_section_patch(tmp_path: Path) -> None:
    with _client(tmp_path) as api:
        created = api.post(
            "/api/brand-systems", json={"brand_name": "Northstar", "owner_name": "Ryan"}
        ).json()
        brand_id, section = created["brand_id"], created["sections"][0]
        # Mirror the add-paragraph + in-place edit the client performs.
        section["blocks"].append(
            {"id": "block.new.p", "type": "paragraph", "text": "Old text.", "references": []}
        )
        api.patch(
            f"/api/brand-systems/{brand_id}/sections/{section['id']}",
            json={"expected_revision": created["revision"], "section": section},
        )
        current = api.get(f"/api/brand-systems/{brand_id}").json()
        edited = next(s for s in current["sections"] if s["id"] == section["id"])
        block = next(b for b in edited["blocks"] if b["id"] == "block.new.p")
        block["text"] = "Edited in place."
        saved = api.patch(
            f"/api/brand-systems/{brand_id}/sections/{section['id']}",
            json={"expected_revision": current["revision"], "section": edited},
        )

    assert saved.status_code == 200
    stored_block = next(
        b
        for s in saved.json()["sections"]
        if s["id"] == section["id"]
        for b in s["blocks"]
        if b["id"] == "block.new.p"
    )
    assert stored_block["text"] == "Edited in place."


def test_font_pick_persists_as_typography_token(tmp_path: Path) -> None:
    with _client(tmp_path) as api:
        created = api.post(
            "/api/brand-systems", json={"brand_name": "Northstar", "owner_name": "Ryan"}
        ).json()
        brand_id = created["brand_id"]
        typo = next(s for s in created["sections"] if s["id"] == "section.typography")
        # Mirror the picker's upsert of a display font token.
        typo["tokens"].append(
            {
                "id": "token.font.display",
                "name": "Display font",
                "value_type": "font",
                "value": "'Playfair Display', serif",
                "references": [],
            }
        )
        saved = api.patch(
            f"/api/brand-systems/{brand_id}/sections/section.typography",
            json={"expected_revision": created["revision"], "section": typo},
        )
        bible = api.get(f"/brand-systems/{brand_id}/bible")

    assert saved.status_code == 200
    # The saved token now drives both the external font link and the theme override.
    assert "css2?family=Playfair+Display" in bible.text
    assert "--font-display:'Playfair Display', serif" in bible.text
