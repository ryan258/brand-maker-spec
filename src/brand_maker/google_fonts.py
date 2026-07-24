"""Curated Google Fonts for the brand font picker (no API key required)."""

# ponytail: a hand-picked shortlist, not the full Google catalog. Extend the tuple
# if brands ask for more; a live API pull needs a key and isn't worth it here.
GOOGLE_FONTS: tuple[tuple[str, str], ...] = (
    ("Inter", "sans-serif"),
    ("Roboto", "sans-serif"),
    ("Open Sans", "sans-serif"),
    ("Lato", "sans-serif"),
    ("Montserrat", "sans-serif"),
    ("Poppins", "sans-serif"),
    ("Work Sans", "sans-serif"),
    ("Source Sans 3", "sans-serif"),
    ("Nunito", "sans-serif"),
    ("Raleway", "sans-serif"),
    ("DM Sans", "sans-serif"),
    ("Space Grotesk", "sans-serif"),
    ("Manrope", "sans-serif"),
    ("Archivo", "sans-serif"),
    ("Rubik", "sans-serif"),
    ("Playfair Display", "serif"),
    ("Merriweather", "serif"),
    ("Lora", "serif"),
    ("PT Serif", "serif"),
    ("Source Serif 4", "serif"),
    ("Libre Baskerville", "serif"),
    ("EB Garamond", "serif"),
    ("Cormorant Garamond", "serif"),
    ("Spectral", "serif"),
    ("Fraunces", "serif"),
    ("DM Serif Display", "serif"),
    ("JetBrains Mono", "monospace"),
    ("IBM Plex Mono", "monospace"),
    ("Space Mono", "monospace"),
)

_GENERIC = dict(GOOGLE_FONTS)


def font_stack(family: str) -> str:
    """CSS value for a known family, e.g. 'Playfair Display' -> \"'Playfair Display', serif\"."""
    return f"'{family}', {_GENERIC[family]}"


def family_of(value: str) -> str | None:
    """Return the Google family named in a stored token value, if we know it."""
    family = value.split("'")[1] if "'" in value else value.split(",")[0].strip()
    return family if family in _GENERIC else None


def google_css_url(families: list[str]) -> str:
    """Build the fonts.googleapis.com css2 URL for known families (spaces -> '+')."""
    spec = "&".join(f"family={family.replace(' ', '+')}" for family in families)
    return f"https://fonts.googleapis.com/css2?{spec}&display=swap"
