"""Test fixtures backed by a REAL Postgres (docker-compose), no mocks.

Start it once: docker compose -f apps/api/docker-compose.yml up -d
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from lull_api.db import Base
from lull_api import models  # noqa: F401  — register tables on Base.metadata

TEST_DB_URL = "postgresql+psycopg://lull:lull@localhost:5432/lull_test"


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
