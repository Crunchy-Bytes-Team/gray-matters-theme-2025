"""Foundation primitives for the Gray Matters store parity audit."""

from store_parity.models import (
    Artifact,
    ArtifactKind,
    CaseResult,
    CaseStatus,
    Issue,
    IssueSeverity,
    Page,
    RunStatus,
    TaskStatus,
    Viewport,
)

__all__ = [
    "Artifact",
    "ArtifactKind",
    "CaseResult",
    "CaseStatus",
    "Issue",
    "IssueSeverity",
    "Page",
    "RunStatus",
    "TaskStatus",
    "Viewport",
]

__version__ = "0.1.0"
