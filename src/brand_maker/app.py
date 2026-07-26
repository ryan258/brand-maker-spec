"""FastAPI application factory and HTTP routes."""

import asyncio
import io
import json
import logging
import mimetypes
import re
import tempfile
import zipfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from typing import Literal, cast
from urllib.parse import quote
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from brand_maker.brand_bible import render_brand_bible
from brand_maker.brand_bible_styles import BRAND_BIBLE_CSS
from brand_maker.brand_system.amendments import (
    AmendmentRevisionNotFound,
    AmendmentTargetNotClerical,
    SQLiteAmendmentRepository,
    StaleAmendmentValue,
)
from brand_maker.brand_system.assets import (
    AssetChanged,
    AssetMissing,
    AssetStore,
    generate_font_face_css,
    validate_font_file_header,
)
from brand_maker.brand_system.audit import AuditPage, RevisionCommand
from brand_maker.brand_system.backup import (
    MAX_BACKUP_BYTES,
    InvalidWorkspaceBackup,
    create_workspace_backup,
    install_backup_assets,
    read_workspace_backup,
)
from brand_maker.brand_system.models import (
    AmendmentRequest,
    ApprovalRecord,
    ApprovalRequest,
    AssetRegistration,
    CreateAssetDerivativeRequest,
    CreateEvidenceRequest,
    CreateWorkspaceRequest,
    EditImpact,
    GenerateLogoRequest,
    GenerateLogoVariantsRequest,
    PublicationAmendment,
    PublicationRequest,
    PublishedVersion,
    RegisterAssetRequest,
    RenderedPublishedVersion,
    UpdateBriefRequest,
    UpdateSectionRequest,
    WorkingDraft,
    WorkspacePage,
)
from brand_maker.brand_system.publication import (
    DraftNotApproved,
    DraftNotReady,
    PublicationDraftNotFound,
    PublishedVersionExists,
    SQLitePublicationRepository,
)
from brand_maker.brand_system.readiness import (
    ReadinessReport,
    ReadinessRequest,
    assess_readiness,
)
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
from brand_maker.compliance.campaigns import (
    CampaignResult,
    CampaignService,
    CreateCampaignRequest,
)
from brand_maker.compliance.copy_checker import check_copy_against_brand_rules
from brand_maker.compliance.deterministic import (
    audit_token_collisions,
    audit_token_contrast_pairs,
    evaluate_artifact,
)
from brand_maker.compliance.exceptions import (
    ComplianceException,
    ExceptionLedger,
    ExceptionRequest,
    RenewExceptionRequest,
)
from brand_maker.compliance.judgment import (
    RegisteredEvidence,
    RegisterEvidenceRequest,
    SQLiteEvidenceRepository,
)
from brand_maker.compliance.models import (
    ArtifactEvaluation,
    ArtifactInput,
    ArtifactRevision,
    EvaluateArtifactRequest,
)
from brand_maker.compliance.repository import SQLiteComplianceRepository
from brand_maker.compliance_ui import COMPLIANCE_SCRIPT
from brand_maker.compliance_web import compliance_page
from brand_maker.config import Settings
from brand_maker.generation.orchestrator import (
    Completer,
    GenerationOrchestrator,
    GenerationRunNotFound,
)
from brand_maker.generation.repository import (
    GenerateSectionVariantsRequest,
    GenerationRun,
    RegenerateFieldRequest,
    SQLiteGenerationRepository,
    StartGenerationRequest,
)
from brand_maker.image_gen import OpenRouterImageClient, logo_prompt, logo_variant_prompt
from brand_maker.library_styles import LIBRARY_CSS
from brand_maker.library_ui import LIBRARY_SCRIPT
from brand_maker.library_web import detail_page, library_page, not_found_page
from brand_maker.logo_derivatives import (
    RASTER_MEDIA_TYPES,
    LogoDerivative,
    check_logo_contrast_against_backgrounds,
    create_icon_set,
    vectorize_logo,
)
from brand_maker.models import (
    BrandRequest,
    BrandResponse,
    SavedBrand,
    SavedBrandGeneration,
    SavedBrandPage,
)
from brand_maker.openrouter import (
    ModelUnavailable,
    OpenRouterClient,
    ProviderError,
    ProviderRefusal,
)
from brand_maker.pipeline import BrandBuilder, BrandPipeline
from brand_maker.publishing.archive import (
    MAX_ARCHIVE_BYTES,
    MAX_ENTRIES,
    MAX_ENTRY_BYTES,
    ArchiveContents,
    InvalidArchive,
    create_archive,
    import_archive,
)
from brand_maker.publishing.developer_exports import (
    export_developer_package,
    export_draft_tokens,
)
from brand_maker.publishing.markdown import export_markdown
from brand_maker.publishing.pdf import render_html_pdf, render_pdf
from brand_maker.publishing.projections import Audience, project
from brand_maker.publishing.web import render_projection
from brand_maker.storage import SQLiteBrandRepository
from brand_maker.ui import UI_SCRIPT
from brand_maker.web import FAVICON, HOME_PAGE, add_home_navigation
from brand_maker.workshop_styles import WORKSHOP_CSS
from brand_maker.workshop_ui import WORKSHOP_SCRIPT
from brand_maker.workshop_web import workspace_detail, workspace_index

logger = logging.getLogger(__name__)

BROWSER_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self'; connect-src 'self'; base-uri 'none'; "
        "form-action 'self'; frame-ancestors 'none'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}


def _content_disposition(filename: str, prefix: str = "attachment") -> str:
    ascii_filename = re.sub(r"[^\x20-\x7E]", "_", filename).replace('"', "_").strip()
    if not ascii_filename:
        ascii_filename = "export"
    utf8_encoded = quote(filename)
    return f"{prefix}; filename=\"{ascii_filename}\"; filename*=UTF-8''{utf8_encoded}"


def _safe_zip_filename(name: str) -> str:
    base = Path(name).name
    cleaned = re.sub(r"[^a-zA-Z0-9_ .-]", "_", base).strip(". ")
    return cleaned or "file"


