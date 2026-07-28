"""HTTP endpoints for artifact compliance records and campaigns."""

from functools import partial
from typing import cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from brand_maker.brand_system.assets import AssetStore
from brand_maker.brand_system.publication import SQLitePublicationRepository
from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
from brand_maker.compliance.campaigns import (
    CampaignResult,
    CampaignService,
    CreateCampaignRequest,
)
from brand_maker.compliance.copy_checker import (
    check_copy_against_brand_rules,
    deterministic_copy_rules,
)
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
    CopyCheckReport,
    CopyCheckRequest,
    DeterministicRule,
    EvaluateArtifactRequest,
)
from brand_maker.compliance.repository import SQLiteComplianceRepository
from brand_maker.logo_derivatives import RASTER_MEDIA_TYPES, check_logo_contrast_against_backgrounds

router = APIRouter()


@router.post(
    "/api/brand-systems/{brand_id}/compliance/check-copy",
    response_model=CopyCheckReport,
    tags=["brand compliance"],
)
async def check_copy_compliance(
    brand_id: UUID,
    payload: CopyCheckRequest,
    request: Request,
) -> CopyCheckReport:
    workspaces = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    draft = await run_in_threadpool(workspaces.get, brand_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    return check_copy_against_brand_rules(payload.copy_text, draft)


@router.get(
    "/api/brand-systems/{brand_id}/token-collisions",
    tags=["brand compliance"],
)
async def get_token_collisions(
    brand_id: UUID,
    request: Request,
) -> dict[str, object]:
    workspaces = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    draft = await run_in_threadpool(workspaces.get, brand_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    findings = audit_token_collisions(draft.sections)
    return {"collisions": [f.model_dump(mode="json") for f in findings]}


@router.get(
    "/api/brand-systems/{brand_id}/wcag-audit",
    tags=["brand compliance"],
)
async def get_wcag_token_audit(
    brand_id: UUID,
    request: Request,
) -> dict[str, object]:
    workspaces = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    draft = await run_in_threadpool(workspaces.get, brand_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    findings = audit_token_contrast_pairs(draft.sections)
    return {"findings": [f.model_dump(mode="json") for f in findings]}


@router.get(
    "/api/brand-systems/{brand_id}/logo-contrast-check",
    tags=["brand compliance"],
)
async def check_logo_contrast_route(
    brand_id: UUID,
    request: Request,
) -> dict[str, object]:
    workspaces = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
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


@router.get(
    "/api/brand-systems/{brand_id}/versions/{version}/compliance-rules",
    response_model=list[DeterministicRule],
    tags=["brand compliance"],
)
async def get_published_compliance_rules(
    brand_id: UUID, version: str, request: Request
) -> list[DeterministicRule]:
    publications = cast(SQLitePublicationRepository, request.app.state.publication_repository)
    published = await run_in_threadpool(publications.get, brand_id, version)
    if published is None:
        raise HTTPException(status_code=404, detail="Published version not found.")
    return deterministic_copy_rules(published.snapshot)


@router.post(
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


@router.post(
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
            tool_version=request.app.version,
        )
    )
    return await run_in_threadpool(store.save_evaluation, evaluation)


@router.post(
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


@router.get(
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


@router.post(
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
        raise HTTPException(status_code=422, detail="Renewal must extend the expiration.") from None


@router.post(
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


@router.post(
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


@router.get(
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
