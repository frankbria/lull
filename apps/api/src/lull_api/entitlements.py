"""Entitlement seam + generation-credit counter (FR-A5).

Free at launch: has_access() grants everything and record_generation() counts but never blocks.
ponytail: the seam is a function + two tables, not a billing engine.
Upgrade path when paid tiers land — has_access checks Entitlement rows / the user's plan, and
record_generation raises / returns False once `used` hits the plan's monthly cap.
"""

from __future__ import annotations

import uuid

from sqlalchemy import update
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


def reserve_guest_generation(db: Session, guest_id: uuid.UUID) -> bool:
    """Atomically claim a guest generation BEFORE the billable synth. Returns True if the claim is
    within the free allowance, else False (caller rejects). The atomic upsert means two concurrent
    first-requests can't both pass — one gets used=1 (True), the other used=2 (False). Pair with
    release_guest_generation on synth failure so a failed render doesn't burn the credit."""
    stmt = (
        pg_insert(GuestCredit)
        .values(guest_id=guest_id, used=1)
        .on_conflict_do_update(
            index_elements=[GuestCredit.guest_id],
            set_={"used": GuestCredit.used + 1},
        )
        .returning(GuestCredit.used)
    )
    return db.execute(stmt).scalar_one() <= GUEST_FREE_GENERATIONS


def release_guest_generation(db: Session, guest_id: uuid.UUID) -> None:
    """Give back a reserved guest generation (synth failed). Floors at 0 so it can't go negative."""
    db.execute(
        update(GuestCredit)
        .where(GuestCredit.guest_id == guest_id, GuestCredit.used > 0)
        .values(used=GuestCredit.used - 1)
    )
