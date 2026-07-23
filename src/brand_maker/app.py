"""FastAPI application factory and HTTP routes."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

import httpx
from fastapi import FastAPI, Request
from pydantic import ValidationError

from brand_maker.config import Settings
from brand_maker.models import BrandRequest, BrandResponse
from brand_maker.openrouter import OpenRouterClient
from brand_maker.pipeline import BrandBuilder, BrandPipeline

logger = logging.getLogger(__name__)


def create_app(
    *, settings: Settings | None = None, pipeline: BrandBuilder | None = None
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

        if pipeline is not None:
            app.state.pipeline = pipeline
            yield
            return

        timeout = httpx.Timeout(resolved_settings.request_timeout_seconds)
        limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
        async with httpx.AsyncClient(timeout=timeout, limits=limits) as http:
            generator = OpenRouterClient(
                http=http,
                api_key=resolved_settings.openrouter_api_key.get_secret_value(),
            )
            app.state.pipeline = BrandPipeline(
                generator=generator,
                primary_model=resolved_settings.primary_model,
                fallback_model=resolved_settings.fallback_model,
            )
            yield

    app = FastAPI(
        title="Brand System Maker",
        version="0.1.0",
        description="Generate one validated parody brand kit from one brand name.",
        lifespan=lifespan,
    )

    @app.get("/", tags=["operations"])
    async def root() -> dict[str, str]:
        return {
            "service": "Brand System Maker",
            "docs": "/docs",
            "health": "/health",
            "generate": "POST /brand",
        }

    @app.get("/health", tags=["operations"])
    async def health() -> dict[str, str]:
        return {"status": "up"}

    @app.post("/brand", response_model=BrandResponse, tags=["brands"])
    async def build_brand(payload: BrandRequest, request: Request) -> BrandResponse:
        builder = cast(BrandBuilder, request.app.state.pipeline)
        return await builder.build(payload.brand_name)

    return app
