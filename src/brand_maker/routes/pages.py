"""HTML shell, documentation, and static-asset routes."""

from typing import cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.responses import HTMLResponse, Response
from starlette.concurrency import run_in_threadpool

from brand_maker.brand_bible import render_brand_bible
from brand_maker.brand_bible_styles import BRAND_BIBLE_CSS
from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
from brand_maker.compliance_ui import COMPLIANCE_SCRIPT
from brand_maker.compliance_web import compliance_page
from brand_maker.http import BROWSER_HEADERS, static_response
from brand_maker.library_styles import LIBRARY_CSS
from brand_maker.library_ui import LIBRARY_SCRIPT
from brand_maker.library_web import detail_page, library_page, not_found_page
from brand_maker.storage import SQLiteBrandRepository
from brand_maker.ui import UI_SCRIPT
from brand_maker.web import FAVICON, HOME_PAGE, add_home_navigation
from brand_maker.workshop_styles import WORKSHOP_CSS
from brand_maker.workshop_ui import WORKSHOP_SCRIPT
from brand_maker.workshop_web import workspace_detail, workspace_index

router = APIRouter()


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root() -> HTMLResponse:
    return HTMLResponse(HOME_PAGE, headers=BROWSER_HEADERS)


@router.get("/assets/app.js", include_in_schema=False)
async def ui_script() -> Response:
    return static_response(UI_SCRIPT, "text/javascript")


@router.get("/assets/library.js", include_in_schema=False)
async def library_script() -> Response:
    return static_response(LIBRARY_SCRIPT, "text/javascript")


@router.get("/assets/library.css", include_in_schema=False)
async def library_styles() -> Response:
    return static_response(LIBRARY_CSS, "text/css")


@router.get("/assets/workshop.js", include_in_schema=False)
async def workshop_script() -> Response:
    return static_response(WORKSHOP_SCRIPT, "text/javascript")


@router.get("/assets/workshop.css", include_in_schema=False)
async def workshop_styles() -> Response:
    return static_response(WORKSHOP_CSS, "text/css")


@router.get("/assets/brand-bible.css", include_in_schema=False)
async def brand_bible_styles() -> Response:
    return static_response(BRAND_BIBLE_CSS, "text/css")


@router.get("/assets/compliance.js", include_in_schema=False)
async def compliance_script() -> Response:
    return static_response(COMPLIANCE_SCRIPT, "text/javascript")


@router.get("/brand-systems", response_class=HTMLResponse, include_in_schema=False)
async def brand_system_index() -> HTMLResponse:
    return HTMLResponse(workspace_index(), headers=BROWSER_HEADERS)


@router.get("/compliance", response_class=HTMLResponse, include_in_schema=False)
async def compliance_workflow() -> HTMLResponse:
    return HTMLResponse(compliance_page(), headers=BROWSER_HEADERS)


@router.get("/brand-systems/{brand_id}", response_class=HTMLResponse, include_in_schema=False)
async def brand_system_workshop(brand_id: UUID, request: Request) -> HTMLResponse:
    store = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    if await run_in_threadpool(store.get, brand_id) is None:
        raise HTTPException(status_code=404, detail="Brand system not found.")
    return HTMLResponse(workspace_detail(brand_id), headers=BROWSER_HEADERS)


@router.get(
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


@router.get("/brands", response_class=HTMLResponse, include_in_schema=False)
async def brand_library_page() -> HTMLResponse:
    return HTMLResponse(library_page(), headers=BROWSER_HEADERS)


@router.get("/brands/{brand_id}", response_class=HTMLResponse, include_in_schema=False)
async def saved_brand_page(brand_id: UUID, request: Request) -> HTMLResponse:
    store = cast(SQLiteBrandRepository, request.app.state.repository)
    saved = await run_in_threadpool(store.get, brand_id)
    if saved is None:
        return HTMLResponse(not_found_page(), status_code=404, headers=BROWSER_HEADERS)
    return HTMLResponse(detail_page(brand_id), headers=BROWSER_HEADERS)


@router.get("/docs", response_class=HTMLResponse, include_in_schema=False)
async def swagger_docs(request: Request) -> HTMLResponse:
    page = get_swagger_ui_html(
        openapi_url=request.app.openapi_url or "/openapi.json",
        title=f"{request.app.title} — API console",
        oauth2_redirect_url=request.app.swagger_ui_oauth2_redirect_url,
    )
    return add_home_navigation(page)


@router.get("/docs/oauth2-redirect", include_in_schema=False)
async def swagger_oauth2_redirect() -> HTMLResponse:
    return get_swagger_ui_oauth2_redirect_html()


@router.get("/redoc", response_class=HTMLResponse, include_in_schema=False)
async def redoc_docs(request: Request) -> HTMLResponse:
    page = get_redoc_html(
        openapi_url=request.app.openapi_url or "/openapi.json",
        title=f"{request.app.title} — Reference",
    )
    return add_home_navigation(page)


@router.get("/favicon.svg", include_in_schema=False)
async def favicon() -> Response:
    return static_response(FAVICON, "image/svg+xml")


@router.get("/health", tags=["operations"])
async def health() -> dict[str, str]:
    return {"status": "up"}
