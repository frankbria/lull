"""Initial data model (ARCHITECTURE.md §Data model).

UUID PKs (Postgres gen_random_uuid()) so client-facing ids aren't enumerable and inserts need no
round-trip to learn the id. Auth columns on User exist now but carry no auth logic yet — the
signup/login/OAuth slice (Authlib/passlib/JWT) lands in a follow-up issue.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = _pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    # Nullable: OAuth-only accounts have no local password. Auth slice fills this in.
    password_hash: Mapped[str | None] = mapped_column(String(255), default=None)
    age_verified: Mapped[bool] = mapped_column(Boolean, default=False)  # 18+ gate (enforced later)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tracks: Mapped[list[Track]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Track(Base):
    __tablename__ = "tracks"
    # Lets SessionLog reference (track_id, user_id) so a log can't pair a track with a non-owner.
    __table_args__ = (UniqueConstraint("id", "user_id", name="uq_tracks_id_user"),)

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    spec: Mapped[dict] = mapped_column(JSONB)  # the TrackSpec the track was generated from
    status: Mapped[str] = mapped_column(
        String(32), default="draft"
    )  # draft|generating|ready|failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="tracks")
    components: Mapped[list[TrackComponent]] = relationship(
        back_populates="track", cascade="all, delete-orphan"
    )
    audio_files: Mapped[list[AudioFile]] = relationship(
        back_populates="track", cascade="all, delete-orphan"
    )


class TrackComponent(Base):
    __tablename__ = "track_components"

    id: Mapped[uuid.UUID] = _pk()
    track_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(32))  # induction|deepener|body|ending
    choice: Mapped[str] = mapped_column(String(64))  # resolved choice (never "ai")
    ai_chosen: Mapped[bool] = mapped_column(Boolean, default=False)  # was this an "ai" pick?

    track: Mapped[Track] = relationship(back_populates="components")


class AudioFile(Base):
    __tablename__ = "audio_files"

    id: Mapped[uuid.UUID] = _pk()
    track_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"))
    path: Mapped[str] = mapped_column(Text)
    checksum: Mapped[str] = mapped_column(String(64), index=True)  # identical scripts cache-serve
    duration_seconds: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(32))  # AudioSource impl: elevenlabs|stub|music_bed

    track: Mapped[Track] = relationship(back_populates="audio_files")


class SessionLog(Base):
    __tablename__ = "session_logs"
    # Composite FK enforces account scoping: the (track_id, user_id) pair must match a real
    # track owned by that user — a session log can't point at someone else's track.
    __table_args__ = (
        ForeignKeyConstraint(
            ["track_id", "user_id"],
            ["tracks.id", "tracks.user_id"],
            ondelete="CASCADE",
        ),
    )

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    track_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True)
    )  # half of the composite FK above
    position_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    partial: Mapped[bool] = mapped_column(Boolean, default=True)  # finished the track?
    rating: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MusicBed(Base):
    __tablename__ = "music_beds"

    id: Mapped[uuid.UUID] = _pk()
    path: Mapped[str] = mapped_column(Text)
    tags: Mapped[list] = mapped_column(JSONB, default=list)  # mood/context tags — data, not code
    loop_start_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    loop_end_seconds: Mapped[float | None] = mapped_column(Float, default=None)


class Entitlement(Base):
    __tablename__ = "entitlements"

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    feature: Mapped[str] = mapped_column(String(64))  # e.g. "music_beds", "unlimited_generation"
    granted: Mapped[bool] = mapped_column(Boolean, default=True)


class GenerationCredit(Base):
    __tablename__ = "generation_credits"

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    used: Mapped[int] = mapped_column(Integer, default=0)  # generations consumed (counter)


class GuestCredit(Base):
    """Pre-account free generations (FR-A2). Keyed on a client-supplied device UUID (X-Guest-Id),
    so a guest gets a fixed free allowance before being prompted to sign up."""

    __tablename__ = "guest_credits"

    id: Mapped[uuid.UUID] = _pk()
    guest_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, index=True)
    used: Mapped[int] = mapped_column(Integer, default=0)
