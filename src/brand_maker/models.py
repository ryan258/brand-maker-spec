"""Public request and response contracts for the service."""

from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

HEX = r"^#(?:[0-9a-fA-F]{6})$"


class ContractModel(BaseModel):
    """Strict base model used at all public boundaries."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class BrandRequest(ContractModel):
    """The only thing the caller provides: a brand name."""

    brand_name: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description="The brand name to develop into a quick concept-stage kit.",
    )


class ColorPalette(ContractModel):
    """Full palette. All four roles required and encoded as six-digit hex."""

    primary: str = Field(..., pattern=HEX)
    secondary: str = Field(..., pattern=HEX)
    accent: str = Field(..., pattern=HEX)
    background: str = Field(..., pattern=HEX)


class BrandKit(ContractModel):
    """The finished brand kit returned to the caller."""

    brand_name: str = Field(..., min_length=1)
    parody_target: str = Field(
        ...,
        min_length=1,
        description="Legacy field containing the positioning reference or category.",
    )
    tagline: str = Field(..., min_length=1, max_length=120)
    description: str = Field(..., min_length=1, max_length=500)
    brand_voice: str = Field(..., min_length=1, max_length=400)
    personality: list[Annotated[str, Field(min_length=1)]] = Field(
        ..., min_length=3, max_length=6, description="3 to 6 trait words."
    )
    color_palette: ColorPalette


class BrandResponse(ContractModel):
    """A discriminated service outcome with no contradictory partial state."""

    status: Literal["ok", "refused", "error"]
    kit: BrandKit | None = None
    message: str | None = None

    @model_validator(mode="after")
    def validate_outcome(self) -> Self:
        if self.status == "ok" and (self.kit is None or self.message is not None):
            raise ValueError("ok responses require a kit and no message")
        if self.status != "ok" and (self.kit is not None or not self.message):
            raise ValueError("non-ok responses require a message and no kit")
        return self


class SavedBrand(ContractModel):
    """An immutable generated kit with server-owned identity and creation time."""

    id: UUID
    created_at: datetime
    kit: BrandKit


class BrandSummary(ContractModel):
    """The compact brand representation returned by collection endpoints."""

    id: UUID
    created_at: datetime
    brand_name: str
    parody_target: str
    tagline: str
    color_palette: ColorPalette

    @classmethod
    def from_saved(cls, saved: SavedBrand) -> Self:
        return cls(
            id=saved.id,
            created_at=saved.created_at,
            brand_name=saved.kit.brand_name,
            parody_target=saved.kit.parody_target,
            tagline=saved.kit.tagline,
            color_palette=saved.kit.color_palette,
        )


class SavedBrandPage(ContractModel):
    """A bounded, newest-first page from the local brand library."""

    items: list[BrandSummary]
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_items: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)


class SavedBrandGeneration(ContractModel):
    """Generation outcome whose successful variant points to a saved resource."""

    status: Literal["ok", "refused", "error"]
    id: UUID | None = None
    workspace_id: UUID | None = None
    created_at: datetime | None = None
    kit: BrandKit | None = None
    message: str | None = None

    @model_validator(mode="after")
    def validate_outcome(self) -> Self:
        saved_fields = (self.id, self.workspace_id, self.created_at, self.kit)
        if self.status == "ok" and (any(value is None for value in saved_fields) or self.message):
            raise ValueError("ok generations require a saved brand and no message")
        has_saved_fields = any(value is not None for value in saved_fields)
        if self.status != "ok" and (has_saved_fields or not self.message):
            raise ValueError("non-ok generations require only a message")
        return self
