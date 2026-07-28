"""Asset management, logo generation, derivatives, and font upload endpoints."""

import mimetypes
import tempfile
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from brand_maker.brand_system.assets import (
    AssetChanged,
    AssetMissing,
    AssetStore,
    generate_font_face_css,
    validate_font_file_header,
)
from brand_maker.brand_system.models import (
    AssetRegistration,
    CreateAssetDerivativeRequest,
    GenerateLogoRequest,
    GenerateLogoVariantsRequest,
    RegisterAssetRequest,
    WorkingDraft,
)
from brand_maker.brand_system.repository import (
    SQLiteBrandSystemRepository,
    StaleDraftRevision,
)
from brand_maker.config import Settings
from brand_maker.http import asset_response
from brand_maker.image_gen import (
    OpenRouterImageClient,
    logo_prompt,
    logo_variant_prompt,
)
from brand_maker.logo_derivatives import (
    RASTER_MEDIA_TYPES,
    LogoDerivative,
    create_icon_set,
    vectorize_logo,
)
from brand_maker.openrouter import ModelUnavailable, ProviderError, ProviderRefusal

if TYPE_CHECKING:
    from brand_maker.image_gen import OpenRouterImageClient

router = APIRouter()


def _asset_source_is_allowed(source: Path, settings: Settings) -> bool:
    candidate = source.expanduser()
    db_path = settings.database_path.expanduser()
    candidate_parent = candidate.parent.resolve()
    db_parent = db_path.parent.resolve()
    if candidate_parent == db_parent and candidate.name.startswith(db_path.name):
        return False
    configured_roots = [
        root.expanduser().resolve()
        for root in (settings.asset_source_roots or [settings.database_path.parent])
    ]
    candidate_resolved = candidate.resolve()
    return any(
        candidate_resolved == root or root in candidate_resolved.parents
        for root in configured_roots
    )


async def _append_asset(
    workspaces: SQLiteBrandSystemRepository,
    draft: WorkingDraft,
    registration: AssetRegistration,
) -> WorkingDraft:
    return await _append_assets(workspaces, draft, [registration])


async def _append_assets(
    workspaces: SQLiteBrandSystemRepository,
    draft: WorkingDraft,
    registrations: list[AssetRegistration],
) -> WorkingDraft:
    current_assets = list(draft.assets)
    for registration in registrations:
        existing_idx = next(
            (index for index, item in enumerate(current_assets) if item.id == registration.id), None
        )
        if existing_idx is None:
            current_assets.append(registration)
        else:
            current_assets[existing_idx] = registration

    payload = draft.model_dump(mode="json")
    payload.update(
        {
            "assets": [item.model_dump(mode="json") for item in current_assets],
            "revision": draft.revision + 1,
        }
    )
    updated = WorkingDraft.model_validate(payload)
    return await run_in_threadpool(workspaces.update, updated, expected_revision=draft.revision)


DISPLAY_NAME_SUFFIXES = {
    "favicon-16": "favicon 16",
    "favicon-32": "favicon 32",
    "favicon-48": "favicon 48",
    "apple-touch-icon-180": "apple touch icon 180",
    "app-icon-192": "app icon 192",
    "app-icon-512": "app icon 512",
    "monochrome": "monochrome",
    "inverted": "inverted",
    "horizontal-lockup": "horizontal lockup",
    "icon-only": "icon only",
    "vector": "vector",
    "vector-svg": "vector",
}


async def _register_derivatives(
    assets: AssetStore,
    source: AssetRegistration,
    derivatives: list[LogoDerivative],
) -> list[AssetRegistration]:
    registrations: list[AssetRegistration] = []
    for item in derivatives:
        with tempfile.NamedTemporaryFile(delete=False) as buffer:
            temporary = Path(buffer.name)
            buffer.write(item.content)
        display = DISPLAY_NAME_SUFFIXES.get(item.name_suffix, item.name_suffix.replace("-", " "))
        try:
            registration = await run_in_threadpool(
                partial(
                    assets.import_managed,
                    asset_id=f"{source.id}.{item.name_suffix}",
                    name=f"{source.name} — {display}",
                    source=temporary,
                    media_type=item.media_type,
                    required=False,
                )
            )
            registrations.append(registration)
        finally:
            temporary.unlink(missing_ok=True)
    return registrations


async def _discard_created_blob(
    workspaces: SQLiteBrandSystemRepository,
    assets: AssetStore,
    registration: AssetRegistration | None,
    created_blob: bool,
) -> None:
    if (
        registration is not None
        and created_blob
        and not await run_in_threadpool(workspaces.references_asset_hash, registration.content_hash)
    ):
        await run_in_threadpool(
            partial(
                assets.discard_managed,
                registration,
                is_referenced=workspaces.references_asset_hash,
            )
        )


async def _load_derivative_source(
    request: Request,
    brand_id: UUID,
    asset_id: str,
    expected_revision: int,
) -> tuple[
    SQLiteBrandSystemRepository,
    AssetStore,
    WorkingDraft,
    AssetRegistration,
    bytes,
]:
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


