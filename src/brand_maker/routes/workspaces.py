"""Workspace lifecycle, backup/restore, and history routes."""

import tempfile
from functools import partial
from pathlib import Path
from typing import cast
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from brand_maker.brand_system.assets import AssetStore
from brand_maker.brand_system.audit import AuditPage, RevisionCommand
from brand_maker.brand_system.backup import (
    MAX_BACKUP_BYTES,
    InvalidWorkspaceBackup,
    create_workspace_backup,
    discard_installed_backup_assets,
    install_backup_assets,
    read_workspace_backup,
)
from brand_maker.brand_system.models import (
    CreateEvidenceRequest,
    CreateWorkspaceRequest,
    EditImpact,
    UpdateBriefRequest,
    UpdateSectionRequest,
    WorkingDraft,
    WorkspacePage,
)
from brand_maker.brand_system.readiness import ReadinessReport, ReadinessRequest, assess_readiness
from brand_maker.brand_system.recovery import (
    DeleteWorkspaceRequest,
    RestoreWorkspaceRequest,
    TrashPage,
    TrashRecord,
)
from brand_maker.brand_system.repository import (
    NothingToRedo,
    NothingToUndo,
    SQLiteBrandSystemRepository,
    StaleDraftRevision,
    WorkspaceAlreadyTrashed,
    WorkspaceNotTrashed,
)
from brand_maker.brand_system.service import (
    BrandSystemService,
    InvalidSectionEdit,
    LockedSection,
    SectionNotFound,
    SourceBrandNotFound,
    WorkspaceNotFound,
)
from brand_maker.config import Settings
from brand_maker.routes.request_streams import bounded_request_file

router = APIRouter()


@router.post(
    "/api/brand-systems",
    response_model=WorkingDraft,
    status_code=201,
    tags=["living brand systems"],
)
async def create_brand_system(payload: CreateWorkspaceRequest, request: Request) -> WorkingDraft:
    service = cast(BrandSystemService, request.app.state.brand_system_service)
    try:
        return await run_in_threadpool(service.create, payload)
    except SourceBrandNotFound:
        raise HTTPException(status_code=404, detail="Source brand not found.") from None
    except WorkspaceAlreadyTrashed:
        raise HTTPException(
            status_code=409, detail="The source workspace is in recoverable trash."
        ) from None


