"""Entitlement seam + generation-credit counter (FR-A5).

Free at launch: has_access() grants everything and record_generation() counts but never blocks.
ponytail: the seam is a function + two tables, not a billing engine.
Upgrade path when paid tiers land — has_access checks Entitlement rows / the user's plan, and
record_generation raises / returns False once `used` hits the plan's monthly cap.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from .models import GenerationCredit, GuestCredit

# Free generations a guest gets before being prompted to create an account (FR-A2).
GUEST_FREE_GENERATIONS = 1


def has_access(db: Session, user_id: uuid.UUID, feature: str) -> bool:
    """Whether the user may use `feature`. Free at launch → always True."""
    return True


def record_generation(db: Session, user_id: uuid.UUID) -> int:
    """Increment the user's generation counter; return the new total. Never blocks at launch.

    Single atomic upsert (INSERT ... ON CONFLICT DO UPDATE ... RETURNING) so concurrent requests
    for the same user can't lose a count or race on the unique user_id constraint.
    """
    stmt = (
        pg_insert(GenerationCredit)
        .values(user_id=user_id, used=1)
        .on_conflict_do_update(
            index_elements=[GenerationCredit.user_id],
            set_={"used": GenerationCredit.used + 1},
        )
        .returning(GenerationCredit.used)
    )
    return db.execute(stmt).scalar_one()


def guest_within_limit(db: Session, guest_id: uuid.UUID) -> bool:
    """Whether this guest still has a free generation left. Read-only — call BEFORE the billable
    synth so a failed render doesn't burn the credit; record_guest_generation commits it after."""
    used = db.scalar(select(GuestCredit.used).where(GuestCredit.guest_id == guest_id)) or 0
    return used < GUEST_FREE_GENERATIONS


def record_guest_generation(db: Session, guest_id: uuid.UUID) -> int:
    """Increment the guest's counter after a successful generation; return the new total. Atomic
    upsert (same pattern as record_generation) so concurrent requests can't lose a count."""
    stmt = (
        pg_insert(GuestCredit)
        .values(guest_id=guest_id, used=1)
        .on_conflict_do_update(
            index_elements=[GuestCredit.guest_id],
            set_={"used": GuestCredit.used + 1},
        )
        .returning(GuestCredit.used)
    )
    return db.execute(stmt).scalar_one()
