"""Test fixtures backed by a REAL Postgres (docker-compose), no mocks.

Start it once: docker compose -f apps/api/docker-compose.yml up -d
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from lull_api.config import settings
from lull_api.db import Base, get_db
from lull_api.main import app
from lull_api import models  # noqa: F401  — register tables on Base.metadata

TEST_DB_URL = "postgresql+psycopg://lull:lull@localhost:5432/lull_test"


@pytest.fixture(autouse=True)
def isolated_audio_store(tmp_path, monkeypatch):
    """Give each test a fresh on-disk audio cache dir, so the content-addressed dedup cache (US-008)
    never leaks a render between tests and never writes into the repo."""
    monkeypatch.setattr(settings, "audio_store_dir", str(tmp_path / "audio_store"))


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DB_URL, future=True)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def db(engine) -> Iterator[Session]:
    """Each test runs in a transaction that is rolled back — full isolation, no cross-test bleed."""
    conn = engine.connect()
    txn = conn.begin()
    # create_savepoint: a failed flush (e.g. FK violation) rolls back a SAVEPOINT, leaving the
    # outer transaction intact for a clean teardown rollback.
    session = sessionmaker(
        bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )()
    try:
        yield session
    finally:
        session.close()
        txn.rollback()
        conn.close()


@pytest.fixture
def client(db) -> Iterator[TestClient]:
    """TestClient whose get_db yields the rolled-back test session, so endpoint writes (commits
    included) hit the test DB inside the per-test transaction and never persist."""
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
