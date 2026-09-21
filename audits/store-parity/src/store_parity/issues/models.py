from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Mapping


class Severity(StrEnum):
    BLOCKER = "blocker"
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


class IssueStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"
    WAIVED = "waived"
    INHERITED_DEBT = "inherited_debt"
    FLAKY = "flaky"


_SEVERITY_RANK = {
    Severity.INFO: 0,
    Severity.MINOR: 1,
    Severity.MAJOR: 2,
    Severity.CRITICAL: 3,
    Severity.BLOCKER: 4,
}


def severity_rank(severity: Severity | str) -> int:
    return _SEVERITY_RANK[Severity(str(severity))]


@dataclass(frozen=True, slots=True)
class DetectorFinding:
    detector: str
    code: str
    category: str
    message: str
    severity: Severity = Severity.MAJOR
    confidence: float = 1.0
    selector: str | None = None
    expected: Any = None
    actual: Any = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    exact_identity: bool = False

    def __post_init__(self) -> None:
        if not self.detector.strip():
            raise ValueError("detector must not be empty")
        if not self.code.strip():
            raise ValueError("code must not be empty")
        if not self.category.strip():
            raise ValueError("category must not be empty")
        if not self.message.strip():
            raise ValueError("message must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        object.__setattr__(self, "severity", Severity(self.severity))

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["severity"] = self.severity.value
        return value


@dataclass(frozen=True, slots=True)
class ClassifiedIssue:
    finding: DetectorFinding
    fingerprint: str
    status: IssueStatus
    rationale: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", IssueStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.finding.to_dict(),
            "fingerprint": self.fingerprint,
            "status": self.status.value,
            "rationale": self.rationale,
        }


@dataclass(frozen=True, slots=True)
class GateResult:
    accepted: bool
    status: IssueStatus
    reasons: tuple[str, ...] = ()
    counts: Mapping[str, int] = field(default_factory=dict)
    evaluated: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", IssueStatus(self.status))

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status.value,
            "reasons": list(self.reasons),
            "counts": dict(self.counts),
            "evaluated": self.evaluated,
        }
