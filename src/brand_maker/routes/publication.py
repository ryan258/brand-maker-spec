"""Publication, versioning, approvals, and amendment routes."""

import json
import tempfile
from functools import partial
from pathlib import Path
from typing import Literal, cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from starlette.concurrency import run_in_threadpool

from brand_maker.brand_system.amendments import (
    AmendmentRevisionNotFound,
    AmendmentTargetNotClerical,
    SQLiteAmendmentRepository,
    StaleAmendmentValue,
)
from brand_maker.brand_system.assets import AssetChanged, AssetMissing, AssetStore
from brand_maker.brand_system.models import (
    AmendmentRequest,
    ApprovalRecord,
    ApprovalRequest,
    PublicationAmendment,
    PublicationRequest,
    PublishedVersion,
    RenderedPublishedVersion,
)
from brand_maker.brand_system.publication import (
    DraftNotApproved,
    DraftNotReady,
    PublicationDraftNotFound,
    PublishedVersionExists,
    SQLitePublicationRepository,
)
from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
from brand_maker.config import Settings
from brand_maker.http import BROWSER_HEADERS
from brand_maker.publishing.archive import (
    MAX_ARCHIVE_BYTES,
    ArchiveContents,
    InvalidArchive,
    create_archive,
    import_archive,
)
from brand_maker.publishing.developer_exports import export_developer_package
from brand_maker.publishing.markdown import export_markdown
from brand_maker.publishing.pdf import render_pdf
from brand_maker.publishing.projections import Audience, project
from brand_maker.publishing.web import render_projection
from brand_maker.routes.request_streams import bounded_request_file

router = APIRouter()


@router.post(
    "/api/brand-systems/{brand_id}/approvals",
    response_model=ApprovalRecord,
    status_code=201,
    tags=["living brand systems"],
)
async def approve_brand_system(
    brand_id: UUID, payload: ApprovalRequest, request: Request
) -> ApprovalRecord:
    store = cast(SQLitePublicationRepository, request.app.state.publication_repository)
    try:
        return await run_in_threadpool(
            store.approve, brand_id, payload.expected_revision, payload.rationale
        )
    except PublicationDraftNotFound:
        raise HTTPException(status_code=404, detail="Brand system not found.") from None
    except DraftNotReady:
        raise HTTPException(
            status_code=409, detail="Current draft is not ready for approval."
        ) from None
    except DraftNotApproved:
        raise HTTPException(status_code=409, detail="Draft revision conflict.") from None


@router.post(
    "/api/brand-systems/{brand_id}/versions",
    response_model=PublishedVersion,
    status_code=201,
    tags=["living brand systems"],
)
async def publish_brand_system(
    brand_id: UUID, payload: PublicationRequest, request: Request
) -> PublishedVersion:
    store = cast(SQLitePublicationRepository, request.app.state.publication_repository)
    workspaces = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    assets = cast(AssetStore, request.app.state.asset_store)
    try:
        draft = await run_in_threadpool(workspaces.get, brand_id)
        if draft is None:
            raise PublicationDraftNotFound
        snapshot = await run_in_threadpool(assets.prepare_publication, draft)
        return await run_in_threadpool(store.publish, brand_id, payload, snapshot=snapshot)
    except PublicationDraftNotFound:
        raise HTTPException(status_code=404, detail="Brand system not found.") from None
    except DraftNotReady:
        raise HTTPException(
            status_code=409, detail="Current draft is not ready for publication."
        ) from None
    except DraftNotApproved:
        raise HTTPException(
            status_code=409, detail="Current draft revision is not approved."
        ) from None
    except PublishedVersionExists:
        raise HTTPException(status_code=409, detail="Published version already exists.") from None
    except (AssetMissing, AssetChanged, ValueError):
        raise HTTPException(
            status_code=409, detail="Required publication asset is missing or changed."
        ) from None


@router.get(
    "/api/brand-systems/{brand_id}/versions/{version}",
    response_model=PublishedVersion,
    tags=["living brand systems"],
)
async def get_published_brand_system(
    brand_id: UUID, version: str, request: Request
) -> PublishedVersion:
    store = cast(SQLitePublicationRepository, request.app.state.publication_repository)
    published = await run_in_threadpool(store.get, brand_id, version)
    if published is None:
        raise HTTPException(status_code=404, detail="Published version not found.")
    return published


