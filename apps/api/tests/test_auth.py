"""Email/password signup + login, the 18+ age gate, and the current_user dependency."""

from __future__ import annotations


def _signup(client, email="user@example.com", password="hunter2hunter", age=True):
    return client.post(
        "/auth/signup",
        json={"email": email, "password": password, "age_confirmed": age},
    )


def test_signup_returns_token_and_sets_age_verified(client):
    r = _signup(client)
    assert r.status_code == 201
    token = r.json()["access_token"]
    assert token

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"
    assert me.json()["age_verified"] is True


def test_signup_blocks_under_18(client):
    r = _signup(client, age=False)
    assert r.status_code == 422


def test_signup_rejects_short_password(client):
    r = _signup(client, password="short")
    assert r.status_code == 422


def test_signup_duplicate_email_conflicts(client):
    assert _signup(client).status_code == 201
    assert _signup(client).status_code == 409  # same email again


def test_signup_normalizes_email_case(client):
    assert _signup(client, email="Mixed@Example.com").status_code == 201
    # Different case is the same account → conflict, not a second user.
    assert _signup(client, email="mixed@example.com").status_code == 409


def test_login_succeeds_then_rejects_bad_password(client):
    _signup(client)
    ok = client.post("/auth/login", json={"email": "user@example.com", "password": "hunter2hunter"})
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = client.post("/auth/login", json={"email": "user@example.com", "password": "nope"})
    assert bad.status_code == 401


def test_login_unknown_email_is_401(client):
    r = client.post("/auth/login", json={"email": "ghost@example.com", "password": "whatever12"})
    assert r.status_code == 401


def test_me_requires_valid_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
