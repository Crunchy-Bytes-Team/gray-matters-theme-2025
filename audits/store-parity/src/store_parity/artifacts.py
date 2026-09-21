from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker

from store_parity.layout import RunLayout
from store_parity.models import Artifact, ArtifactKind, utc_now
from store_parity.state import StateError, TaskStateStore


class ArtifactError(RuntimeError):
    """Raised when an artifact cannot be safely registered or consumed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ArtifactRegistry:
    def __init__(
        self,
        layout: RunLayout,
        state: TaskStateStore | None = None,
        *,
        schema_path: str | Path | None = None,
    ) -> None:
        self.layout = layout
        self.state = state or TaskStateStore(layout.state_db)
        default_schema = Path(__file__).resolve().parents[2] / "schemas" / "artifact.schema.json"
        resolved_schema = Path(schema_path) if schema_path is not None else default_schema
        self._validator = Draft202012Validator(
            json.loads(resolved_schema.read_text(encoding="utf-8")),
            format_checker=FormatChecker(),
        )

    def register_bytes(
        self,
        relative_path: str,
        content: bytes,
        *,
        kind: ArtifactKind,
        media_type: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> Artifact:
        destination = self.layout.artifact_path(relative_path)
        registry_path = destination.relative_to(self.layout.root).as_posix()
        if destination.exists() or self.state.artifact_for_path(registry_path) is not None:
            raise ArtifactError(f"artifact destination already exists: {registry_path}")

        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{destination.name}.",
                suffix=".tmp",
                dir=self.layout.temp_dir,
            )
            temporary_path = Path(temporary_name)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())

            digest = sha256_file(temporary_path)
            size_bytes = temporary_path.stat().st_size
            os.replace(temporary_path, destination)
            temporary_path = None
            self._fsync_directory(destination.parent)

            artifact = Artifact(
                id=str(uuid.uuid4()),
                run_id=self.layout.run_id,
                kind=kind,
                relative_path=registry_path,
                media_type=media_type,
                size_bytes=size_bytes,
                sha256=digest,
                created_at=utc_now(),
                metadata=dict(metadata or {}),
            )
            self._validator.validate(artifact.to_dict())
            try:
                self.state.insert_artifact(artifact)
            except StateError:
                destination.unlink(missing_ok=True)
                raise
            return artifact
        except (OSError, StateError) as error:
            raise ArtifactError(f"failed to register artifact {registry_path}: {error}") from error
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def register_json(
        self,
        relative_path: str,
        value: Any,
        *,
        kind: ArtifactKind = ArtifactKind.METADATA,
        metadata: Mapping[str, Any] | None = None,
    ) -> Artifact:
        content = (
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        return self.register_bytes(
            relative_path,
            content,
            kind=kind,
            media_type="application/json",
            metadata=metadata,
        )

    def resolve(self, artifact_id: str, *, verify: bool = True) -> Path:
        artifact = self.state.get_artifact(artifact_id)
        if artifact is None:
            raise ArtifactError(f"artifact is not registered: {artifact_id}")
        path = self.layout.root / artifact.relative_path
        if verify:
            self.validate(artifact)
        return path

    def list_registered(
        self, *, kind: ArtifactKind | None = None, verify: bool = False
    ) -> tuple[Artifact, ...]:
        artifacts = self.state.list_artifacts(kind=kind)
        if verify:
            for artifact in artifacts:
                self.validate(artifact)
        return artifacts

    def validate(self, artifact: Artifact) -> None:
        if artifact.run_id != self.layout.run_id:
            raise ArtifactError(
                f"artifact {artifact.id} belongs to run {artifact.run_id}, "
                f"not {self.layout.run_id}"
            )
        self._validator.validate(artifact.to_dict())
        path = (self.layout.root / artifact.relative_path).resolve()
        if self.layout.artifacts_dir.resolve() not in path.parents:
            raise ArtifactError(f"registered artifact escapes run directory: {artifact.id}")
        if not path.is_file():
            raise ArtifactError(f"registered artifact is missing: {artifact.relative_path}")
        if path.stat().st_size != artifact.size_bytes:
            raise ArtifactError(f"registered artifact size changed: {artifact.relative_path}")
        if sha256_file(path) != artifact.sha256:
            raise ArtifactError(f"registered artifact hash changed: {artifact.relative_path}")

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        try:
            descriptor = os.open(path, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
