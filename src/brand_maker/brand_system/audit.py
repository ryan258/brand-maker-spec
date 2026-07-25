"""Public audit-feed contracts for reversible local workspace history."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from brand_maker.models import ContractModel


class AuditEvent(ContractModel):
    """A bounded, snapshot-free description of one durable workspace mutation."""

    event_id: UUID
    brand_id: UUID
    action: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_.-]*$")
    from_revision: int | None = Field(default=None, ge=1)
    to_revision: int = Field(..., ge=1)
    changed_fields: list[str] = Field(default_factory=list, max_length=100)
    reason: str | None = Field(default=None, min_length=1, max_length=500)
    target_event_id: UUID | None = None
    created_at: datetime
    undone_at: datetime | None = None
    redo_discarded: bool = False


class AuditPage(ContractModel):
    items: list[AuditEvent]
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_items: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)


class RevisionCommand(ContractModel):
    """Optimistic command for changing the draft history cursor."""

    expected_revision: int = Field(..., ge=1)
