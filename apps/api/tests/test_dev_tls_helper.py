"""The dev-TLS helper (#54) lets a standalone Android APK reach the dev API. The device reaches it
*through* `tailscale serve` (TLS, since a release APK blocks cleartext), and `tailscale serve`
proxies to uvicorn on loopback — so uvicorn must bind 127.0.0.1, NOT 0.0.0.0 (0.0.0.0 would expose
the API in cleartext on every other interface, behind the TLS front). We assert the `--check`
dry-run, which prints the exact commands without executing them — so no Tailscale/uvicorn in CI."""

from __future__ import annotations

import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "dev-tls.sh"


def _check_output() -> str:
    res = subprocess.run(
        ["bash", str(SCRIPT), "--check"], capture_output=True, text=True, timeout=10
    )
    assert res.returncode == 0, res.stderr
    return res.stdout


def test_binds_loopback_behind_the_tls_front():
    out = _check_output()
    assert "--host 127.0.0.1" in out  # tailscale serve proxies to loopback; reach it via the front
    assert "--host 0.0.0.0" not in out  # never expose the API in cleartext on other interfaces
    assert "--port 8000" in out


def test_fronts_the_api_port_with_tailscale_serve_tls():
    out = _check_output()
    assert "tailscale serve" in out
    assert "8000" in out
