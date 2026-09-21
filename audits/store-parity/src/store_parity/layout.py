from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


LAYOUT_VERSION = 1
ARTIFACT_NAMESPACES = ("captures", "diffs", "reports", "metadata", "logs", "other")
_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class LayoutError(ValueError):
    """Raised when a run directory violates the fixed layout contract."""


@dataclass(frozen=True, slots=True)
class RunLayout:
    run_id: str
    root: Path
    artifacts_dir: Path
    temp_dir: Path
    state_db: Path
    manifest_path: Path

    @classmethod
    def create(cls, runs_dir: str | Path, run_id: str) -> RunLayout:
        if not _RUN_ID_PATTERN.fullmatch(run_id):
            raise LayoutError("run_id may contain only letters, numbers, '.', '_' and '-'")

        base = Path(runs_dir).expanduser().resolve()
        base.mkdir(parents=True, exist_ok=True)
        root = base / run_id
        try:
            root.mkdir()
        except FileExistsError as error:
            raise LayoutError(f"run directory already exists: {root}") from error

        layout = cls._from_root(root, run_id)
        layout.artifacts_dir.mkdir()
        for namespace in ARTIFACT_NAMESPACES:
            (layout.artifacts_dir / namespace).mkdir()
        layout.temp_dir.mkdir()
        layout._write_descriptor()
        return layout

    @classmethod
    def open(cls, root: str | Path) -> RunLayout:
        resolved = Path(root).expanduser().resolve()
        descriptor_path = resolved / ".layout.json"
        try:
            descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise LayoutError(f"invalid run layout at {resolved}: {error}") from error

        expected_keys = {"version", "run_id", "artifact_namespaces"}
        if set(descriptor) != expected_keys:
            raise LayoutError("run layout descriptor contains unexpected fields")
        if descriptor["version"] != LAYOUT_VERSION:
            raise LayoutError(f"unsupported run layout version: {descriptor['version']}")
        if descriptor["artifact_namespaces"] != list(ARTIFACT_NAMESPACES):
            raise LayoutError("run artifact namespaces do not match the layout contract")

        layout = cls._from_root(resolved, descriptor["run_id"])
        required = (layout.artifacts_dir, layout.temp_dir)
        if not all(path.is_dir() for path in required):
            raise LayoutError("run layout is missing required directories")
        return layout

    @classmethod
    def _from_root(cls, root: Path, run_id: str) -> RunLayout:
        return cls(
            run_id=run_id,
            root=root,
            artifacts_dir=root / "artifacts",
            temp_dir=root / ".tmp",
            state_db=root / "state.sqlite3",
            manifest_path=root / "manifest.json",
        )

    def artifact_path(self, relative_path: str) -> Path:
        relative = PurePosixPath(relative_path)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise LayoutError(f"unsafe artifact path: {relative_path!r}")
        if relative.parts[0] not in ARTIFACT_NAMESPACES:
            allowed = ", ".join(ARTIFACT_NAMESPACES)
            raise LayoutError(f"artifact path must start with one of: {allowed}")

        destination = (self.artifacts_dir / Path(*relative.parts)).resolve()
        if self.artifacts_dir.resolve() not in destination.parents:
            raise LayoutError(f"artifact path escapes run directory: {relative_path!r}")
        return destination

    def _write_descriptor(self) -> None:
        descriptor = {
            "version": LAYOUT_VERSION,
            "run_id": self.run_id,
            "artifact_namespaces": list(ARTIFACT_NAMESPACES),
        }
        (self.root / ".layout.json").write_text(
            json.dumps(descriptor, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