def _build_brand_kit_zip(draft: WorkingDraft, asset_store: AssetStore) -> bytes:
    if len(draft.assets) > MAX_ENTRIES:
        raise HTTPException(
            status_code=413,
            detail=f"Brand kit contains too many asset entries (max {MAX_ENTRIES}).",
        )

    total_declared = sum(asset.size_bytes for asset in draft.assets)
    if total_declared > MAX_ARCHIVE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Brand kit assets exceed maximum archive size limit of 250 MB.",
        )

    for asset in draft.assets:
        if asset.size_bytes > MAX_ENTRY_BYTES and asset.required:
            detail = f"Required asset '{asset.name}' exceeds maximum single file size of 25 MB."
            raise HTTPException(status_code=413, detail=detail)

    token_exports = export_draft_tokens(draft)
    html_content = render_brand_bible(draft, for_pdf=True)
    pdf_bytes = render_html_pdf(html_content)
    md_text = export_markdown(draft, version="draft", amendment_revision=0)

    safe_brand = _safe_zip_filename(draft.brand_name)
    buffer = io.BytesIO()
    total_bytes = 0
    seen_paths: set[str] = set()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:

        def _write_entry(path: str, data: bytes) -> None:
            nonlocal total_bytes
            total_bytes += len(data)
            if total_bytes > MAX_ARCHIVE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail="Brand kit assets exceed maximum archive size limit of 250 MB.",
                )
            seen_paths.add(path)
            zf.writestr(path, data)

        _write_entry("tokens.css", token_exports["tokens.css"].encode("utf-8"))
        _write_entry("tokens.json", token_exports["tokens.json"].encode("utf-8"))
        _write_entry(
            "tailwind.config.js",
            token_exports["tailwind.config.js"].encode("utf-8"),
        )
        _write_entry(f"{safe_brand}-bible.md", md_text.encode("utf-8"))
        _write_entry(f"{safe_brand}-bible.pdf", pdf_bytes)

        for asset in draft.assets:
            if asset.size_bytes > MAX_ENTRY_BYTES:
                continue

            try:
                asset_bytes = asset_store.read(asset)
                raw_safe = _safe_zip_filename(asset.name)
                stem = Path(raw_safe).stem
                ext = Path(raw_safe).suffix
                entry_name = f"assets/{raw_safe}"
                counter = 1
                while entry_name in seen_paths:
                    entry_name = f"assets/{stem}_{counter}{ext}"
                    counter += 1
                _write_entry(entry_name, asset_bytes)
            except (AssetMissing, AssetChanged, ValueError) as exc:
                if asset.required:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Required asset '{asset.name}' is missing or changed.",
                    ) from exc

    return buffer.getvalue()


async def _append_asset(
    workspaces: SQLiteBrandSystemRepository,
    draft: WorkingDraft,
    registration: AssetRegistration,
) -> WorkingDraft:
    """Append one registered asset to the draft and persist the next revision."""

    data = draft.model_dump(mode="json")
    data.update(
        {
            "assets": [
                *[item.model_dump(mode="json") for item in draft.assets],
                registration.model_dump(mode="json"),
            ],
            "revision": draft.revision + 1,
        }
    )
    updated = WorkingDraft.model_validate(data)
    return await run_in_threadpool(
        partial(workspaces.update, updated, expected_revision=draft.revision)
    )


async def _append_assets(
    workspaces: SQLiteBrandSystemRepository,
    draft: WorkingDraft,
    registrations: list[AssetRegistration],
) -> WorkingDraft:
    """Append a complete derivative set in one draft revision."""

    data = draft.model_dump(mode="json")
    data.update(
        {
            "assets": [
                *[item.model_dump(mode="json") for item in draft.assets],
                *[item.model_dump(mode="json") for item in registrations],
            ],
            "revision": draft.revision + 1,
        }
    )
    updated = WorkingDraft.model_validate(data)
    return await run_in_threadpool(
        partial(workspaces.update, updated, expected_revision=draft.revision)
    )


async def _register_derivatives(
    assets: AssetStore,
    source: AssetRegistration,
    derivatives: list[LogoDerivative],
) -> list[AssetRegistration]:
    registrations: list[AssetRegistration] = []
    for derivative in derivatives:
        with tempfile.NamedTemporaryFile(delete=False) as buffer:
            temporary = Path(buffer.name)
            buffer.write(derivative.content)
        try:
            registrations.append(
                await run_in_threadpool(
                    partial(
                        assets.import_managed,
                        asset_id=f"asset.derivative.{uuid4().hex}",
                        name=f"{source.name} — {derivative.name_suffix.replace('-', ' ')}",
                        source=temporary,
                        media_type=derivative.media_type,
                        required=False,
                    )
                )
            )
        finally:
            temporary.unlink(missing_ok=True)
    return registrations


