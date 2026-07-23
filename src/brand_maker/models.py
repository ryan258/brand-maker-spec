"""Public request and response contracts for the service."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

HEX = r"^#(?:[0-9a-fA-F]{6})$"


class ContractModel(BaseModel):
    """Strict base model used at all public boundaries."""

    model_config = ConfigDict(extra="forbid")


class BrandRequest(ContractModel):
    """The only thing the caller provides: a brand name."""

    brand_name: str = Field(
        ...,
        min_length=1,
        max_length=80,
        description="The parody brand name to build a full kit for.",
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
        ..., min_length=1, description="The real brand being parodied."
    )
    tagline: str = Field(..., min_length=1, max_length=120)
    description: str = Field(..., min_length=1, max_length=500)
    brand_voice: str = Field(..., min_length=1, max_length=400)
    personality: list[str] = Field(
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
