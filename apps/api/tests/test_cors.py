"""CORS: browser clients (Expo web) must get cross-origin allow headers."""

from fastapi.testclient import TestClient

from lull_api.main import app

client = TestClient(app)
ORIGIN = "http://localhost:8081"  # Expo web dev origin


def test_preflight_options_allows_cross_origin_post():
    r = client.options(
        "/script",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "*"


def test_actual_request_carries_allow_origin_header():
    r = client.post("/script", json={"hypnosis": True}, headers={"Origin": ORIGIN})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "*"
