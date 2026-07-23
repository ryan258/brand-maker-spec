import pytest
from pydantic import ValidationError

from brand_maker.models import (
    BrandKit,
    BrandRequest,
    BrandResponse,
    BrandSummary,
    ColorPalette,
    SavedBrand,
    SavedBrandPage,
)


def valid_kit_data() -> dict[str, object]:
    return {
        "brand_name": "Floogle",
        "parody_target": "Google",
        "tagline": "Search less. Guess more.",
        "description": "A search engine that indexes vibes instead of facts.",
        "brand_voice": "Cheerful, over-confident, and technically wrong on purpose.",
        "personality": ["Playful", "Chaotic", "Helpful"],
        "color_palette": {
            "primary": "#4285F4",
            "secondary": "#EA4335",
            "accent": "#FBBC05",
            "background": "#FFFFFF",
        },
    }


def test_brand_request_accepts_name_at_contract_boundaries() -> None:
    assert BrandRequest(brand_name="F").brand_name == "F"
    assert len(BrandRequest(brand_name="F" * 80).brand_name) == 80


@pytest.mark.parametrize("brand_name", ["", "F" * 81])
def test_brand_request_rejects_name_outside_contract(brand_name: str) -> None:
    with pytest.raises(ValidationError):
        BrandRequest(brand_name=brand_name)


def test_brand_kit_accepts_complete_contract() -> None:
    kit = BrandKit.model_validate(valid_kit_data())

    assert kit.color_palette.primary == "#4285F4"
    assert len(kit.personality) == 3


@pytest.mark.parametrize("color", ["4285F4", "#fff", "#GGGGGG", "#1234567"])
def test_color_palette_rejects_non_six_digit_hex(color: str) -> None:
    palette = valid_kit_data()["color_palette"]
    assert isinstance(palette, dict)
    palette["primary"] = color

    with pytest.raises(ValidationError):
        ColorPalette.model_validate(palette)


@pytest.mark.parametrize(
    ("status", "kit", "message"),
    [
        ("ok", None, None),
        ("error", valid_kit_data(), "failed"),
        ("refused", valid_kit_data(), None),
    ],
)
def test_brand_response_rejects_inconsistent_status_payload(
    status: str, kit: object, message: str | None
) -> None:
    with pytest.raises(ValidationError):
        BrandResponse.model_validate({"status": status, "kit": kit, "message": message})


def test_models_reject_unknown_fields() -> None:
    data = valid_kit_data()
    data["unexpected"] = "not part of the contract"

    with pytest.raises(ValidationError):
        BrandKit.model_validate(data)


def test_saved_brand_summary_and_page_contracts() -> None:
    saved = SavedBrand.model_validate(
        {
            "id": "7b48b1ac-95e3-4fab-bf83-b7009ee2f6c4",
            "created_at": "2026-07-23T12:00:00Z",
            "kit": valid_kit_data(),
        }
    )
    summary = BrandSummary.from_saved(saved)
    page = SavedBrandPage(
        items=[summary], page=1, page_size=12, total_items=1, total_pages=1
    )

    assert summary.brand_name == "Floogle"
    assert summary.color_palette.primary == "#4285F4"
    assert page.items == [summary]
