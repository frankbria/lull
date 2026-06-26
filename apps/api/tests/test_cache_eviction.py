"""Audio cache eviction/quota — issue #51.

`audio_store/` is a content-addressed dedup cache that otherwise grows unbounded. An on-write LRU
sweep keeps total bytes under LULL_AUDIO_STORE_MAX_BYTES by deleting the oldest (least-recently-used,
by mtime) files first. The store dir is isolated per test by the autouse `isolated_audio_store`
fixture.
"""

from __future__ import annotations

import os
from pathlib import Path

from lull_api.persistence import evict_audio_store, store_audio


def _write(d: Path, name: str, size: int, mtime: float) -> Path:
    p = d / name
    p.write_bytes(b"x" * size)
    os.utime(p, (mtime, mtime))
    return p


def test_evict_removes_oldest_until_under_quota(tmp_path):
    d = tmp_path
    old = _write(d, "a.wav", 100, mtime=1_000)
    mid = _write(d, "b.wav", 100, mtime=2_000)
    new = _write(d, "c.wav", 100, mtime=3_000)  # total 300

    evict_audio_store(str(d), max_bytes=150)  # room for ~1 file

    # Oldest go first; the newest survives, total is under the cap.
    assert not old.exists()
    assert not mid.exists()
    assert new.exists()
    assert sum(f.stat().st_size for f in d.glob("*.wav")) <= 150


def test_evict_keeps_all_when_under_quota(tmp_path):
    d = tmp_path
    a = _write(d, "a.wav", 100, mtime=1_000)
    b = _write(d, "b.wav", 100, mtime=2_000)
    evict_audio_store(str(d), max_bytes=1_000)
    assert a.exists() and b.exists()


def test_evict_disabled_when_max_bytes_not_positive(tmp_path):
    d = tmp_path
    a = _write(d, "a.wav", 100, mtime=1_000)
    b = _write(d, "b.wav", 100, mtime=2_000)
    evict_audio_store(str(d), max_bytes=0)  # disabled
    evict_audio_store(str(d), max_bytes=-1)
    assert a.exists() and b.exists()


def test_evict_tolerates_missing_dir(tmp_path):
    evict_audio_store(str(tmp_path / "nope"), max_bytes=10)  # must not raise


def test_store_audio_evicts_when_over_quota(tmp_path):
    d = str(tmp_path)
    # Each write is 50 bytes; cap at 120 → at most 2 files survive.
    for i in range(5):
        store_audio(b"y" * 50, f"sum{i}", "wav", d, max_bytes=120)
    total = sum(f.stat().st_size for f in Path(d).glob("*.wav"))
    assert total <= 120
    # The most recent write must survive (it's the freshest by mtime).
    assert (Path(d) / "sum4.wav").exists()
