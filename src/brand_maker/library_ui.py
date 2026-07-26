"""Brand-library JavaScript package resource."""

from importlib.resources import files

LIBRARY_SCRIPT = files("brand_maker").joinpath("static/library.js").read_text(encoding="utf-8")
