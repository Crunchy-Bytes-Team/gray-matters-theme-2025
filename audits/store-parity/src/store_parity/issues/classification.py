from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from store_parity.issues.fingerprint import normalize_finding, stable_fingerprint
from store_parity.issues.models import (
    ClassifiedIssue,
    DetectorFinding,
    GateResult,
    IssueStatus,
    Severity,
    severity_rank,
)


@dataclass(frozen=True, slots=True)
class GatePolicy:
    minimum_severity: Severity = Severity.MAJOR
    minimum_confidence: float = 0.5
    fail_on_inherited_debt: bool = False
    fail_on_flaky: bool = False
    block_on_blocked: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "minimum_severity", Severity(self.minimum_severity))
        if not 0.0 <= self.minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0 and 1")


def classify_findings(
    findings: Iterable[DetectorFinding | Mapping[str, object]],
    *,
    scope: Sequence[str] = (),
    waived: Iterable[str] = (),
    inherited_debt: Iterable[str] = (),
    flaky: Iterable[str] = (),
    blocked: Iterable[str] = (),
) -> tuple[ClassifiedIssue, ...]:
    waived_set = set(waived)
    inherited_set = set(inherited_debt)
    flaky_set = set(flaky)
    blocked_set = set(blocked)
    classified: list[ClassifiedIssue] = []
    for raw in findings:
        finding = normalize_finding(raw)
        fingerprint = stable_fingerprint(finding, scope=scope)
        requested_status = finding.metadata.get("status")
        if fingerprint in blocked_set or requested_status == IssueStatus.BLOCKED.value:
            status = IssueStatus.BLOCKED
            rationale = "required comparison evidence was unavailable"
        elif fingerprint in waived_set or requested_status == IssueStatus.WAIVED.value:
            status = IssueStatus.WAIVED
            rationale = "explicitly waived"
        elif (
            fingerprint in inherited_set
            or requested_status == IssueStatus.INHERITED_DEBT.value
        ):
            status = IssueStatus.INHERITED_DEBT
            rationale = "known baseline debt"
        elif fingerprint in flaky_set or requested_status == IssueStatus.FLAKY.value:
            status = IssueStatus.FLAKY
            rationale = "classified as non-deterministic"
        else:
            status = IssueStatus.FAIL
            rationale = None
        classified.append(
            ClassifiedIssue(
                finding=finding,
                fingerprint=fingerprint,
                status=status,
                rationale=rationale,
            )
        )
    return tuple(classified)


def _is_exact_identity_failure(finding: DetectorFinding) -> bool:
    identity_scope = str(finding.metadata.get("identity_scope", "")).lower()
    return finding.exact_identity and (
        finding.category in {"content", "interaction", "theme"}
        or identity_scope in {"semantic", "interaction", "theme"}
    )


def evaluate_acceptance_gate(
    issues: Iterable[
        ClassifiedIssue | DetectorFinding | Mapping[str, object]
    ] = (),
    *,
    policy: GatePolicy | None = None,
    scope: Sequence[str] = (),
    blocked_reasons: Iterable[str] = (),
) -> GateResult:
    active_policy = policy or GatePolicy()
    classified: list[ClassifiedIssue] = []
    for item in issues:
        if isinstance(item, ClassifiedIssue):
            classified.append(item)
        else:
            classified.extend(classify_findings((item,), scope=scope))

    explicit_blocks = tuple(str(reason) for reason in blocked_reasons if str(reason))
    counts = Counter(issue.status.value for issue in classified)
    reasons: list[str] = list(explicit_blocks)

    blocked_issues = [
        issue for issue in classified if issue.status is IssueStatus.BLOCKED
    ]
    if active_policy.block_on_blocked and (blocked_issues or explicit_blocks):
        reasons.extend(
            f"blocked: {issue.finding.code}" for issue in blocked_issues
        )
        return GateResult(
            accepted=False,
            status=IssueStatus.BLOCKED,
            reasons=tuple(dict.fromkeys(reasons)),
            counts=dict(counts),
            evaluated=len(classified),
        )

    failures: list[ClassifiedIssue] = []
    for issue in classified:
        finding = issue.finding
        exact_override = _is_exact_identity_failure(finding)
        status_fails = (
            issue.status is IssueStatus.FAIL
            or (
                issue.status is IssueStatus.INHERITED_DEBT
                and active_policy.fail_on_inherited_debt
            )
            or (
                issue.status is IssueStatus.FLAKY and active_policy.fail_on_flaky
            )
        )
        threshold_fails = (
            severity_rank(finding.severity)
            >= severity_rank(active_policy.minimum_severity)
            and finding.confidence >= active_policy.minimum_confidence
        )
        if exact_override or (status_fails and threshold_fails):
            failures.append(issue)

    if failures:
        reasons.extend(
            (
                f"exact identity mismatch: {issue.finding.code}"
                if _is_exact_identity_failure(issue.finding)
                else f"{issue.finding.severity.value}: {issue.finding.code}"
            )
            for issue in failures
        )
        return GateResult(
            accepted=False,
            status=IssueStatus.FAIL,
            reasons=tuple(dict.fromkeys(reasons)),
            counts=dict(counts),
            evaluated=len(classified),
        )

    return GateResult(
        accepted=True,
        status=IssueStatus.PASS,
        reasons=(),
        counts=dict(counts),
        evaluated=len(classified),
    )