async def _load_derivative_source(
    request: Request,
    brand_id: UUID,
    asset_id: str,
    expected_revision: int,
) -> tuple[SQLiteBrandSystemRepository, AssetStore, WorkingDraft, AssetRegistration, bytes]:
    workspaces = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    assets = cast(AssetStore, request.app.state.asset_store)
    draft = await run_in_threadpool(workspaces.get, brand_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Brand system not found.")
    if draft.revision != expected_revision:
        raise HTTPException(status_code=409, detail="Draft revision conflict.")
    source = next((item for item in draft.assets if item.id == asset_id), None)
    if source is None:
        raise HTTPException(status_code=404, detail="Asset not found.")
    if source.media_type not in RASTER_MEDIA_TYPES:
        raise HTTPException(status_code=422, detail="A raster logo asset is required.")
    try:
        content = await run_in_threadpool(assets.read, source)
    except (AssetMissing, AssetChanged, ValueError):
        raise HTTPException(status_code=422, detail="The source asset failed validation.") from None
    return workspaces, assets, draft, source, content


def create_app(
    *,
    settings: Settings | None = None,
    pipeline: BrandBuilder | None = None,
    repository: SQLiteBrandRepository | None = None,
    brand_system_repository: SQLiteBrandSystemRepository | None = None,
    generation_completer: Completer | None = None,
    image_client: OpenRouterImageClient | None = None,
) -> FastAPI:
    """Create an application whose resources are owned by its lifespan."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            resolved_settings = settings or Settings.model_validate({})
        except ValidationError:
            logger.critical("OPENROUTER_API_KEY is required; server startup aborted.")
            raise
        app.state.settings = resolved_settings
        app.state.repository = repository or SQLiteBrandRepository(resolved_settings.database_path)
        app.state.brand_system_repository = brand_system_repository or SQLiteBrandSystemRepository(
            resolved_settings.database_path
        )
        app.state.brand_system_service = BrandSystemService(
            workspaces=app.state.brand_system_repository,
            legacy=app.state.repository,
        )
        app.state.publication_repository = SQLitePublicationRepository(
            resolved_settings.database_path
        )
        app.state.amendment_repository = SQLiteAmendmentRepository(resolved_settings.database_path)
        app.state.asset_store = AssetStore(resolved_settings.database_path.parent / "assets")
        app.state.image_client = image_client
        app.state.compliance_repository = SQLiteComplianceRepository(
            resolved_settings.database_path
        )
        app.state.campaign_service = CampaignService(app.state.compliance_repository)
        app.state.exception_ledger = ExceptionLedger(path=resolved_settings.database_path)
        app.state.evidence_repository = SQLiteEvidenceRepository(resolved_settings.database_path)
        app.state.generation_repository = SQLiteGenerationRepository(
            resolved_settings.database_path
        )
        app.state.generation_orchestrator = GenerationOrchestrator(
            workspaces=app.state.brand_system_repository,
            runs=app.state.generation_repository,
        )
        app.state.generation_completer = generation_completer

        if pipeline is not None:
            app.state.pipeline = pipeline
            yield
            return

        timeout = httpx.Timeout(resolved_settings.request_timeout_seconds)
        limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
        async with httpx.AsyncClient(timeout=timeout, limits=limits) as http:
            api_key = resolved_settings.openrouter_api_key.get_secret_value()
            generator = OpenRouterClient(http=http, api_key=api_key)
            app.state.image_client = image_client or OpenRouterImageClient(
                http=http, api_key=api_key
            )
            app.state.generation_completer = generator
            app.state.pipeline = BrandPipeline(
                generator=generator,
                primary_model=resolved_settings.primary_model,
                fallback_model=resolved_settings.fallback_model,
            )
            yield

    app = FastAPI(
        title="Brand System Maker",
        version="0.1.0",
        description=(
            "Create, publish, export, and check local living brand systems; "
            "the original quick-kit API remains compatible."
        ),
        docs_url=None,
        redoc_url=None,
        swagger_ui_oauth2_redirect_url="/docs/oauth2-redirect",
        lifespan=lifespan,
    )
    openapi_url = app.openapi_url or "/openapi.json"

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def root() -> HTMLResponse:
        return HTMLResponse(HOME_PAGE, headers=BROWSER_HEADERS)

    @app.get("/assets/app.js", include_in_schema=False)
    async def ui_script() -> Response:
        return Response(
            UI_SCRIPT,
            media_type="text/javascript",
            headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"},
        )

    @app.get("/assets/library.js", include_in_schema=False)
    async def library_script() -> Response:
        return Response(
            LIBRARY_SCRIPT,
            media_type="text/javascript",
            headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"},
        )

    @app.get("/assets/library.css", include_in_schema=False)
    async def library_styles() -> Response:
        return Response(
            LIBRARY_CSS,
            media_type="text/css",
            headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"},
        )

    @app.get("/assets/workshop.js", include_in_schema=False)
    async def workshop_script() -> Response:
        return Response(WORKSHOP_SCRIPT, media_type="text/javascript")

    @app.get("/assets/workshop.css", include_in_schema=False)
    async def workshop_styles() -> Response:
        return Response(WORKSHOP_CSS, media_type="text/css")

    @app.get("/assets/brand-bible.css", include_in_schema=False)
    async def brand_bible_styles() -> Response:
        return Response(
            BRAND_BIBLE_CSS,
            media_type="text/css",
            headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"},
        )

    @app.get("/assets/compliance.js", include_in_schema=False)
    async def compliance_script() -> Response:
        return Response(COMPLIANCE_SCRIPT, media_type="text/javascript")

    @app.get("/brand-systems", response_class=HTMLResponse, include_in_schema=False)
    async def brand_system_index() -> HTMLResponse:
        return HTMLResponse(workspace_index(), headers=BROWSER_HEADERS)

    @app.get("/compliance", response_class=HTMLResponse, include_in_schema=False)
    async def compliance_workflow() -> HTMLResponse:
        return HTMLResponse(compliance_page(), headers=BROWSER_HEADERS)

    @app.get("/brand-systems/{brand_id}", response_class=HTMLResponse, include_in_schema=False)
    async def brand_system_workshop(brand_id: UUID, request: Request) -> HTMLResponse:
        store = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
        if await run_in_threadpool(store.get, brand_id) is None:
            raise HTTPException(status_code=404, detail="Brand system not found.")
        return HTMLResponse(workspace_detail(brand_id), headers=BROWSER_HEADERS)

    @app.get(
        "/brand-systems/{brand_id}/bible",
        response_class=HTMLResponse,
        include_in_schema=False,
    )
    async def brand_system_bible(brand_id: UUID, request: Request) -> HTMLResponse:
        store = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
        draft = await run_in_threadpool(store.get, brand_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Brand system not found.")
        return HTMLResponse(render_brand_bible(draft), headers=BROWSER_HEADERS)

    @app.get("/brands", response_class=HTMLResponse, include_in_schema=False)
    async def brand_library_page() -> HTMLResponse:
        return HTMLResponse(library_page(), headers=BROWSER_HEADERS)

    @app.get("/brands/{brand_id}", response_class=HTMLResponse, include_in_schema=False)
    async def saved_brand_page(brand_id: UUID, request: Request) -> HTMLResponse:
        store = cast(SQLiteBrandRepository, request.app.state.repository)
        saved = await run_in_threadpool(store.get, brand_id)
        if saved is None:
            return HTMLResponse(not_found_page(), status_code=404, headers=BROWSER_HEADERS)
        return HTMLResponse(detail_page(brand_id), headers=BROWSER_HEADERS)

    # FastAPI's supported custom-docs hooks let us retain its generated viewers while
    # adding project navigation: https://fastapi.tiangolo.com/how-to/custom-docs-ui-assets/
    @app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
    async def swagger_docs() -> HTMLResponse:
        page = get_swagger_ui_html(
            openapi_url=openapi_url,
            title=f"{app.title} — API console",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        )
        return add_home_navigation(page)

    @app.get("/docs/oauth2-redirect", include_in_schema=False)
    async def swagger_oauth2_redirect() -> HTMLResponse:
        return get_swagger_ui_oauth2_redirect_html()

    @app.get("/redoc", response_class=HTMLResponse, include_in_schema=False)
    async def redoc_docs() -> HTMLResponse:
        page = get_redoc_html(openapi_url=openapi_url, title=f"{app.title} — Reference")
        return add_home_navigation(page)

    @app.get("/favicon.svg", include_in_schema=False)
    async def favicon() -> Response:
        return Response(FAVICON, media_type="image/svg+xml")

    @app.get("/health", tags=["operations"])
    async def health() -> dict[str, str]:
        return {"status": "up"}

    @app.post("/brand", response_model=BrandResponse, tags=["brands"])
    async def build_brand(payload: BrandRequest, request: Request) -> BrandResponse:
        builder = cast(BrandBuilder, request.app.state.pipeline)
        return await builder.build(payload.brand_name)

    @app.post("/api/brands", response_model=SavedBrandGeneration, tags=["brand library"])
    async def create_saved_brand(payload: BrandRequest, request: Request) -> SavedBrandGeneration:
        builder = cast(BrandBuilder, request.app.state.pipeline)
        result = await builder.build(payload.brand_name)
        if result.status != "ok":
            return SavedBrandGeneration(status=result.status, message=result.message)

        if result.kit is None:  # Defensive narrowing; BrandResponse already enforces this.
            raise RuntimeError("successful generation did not contain a kit")
        store = cast(SQLiteBrandRepository, request.app.state.repository)
        saved = await run_in_threadpool(store.save, result.kit)
        brand_systems = cast(BrandSystemService, request.app.state.brand_system_service)
        workspace = await run_in_threadpool(
            brand_systems.create,
            CreateWorkspaceRequest(
                source_brand_id=saved.id,
                owner_name="Local owner",
                entry_path="quick_start",
                assistance_mode="copilot",
                research_mode="controlled",
            ),
        )
        return SavedBrandGeneration(
            status="ok",
            id=saved.id,
            workspace_id=workspace.brand_id,
            created_at=saved.created_at,
            kit=saved.kit,
        )

    @app.get("/api/brands", response_model=SavedBrandPage, tags=["brand library"])
    async def list_saved_brands(
        request: Request,
        page: int = Query(1, ge=1, le=1_000_000),
        page_size: int = Query(12, alias="pageSize", ge=1, le=100),
    ) -> SavedBrandPage:
        store = cast(SQLiteBrandRepository, request.app.state.repository)
        items, total = await run_in_threadpool(partial(store.list, page=page, page_size=page_size))
        total_pages = (total + page_size - 1) // page_size
        return SavedBrandPage(
            items=items,
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
        )

    @app.get("/api/brands/{brand_id}", response_model=SavedBrand, tags=["brand library"])
    async def get_saved_brand(brand_id: UUID, request: Request) -> SavedBrand:
        store = cast(SQLiteBrandRepository, request.app.state.repository)
        saved = await run_in_threadpool(store.get, brand_id)
        if saved is None:
            raise HTTPException(status_code=404, detail="Brand not found.")
        return saved

    @app.post(
        "/api/compliance/artifacts",
        response_model=ArtifactRevision,
        status_code=201,
        tags=["brand compliance"],
    )
    async def register_compliance_artifact(
        payload: ArtifactInput, request: Request
    ) -> ArtifactRevision:
        store = cast(SQLiteComplianceRepository, request.app.state.compliance_repository)
        return await run_in_threadpool(store.register_artifact, payload)

    @app.post(
        "/api/compliance/artifact-evaluations",
        response_model=ArtifactEvaluation,
        status_code=201,
        tags=["brand compliance"],
    )
    async def create_artifact_evaluation(
        payload: EvaluateArtifactRequest, request: Request
    ) -> ArtifactEvaluation:
        store = cast(SQLiteComplianceRepository, request.app.state.compliance_repository)
        await run_in_threadpool(store.register_artifact, payload.artifact)
        evaluation = await run_in_threadpool(
            partial(
                evaluate_artifact,
                payload.artifact,
                rules=payload.rules,
                brand_version=payload.brand_version,
                amendment_revision=payload.amendment_revision,
                tool_version=app.version,
            )
        )
        return await run_in_threadpool(store.save_evaluation, evaluation)

    @app.post(
        "/api/compliance/exceptions",
        response_model=ComplianceException,
        status_code=201,
        tags=["brand compliance"],
    )
    async def create_compliance_exception(
        payload: ExceptionRequest, request: Request
    ) -> ComplianceException:
        ledger = cast(ExceptionLedger, request.app.state.exception_ledger)
        try:
            return await run_in_threadpool(partial(ledger.approve, payload, owner_id="local-owner"))
        except ValueError:
            raise HTTPException(
                status_code=422, detail="Exception expiration must be in the future."
            ) from None

    @app.get(
        "/api/compliance/exceptions/{exception_id}",
        response_model=ComplianceException,
        tags=["brand compliance"],
    )
    async def get_compliance_exception(exception_id: UUID, request: Request) -> ComplianceException:
        ledger = cast(ExceptionLedger, request.app.state.exception_ledger)
        record = await run_in_threadpool(ledger.get, exception_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Compliance exception not found.")
        return record

    @app.post(
        "/api/compliance/exceptions/{exception_id}/renewals",
        response_model=ComplianceException,
        tags=["brand compliance"],
    )
    async def renew_compliance_exception(
        exception_id: UUID, payload: RenewExceptionRequest, request: Request
    ) -> ComplianceException:
        ledger = cast(ExceptionLedger, request.app.state.exception_ledger)
        try:
            return await run_in_threadpool(
                partial(ledger.renew, exception_id, expires_at=payload.expires_at)
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="Compliance exception not found.") from None
        except ValueError:
            raise HTTPException(
                status_code=422, detail="Renewal must extend the expiration."
            ) from None

    @app.post(
        "/api/compliance/evidence",
        response_model=RegisteredEvidence,
        status_code=201,
        tags=["brand compliance"],
    )
    async def register_compliance_evidence(
        payload: RegisterEvidenceRequest, request: Request
    ) -> RegisteredEvidence:
        evidence = cast(SQLiteEvidenceRepository, request.app.state.evidence_repository)
        return await run_in_threadpool(evidence.register, payload.artifact_id, payload.evidence)

    @app.post(
        "/api/compliance/campaigns",
        response_model=CampaignResult,
        status_code=201,
        tags=["brand compliance"],
    )
    async def create_compliance_campaign(
        payload: CreateCampaignRequest, request: Request
    ) -> CampaignResult:
        campaigns = cast(CampaignService, request.app.state.campaign_service)
        return await run_in_threadpool(
            partial(
                campaigns.evaluate,
                name=payload.name,
                artifact_revisions=payload.artifacts,
                brand_version=payload.brand_version,
                amendment_revision=payload.amendment_revision,
                atomic_evaluations=payload.atomic_evaluations,
            )
        )

    @app.get(
        "/api/compliance/campaigns/{campaign_id}",
        response_model=CampaignResult,
        tags=["brand compliance"],
    )
    async def get_compliance_campaign(campaign_id: UUID, request: Request) -> CampaignResult:
        campaigns = cast(CampaignService, request.app.state.campaign_service)
        result = await run_in_threadpool(campaigns.get, campaign_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Compliance campaign not found.")
        return result

    @app.post(
        "/api/brand-systems",
        response_model=WorkingDraft,
        status_code=201,
        tags=["living brand systems"],
    )
    async def create_brand_system(
        payload: CreateWorkspaceRequest, request: Request
    ) -> WorkingDraft:
        service = cast(BrandSystemService, request.app.state.brand_system_service)
        try:
            return await run_in_threadpool(service.create, payload)
        except SourceBrandNotFound:
            raise HTTPException(status_code=404, detail="Source brand not found.") from None
        except WorkspaceAlreadyTrashed:
            raise HTTPException(
                status_code=409, detail="The source workspace is in recoverable trash."
            ) from None

    @app.get(
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

    @app.get(
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

    @app.post(
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

    @app.get(
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

    @app.patch(
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

    @app.post(
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

    @app.get(
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
                await run_in_threadpool(
                    create_workspace_backup, draft, assets, Path(temporary.name)
                )
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

    @app.post(
        "/api/brand-system-backups",
        response_model=WorkingDraft,
        tags=["living brand exports"],
    )
    async def restore_brand_system_backup(
        request: Request,
        expected_revision: int | None = Query(None, alias="expectedRevision", ge=1),
    ) -> WorkingDraft:
        declared = request.headers.get("content-length")
        if declared is not None:
            try:
                declared_size = int(declared)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid Content-Length.") from None
            if declared_size > MAX_BACKUP_BYTES:
                raise HTTPException(status_code=413, detail="Backup exceeds the safety limit.")
        observed = 0
        with tempfile.NamedTemporaryFile(suffix=".zip") as temporary:
            async for chunk in request.stream():
                observed += len(chunk)
                if observed > MAX_BACKUP_BYTES:
                    raise HTTPException(status_code=413, detail="Backup exceeds the safety limit.")
                temporary.write(chunk)
            temporary.flush()
            try:
                snapshot, asset_payloads = await run_in_threadpool(
                    read_workspace_backup, Path(temporary.name)
                )
            except InvalidWorkspaceBackup:
                raise HTTPException(
                    status_code=422, detail="Workspace backup is invalid."
                ) from None

        store = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
        current = await run_in_threadpool(store.get_including_trash, snapshot.brand_id)
        if (current is None and expected_revision is not None) or (
            current is not None and current.revision != expected_revision
        ):
            raise HTTPException(status_code=409, detail="Draft revision conflict.")
        settings_for_restore = cast(Settings, request.app.state.settings)
        await run_in_threadpool(
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
            raise HTTPException(status_code=409, detail="Draft revision conflict.") from None

    @app.delete(
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

    @app.get(
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

    async def move_brand_system_history(
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

    @app.post(
        "/api/brand-systems/{brand_id}/undo",
        response_model=WorkingDraft,
        tags=["living brand systems"],
    )
    async def undo_brand_system(
        brand_id: UUID, payload: RevisionCommand, request: Request
    ) -> WorkingDraft:
        return await move_brand_system_history(brand_id, payload, request, redo=False)

    @app.post(
        "/api/brand-systems/{brand_id}/redo",
        response_model=WorkingDraft,
        tags=["living brand systems"],
    )
    async def redo_brand_system(
        brand_id: UUID, payload: RevisionCommand, request: Request
    ) -> WorkingDraft:
        return await move_brand_system_history(brand_id, payload, request, redo=True)

    @app.post(
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

    @app.patch(
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

    @app.post(
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

    @app.post(
        "/api/brand-systems/{brand_id}/assets",
        response_model=WorkingDraft,
        status_code=201,
        tags=["living brand systems"],
    )
    async def register_brand_asset(
        brand_id: UUID, payload: RegisterAssetRequest, request: Request
    ) -> WorkingDraft:
        workspaces = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
        assets = cast(AssetStore, request.app.state.asset_store)
        draft = await run_in_threadpool(workspaces.get, brand_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Brand system not found.")
        if draft.revision != payload.expected_revision:
            raise HTTPException(status_code=409, detail="Draft revision conflict.")
        source = Path(payload.source_path)
        try:
            if payload.storage == "managed":
                registration = await run_in_threadpool(
                    partial(
                        assets.import_managed,
                        asset_id=payload.id,
                        name=payload.name,
                        source=source,
                        media_type=payload.media_type,
                        required=payload.required,
                    )
                )
            else:
                registration = await run_in_threadpool(
                    partial(
                        assets.register_linked,
                        asset_id=payload.id,
                        name=payload.name,
                        source=source,
                        media_type=payload.media_type,
                        required=payload.required,
                    )
                )
            return await _append_asset(workspaces, draft, registration)
        except StaleDraftRevision:
            raise HTTPException(status_code=409, detail="Draft revision conflict.") from None
        except (AssetMissing, AssetChanged, ValueError):
            raise HTTPException(status_code=422, detail="Asset registration is invalid.") from None

    @app.post(
        "/api/brand-systems/{brand_id}/asset-uploads",
        response_model=WorkingDraft,
        status_code=201,
        tags=["living brand systems"],
    )
    async def upload_brand_asset(
        brand_id: UUID,
        request: Request,
        expected_revision: int = Form(..., ge=1),
        name: str = Form(..., min_length=1, max_length=300),
        file: UploadFile = File(...),
        required: bool = Form(True),
    ) -> WorkingDraft:
        """Store a browser-uploaded file as a content-addressed managed asset."""

        workspaces = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
        assets = cast(AssetStore, request.app.state.asset_store)
        draft = await run_in_threadpool(workspaces.get, brand_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Brand system not found.")
        if draft.revision != expected_revision:
            raise HTTPException(status_code=409, detail="Draft revision conflict.")
        media_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or ""
        # Stream to a temp file so the store can hash + copy it; cap before we fill disk.
        with tempfile.NamedTemporaryFile(delete=False) as buffer:
            temporary = Path(buffer.name)
            written = 0
            while chunk := await file.read(64 * 1024):
                written += len(chunk)
                if written > assets.max_bytes:
                    buffer.close()
                    temporary.unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="Uploaded file is too large.")
                buffer.write(chunk)
        try:
            registration = await run_in_threadpool(
                partial(
                    assets.import_managed,
                    asset_id=f"asset.upload.{uuid4().hex}",
                    name=name,
                    source=temporary,
                    media_type=media_type,
                    required=required,
                )
            )
            return await _append_asset(workspaces, draft, registration)
        except StaleDraftRevision:
            raise HTTPException(status_code=409, detail="Draft revision conflict.") from None
        except (AssetMissing, AssetChanged, ValueError):
            raise HTTPException(
                status_code=422, detail="Uploaded file is not an accepted asset type."
            ) from None
        finally:
            temporary.unlink(missing_ok=True)

    @app.post(
        "/api/brand-systems/{brand_id}/logo-generations",
        response_model=WorkingDraft,
        status_code=201,
        tags=["living brand systems"],
    )
    async def generate_brand_logo(
        brand_id: UUID, payload: GenerateLogoRequest, request: Request
    ) -> WorkingDraft:
        """Generate a logo from the brand's own tokens and store it as a managed asset."""

        client = cast("OpenRouterImageClient | None", request.app.state.image_client)
        if client is None:
            raise HTTPException(status_code=503, detail="Image generation is not configured.")
        workspaces = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
        assets = cast(AssetStore, request.app.state.asset_store)
        settings = cast(Settings, request.app.state.settings)
        draft = await run_in_threadpool(workspaces.get, brand_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Brand system not found.")
        if draft.revision != payload.expected_revision:
            raise HTTPException(status_code=409, detail="Draft revision conflict.")
        try:
            image_bytes, media_type = await client.generate(
                prompt=logo_prompt(draft, payload.instructions), model=settings.image_model
            )
        except ProviderRefusal:
            raise HTTPException(
                status_code=422, detail="The image model declined this request."
            ) from None
        except ModelUnavailable:
            raise HTTPException(
                status_code=503, detail="The image model is temporarily unavailable."
            ) from None
        except ProviderError:
            raise HTTPException(status_code=502, detail="Logo generation failed.") from None
        with tempfile.NamedTemporaryFile(delete=False) as buffer:
            temporary = Path(buffer.name)
            buffer.write(image_bytes)
        try:
            registration = await run_in_threadpool(
                partial(
                    assets.import_managed,
                    asset_id=f"asset.logo.{uuid4().hex}",
                    name=payload.name or f"{draft.brand_name} logo",
                    source=temporary,
                    media_type=media_type,
                    required=False,
                )
            )
            return await _append_asset(workspaces, draft, registration)
        except StaleDraftRevision:
            raise HTTPException(status_code=409, detail="Draft revision conflict.") from None
        except (AssetMissing, AssetChanged, ValueError):
            raise HTTPException(
                status_code=502, detail="The generated image was not a usable asset."
            ) from None
        finally:
            temporary.unlink(missing_ok=True)

    @app.get(
        "/api/brand-systems/{brand_id}/assets/{asset_id}/content",
        include_in_schema=False,
    )
    async def read_brand_asset(brand_id: UUID, asset_id: str, request: Request) -> Response:
        """Serve one registered asset's bytes so the workshop can show thumbnails."""

        workspaces = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
        assets = cast(AssetStore, request.app.state.asset_store)
        draft = await run_in_threadpool(workspaces.get, brand_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Brand system not found.")
        asset = next((item for item in draft.assets if item.id == asset_id), None)
        if asset is None:
            raise HTTPException(status_code=404, detail="Asset not found.")
        try:
            content = await run_in_threadpool(assets.read, asset)
        except (AssetMissing, AssetChanged, ValueError):
            raise HTTPException(status_code=404, detail="Asset content unavailable.") from None
        # Uploaded SVG can carry script; sandbox it so direct navigation can't run it.
        return Response(
            content,
            media_type=asset.media_type,
            headers={
                "Content-Security-Policy": "default-src 'none'; sandbox",
                "X-Content-Type-Options": "nosniff",
                "Content-Disposition": "inline",
            },
        )

    @app.post(
        "/api/brand-systems/{brand_id}/assets/{asset_id}/favicon-sets",
        response_model=WorkingDraft,
        status_code=201,
        tags=["living brand systems"],
    )
    async def create_brand_favicon_set(
        brand_id: UUID,
        asset_id: str,
        payload: CreateAssetDerivativeRequest,
        request: Request,
    ) -> WorkingDraft:
        """Create six metadata-free favicon and app-icon PNGs from one raster logo."""

        workspaces, assets, draft, source, content = await _load_derivative_source(
            request, brand_id, asset_id, payload.expected_revision
        )
        try:
            derivatives = await run_in_threadpool(create_icon_set, content, source.media_type)
            registrations = await _register_derivatives(assets, source, derivatives)
            return await _append_assets(workspaces, draft, registrations)
        except StaleDraftRevision:
            raise HTTPException(status_code=409, detail="Draft revision conflict.") from None
        except (AssetMissing, AssetChanged, ValueError):
            raise HTTPException(status_code=422, detail="Could not create icons.") from None

    @app.post(
        "/api/brand-systems/{brand_id}/assets/{asset_id}/vectorizations",
        response_model=WorkingDraft,
        status_code=201,
        tags=["living brand systems"],
    )
    async def create_brand_vectorization(
        brand_id: UUID,
        asset_id: str,
        payload: CreateAssetDerivativeRequest,
        request: Request,
    ) -> WorkingDraft:
        """Trace one raster logo into path-only SVG geometry."""

        workspaces, assets, draft, source, content = await _load_derivative_source(
            request, brand_id, asset_id, payload.expected_revision
        )
        try:
            derivative = await run_in_threadpool(vectorize_logo, content, source.media_type)
            registrations = await _register_derivatives(assets, source, [derivative])
            return await _append_assets(workspaces, draft, registrations)
        except StaleDraftRevision:
            raise HTTPException(status_code=409, detail="Draft revision conflict.") from None
        except (AssetMissing, AssetChanged, ValueError):
            raise HTTPException(status_code=422, detail="Could not vectorize this logo.") from None

    @app.post(
        "/api/brand-systems/{brand_id}/assets/{asset_id}/logo-variant-sets",
        response_model=WorkingDraft,
        status_code=201,
        tags=["living brand systems"],
    )
    async def create_brand_logo_variant_set(
        brand_id: UUID,
        asset_id: str,
        payload: GenerateLogoVariantsRequest,
        request: Request,
    ) -> WorkingDraft:
        """Use the selected logo as an AI reference for explicit production variants."""

        client = cast("OpenRouterImageClient | None", request.app.state.image_client)
        if client is None:
            raise HTTPException(status_code=503, detail="Image generation is not configured.")
        workspaces, assets, draft, source, content = await _load_derivative_source(
            request, brand_id, asset_id, payload.expected_revision
        )
        settings = cast(Settings, request.app.state.settings)
        derivatives: list[LogoDerivative] = []
        try:
            for variant in payload.variants:
                image_bytes, media_type = await client.generate(
                    prompt=logo_variant_prompt(draft.brand_name, variant, payload.instructions),
                    model=settings.image_model,
                    reference=(content, source.media_type),
                    aspect_ratio="2:1" if variant == "horizontal-lockup" else "1:1",
                    background="transparent" if variant != "inverted" else "opaque",
                )
                derivatives.append(LogoDerivative(variant, image_bytes, media_type))
            registrations = await _register_derivatives(assets, source, derivatives)
            return await _append_assets(workspaces, draft, registrations)
        except ProviderRefusal:
            raise HTTPException(
                status_code=422, detail="The image model declined this request."
            ) from None
        except ModelUnavailable:
            raise HTTPException(
                status_code=503, detail="The image model is temporarily unavailable."
            ) from None
        except ProviderError:
            raise HTTPException(status_code=502, detail="Logo variant generation failed.") from None
        except StaleDraftRevision:
            raise HTTPException(status_code=409, detail="Draft revision conflict.") from None
        except (AssetMissing, AssetChanged, ValueError):
            raise HTTPException(
                status_code=502, detail="A generated logo variant was not usable."
            ) from None

    @app.post(
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

    @app.post(
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
            return await run_in_threadpool(
                partial(store.publish, brand_id, payload, snapshot=snapshot)
            )
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
            raise HTTPException(
                status_code=409, detail="Published version already exists."
            ) from None
        except (AssetMissing, AssetChanged):
            raise HTTPException(
                status_code=409, detail="Required publication asset is missing or changed."
            ) from None

    @app.get(
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

    @app.post(
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
            raise HTTPException(
                status_code=422, detail="Amendment target is not clerical."
            ) from None
        except StaleAmendmentValue:
            raise HTTPException(
                status_code=409, detail="Amendment before-value is stale."
            ) from None

    @app.get(
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

    async def rendered_publication(
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

    @app.get(
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
        published, rendered = await rendered_publication(
            brand_id, version, amendment_revision, request
        )
        view = project(rendered, content_hash=published.content_hash, audience=audience)
        return HTMLResponse(render_projection(view), headers=BROWSER_HEADERS)

    @app.get(
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
        published, rendered = await rendered_publication(
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

    @app.post(
        "/api/brand-system-archives",
        response_model=ArchiveContents,
        status_code=201,
        tags=["living brand exports"],
    )
    async def restore_brand_system_archive(request: Request) -> ArchiveContents:
        declared = request.headers.get("content-length")
        if declared is not None:
            try:
                declared_size = int(declared)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid Content-Length.") from None
            if declared_size > MAX_ARCHIVE_BYTES:
                raise HTTPException(status_code=413, detail="Archive exceeds the safety limit.")
        observed = 0
        with tempfile.NamedTemporaryFile(suffix=".zip") as temporary:
            async for chunk in request.stream():
                observed += len(chunk)
                if observed > MAX_ARCHIVE_BYTES:
                    raise HTTPException(status_code=413, detail="Archive exceeds the safety limit.")
                temporary.write(chunk)
            temporary.flush()
            settings_for_import = cast(Settings, request.app.state.settings)
            try:
                return await run_in_threadpool(
                    partial(
                        import_archive,
                        Path(temporary.name),
                        asset_root=settings_for_import.database_path.parent / "assets",
                        database_path=settings_for_import.database_path,
                    )
                )
            except InvalidArchive:
                raise HTTPException(status_code=422, detail="Archive is invalid.") from None

    @app.post(
        "/api/brand-systems/{brand_id}/generation-runs",
        response_model=GenerationRun,
        status_code=201,
        tags=["living brand generation"],
    )
    async def start_generation_run(
        brand_id: UUID, payload: StartGenerationRequest, request: Request
    ) -> GenerationRun:
        workspaces = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
        orchestrator = cast(GenerationOrchestrator, request.app.state.generation_orchestrator)
        draft = await run_in_threadpool(workspaces.get, brand_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Brand system not found.")
        try:
            return await run_in_threadpool(
                partial(
                    orchestrator.start,
                    draft,
                    target_section_id=payload.target_section_id,
                    model=request.app.state.settings.primary_model,
                    fallback_model=request.app.state.settings.fallback_model,
                )
            )
        except ValueError:
            raise HTTPException(status_code=422, detail="Unknown generation section.") from None

    @app.get(
        "/api/generation-runs/{run_id}",
        response_model=GenerationRun,
        tags=["living brand generation"],
    )
    async def get_generation_run(run_id: UUID, request: Request) -> GenerationRun:
        runs = cast(SQLiteGenerationRepository, request.app.state.generation_repository)
        run = await run_in_threadpool(runs.get, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Generation run not found.")
        return run

    @app.post(
        "/api/generation-runs/{run_id}/resume",
        response_model=GenerationRun,
        tags=["living brand generation"],
    )
    async def resume_generation_run(run_id: UUID, request: Request) -> GenerationRun:
        orchestrator = cast(GenerationOrchestrator, request.app.state.generation_orchestrator)
        completer = cast(Completer | None, request.app.state.generation_completer)
        if completer is None:
            raise HTTPException(status_code=503, detail="Generation provider unavailable.")
        try:
            return await orchestrator.resume(run_id, completer=completer)
        except GenerationRunNotFound:
            raise HTTPException(status_code=404, detail="Generation run not found.") from None

    @app.post(
        "/api/generation-runs/{run_id}/pause",
        response_model=GenerationRun,
        tags=["living brand generation"],
    )
    async def pause_generation_run(run_id: UUID, request: Request) -> GenerationRun:
        return await control_generation_run(run_id, request, "pause")

    @app.post(
        "/api/generation-runs/{run_id}/cancel",
        response_model=GenerationRun,
        tags=["living brand generation"],
    )
    async def cancel_generation_run(run_id: UUID, request: Request) -> GenerationRun:
        return await control_generation_run(run_id, request, "cancel")

    async def control_generation_run(run_id: UUID, request: Request, command: str) -> GenerationRun:
        orchestrator = cast(GenerationOrchestrator, request.app.state.generation_orchestrator)
        try:
            operation = orchestrator.pause if command == "pause" else orchestrator.cancel
            return await run_in_threadpool(operation, run_id)
        except GenerationRunNotFound:
            raise HTTPException(status_code=404, detail="Generation run not found.") from None

    @app.get(
        "/api/brand-systems/{brand_id}/assets/{sha}",
        tags=["living brand assets"],
    )
    async def get_brand_system_asset(brand_id: UUID, sha: str, request: Request) -> Response:
        workspaces = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
        asset_store = cast(AssetStore, request.app.state.asset_store)
        draft = await run_in_threadpool(workspaces.get, brand_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Brand system not found.")
        asset = next(
            (item for item in draft.assets if item.content_hash == sha or item.id == sha),
            None,
        )
        if asset is None:
            raise HTTPException(status_code=404, detail="Asset not found.")
        try:
            content = await run_in_threadpool(asset_store.read, asset)
            return Response(content, media_type=asset.media_type)
        except (AssetMissing, ValueError):
            raise HTTPException(status_code=404, detail="Asset file missing or invalid.") from None
        except AssetChanged:
            raise HTTPException(status_code=409, detail="Asset file integrity breach.") from None

    @app.get(
        "/api/brand-systems/{brand_id}/draft-exports/{format_name}",
        tags=["living brand exports"],
    )
    async def export_draft_brand_system(
        brand_id: UUID,
        format_name: Literal["pdf", "markdown", "tokens-css", "tokens-json", "tailwind", "kit"],
        request: Request,
    ) -> Response:
        workspaces = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
        asset_store = cast(AssetStore, request.app.state.asset_store)
        draft = await run_in_threadpool(workspaces.get, brand_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Brand system not found.")

        if format_name == "markdown":
            body = export_markdown(draft, version="draft", amendment_revision=0)
            return Response(
                body,
                media_type="text/markdown",
                headers={
                    "Content-Disposition": _content_disposition(f"{draft.brand_name}-bible.md")
                },
            )

        if format_name in {"tokens-css", "tokens-json", "tailwind"}:
            token_exports = export_draft_tokens(draft)
            if format_name == "tokens-css":
                return Response(
                    token_exports["tokens.css"],
                    media_type="text/css",
                    headers={"Content-Disposition": _content_disposition("tokens.css")},
                )
            if format_name == "tokens-json":
                return Response(
                    token_exports["tokens.json"],
                    media_type="application/json",
                    headers={"Content-Disposition": _content_disposition("tokens.json")},
                )
            return Response(
                token_exports["tailwind.config.js"],
                media_type="application/javascript",
                headers={"Content-Disposition": _content_disposition("tailwind.config.js")},
            )

        if format_name == "pdf":
            html_content = render_brand_bible(draft, for_pdf=True)
            pdf_bytes = await run_in_threadpool(render_html_pdf, html_content)
            return Response(
                pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": _content_disposition(f"{draft.brand_name}-bible.pdf")
                },
            )

        zip_bytes = await run_in_threadpool(_build_brand_kit_zip, draft, asset_store)
        return Response(
            zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": _content_disposition(f"{draft.brand_name}-brand-kit.zip")
            },
        )

    @app.get(
        "/api/generation-runs/{run_id}/stream",
        tags=["living brand generation"],
    )
    async def stream_generation_run(run_id: UUID, request: Request) -> StreamingResponse:
        orchestrator = cast(GenerationOrchestrator, request.app.state.generation_orchestrator)
        try:
            queue = await run_in_threadpool(orchestrator.subscribe, run_id)
        except GenerationRunNotFound:
            raise HTTPException(status_code=404, detail="Generation run not found.") from None

        async def event_generator() -> AsyncIterator[str]:
            try:
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=15.0)
                        yield f"data: {json.dumps(event)}\n\n"
                        if event.get("status") in {"completed", "cancelled", "failed"}:
                            break
                    except TimeoutError:
                        yield ": keep-alive\n\n"
            finally:
                orchestrator.unsubscribe(run_id, queue)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    @app.post(
        "/api/brand-systems/{brand_id}/sections/{section_id}/fields/regenerate",
        tags=["living brand generation"],
    )
    async def regenerate_section_field(
        brand_id: UUID,
        section_id: str,
        payload: RegenerateFieldRequest,
        request: Request,
    ) -> dict[str, str]:
        workspaces = cast(
            SQLiteBrandSystemRepository, request.app.state.brand_system_repository
        )
        orchestrator = cast(
            GenerationOrchestrator, request.app.state.generation_orchestrator
        )
        completer = cast(Completer | None, request.app.state.generation_completer)
        settings = cast(Settings, request.app.state.settings)
        if completer is None:
            raise HTTPException(status_code=503, detail="Generation provider unavailable.")
        draft = await run_in_threadpool(workspaces.get, brand_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Workspace not found.")

        return await orchestrator.regenerate_field(
            draft=draft,
            section_id=section_id,
            field_label=payload.field_label,
            current_text=payload.current_text,
            instruction=payload.instruction,
            model=payload.model or settings.primary_model,
            completer=completer,
        )

    @app.post(
        "/api/brand-systems/{brand_id}/sections/{section_id}/variants",
        tags=["living brand generation"],
    )
    async def generate_section_variants_route(
        brand_id: UUID,
        section_id: str,
        payload: GenerateSectionVariantsRequest,
        request: Request,
    ) -> dict[str, list[dict[str, object]]]:
        workspaces = cast(
            SQLiteBrandSystemRepository, request.app.state.brand_system_repository
        )
        orchestrator = cast(
            GenerationOrchestrator, request.app.state.generation_orchestrator
        )
        completer = cast(Completer | None, request.app.state.generation_completer)
        settings = cast(Settings, request.app.state.settings)
        if completer is None:
            raise HTTPException(status_code=503, detail="Generation provider unavailable.")
        draft = await run_in_threadpool(workspaces.get, brand_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Workspace not found.")

        variants = await orchestrator.generate_section_variants(
            draft=draft,
            section_id=section_id,
            postures=payload.postures,
            model=payload.model or settings.primary_model,
            completer=completer,
        )
        return {"variants": variants}

    @app.post(
        "/api/brand-systems/{brand_id}/fonts",
        tags=["living brand assets"],
    )
    async def upload_font_asset(
        brand_id: UUID,
        request: Request,
        file: UploadFile = File(...),
        font_family: str = Form(..., min_length=1, max_length=300),
        expected_revision: int | None = Form(default=None, ge=1),
    ) -> dict[str, object]:
        workspaces = cast(
            SQLiteBrandSystemRepository, request.app.state.brand_system_repository
        )
        asset_store = cast(AssetStore, request.app.state.asset_store)
        draft = await run_in_threadpool(workspaces.get, brand_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Workspace not found.")
        if expected_revision is not None and expected_revision != draft.revision:
            raise HTTPException(
                status_code=409,
                detail="Stale revision: workspace was modified by another operation.",
            )

        content = bytearray()
        while chunk := await file.read(64 * 1024):
            content.extend(chunk)
            if len(content) > 5_000_000:
                raise HTTPException(status_code=422, detail="Font file exceeds 5MB limit.")

        if not content:
            raise HTTPException(status_code=422, detail="Font file is empty.")

        font_bytes = bytes(content)
        try:
            font_fmt = validate_font_file_header(font_bytes)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        media_types = {
            "woff": "font/woff",
            "woff2": "font/woff2",
            "truetype": "font/ttf",
            "opentype": "font/otf",
        }
        media_type = media_types[font_fmt]
        filename = file.filename or f"{font_family}.{font_fmt}"
        try:
            generate_font_face_css(font_family, media_type, "/")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        with tempfile.NamedTemporaryFile(delete=False) as temp_f:
            temp_f.write(font_bytes)
            temp_path = Path(temp_f.name)

        registration: AssetRegistration | None = None
        created_blob = False
        try:
            asset_id = f"asset.font.{uuid4().hex[:8]}"
            imported_registration, created_blob = await run_in_threadpool(
                asset_store.import_managed_with_status,
                asset_id=asset_id,
                name=filename,
                source=temp_path,
                media_type=media_type,
                required=False,
            )
            registration = imported_registration
            assets = [*draft.assets, imported_registration]
            updated = draft.model_copy(update={"assets": assets, "revision": draft.revision + 1})
            exp_rev = expected_revision if expected_revision is not None else draft.revision
            await run_in_threadpool(
                workspaces.update, updated, expected_revision=exp_rev
            )

            asset_url = (
                f"/api/brand-systems/{brand_id}/assets/{imported_registration.content_hash}"
            )
            font_css = generate_font_face_css(font_family, media_type, asset_url)
            return {
                "asset": imported_registration.model_dump(mode="json"),
                "font_family": font_family,
                "font_face_css": font_css,
            }
        except StaleDraftRevision:
            if (
                registration is not None
                and created_blob
                and not await run_in_threadpool(
                    workspaces.references_asset_hash, registration.content_hash
                )
            ):
                await run_in_threadpool(asset_store.discard_managed, registration)
            raise HTTPException(
                status_code=409,
                detail="Stale revision: workspace was modified by another operation.",
            ) from None
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        finally:
            temp_path.unlink(missing_ok=True)

    @app.post(
        "/api/brand-systems/{brand_id}/compliance/check-copy",
        tags=["living brand compliance"],
    )
    async def check_copy_compliance(
        brand_id: UUID,
        payload: dict[str, object],
        request: Request,
    ) -> dict[str, object]:
        workspaces = cast(
            SQLiteBrandSystemRepository, request.app.state.brand_system_repository
        )
        draft = await run_in_threadpool(workspaces.get, brand_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Workspace not found.")

        copy_text = str(payload.get("copy_text", ""))
        if not copy_text:
            raise HTTPException(status_code=422, detail="copy_text is required.")
        report = check_copy_against_brand_rules(copy_text, draft)
        return report.model_dump(mode="json")

    @app.get(
        "/api/brand-systems/{brand_id}/token-collisions",
        tags=["living brand compliance"],
    )
    async def get_token_collisions(
        brand_id: UUID,
        request: Request,
    ) -> dict[str, object]:
        workspaces = cast(
            SQLiteBrandSystemRepository, request.app.state.brand_system_repository
        )
        draft = await run_in_threadpool(workspaces.get, brand_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Workspace not found.")

        findings = audit_token_collisions(draft.sections)
        return {"collisions": [f.model_dump(mode="json") for f in findings]}

    @app.get(
        "/api/brand-systems/{brand_id}/wcag-audit",
        tags=["living brand compliance"],
    )
    async def get_wcag_token_audit(
        brand_id: UUID,
        request: Request,
    ) -> dict[str, object]:
        workspaces = cast(
            SQLiteBrandSystemRepository, request.app.state.brand_system_repository
        )
        draft = await run_in_threadpool(workspaces.get, brand_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Workspace not found.")

        findings = audit_token_contrast_pairs(draft.sections)
        return {"findings": [f.model_dump(mode="json") for f in findings]}

    @app.get(
        "/api/brand-systems/{brand_id}/logo-contrast-check",
        tags=["living brand compliance"],
    )
    async def check_logo_contrast_route(
        brand_id: UUID,
        request: Request,
    ) -> dict[str, object]:
        workspaces = cast(
            SQLiteBrandSystemRepository, request.app.state.brand_system_repository
        )
        asset_store = cast(AssetStore, request.app.state.asset_store)
        draft = await run_in_threadpool(workspaces.get, brand_id)
        if draft is None:
            raise HTTPException(status_code=404, detail="Workspace not found.")

        logo_asset = next(
            (
                a
                for a in draft.assets
                if ("logo" in a.id or "logo" in a.name.lower())
                and a.media_type in RASTER_MEDIA_TYPES
            ),
            None,
        )
        if logo_asset is None:
            raise HTTPException(
                status_code=422, detail="No registered raster logo asset found in workspace."
            )

        content = await run_in_threadpool(asset_store.read, logo_asset)
        bg_tokens: list[tuple[str, str]] = []
        for s in draft.sections:
            for t in s.tokens:
                if t.value_type == "color" and isinstance(t.value, str):
                    if any(
                        k in t.id.lower() or k in t.name.lower()
                        for k in ["paper", "background", "surface"]
                    ):
                        bg_tokens.append((t.name, t.value))
        if not bg_tokens:
            bg_tokens = [("Paper Light", "#ffffff"), ("Paper Dark", "#111827")]

        results = await run_in_threadpool(
            check_logo_contrast_against_backgrounds, content, logo_asset.media_type, bg_tokens
        )
        return {"results": results}

    return app
