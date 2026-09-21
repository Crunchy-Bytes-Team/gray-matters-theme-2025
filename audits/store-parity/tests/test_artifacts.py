from __future__ import annotations

import hashlib
from pathlib import Path

from store_parity.artifacts import ArtifactRegistry
from store_parity.layout import RunLayout
from store_parity.models import ArtifactKind
from store_parity.state import TaskStateStore


def test_artifact_write_is_atomic_hashed_and_registry_only(tmp_path: Path) -> None:
    layout = RunLayout.create(tmp_path / "runs", "test-run")
    state = TaskStateStore(layout.state_db)
    registry = ArtifactRegistry(layout, state)
    content = b"deterministic screenshot bytes"

    artifact = registry.register_bytes(
        "captures/home-mobile.png",
        content,
        kind=ArtifactKind.SCREENSHOT,
        media_type="image/png",
        metadata={"viewport": "mobile"},
    )

    path = registry.resolve(artifact.id)
    assert path.read_bytes() == content
    assert artifact.sha256 == hashlib.sha256(content).hexdigest()
    assert artifact.size_bytes == len(content)
    assert list(layout.temp_dir.iterdir()) == []

    stale = layout.artifacts_dir / "reports" / "stale.html"
    stale.write_text("must not be consumed", encoding="utf-8")
    registered = registry.list_registered(verify=True)
    assert [item.id for item in registered] == [artifact.id]
    assert all(item.relative_path != "artifacts/reports/stale.html" for item in registered)
