"""FastAPI application factory and HTTP routes."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import ValidationError

from brand_maker.config import Settings

logger = logging.getLogger(__name__)


def create_app(*, settings: Settings | None = None) -> FastAPI:
    """Create an application whose resources are owned by its lifespan."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            app.state.settings = settings or Settings.model_validate({})
        except ValidationError:
            logger.critical("OPENROUTER_API_KEY is required; server startup aborted.")
            raise
        yield

    app = FastAPI(
        title="Brand System Maker",
        version="0.1.0",
        description="Generate one validated parody brand kit from one brand name.",
        lifespan=lifespan,
    )

    @app.get("/health", tags=["operations"])
    async def health() -> dict[str, str]:
        return {"status": "up"}

    return app
