"""Shared bounded request-body streaming for archive-style uploads."""

import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import HTTPException, Request


@asynccontextmanager
async def bounded_request_file(
    request: Request,
    *,
    max_bytes: int,
    suffix: str,
    limit_detail: str,
    empty_detail: str | None = None,
) -> AsyncIterator[Path]:
    """Stream one request body to a temporary file without exceeding its limit."""

    declared = request.headers.get("content-length")
    if declared is not None:
        try:
            declared_size = int(declared)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Content-Length.") from None
        if declared_size > max_bytes:
            raise HTTPException(status_code=413, detail=limit_detail)

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
        temp_path = Path(temporary.name)
    try:
        observed = 0
        with temp_path.open("wb") as temporary:
            async for chunk in request.stream():
                observed += len(chunk)
                if observed > max_bytes:
                    raise HTTPException(status_code=413, detail=limit_detail)
                temporary.write(chunk)
        if observed == 0 and empty_detail is not None:
            raise HTTPException(status_code=422, detail=empty_detail)
        yield temp_path
    finally:
        temp_path.unlink(missing_ok=True)
