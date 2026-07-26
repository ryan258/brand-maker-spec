"""HTTP endpoints for artifact compliance records and campaigns."""

from functools import partial
from typing import cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from brand_maker.brand_system.publication import SQLitePublicationRepository
from brand_maker.compliance.campaigns import (
    CampaignResult,
    CampaignService,
    CreateCampaignRequest,
)
from brand_maker.compliance.copy_checker import deterministic_copy_rules
from brand_maker.compliance.deterministic import evaluate_artifact
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
    DeterministicRule,
    EvaluateArtifactRequest,
)
from brand_maker.compliance.repository import SQLiteComplianceRepository

router = APIRouter()


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
