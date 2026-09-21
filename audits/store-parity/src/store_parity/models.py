from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Mapping


def utc_now() -> datetime:
    return datetime.now(UTC)


def isoformat(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return isoformat(value)
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


class RunStatus(StrEnum):
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    COMPLETE = "COMPLETE"


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class CaseStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


class ArtifactKind(StrEnum):
    SCREENSHOT = "screenshot"
    DOM = "dom"
    METADATA = "metadata"
    DIFF = "diff"
    REPORT = "report"
    LOG = "log"
    OTHER = "other"


class IssueSeverity(StrEnum):
    BLOCKER = "blocker"
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class Viewport:
    width: int
    height: int

    def to_dict(self) -> dict[str, int]:
        return {"width": self.width, "height": self.height}


@dataclass(frozen=True, slots=True)
class Page:
    id: str
    url: str
    path: str
    page_type: str
    source: str
    discovered_at: datetime = field(default_factory=utc_now)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True, slots=True)
class CaseResult:
    id: str
    page_id: str
    profile: str
    scenario: str
    viewport: Viewport
    status: CaseStatus = CaseStatus.PENDING
    started_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None
    artifact_ids: tuple[str, ...] = ()
    metrics: Mapping[str, float] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True, slots=True)
class Issue:
    id: str
    case_result_id: str
    category: str
    severity: IssueSeverity
    title: str
    description: str
    selector: str | None = None
    artifact_ids: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True, slots=True)
class Artifact:
    id: str
    run_id: str
    kind: ArtifactKind
    relative_path: str
    media_type: str
    size_bytes: int
    sha256: str
    created_at: datetime
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))
