"""Home-page JavaScript package resource."""

from importlib.resources import files

UI_SCRIPT = files("brand_maker").joinpath("static/app.js").read_text(encoding="utf-8")
