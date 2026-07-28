"""Shared HTTP response policies."""

from fastapi.responses import Response

BROWSER_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self'; connect-src 'self'; base-uri 'none'; "
        "form-action 'self'; frame-ancestors 'none'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
}


def static_response(content: str, media_type: str) -> Response:
    return Response(
        content,
        media_type=media_type,
        headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"},
    )


def asset_response(content: bytes, media_type: str) -> Response:
    """Serve untrusted asset bytes with one consistent browser security policy."""

    return Response(
        content,
        media_type=media_type,
        headers={
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        },
    )
