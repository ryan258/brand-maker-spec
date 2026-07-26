"""Bounded, metadata-free derivatives for raster logo assets."""

from dataclasses import dataclass
from io import BytesIO
from typing import cast

from PIL import Image, ImageChops, ImageOps, UnidentifiedImageError

RASTER_MEDIA_TYPES = {"image/gif", "image/jpeg", "image/png", "image/webp"}
MAX_RASTER_PIXELS = 16_000_000
ICON_SIZES = (
    ("favicon-16", 16),
    ("favicon-32", 32),
    ("favicon-48", 48),
    ("apple-touch-icon-180", 180),
    ("app-icon-192", 192),
    ("app-icon-512", 512),
)


@dataclass(frozen=True)
class LogoDerivative:
    name_suffix: str
    content: bytes
    media_type: str


def _decode_raster(content: bytes, media_type: str) -> Image.Image:
    if media_type not in RASTER_MEDIA_TYPES:
        raise ValueError("logo derivative source must be a supported raster image")
    try:
        with Image.open(BytesIO(content)) as source:
            if source.width * source.height > MAX_RASTER_PIXELS:
                raise ValueError("raster image exceeds the decoded-pixel safety limit")
            source.seek(0)
            image = ImageOps.exif_transpose(source).convert("RGBA")
            image.load()
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ValueError("could not decode the raster logo") from exc
    return image


def _content_bounds(image: Image.Image) -> tuple[int, int, int, int]:
    alpha = image.getchannel("A")
    alpha_min, alpha_max = alpha.getextrema()
    if alpha_min != alpha_max:
        bounds = alpha.point(lambda value: 255 if value > 8 else 0).getbbox()
        if bounds is not None:
            return bounds

    corner = Image.new("RGBA", image.size, image.getpixel((0, 0)))
    difference = ImageChops.difference(image, corner).convert("RGB")
    contrast = difference.point(lambda value: 255 if value > 12 else 0)
    bounds = contrast.getbbox()
    return bounds or (0, 0, image.width, image.height)


