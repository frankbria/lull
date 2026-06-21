"""Data-model integrity against real Postgres: PKs default, FKs cascade, relationships wire up."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from lull_api.models import (
    AudioFile,
    Entitlement,
    GenerationCredit,
    MusicBed,
    SessionLog,
    Track,
    TrackComponent,
    User,
)


def _user(db, email="a@b.co"):
    u = User(email=email, age_verified=True)
    db.add(u)
    db.flush()
    return u


def test_uuid_pk_and_defaults(db):
    u = _user(db)
    assert isinstance(u.id, uuid.UUID)  # server_default gen_random_uuid() populated on flush
    assert u.password_hash is None  # OAuth-style account: no local password yet
    assert u.created_at is not None


def test_track_graph_and_relationships(db):
    u = _user(db)
    track = Track(user_id=u.id, spec={"hypnosis": True}, status="ready")
    db.add(track)
    db.flush()
    track.components.append(TrackComponent(category="induction", choice="fixation", ai_chosen=True))
    track.audio_files.append(
        AudioFile(path="/c/x.wav", checksum="deadbeef", duration_seconds=90.0, source="stub")
    )
    db.flush()

    fetched = db.scalar(select(Track).where(Track.id == track.id))
    assert fetched.user.email == "a@b.co"
    assert fetched.components[0].choice == "fixation"
    assert fetched.audio_files[0].source == "stub"


def test_track_requires_existing_user(db):
    bogus = Track(user_id=uuid.uuid4(), spec={}, status="draft")
    db.add(bogus)
    with pytest.raises(IntegrityError):  # FK to a non-existent user is rejected
        db.flush()


def test_cascade_delete_user_removes_tracks(db):
    u = _user(db)
    db.add(Track(user_id=u.id, spec={}, status="draft"))
    db.flush()
    db.delete(u)
    db.flush()
    assert db.scalars(select(Track).where(Track.user_id == u.id)).first() is None


def test_session_log_music_bed_entitlement_credit(db):
    u = _user(db)
    track = Track(user_id=u.id, spec={}, status="ready")
    db.add(track)
    db.flush()
    db.add_all(
        [
            SessionLog(user_id=u.id, track_id=track.id, position_seconds=42.0, partial=True),
            MusicBed(path="/beds/rain.wav", tags=["calm", "rain"], loop_end_seconds=30.0),
            Entitlement(user_id=u.id, feature="music_beds", granted=True),
            GenerationCredit(user_id=u.id, used=0),
        ]
    )
    db.flush()
    bed = db.scalar(select(MusicBed))
    assert bed.tags == ["calm", "rain"]
    assert db.scalar(select(SessionLog)).position_seconds == 42.0
