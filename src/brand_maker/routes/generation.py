"""HTTP endpoints for resumable living-brand generation."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from functools import partial
from typing import cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from brand_maker.brand_system.repository import SQLiteBrandSystemRepository
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

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
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
    settings = cast(Settings, request.app.state.settings)
    draft = await run_in_threadpool(workspaces.get, brand_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Brand system not found.")
    try:
        return await run_in_threadpool(
            partial(
                orchestrator.start,
                draft,
                target_section_id=payload.target_section_id,
                model=settings.primary_model,
                fallback_model=settings.fallback_model,
            )
        )
    except ValueError:
        raise HTTPException(status_code=422, detail="Unknown generation section.") from None


@router.get(
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


@router.post(
    "/api/generation-runs/{run_id}/resume",
    response_model=GenerationRun,
    status_code=202,
    tags=["living brand generation"],
)
async def resume_generation_run(run_id: UUID, request: Request) -> GenerationRun:
    orchestrator = cast(GenerationOrchestrator, request.app.state.generation_orchestrator)
    runs = cast(SQLiteGenerationRepository, request.app.state.generation_repository)
    completer = cast(Completer | None, request.app.state.generation_completer)
    if completer is None:
        raise HTTPException(status_code=503, detail="Generation provider unavailable.")
    run = await run_in_threadpool(runs.get, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Generation run not found.")

    tasks = cast(dict[UUID, asyncio.Task[GenerationRun]], request.app.state.generation_tasks)
    existing = tasks.get(run_id)
    if existing is not None and not existing.done():
        return run

    task = asyncio.create_task(orchestrator.resume(run_id, completer=completer))
    tasks[run_id] = task

    def finish_generation(completed: asyncio.Task[GenerationRun]) -> None:
        if tasks.get(run_id) is completed:
            tasks.pop(run_id)
        try:
            completed.result()
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("generation run %s stopped unexpectedly", run_id)

    task.add_done_callback(finish_generation)
    return run


async def _control_generation_run(run_id: UUID, request: Request, command: str) -> GenerationRun:
    orchestrator = cast(GenerationOrchestrator, request.app.state.generation_orchestrator)
    try:
        operation = orchestrator.pause if command == "pause" else orchestrator.cancel
        return await run_in_threadpool(operation, run_id)
    except GenerationRunNotFound:
        raise HTTPException(status_code=404, detail="Generation run not found.") from None


@router.post(
    "/api/generation-runs/{run_id}/pause",
    response_model=GenerationRun,
    tags=["living brand generation"],
)
async def pause_generation_run(run_id: UUID, request: Request) -> GenerationRun:
    return await _control_generation_run(run_id, request, "pause")


@router.post(
    "/api/generation-runs/{run_id}/cancel",
    response_model=GenerationRun,
    tags=["living brand generation"],
)
async def cancel_generation_run(run_id: UUID, request: Request) -> GenerationRun:
    return await _control_generation_run(run_id, request, "cancel")


@router.get(
    "/api/generation-runs/{run_id}/stream",
    tags=["living brand generation"],
)
async def stream_generation_run(run_id: UUID, request: Request) -> StreamingResponse:
    orchestrator = cast(GenerationOrchestrator, request.app.state.generation_orchestrator)
    try:
        queue = await run_in_threadpool(
            partial(
                orchestrator.subscribe,
                run_id,
                event_loop=asyncio.get_running_loop(),
            )
        )
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
        headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"},
    )


@router.post(
    "/api/brand-systems/{brand_id}/sections/{section_id}/fields/regenerate",
    tags=["living brand generation"],
)
async def regenerate_section_field(
    brand_id: UUID,
    section_id: str,
    payload: RegenerateFieldRequest,
    request: Request,
) -> dict[str, str]:
    workspaces = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    orchestrator = cast(GenerationOrchestrator, request.app.state.generation_orchestrator)
    completer = cast(Completer | None, request.app.state.generation_completer)
    if completer is None:
        raise HTTPException(status_code=503, detail="Generation provider unavailable.")
    draft = await run_in_threadpool(workspaces.get, brand_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    settings = cast(Settings, request.app.state.settings)
    return await orchestrator.regenerate_field(
        draft=draft,
        section_id=section_id,
        field_label=payload.field_label,
        current_text=payload.current_text,
        instruction=payload.instruction,
        model=payload.model or settings.primary_model,
        completer=completer,
    )


@router.post(
    "/api/brand-systems/{brand_id}/sections/{section_id}/variants",
    tags=["living brand generation"],
)
async def generate_section_variants(
    brand_id: UUID,
    section_id: str,
    payload: GenerateSectionVariantsRequest,
    request: Request,
) -> dict[str, list[dict[str, object]]]:
    workspaces = cast(SQLiteBrandSystemRepository, request.app.state.brand_system_repository)
    orchestrator = cast(GenerationOrchestrator, request.app.state.generation_orchestrator)
    completer = cast(Completer | None, request.app.state.generation_completer)
    if completer is None:
        raise HTTPException(status_code=503, detail="Generation provider unavailable.")
    draft = await run_in_threadpool(workspaces.get, brand_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    settings = cast(Settings, request.app.state.settings)
    variants = await orchestrator.generate_section_variants(
        draft=draft,
        section_id=section_id,
        postures=payload.postures,
        model=payload.model or settings.primary_model,
        completer=completer,
    )
    return {"variants": variants}
