from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from store_parity.artifacts import ArtifactError, ArtifactRegistry
from store_parity.layout import RunLayout
from store_parity.models import RunStatus, isoformat, utc_now
from store_parity.state import TaskStateStore


class ManifestError(RuntimeError):
    """Raised when a run manifest transition cannot be safely committed."""


class ManifestLifecycle:
    def __init__(
        self,
        layout: RunLayout,
        registry: ArtifactRegistry,
        state: TaskStateStore | None = None,
        *,
        schema_path: str | Path | None = None,
    ) -> None:
        self.layout = layout
        self.registry = registry
        self.state = state or registry.state
        default_schema = (
            Path(__file__).resolve().parents[2] / "schemas" / "run-manifest.schema.json"
        )
        resolved_schema = Path(schema_path) if schema_path is not None else default_schema
        self._validator = Draft202012Validator(
            json.loads(resolved_schema.read_text(encoding="utf-8")),
            format_checker=FormatChecker(),
        )

    def start(self, *, config_digest: str, profile: str) -> dict[str, Any]:
        if self.layout.manifest_path.exists():
            raise ManifestError(f"manifest already exists: {self.layout.manifest_path}")
        manifest = {
            "schema_version": 1,
            "run_id": self.layout.run_id,
            "status": RunStatus.INITIALIZING.value,
            "created_at": isoformat(utc_now()),
            "config_digest": config_digest,
            "profile": profile,
            "artifact_ids": [],
            "task_summary": self.state.counts(),
        }
        self._validated_write(manifest)
        return manifest

    def mark_running(self) -> dict[str, Any]:
        manifest = self.read()
        if manifest["status"] != RunStatus.INITIALIZING.value:
            raise ManifestError("only an INITIALIZING manifest may transition to RUNNING")
        manifest["status"] = RunStatus.RUNNING.value
        manifest["task_summary"] = self.state.counts()
        self._validated_write(manifest)
        return manifest

    def resume(self) -> dict[str, Any]:
        manifest = self.read()
        if manifest["status"] == RunStatus.COMPLETE.value:
            raise ManifestError("a COMPLETE manifest is immutable")
        manifest["status"] = RunStatus.RUNNING.value
        manifest.pop("completed_at", None)
        manifest["task_summary"] = self.state.counts()
        self._validated_write(manifest)
        return manifest

    def fail(self, artifact_ids: Iterable[str] | None = None) -> dict[str, Any]:
        manifest = self.read()
        if manifest["status"] == RunStatus.COMPLETE.value:
            raise ManifestError("a COMPLETE manifest is immutable")
        if artifact_ids is not None:
            ids = list(artifact_ids)
            if len(ids) != len(set(ids)):
                raise ManifestError("manifest artifact_ids must be unique")
            try:
                for artifact_id in ids:
                    self.registry.resolve(artifact_id, verify=True)
            except ArtifactError as error:
                raise ManifestError(f"cannot fail manifest: {error}") from error
            manifest["artifact_ids"] = ids
        manifest["status"] = RunStatus.FAILED.value
        manifest["task_summary"] = self.state.counts()
        self._validated_write(manifest)
        return manifest

    def complete(self, artifact_ids: Iterable[str] | None = None) -> dict[str, Any]:
        manifest = self.read()
        if manifest["status"] == RunStatus.COMPLETE.value:
            raise ManifestError("a COMPLETE manifest is immutable")

        counts = self.state.counts()
        unfinished = counts.get("PENDING", 0) + counts.get("RUNNING", 0)
        if unfinished:
            raise ManifestError(f"cannot complete run with {unfinished} unfinished task(s)")

        if artifact_ids is None:
            ids = [artifact.id for artifact in self.registry.list_registered()]
        else:
            ids = list(artifact_ids)
        if len(ids) != len(set(ids)):
            raise ManifestError("manifest artifact_ids must be unique")

        try:
            for artifact_id in ids:
                self.registry.resolve(artifact_id, verify=True)
        except ArtifactError as error:
            raise ManifestError(f"cannot complete manifest: {error}") from error

        candidate = {
            **manifest,
            "status": RunStatus.COMPLETE.value,
            "completed_at": isoformat(utc_now()),
            "artifact_ids": ids,
            "task_summary": counts,
        }
        self._validated_write(candidate)
        return candidate

    def read(self) -> dict[str, Any]:
        try:
            value = json.loads(self.layout.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ManifestError(f"unable to read manifest: {error}") from error
        if not isinstance(value, dict):
            raise ManifestError("manifest root must be an object")
        return value

    def _validated_write(self, manifest: dict[str, Any]) -> None:
        try:
            self._validator.validate(manifest)
        except ValidationError as error:
            raise ManifestError(f"manifest validation failed: {error.message}") from error

        temporary_path: Path | None = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=".manifest.",
                suffix=".tmp",
                dir=self.layout.temp_dir,
            )
            temporary_path = Path(temporary_name)
            payload = (
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8")
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, self.layout.manifest_path)
            temporary_path = None
        except OSError as error:
            raise ManifestError(f"unable to write manifest: {error}") from error
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
