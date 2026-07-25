"""Contracts for recoverable local workspace deletion."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from brand_maker.brand_system.models import ShortText
from brand_maker.models import ContractModel


class DeleteWorkspaceRequest(ContractModel):
    expected_revision: int = Field(..., ge=1)
    reason: ShortText | None = None


class RestoreWorkspaceRequest(ContractModel):
    expected_revision: int = Field(..., ge=1)


class TrashRecord(ContractModel):
    brand_id: UUID
    brand_name: str
    revision: int = Field(..., ge=1)
    deleted_at: datetime
    reason: str | None = None


class TrashPage(ContractModel):
    items: list[TrashRecord]
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_items: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)
