"""Export and download endpoints for living brand systems."""

import re
from typing import cast
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from brand_maker.brand_bible import render_brand_bible
from brand_maker.brand_system.assets import AssetStore
from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
from brand_maker.publishing.developer_exports import (
    BrandKitLimitExceeded,
    RequiredBrandKitAssetUnavailable,
    build_brand_kit_zip,
    export_draft_tokens,
)
from brand_maker.publishing.markdown import export_markdown
from brand_maker.publishing.pdf import render_html_pdf

router = APIRouter()


def _content_disposition(filename: str, prefix: str = "attachment") -> str:
    ascii_filename = re.sub(r"[^\x20-\x7E]", "_", filename).replace('"', "_").strip()
    if not ascii_filename:
        ascii_filename = "export"
    utf8_encoded = quote(filename)
    return f"{prefix}; filename=\"{ascii_filename}\"; filename*=UTF-8''{utf8_encoded}"


@router.get(
    "/api/brand-systems/{brand_id}/exports/{format_name}",
    tags=["living brand exports"],
)
@router.get(
    "/api/brand-systems/{brand_id}/draft-exports/{format_name}",
    tags=["living brand exports"],
)
async def download_draft_export(
    brand_id: UUID,
    format_name: str,
    request: Request,
) -> Response:
    workspaces = cast(
        SQLiteBrandSystemRepository, request.app.state.brand_system_repository
    )
    asset_store = cast(AssetStore, request.app.state.asset_store)
    draft = await run_in_threadpool(workspaces.get, brand_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    allowed_formats = {"markdown", "tokens-css", "tokens-json", "tailwind", "pdf", "zip", "kit"}
    if format_name not in allowed_formats:
        raise HTTPException(
            status_code=422,
            detail=(
                "Export format must be one of: "
                "markdown, tokens-css, tokens-json, tailwind, pdf, zip, kit."
            ),
        )

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

    total_asset_bytes = sum(asset.size_bytes for asset in draft.assets)
    if total_asset_bytes > 250_000_000:
        raise HTTPException(
            status_code=413, detail="Total asset size exceeds 250 MB export limit."
        )

    try:
        zip_bytes = await run_in_threadpool(build_brand_kit_zip, draft, asset_store)
    except BrandKitLimitExceeded as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except RequiredBrandKitAssetUnavailable as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Required asset '{exc.asset.name}' is missing or changed.",
        ) from exc
    return Response(
        zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": _content_disposition(f"{draft.brand_name}-brand-kit.zip")
        },
    )