def _square_icon(image: Image.Image, size: int) -> bytes:
    cropped = image.crop(_content_bounds(image))
    content_size = max(1, round(size * 0.8))
    cropped.thumbnail((content_size, content_size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    offset = ((size - cropped.width) // 2, (size - cropped.height) // 2)
    canvas.alpha_composite(cropped, offset)
    output = BytesIO()
    canvas.save(output, format="PNG", optimize=True)
    return output.getvalue()


def create_icon_set(content: bytes, media_type: str) -> list[LogoDerivative]:
    """Create padded square favicon and app-icon PNGs from one raster logo."""

    image = _decode_raster(content, media_type)
    return [
        LogoDerivative(
            name_suffix=suffix,
            content=_square_icon(image, size),
            media_type="image/png",
        )
        for suffix, size in ICON_SIZES
    ]


def vectorize_logo(content: bytes, media_type: str) -> LogoDerivative:
    """Trace a raster logo into editable SVG path geometry."""

    image = _decode_raster(content, media_type)
    image.thumbnail((192, 192), Image.Resampling.LANCZOS)
    alpha = image.getchannel("A")
    if alpha.getbbox() is None:
        raise ValueError("raster logo has no visible pixels to vectorize")

    palette = image.convert("RGB").quantize(colors=8).convert("RGB")
    color_pixels: dict[tuple[int, int, int], set[tuple[int, int]]] = {}
    for y in range(image.height):
        for x in range(image.width):
            if cast(int, alpha.getpixel((x, y))) > 32:
                color = cast(tuple[int, int, int], palette.getpixel((x, y)))
                color_pixels.setdefault(color, set()).add((x, y))

    paths: list[str] = []
    for color, pixels in color_pixels.items():
        loops = _trace_pixel_boundaries(pixels)
        commands = " ".join(_loop_path(loop) for loop in loops if len(loop) >= 4)
        if commands:
            fill = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
            paths.append(f'<path fill="{fill}" fill-rule="evenodd" d="{commands}"/>')
    if not paths:
        raise ValueError("raster logo has no traceable paths")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {image.width} {image.height}" role="img">' + "".join(paths) + "</svg>"
    )
    return LogoDerivative("vector", svg.encode("utf-8"), "image/svg+xml")


Point = tuple[int, int]
Edge = tuple[Point, Point]


def _trace_pixel_boundaries(pixels: set[Point]) -> list[list[Point]]:
    edges: set[Edge] = set()
    for x, y in pixels:
        if (x, y - 1) not in pixels:
            edges.add(((x, y), (x + 1, y)))
        if (x + 1, y) not in pixels:
            edges.add(((x + 1, y), (x + 1, y + 1)))
        if (x, y + 1) not in pixels:
            edges.add(((x + 1, y + 1), (x, y + 1)))
        if (x - 1, y) not in pixels:
            edges.add(((x, y + 1), (x, y)))

    starts: dict[Point, list[Point]] = {}
    for start, end in edges:
        starts.setdefault(start, []).append(end)
    loops: list[list[Point]] = []
    while edges:
        start, current = next(iter(edges))
        edges.remove((start, current))
        loop = [start, current]
        while current != start:
            candidates = starts.get(current, [])
            next_point = next(
                (candidate for candidate in candidates if (current, candidate) in edges), None
            )
            if next_point is None:
                break
            edges.remove((current, next_point))
            loop.append(next_point)
            current = next_point
        loops.append(_simplify_loop(loop))
    return loops


def _simplify_loop(points: list[Point]) -> list[Point]:
    if len(points) < 4:
        return points
    closed = points[:-1] if points[0] == points[-1] else points
    simplified: list[Point] = []
    for index, point in enumerate(closed):
        previous = closed[index - 1]
        following = closed[(index + 1) % len(closed)]
        if (previous[0] == point[0] == following[0]) or (previous[1] == point[1] == following[1]):
            continue
        simplified.append(point)
    return [*simplified, simplified[0]] if simplified else points


def _loop_path(points: list[Point]) -> str:
    start, *rest = points
    return f"M{start[0]} {start[1]} " + " ".join(f"L{x} {y}" for x, y in rest) + " Z"


def extract_dominant_logo_color(content: bytes, media_type: str) -> str:
    """Extract dominant foreground RGB hex color from a raster logo image."""
    image = _decode_raster(content, media_type)
    alpha = image.getchannel("A")
    rgb = image.convert("RGB")
    quantized = rgb.quantize(colors=16).convert("RGB")
    background: tuple[int, int, int] | None = None
    if alpha.getextrema() == (255, 255):
        corners = [
            cast(tuple[int, int, int], rgb.getpixel(point))
            for point in (
                (0, 0),
                (image.width - 1, 0),
                (0, image.height - 1),
                (image.width - 1, image.height - 1),
            )
        ]
        background = max(corners, key=corners.count)

    def count_colors(*, exclude_background: bool) -> dict[tuple[int, int, int], int]:
        counts: dict[tuple[int, int, int], int] = {}
        for y in range(image.height):
            for x in range(image.width):
                if cast(int, alpha.getpixel((x, y))) <= 64:
                    continue
                raw_color = cast(tuple[int, int, int], rgb.getpixel((x, y)))
                if (
                    exclude_background
                    and background is not None
                    and max(abs(raw_color[index] - background[index]) for index in range(3)) <= 12
                ):
                    continue
                color = cast(tuple[int, int, int], quantized.getpixel((x, y)))
                counts[color] = counts.get(color, 0) + 1
        return counts

    counts = count_colors(exclude_background=background is not None)
    if not counts and background is not None:
        counts = count_colors(exclude_background=False)
    if not counts:
        return "#000000"
    dominant = max(counts, key=counts.get)  # type: ignore[arg-type]
    return f"#{dominant[0]:02x}{dominant[1]:02x}{dominant[2]:02x}"


def check_logo_contrast_against_backgrounds(
    content: bytes, media_type: str, background_tokens: list[tuple[str, str]]
) -> list[dict[str, object]]:
    """Check extracted logo color contrast against list of background token (name, hex) pairs."""
    from brand_maker.compliance.deterministic import _contrast

    logo_hex = extract_dominant_logo_color(content, media_type)
    results = []
    for token_name, bg_hex in background_tokens:
        if bg_hex.startswith("#") and len(bg_hex) == 7:
            ratio = round(_contrast(logo_hex, bg_hex), 2)
            passes = ratio >= 3.0  # WCAG UI element threshold
            if passes:
                msg = (
                    f"Logo color ({logo_hex}) has adequate contrast "
                    f"({ratio}:1) against '{token_name}' ({bg_hex})."
                )
            else:
                msg = (
                    f"Logo color ({logo_hex}) has low contrast "
                    f"({ratio}:1) against '{token_name}' ({bg_hex}). "
                    f"Consider a light/dark logo variant."
                )
            results.append(
                {
                    "background_token": token_name,
                    "background_color": bg_hex,
                    "logo_color": logo_hex,
                    "contrast_ratio": ratio,
                    "passes": passes,
                    "message": msg,
                }
            )
    return results
