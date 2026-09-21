from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

from store_parity.models import Artifact, ArtifactKind, TaskStatus, isoformat, utc_now


SCHEMA_VERSION = 1
TERMINAL_TASK_STATUSES = {
    TaskStatus.SUCCEEDED,
    TaskStatus.FAILED,
    TaskStatus.SKIPPED,
}


class StateError(RuntimeError):
    """Raised when a state transition or registry operation is invalid."""


@dataclass(frozen=True, slots=True)
class Task:
    id: str
    kind: str
    status: TaskStatus
    payload: Mapping[str, Any]
    priority: int
    attempts: int
    last_error: str | None


class TaskStateStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        try:
            yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 100,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    last_error TEXT,
                    CHECK (status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'SKIPPED'))
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_claim
                    ON tasks(status, priority, id);
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    relative_path TEXT NOT NULL UNIQUE,
                    media_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );
                """
            )
            current = connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
            if current is None:
                connection.execute(
                    "INSERT INTO metadata(key, value) VALUES ('schema_version', ?)",
                    (str(SCHEMA_VERSION),),
                )
            elif int(current["value"]) != SCHEMA_VERSION:
                raise StateError(f"unsupported state schema version: {current['value']}")
            connection.commit()

    def add_tasks(self, tasks: Iterable[tuple[str, str, Mapping[str, Any], int]]) -> int:
        created_at = isoformat(utc_now())
        inserted = 0
        with self._connect() as connection:
            for task_id, kind, payload, priority in tasks:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO tasks(
                        id, kind, status, payload_json, priority, created_at
                    ) VALUES (?, ?, 'PENDING', ?, ?, ?)
                    """,
                    (
                        task_id,
                        kind,
                        json.dumps(payload, sort_keys=True, separators=(",", ":")),
                        priority,
                        created_at,
                    ),
                )
                inserted += cursor.rowcount
            connection.commit()
        return inserted

    def prepare_resume(self, *, retry_failed: bool = False) -> int:
        statuses = [TaskStatus.RUNNING.value]
        if retry_failed:
            statuses.append(TaskStatus.FAILED.value)
        placeholders = ",".join("?" for _ in statuses)
        with self._connect() as connection:
            cursor = connection.execute(
                f"""
                UPDATE tasks
                SET status = 'PENDING',
                    started_at = NULL,
                    completed_at = NULL,
                    last_error = CASE
                        WHEN status = 'RUNNING' THEN 'interrupted before completion'
                        ELSE last_error
                    END
                WHERE status IN ({placeholders})
                """,
                statuses,
            )
            connection.commit()
            return cursor.rowcount

    def claim_next(self, *, kind: str | None = None) -> Task | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if kind is None:
                row = connection.execute(
                    """
                    SELECT * FROM tasks
                    WHERE status = 'PENDING'
                    ORDER BY priority, id
                    LIMIT 1
                    """
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT * FROM tasks
                    WHERE status = 'PENDING' AND kind = ?
                    ORDER BY priority, id
                    LIMIT 1
                    """,
                    (kind,),
                ).fetchone()
            if row is None:
                connection.commit()
                return None

            connection.execute(
                """
                UPDATE tasks
                SET status = 'RUNNING', attempts = attempts + 1, started_at = ?
                WHERE id = ? AND status = 'PENDING'
                """,
                (isoformat(utc_now()), row["id"]),
            )
            claimed = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (row["id"],)
            ).fetchone()
            connection.commit()
            return self._task_from_row(claimed)

    def finish(
        self,
        task_id: str,
        status: TaskStatus,
        *,
        error: str | None = None,
    ) -> None:
        if status not in TERMINAL_TASK_STATUSES:
            raise StateError(f"task may not finish with status {status.value}")
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE tasks
                SET status = ?, completed_at = ?, last_error = ?
                WHERE id = ? AND status = 'RUNNING'
                """,
                (status.value, isoformat(utc_now()), error, task_id),
            )
            if cursor.rowcount != 1:
                raise StateError(f"task is not running or does not exist: {task_id}")
            connection.commit()

    def requeue(self, task_id: str, *, error: str | None = None) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE tasks
                SET status = 'PENDING',
                    started_at = NULL,
                    completed_at = NULL,
                    last_error = ?
                WHERE id = ? AND status = 'RUNNING'
                """,
                (error, task_id),
            )
            if cursor.rowcount != 1:
                raise StateError(f"task is not running or does not exist: {task_id}")
            connection.commit()

    def get_task(self, task_id: str) -> Task | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return None if row is None else self._task_from_row(row)

    def counts(self) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM tasks GROUP BY status"
            ).fetchall()
        return {row["status"]: row["count"] for row in rows}

    def insert_artifact(self, artifact: Artifact) -> None:
        with self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO artifacts(
                        id, run_id, kind, relative_path, media_type, size_bytes,
                        sha256, created_at, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        artifact.id,
                        artifact.run_id,
                        artifact.kind.value,
                        artifact.relative_path,
                        artifact.media_type,
                        artifact.size_bytes,
                        artifact.sha256,
                        isoformat(artifact.created_at),
                        json.dumps(artifact.metadata, sort_keys=True, separators=(",", ":")),
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise StateError(
                    f"artifact is already registered: {artifact.relative_path}"
                ) from error
            connection.commit()

    def get_artifact(self, artifact_id: str) -> Artifact | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
            ).fetchone()
        return None if row is None else self._artifact_from_row(row)

    def artifact_for_path(self, relative_path: str) -> Artifact | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM artifacts WHERE relative_path = ?", (relative_path,)
            ).fetchone()
        return None if row is None else self._artifact_from_row(row)

    def list_artifacts(self, *, kind: ArtifactKind | None = None) -> tuple[Artifact, ...]:
        with self._connect() as connection:
            if kind is None:
                rows = connection.execute(
                    "SELECT * FROM artifacts ORDER BY created_at, id"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM artifacts WHERE kind = ? ORDER BY created_at, id",
                    (kind.value,),
                ).fetchall()
        return tuple(self._artifact_from_row(row) for row in rows)

    @staticmethod
    def _task_from_row(row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            kind=row["kind"],
            status=TaskStatus(row["status"]),
            payload=json.loads(row["payload_json"]),
            priority=row["priority"],
            attempts=row["attempts"],
            last_error=row["last_error"],
        )

    @staticmethod
    def _artifact_from_row(row: sqlite3.Row) -> Artifact:
        from datetime import datetime

        return Artifact(
            id=row["id"],
            run_id=row["run_id"],
            kind=ArtifactKind(row["kind"]),
            relative_path=row["relative_path"],
            media_type=row["media_type"],
            size_bytes=row["size_bytes"],
            sha256=row["sha256"],
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")),
            metadata=json.loads(row["metadata_json"]),
        )
