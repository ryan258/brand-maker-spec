"""FastAPI application factory and app orchestration."""

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from typing import cast
from uuid import UUID

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.types import Scope

from brand_maker.brand_system.amendments import SQLiteAmendmentRepository
from brand_maker.brand_system.assets import AssetStore
from brand_maker.brand_system.models import CreateWorkspaceRequest
from brand_maker.brand_system.publication import SQLitePublicationRepository
from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
from brand_maker.brand_system.service import BrandSystemService
from brand_maker.compliance.campaigns import CampaignService
from brand_maker.compliance.exceptions import ExceptionLedger
from brand_maker.compliance.judgment import SQLiteEvidenceRepository
from brand_maker.compliance.repository import SQLiteComplianceRepository
from brand_maker.config import Settings
from brand_maker.generation.orchestrator import GenerationOrchestrator
from brand_maker.generation.repository import SQLiteGenerationRepository
from brand_maker.image_gen import OpenRouterImageClient
from brand_maker.models import (
    BrandRequest,
    BrandResponse,
    SavedBrand,
    SavedBrandGeneration,
    SavedBrandPage,
)
from brand_maker.openrouter import OpenRouterClient
from brand_maker.pipeline import BrandBuilder, BrandPipeline
from brand_maker.routes.assets import router as assets_router
from brand_maker.routes.compliance import router as compliance_router
from brand_maker.routes.exports import router as exports_router
from brand_maker.routes.generation import router as generation_router
from brand_maker.routes.pages import router as pages_router
from brand_maker.routes.publication import router as publication_router
from brand_maker.routes.workspaces import router as workspaces_router
from brand_maker.storage import SQLiteBrandRepository

_logger = logging.getLogger(__name__)


async def _cancel_generation_tasks(app: FastAPI) -> None:
    raw_tasks = getattr(app.state, "generation_tasks", {})
    tasks = list(raw_tasks.values()) if isinstance(raw_tasks, dict) else list(raw_tasks)
    if not tasks:
        return
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


class CacheControlStaticFiles(StaticFiles):
    def file_response(
        self,
        full_path: str | os.PathLike[str],
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        response = super().file_response(full_path, stat_result, scope, status_code)
        response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response


def create_app(
    settings: Settings | None = None,
    repository: SQLiteBrandRepository | None = None,
    brand_system_repository: SQLiteBrandSystemRepository | None = None,
    publication_repository: SQLitePublicationRepository | None = None,
    amendment_repository: SQLiteAmendmentRepository | None = None,
    generation_repository: SQLiteGenerationRepository | None = None,
    brand_system_service: BrandSystemService | None = None,
    orchestrator: GenerationOrchestrator | None = None,
    completer: OpenRouterClient | None = None,
    generation_completer: OpenRouterClient | None = None,
    image_client: OpenRouterImageClient | None = None,
    pipeline: BrandPipeline | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings.model_validate({})
    resolved_repository = repository or SQLiteBrandRepository(
        resolved_settings.database_path
    )
    resolved_brand_system_repository = (
        brand_system_repository
        or SQLiteBrandSystemRepository(resolved_settings.database_path)
    )
    resolved_publication_repository = (
        publication_repository
        or SQLitePublicationRepository(resolved_settings.database_path)
    )
    resolved_amendment_repository = (
        amendment_repository
        or SQLiteAmendmentRepository(resolved_settings.database_path)
    )
    resolved_generation_repository = (
        generation_repository
        or SQLiteGenerationRepository(resolved_settings.database_path)
    )
    asset_store = AssetStore(resolved_settings.database_path.parent / "assets")
    resolved_service = brand_system_service or BrandSystemService(
        workspaces=resolved_brand_system_repository,
        legacy=resolved_repository,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = resolved_settings
        app.state.repository = resolved_repository
        app.state.brand_system_repository = resolved_brand_system_repository
        app.state.publication_repository = resolved_publication_repository
        app.state.amendment_repository = resolved_amendment_repository
        app.state.generation_repository = resolved_generation_repository
        app.state.asset_store = asset_store
        app.state.brand_system_service = resolved_service
        app.state.compliance_repository = SQLiteComplianceRepository(
            resolved_settings.database_path
        )
        app.state.exception_ledger = ExceptionLedger(path=resolved_settings.database_path)
        app.state.evidence_repository = SQLiteEvidenceRepository(resolved_settings.database_path)
        app.state.campaign_service = CampaignService(app.state.compliance_repository)
        app.state.generation_tasks = {}
        app.state.run_events = {}

        timeout = httpx.Timeout(resolved_settings.request_timeout_seconds)
        limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
        async with httpx.AsyncClient(timeout=timeout, limits=limits) as http:
            app.state.http_client = http
            api_key = resolved_settings.openrouter_api_key.get_secret_value()
            generator = completer or generation_completer or OpenRouterClient(
                http=http,
                api_key=api_key,
            )
            resolved_orchestrator = orchestrator or GenerationOrchestrator(
                workspaces=resolved_brand_system_repository,
                runs=resolved_generation_repository,
                clock=resolved_brand_system_repository._clock,
            )
            app.state.orchestrator = resolved_orchestrator
            app.state.generation_orchestrator = resolved_orchestrator
            app.state.image_client = image_client or (
                None
                if pipeline is not None
                else OpenRouterImageClient(http=http, api_key=api_key)
            )
            app.state.generation_completer = generator
            app.state.pipeline = pipeline or BrandPipeline(
                generator=generator,
                primary_model=resolved_settings.primary_model,
                fallback_model=resolved_settings.fallback_model,
            )
            try:
                yield
            finally:
                await _cancel_generation_tasks(app)

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
    app.include_router(generation_router)
    app.include_router(compliance_router)
    app.include_router(pages_router)
    app.include_router(exports_router)
    app.include_router(workspaces_router)
    app.include_router(publication_router)
    app.include_router(assets_router)

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/assets", CacheControlStaticFiles(directory=static_dir), name="assets")

    @app.post("/brand", response_model=BrandResponse, tags=["brands"])
    async def build_brand(payload: BrandRequest, request: Request) -> BrandResponse:
        builder = cast(BrandBuilder, request.app.state.pipeline)
        return await builder.build(payload.brand_name, brand_context=payload.brand_context)

    @app.post("/api/brands", response_model=SavedBrandGeneration, tags=["brand library"])
    async def create_saved_brand(payload: BrandRequest, request: Request) -> SavedBrandGeneration:
        builder = cast(BrandBuilder, request.app.state.pipeline)
        result = await builder.build(payload.brand_name, brand_context=payload.brand_context)
        if result.status != "ok":
            return SavedBrandGeneration(status=result.status, message=result.message)

        if result.kit is None:
            raise RuntimeError("successful generation did not contain a kit")
        store = cast(SQLiteBrandRepository, request.app.state.repository)
        saved = await run_in_threadpool(store.save, result.kit)
        brand_systems = cast(BrandSystemService, request.app.state.brand_system_service)
        workspace = await run_in_threadpool(
            brand_systems.create,
            CreateWorkspaceRequest(
                source_brand_id=saved.id,
                brand_context=payload.brand_context,
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

    return app
