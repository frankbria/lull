"""Entitlement seam: free-at-launch access + generation-credit counter (FR-A5)."""

from __future__ import annotations

from sqlalchemy import select

from lull_api.entitlements import has_access, record_generation
from lull_api.models import GenerationCredit, User


def _user(db):
    u = User(email="c@d.co", age_verified=True)
    db.add(u)
    db.flush()
    return u


def test_has_access_grants_everything_at_launch(db):
    u = _user(db)
    assert has_access(db, u.id, "music_beds") is True
    assert has_access(db, u.id, "unlimited_generation") is True
    assert has_access(db, u.id, "anything-at-all") is True


def test_record_generation_creates_and_increments_counter(db):
    u = _user(db)
    assert record_generation(db, u.id) == 1  # lazily creates the row
    assert record_generation(db, u.id) == 2
    assert record_generation(db, u.id) == 3
    credit = db.scalar(select(GenerationCredit).where(GenerationCredit.user_id == u.id))
    assert credit.used == 3
