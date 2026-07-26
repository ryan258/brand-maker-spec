"""Run the API with Uvicorn."""

import argparse
import ipaddress

import uvicorn


def validate_bind_host(host: str, *, allow_network_bind: bool) -> None:
    """Require an explicit opt-in before exposing this unauthenticated local app."""

    if allow_network_bind or host == "localhost":
        return
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is None or not address.is_loopback:
        raise ValueError(
            "Refusing non-loopback bind for an unauthenticated local app; "
            "pass --allow-network-bind only behind an access-control gate."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Brand System Maker API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument(
        "--allow-network-bind",
        action="store_true",
        help="Allow a non-loopback bind; use only behind an authentication gate.",
    )
    args = parser.parse_args()
    try:
        validate_bind_host(args.host, allow_network_bind=args.allow_network_bind)
    except ValueError as error:
        parser.error(str(error))
    uvicorn.run(
        "brand_maker.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
