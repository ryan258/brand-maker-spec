"""Workshop JavaScript package resource."""

from importlib.resources import files

WORKSHOP_SCRIPT = files("brand_maker").joinpath("static/workshop.js").read_text(encoding="utf-8")