@router.get(
    "/api/brand-systems",
    response_model=WorkspacePage,
    tags=["living brand systems"],
)
async def list_brand_systems(
    request: Request,
    page: int = Query(1, ge=1, le=1_000_000),
    page_size: int = Query(12, alias="pageSize", ge=1, le=100),
) -> WorkspacePage:
    store = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    items, total = await run_in_threadpool(partial(store.list, page=page, page_size=page_size))
    return WorkspacePage(
        items=items,
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get(
    "/api/brand-system-trash",
    response_model=TrashPage,
    tags=["living brand systems"],
)
async def list_brand_system_trash(
    request: Request,
    page: int = Query(1, ge=1, le=1_000_000),
    page_size: int = Query(12, alias="pageSize", ge=1, le=100),
) -> TrashPage:
    store = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    items, total = await run_in_threadpool(
        partial(store.list_trash, page=page, page_size=page_size)
    )
    return TrashPage(
        items=items,
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post(
    "/api/brand-system-trash/{brand_id}/restore",
    response_model=WorkingDraft,
    tags=["living brand systems"],
)
async def restore_trashed_brand_system(
    brand_id: UUID, payload: RestoreWorkspaceRequest, request: Request
) -> WorkingDraft:
    store = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    try:
        return await run_in_threadpool(
            partial(
                store.restore_from_trash,
                brand_id,
                expected_revision=payload.expected_revision,
            )
        )
    except StaleDraftRevision:
        raise HTTPException(status_code=409, detail="Draft revision conflict.") from None
    except WorkspaceNotTrashed:
        raise HTTPException(status_code=404, detail="Workspace is not in trash.") from None


@router.get(
    "/api/brand-systems/{brand_id}",
    response_model=WorkingDraft,
    tags=["living brand systems"],
)
async def get_brand_system(brand_id: UUID, request: Request) -> WorkingDraft:
    store = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    draft = await run_in_threadpool(store.get, brand_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Brand system not found.")
    return draft


@router.patch(
    "/api/brand-systems/{brand_id}/brief",
    response_model=WorkingDraft,
    tags=["living brand systems"],
)
async def replace_brand_brief(
    brand_id: UUID, payload: UpdateBriefRequest, request: Request
) -> WorkingDraft:
    service = cast(BrandSystemService, request.app.state.brand_system_service)
    try:
        return await run_in_threadpool(service.replace_brief, brand_id, payload)
    except StaleDraftRevision:
        raise HTTPException(status_code=409, detail="Draft revision conflict.") from None
    except WorkspaceNotFound:
        raise HTTPException(status_code=404, detail="Brand system not found.") from None


@router.post(
    "/api/brand-systems/{brand_id}/evidence",
    response_model=WorkingDraft,
    tags=["living brand systems"],
)
async def add_brand_evidence(
    brand_id: UUID, payload: CreateEvidenceRequest, request: Request
) -> WorkingDraft:
    service = cast(BrandSystemService, request.app.state.brand_system_service)
    try:
        return await run_in_threadpool(service.add_evidence, brand_id, payload)
    except StaleDraftRevision:
        raise HTTPException(status_code=409, detail="Draft revision conflict.") from None
    except WorkspaceNotFound:
        raise HTTPException(status_code=404, detail="Brand system not found.") from None


@router.get(
    "/api/brand-systems/{brand_id}/backup",
    tags=["living brand exports"],
)
async def backup_brand_system(brand_id: UUID, request: Request) -> Response:
    store = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    assets = cast(AssetStore, request.app.state.asset_store)
    draft = await run_in_threadpool(store.get, brand_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Brand system not found.")
    try:
        with tempfile.NamedTemporaryFile(suffix=".zip") as temporary:
            await run_in_threadpool(create_workspace_backup, draft, assets, Path(temporary.name))
            body = Path(temporary.name).read_bytes()
    except InvalidWorkspaceBackup:
        raise HTTPException(
            status_code=409, detail="Workspace assets failed backup validation."
        ) from None
    filename = quote(f"{draft.brand_name}-workspace-backup.zip")
    return Response(
        body,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.post(
    "/api/brand-system-backups",
    response_model=WorkingDraft,
    tags=["living brand exports"],
)
async def restore_brand_system_backup(
    request: Request,
    expected_revision: int | None = Query(None, alias="expectedRevision", ge=1),
) -> WorkingDraft:
    async with bounded_request_file(
        request,
        max_bytes=MAX_BACKUP_BYTES,
        suffix=".zip",
        limit_detail="Backup exceeds the safety limit.",
    ) as temporary:
        try:
            snapshot, asset_payloads = await run_in_threadpool(read_workspace_backup, temporary)
        except InvalidWorkspaceBackup:
            raise HTTPException(status_code=422, detail="Workspace backup is invalid.") from None

    store = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    current = await run_in_threadpool(store.get_including_trash, snapshot.brand_id)
    if (current is None and expected_revision is not None) or (
        current is not None and current.revision != expected_revision
    ):
        raise HTTPException(status_code=409, detail="Draft revision conflict.")
    settings_for_restore = cast(Settings, request.app.state.settings)
    created_assets = await run_in_threadpool(
        install_backup_assets,
        settings_for_restore.database_path.parent / "assets",
        asset_payloads,
    )
    try:
        return await run_in_threadpool(
            partial(
                store.restore_backup,
                snapshot,
                expected_revision=expected_revision,
            )
        )
    except StaleDraftRevision:
        await run_in_threadpool(discard_installed_backup_assets, created_assets)
        raise HTTPException(status_code=409, detail="Draft revision conflict.") from None
    except Exception:
        await run_in_threadpool(discard_installed_backup_assets, created_assets)
        raise


@router.delete(
    "/api/brand-systems/{brand_id}",
    response_model=TrashRecord,
    tags=["living brand systems"],
)
async def trash_brand_system(
    brand_id: UUID, payload: DeleteWorkspaceRequest, request: Request
) -> TrashRecord:
    store = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    if await run_in_threadpool(store.get_including_trash, brand_id) is None:
        raise HTTPException(status_code=404, detail="Brand system not found.")
    try:
        return await run_in_threadpool(
            partial(
                store.soft_delete,
                brand_id,
                expected_revision=payload.expected_revision,
                reason=payload.reason,
            )
        )
    except StaleDraftRevision:
        raise HTTPException(status_code=409, detail="Draft revision conflict.") from None
    except WorkspaceAlreadyTrashed:
        raise HTTPException(status_code=409, detail="Workspace is already in trash.") from None


@router.get(
    "/api/brand-systems/{brand_id}/audit",
    response_model=AuditPage,
    tags=["living brand systems"],
)
async def list_brand_system_audit(
    brand_id: UUID,
    request: Request,
    page: int = Query(1, ge=1, le=1_000_000),
    page_size: int = Query(25, alias="pageSize", ge=1, le=100),
) -> AuditPage:
    store = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    if await run_in_threadpool(store.get, brand_id) is None:
        raise HTTPException(status_code=404, detail="Brand system not found.")
    items, total = await run_in_threadpool(
        partial(store.list_audit, brand_id, page=page, page_size=page_size)
    )
    return AuditPage(
        items=items,
        page=page,
        page_size=page_size,
        total_items=total,
        total_pages=(total + page_size - 1) // page_size,
    )


async def _move_brand_system_history(
    brand_id: UUID,
    payload: RevisionCommand,
    request: Request,
    *,
    redo: bool,
) -> WorkingDraft:
    store = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    operation = store.redo if redo else store.undo
    try:
        return await run_in_threadpool(
            partial(operation, brand_id, expected_revision=payload.expected_revision)
        )
    except StaleDraftRevision:
        if await run_in_threadpool(store.get, brand_id) is None:
            raise HTTPException(status_code=404, detail="Brand system not found.") from None
        raise HTTPException(status_code=409, detail="Draft revision conflict.") from None
    except (NothingToUndo, NothingToRedo) as exc:
        raise HTTPException(status_code=409, detail=str(exc).capitalize() + ".") from None


@router.post(
    "/api/brand-systems/{brand_id}/undo",
    response_model=WorkingDraft,
    tags=["living brand systems"],
)
async def undo_brand_system(
    brand_id: UUID, payload: RevisionCommand, request: Request
) -> WorkingDraft:
    return await _move_brand_system_history(brand_id, payload, request, redo=False)


@router.post(
    "/api/brand-systems/{brand_id}/redo",
    response_model=WorkingDraft,
    tags=["living brand systems"],
)
async def redo_brand_system(
    brand_id: UUID, payload: RevisionCommand, request: Request
) -> WorkingDraft:
    return await _move_brand_system_history(brand_id, payload, request, redo=True)


@router.post(
    "/api/brand-systems/{brand_id}/readiness",
    response_model=ReadinessReport,
    tags=["living brand systems"],
)
async def assess_brand_system_readiness(
    brand_id: UUID, payload: ReadinessRequest, request: Request
) -> ReadinessReport:
    store = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    draft = await run_in_threadpool(store.get, brand_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Brand system not found.")
    if draft.revision != payload.expected_revision:
        raise HTTPException(status_code=409, detail="Draft revision conflict.")
    return assess_readiness(draft, payload.target)


@router.patch(
    "/api/brand-systems/{brand_id}/sections/{section_id}",
    response_model=WorkingDraft,
    tags=["living brand systems"],
)
async def replace_brand_section(
    brand_id: UUID,
    section_id: str,
    payload: UpdateSectionRequest,
    request: Request,
) -> WorkingDraft:
    service = cast(BrandSystemService, request.app.state.brand_system_service)
    try:
        return await run_in_threadpool(
            partial(
                service.replace_section,
                brand_id,
                section_id,
                payload.section,
                payload.expected_revision,
                confirm_locked=payload.confirm_locked,
                change_note=payload.change_note,
            )
        )
    except StaleDraftRevision:
        raise HTTPException(status_code=409, detail="Draft revision conflict.") from None
    except WorkspaceNotFound:
        raise HTTPException(status_code=404, detail="Brand system not found.") from None
    except SectionNotFound:
        raise HTTPException(status_code=404, detail="Section not found.") from None
    except LockedSection:
        raise HTTPException(
            status_code=409, detail="Section is locked; confirmation required."
        ) from None
    except InvalidSectionEdit:
        raise HTTPException(
            status_code=422, detail="Section update violates canonical validation."
        ) from None


@router.post(
    "/api/brand-systems/{brand_id}/sections/{section_id}/impact",
    response_model=EditImpact,
    tags=["living brand systems"],
)
async def preview_brand_section_impact(
    brand_id: UUID,
    section_id: str,
    payload: UpdateSectionRequest,
    request: Request,
) -> EditImpact:
    service = cast(BrandSystemService, request.app.state.brand_system_service)
    try:
        return await run_in_threadpool(
            partial(
                service.preview_section,
                brand_id,
                section_id,
                payload.section,
                payload.expected_revision,
            )
        )
    except StaleDraftRevision:
        raise HTTPException(status_code=409, detail="Draft revision conflict.") from None
    except WorkspaceNotFound:
        raise HTTPException(status_code=404, detail="Brand system not found.") from None
    except SectionNotFound:
        raise HTTPException(status_code=404, detail="Section not found.") from None
