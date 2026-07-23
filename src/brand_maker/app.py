"""FastAPI application factory and HTTP routes."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

import httpx
from fastapi import FastAPI, Request
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.responses import HTMLResponse, Response
from pydantic import ValidationError

from brand_maker.config import Settings
from brand_maker.models import BrandRequest, BrandResponse
from brand_maker.openrouter import OpenRouterClient
from brand_maker.pipeline import BrandBuilder, BrandPipeline
from brand_maker.ui import UI_SCRIPT
from brand_maker.web import FAVICON, HOME_PAGE, add_home_navigation

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
        docs_url=None,
        redoc_url=None,
        swagger_ui_oauth2_redirect_url="/docs/oauth2-redirect",
        lifespan=lifespan,
    )
    openapi_url = app.openapi_url or "/openapi.json"

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def root() -> HTMLResponse:
        return HTMLResponse(
            HOME_PAGE,
            headers={
                "Content-Security-Policy": (
                    "default-src 'self'; script-src 'self'; style-src 'unsafe-inline'; "
                    "img-src 'self'; connect-src 'self'; base-uri 'none'; "
                    "form-action 'self'; frame-ancestors 'none'"
                ),
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.get("/assets/app.js", include_in_schema=False)
    async def ui_script() -> Response:
        return Response(
            UI_SCRIPT,
            media_type="text/javascript",
            headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"},
        )

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

    return app
