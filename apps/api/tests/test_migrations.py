"""Alembic migrations apply and reverse cleanly against a real Postgres (lull_migtest)."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

MIGTEST_URL = "postgresql+psycopg://lull:lull@localhost:5432/lull_migtest"
API_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_TABLES = {
    "users",
    "tracks",
    "track_components",
    "audio_files",
    "session_logs",
    "music_beds",
    "entitlements",
    "generation_credits",
}


@pytest.fixture
def alembic_cfg():
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", MIGTEST_URL)  # env.py honors an explicit override
    eng = create_engine(MIGTEST_URL, future=True)
    with eng.begin() as conn:  # start from a clean slate regardless of prior runs
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    eng.dispose()
    return cfg


def test_upgrade_creates_all_tables_then_downgrade_removes_them(alembic_cfg):
    command.upgrade(alembic_cfg, "head")
    eng = create_engine(MIGTEST_URL, future=True)
    tables = set(inspect(eng).get_table_names())
    assert EXPECTED_TABLES <= tables  # all 8 domain tables present after upgrade

    command.downgrade(alembic_cfg, "base")
    remaining = set(inspect(eng).get_table_names())
    eng.dispose()
    assert remaining & EXPECTED_TABLES == set()  # downgrade leaves no domain tables behind
