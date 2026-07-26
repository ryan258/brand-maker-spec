"""Compliance JavaScript package resource."""

from importlib.resources import files

COMPLIANCE_SCRIPT = files("brand_maker").joinpath("static/compliance.js").read_text(
    encoding="utf-8"
)