@router.post(
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
    settings = cast(Settings, request.app.state.settings)
    if not _asset_source_is_allowed(source, settings):
        raise HTTPException(status_code=422, detail="Asset source path is not allowed.")
    try:
        registration = await run_in_threadpool(
            partial(
                assets.register_linked if payload.storage == "linked" else assets.import_managed,
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
    except AssetMissing:
        raise HTTPException(status_code=404, detail="Asset source path does not exist.") from None
    except (AssetChanged, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/api/brand-systems/{brand_id}/asset-uploads",
    response_model=WorkingDraft,
    status_code=201,
    tags=["living brand assets"],
)
async def upload_asset_endpoint(
    brand_id: UUID,
    request: Request,
    expected_revision: int = Form(..., ge=1),
    name: str = Form(..., min_length=1, max_length=300),
    file: UploadFile = File(...),
    required: bool = Form(True),
) -> WorkingDraft:
    workspaces = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    assets = cast(AssetStore, request.app.state.asset_store)
    draft = await run_in_threadpool(workspaces.get, brand_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Brand system not found.")
    if expected_revision != draft.revision:
        raise HTTPException(status_code=409, detail="Draft revision conflict.")
    media_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or ""

    with tempfile.NamedTemporaryFile(delete=False) as buffer:
        temp_path = Path(buffer.name)
        written = 0
        while chunk := await file.read(64 * 1024):
            written += len(chunk)
            if written > assets.max_bytes:
                buffer.close()
                temp_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="Uploaded file is too large.")
            buffer.write(chunk)

    registration: AssetRegistration | None = None
    created_blob = False
    try:
        imported_registration, created_blob = await run_in_threadpool(
            assets.import_managed_with_status,
            asset_id=f"asset.upload.{uuid4().hex}",
            name=name,
            source=temp_path,
            media_type=media_type,
            required=required,
        )
        registration = imported_registration
        return await _append_asset(workspaces, draft, imported_registration)
    except StaleDraftRevision:
        await _discard_created_blob(workspaces, assets, registration, created_blob)
        raise HTTPException(status_code=409, detail="Draft revision conflict.") from None
    except (AssetMissing, AssetChanged, ValidationError, ValueError):
        await _discard_created_blob(workspaces, assets, registration, created_blob)
        raise HTTPException(
            status_code=422, detail="Uploaded file is not an accepted asset type."
        ) from None
    finally:
        temp_path.unlink(missing_ok=True)


@router.post(
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
    workspaces = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    assets = cast(AssetStore, request.app.state.asset_store)
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
            assets.import_managed_with_status,
            asset_id=asset_id,
            name=filename,
            source=temp_path,
            media_type=media_type,
            required=False,
        )
        registration = imported_registration
        current_assets = list(draft.assets)
        current_assets.append(imported_registration)
        payload = draft.model_dump(mode="json")
        payload.update(
            {
                "assets": [item.model_dump(mode="json") for item in current_assets],
                "revision": draft.revision + 1,
            }
        )
        updated = WorkingDraft.model_validate(payload)
        exp_rev = expected_revision if expected_revision is not None else draft.revision
        await run_in_threadpool(workspaces.update, updated, expected_revision=exp_rev)

        asset_url = f"/api/brand-systems/{brand_id}/assets/{imported_registration.content_hash}"
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
            await run_in_threadpool(
                partial(
                    assets.discard_managed,
                    registration,
                    is_referenced=workspaces.references_asset_hash,
                )
            )
        raise HTTPException(
            status_code=409,
            detail="Stale revision: workspace was modified by another operation.",
        ) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        temp_path.unlink(missing_ok=True)


@router.post(
    "/api/brand-systems/{brand_id}/logo/generate",
    response_model=WorkingDraft,
    status_code=201,
    tags=["living brand systems"],
)
@router.post(
    "/api/brand-systems/{brand_id}/logo-generations",
    response_model=WorkingDraft,
    status_code=201,
    tags=["living brand systems"],
)
async def generate_brand_logo(
    brand_id: UUID, payload: GenerateLogoRequest, request: Request
) -> WorkingDraft:
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


@router.get(
    "/api/brand-systems/{brand_id}/assets/{sha_or_id}",
    include_in_schema=False,
)
@router.get(
    "/api/brand-systems/{brand_id}/assets/{sha_or_id}/content",
    include_in_schema=False,
)
async def read_brand_asset(brand_id: UUID, sha_or_id: str, request: Request) -> Response:
    workspaces = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    assets = cast(AssetStore, request.app.state.asset_store)
    draft = await run_in_threadpool(workspaces.get, brand_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Brand system not found.")
    asset = next(
        (item for item in draft.assets if item.id == sha_or_id or item.content_hash == sha_or_id),
        None,
    )
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found.")
    try:
        content = await run_in_threadpool(assets.read, asset)
    except AssetChanged:
        raise HTTPException(status_code=409, detail="Asset integrity breach.") from None
    except (AssetMissing, ValueError):
        raise HTTPException(status_code=404, detail="Asset content unavailable.") from None
    return asset_response(content, asset.media_type)


@router.post(
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


@router.post(
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


@router.post(
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
