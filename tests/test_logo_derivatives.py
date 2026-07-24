from io import BytesIO

import pytest
from PIL import Image

from brand_maker.logo_derivatives import create_icon_set, vectorize_logo


def _logo_png() -> bytes:
    image = Image.new("RGBA", (80, 40), (255, 255, 255, 0))
    for x in range(20, 60):
        for y in range(10, 30):
            image.putpixel((x, y), (18, 52, 86, 255))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_create_icon_set_returns_square_pngs_at_production_sizes() -> None:
    derivatives = create_icon_set(_logo_png(), "image/png")

    assert [item.name_suffix for item in derivatives] == [
        "favicon-16",
        "favicon-32",
        "favicon-48",
        "apple-touch-icon-180",
        "app-icon-192",
        "app-icon-512",
    ]
    for item, expected_size in zip(
        derivatives, (16, 32, 48, 180, 192, 512), strict=True
    ):
        rendered = Image.open(BytesIO(item.content))
        assert rendered.size == (expected_size, expected_size)
        assert rendered.mode == "RGBA"
        assert item.media_type == "image/png"


def test_vectorize_logo_emits_paths_without_embedding_the_raster() -> None:
    derivative = vectorize_logo(_logo_png(), "image/png")
    svg = derivative.content.decode("utf-8")

    assert derivative.media_type == "image/svg+xml"
    assert derivative.name_suffix == "vector"
    assert "<path " in svg
    assert "<image" not in svg
    assert "data:image" not in svg
    assert 'viewBox="0 0 80 40"' in svg


def test_local_derivatives_reject_svg_and_malformed_rasters() -> None:
    with pytest.raises(ValueError, match="raster"):
        create_icon_set(b"<svg/>", "image/svg+xml")
    with pytest.raises(ValueError, match="decode"):
        vectorize_logo(b"not an image", "image/png")
