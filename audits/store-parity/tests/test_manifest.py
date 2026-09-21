from __future__ import annotations

import json
from pathlib import Path

import pytest

from store_parity.artifacts import ArtifactRegistry
from store_parity.layout import RunLayout
from store_parity.manifest import ManifestError, ManifestLifecycle
from store_parity.models import ArtifactKind, RunStatus
from store_parity.state import TaskStateStore


def test_manifest_completion_refuses_missing_registered_artifact(
    tmp_path: Path,
) -> None:
    layout = RunLayout.create(tmp_path / "runs", "manifest-test")
    state = TaskStateStore(layout.state_db)
    registry = ArtifactRegistry(layout, state)
    lifecycle = ManifestLifecycle(layout, registry, state)
    lifecycle.start(config_digest="a" * 64, profile="smoke")
    lifecycle.mark_running()
    artifact = registry.register_bytes(
        "metadata/pages.json",
        b"[]\n",
        kind=ArtifactKind.METADATA,
        media_type="application/json",
    )
    registry.resolve(artifact.id).unlink()

    with pytest.raises(ManifestError, match="registered artifact is missing"):
        lifecycle.complete([artifact.id])

    persisted = json.loads(layout.manifest_path.read_text(encoding="utf-8"))
    assert persisted["status"] == RunStatus.RUNNING.value
    assert "completed_at" not in persisted