@router.post(
    "/api/brand-systems/{brand_id}/versions/{version}/amendments",
    response_model=PublicationAmendment,
    status_code=201,
    tags=["living brand systems"],
)
async def amend_published_brand_system(
    brand_id: UUID, version: str, payload: AmendmentRequest, request: Request
) -> PublicationAmendment:
    store = cast(SQLiteAmendmentRepository, request.app.state.amendment_repository)
    try:
        return await run_in_threadpool(store.append, brand_id, version, payload)
    except AmendmentRevisionNotFound:
        raise HTTPException(status_code=404, detail="Published version not found.") from None
    except AmendmentTargetNotClerical:
        raise HTTPException(status_code=422, detail="Amendment target is not clerical.") from None
    except StaleAmendmentValue:
        raise HTTPException(status_code=409, detail="Amendment before-value is stale.") from None


@router.get(
    "/api/brand-systems/{brand_id}/versions/{version}/revisions/{revision}",
    response_model=RenderedPublishedVersion,
    tags=["living brand systems"],
)
async def get_published_revision(
    brand_id: UUID, version: str, revision: int, request: Request
) -> RenderedPublishedVersion:
    store = cast(SQLiteAmendmentRepository, request.app.state.amendment_repository)
    try:
        return await run_in_threadpool(store.reconstruct, brand_id, version, revision)
    except AmendmentRevisionNotFound:
        raise HTTPException(status_code=404, detail="Amendment revision not found.") from None


async def _rendered_publication(
    brand_id: UUID, version: str, revision: int, request: Request
) -> tuple[PublishedVersion, RenderedPublishedVersion]:
    publications = cast(SQLitePublicationRepository, request.app.state.publication_repository)
    amendments = cast(SQLiteAmendmentRepository, request.app.state.amendment_repository)
    published = await run_in_threadpool(publications.get, brand_id, version)
    if published is None:
        raise HTTPException(status_code=404, detail="Published version not found.")
    try:
        rendered = await run_in_threadpool(amendments.reconstruct, brand_id, version, revision)
    except AmendmentRevisionNotFound:
        raise HTTPException(status_code=404, detail="Amendment revision not found.") from None
    return published, rendered


@router.get(
    "/brand-systems/{brand_id}/versions/{version}/views/{audience}",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def published_audience_view(
    brand_id: UUID,
    version: str,
    audience: Audience,
    request: Request,
    amendment_revision: int = Query(0, alias="amendmentRevision", ge=0),
) -> HTMLResponse:
    published, rendered = await _rendered_publication(
        brand_id, version, amendment_revision, request
    )
    view = project(rendered, content_hash=published.content_hash, audience=audience)
    return HTMLResponse(render_projection(view), headers=BROWSER_HEADERS)


@router.get(
    "/api/brand-systems/{brand_id}/versions/{version}/exports/{format_name}",
    tags=["living brand exports"],
)
async def export_published_brand_system(
    brand_id: UUID,
    version: str,
    format_name: Literal["markdown", "developer", "pdf", "archive"],
    request: Request,
    amendment_revision: int = Query(0, alias="amendmentRevision", ge=0),
    audience: Audience = "agency",
) -> Response:
    published, rendered = await _rendered_publication(
        brand_id, version, amendment_revision, request
    )
    if format_name == "markdown":
        body = export_markdown(
            rendered.rendered_snapshot,
            version=version,
            amendment_revision=amendment_revision,
        )
        return Response(body, media_type="text/markdown")
    if format_name == "developer":
        return Response(
            json.dumps(export_developer_package(published), sort_keys=True),
            media_type="application/json",
        )
    if format_name == "pdf":
        view = project(rendered, content_hash=published.content_hash, audience=audience)
        return Response(render_pdf(view), media_type="application/pdf")
    with tempfile.NamedTemporaryFile(suffix=".zip") as temporary:
        create_archive(
            published,
            Path(request.app.state.settings.database_path).parent / "assets",
            Path(temporary.name),
            rendered=rendered,
        )
        archive_body = Path(temporary.name).read_bytes()
    return Response(archive_body, media_type="application/zip")


@router.post(
    "/api/brand-system-archives",
    response_model=ArchiveContents,
    status_code=201,
    tags=["living brand publication"],
)
async def import_brand_system_archive(
    request: Request,
) -> ArchiveContents:
    settings = cast(Settings, request.app.state.settings)
    database_path = settings.database_path
    asset_root = database_path.parent / "assets"

    async with bounded_request_file(
        request,
        max_bytes=MAX_ARCHIVE_BYTES,
        suffix=".zip",
        limit_detail="Archive exceeds the safety limit.",
        empty_detail="Archive body is empty.",
    ) as temp_path:
        try:
            return await run_in_threadpool(
                partial(
                    import_archive,
                    temp_path,
                    asset_root=asset_root,
                    database_path=database_path,
                )
            )
        except InvalidArchive as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
