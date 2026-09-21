from __future__ import annotations

from pathlib import Path

from store_parity.models import TaskStatus
from store_parity.state import TaskStateStore


def test_sqlite_resume_preserves_completed_and_requeues_running(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite3"
    state = TaskStateStore(database)
    assert (
        state.add_tasks(
            [
                ("capture:a", "capture", {"path": "/a"}, 10),
                ("capture:b", "capture", {"path": "/b"}, 20),
            ]
        )
        == 2
    )

    first = state.claim_next()
    assert first is not None
    assert first.id == "capture:a"
    assert first.status is TaskStatus.RUNNING
    state.finish(first.id, TaskStatus.SUCCEEDED)

    second = state.claim_next()
    assert second is not None
    assert second.id == "capture:b"
    assert second.attempts == 1

    resumed = TaskStateStore(database)
    assert resumed.prepare_resume() == 1
    assert resumed.get_task("capture:a").status is TaskStatus.SUCCEEDED  # type: ignore[union-attr]
    pending = resumed.get_task("capture:b")
    assert pending is not None
    assert pending.status is TaskStatus.PENDING
    assert pending.attempts == 1

    reclaimed = resumed.claim_next()
    assert reclaimed is not None
    assert reclaimed.id == "capture:b"
    assert reclaimed.attempts == 2

    resumed.requeue(reclaimed.id, error="transient navigation failure")
    retried = resumed.claim_next()
    assert retried is not None
    assert retried.id == "capture:b"
    assert retried.attempts == 3
    assert retried.last_error == "transient navigation failure"
