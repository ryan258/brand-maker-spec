import sys

import pytest

from brand_maker.__main__ import main, validate_bind_host


@pytest.mark.parametrize("host", ["127.0.0.1", "127.12.34.56", "::1", "localhost"])
def test_validate_bind_host_accepts_loopback(host: str) -> None:
    validate_bind_host(host, allow_network_bind=False)


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.168.1.20", "example.test"])
def test_validate_bind_host_rejects_non_loopback_without_explicit_opt_in(host: str) -> None:
    with pytest.raises(ValueError, match="non-loopback"):
        validate_bind_host(host, allow_network_bind=False)


def test_validate_bind_host_accepts_explicit_network_opt_in() -> None:
    validate_bind_host("0.0.0.0", allow_network_bind=True)


def test_main_reports_refused_bind_as_a_usage_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["brand-maker", "--host", "0.0.0.0"])

    with pytest.raises(SystemExit) as stopped:
        main()

    assert stopped.value.code == 2
    error = capsys.readouterr().err
    assert "error: Refusing non-loopback bind" in error
    assert "Traceback" not in error
