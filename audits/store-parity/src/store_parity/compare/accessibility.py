from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from store_parity.issues import DetectorFinding, Severity


_RELEVANT_IMPACTS = {"serious", "critical"}
_UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_LONG_HEX = re.compile(r"(?<![0-9a-f])[0-9a-f]{16,}(?![0-9a-f])", re.IGNORECASE)


def _normalize_target(value: Any) -> str:
    target = str(value)
    target = _UUID.sub("<uuid>", target)
    return _LONG_HEX.sub("<hex>", target)


def _targets(node: Mapping[str, Any]) -> tuple[str, ...]:
    target = node.get("target", ())
    if isinstance(target, str):
        return (_normalize_target(target),)
    if isinstance(target, Iterable):
        return tuple(_normalize_target(item) for item in target)
    return ()


def _violation_keys(
    violations: Iterable[Mapping[str, Any]],
) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for violation in violations:
        if str(violation.get("impact", "")).lower() not in _RELEVANT_IMPACTS:
            continue
        rule_id = str(violation.get("id", "unknown"))
        nodes = violation.get("nodes", ())
        if not isinstance(nodes, Iterable) or isinstance(nodes, (str, bytes)):
            nodes = ()
        selectors = {
            selector
            for node in nodes
            if isinstance(node, Mapping)
            for selector in _targets(node)
        }
        for selector in selectors or {""}:
            keys.add((rule_id, selector))
    return keys


@dataclass(frozen=True, slots=True)
class AccessibilityComparison:
    passed: bool
    findings: tuple[DetectorFinding, ...]
    new_serious_or_critical: int


def compare_accessibility_issues(
    baseline: Iterable[Mapping[str, Any]],
    candidate: Iterable[Mapping[str, Any]],
) -> AccessibilityComparison:
    baseline_keys = _violation_keys(baseline)
    findings: list[DetectorFinding] = []
    for violation in candidate:
        impact = str(violation.get("impact", "")).lower()
        if impact not in _RELEVANT_IMPACTS:
            continue
        rule_id = str(violation.get("id", "unknown"))
        nodes = violation.get("nodes", ())
        if not isinstance(nodes, Iterable) or isinstance(nodes, (str, bytes)):
            nodes = ()
        selectors = {
            selector
            for node in nodes
            if isinstance(node, Mapping)
            for selector in _targets(node)
        }
        for selector in sorted(selectors or {""}):
            if (rule_id, selector) in baseline_keys:
                continue
            findings.append(
                DetectorFinding(
                    detector="accessibility",
                    code="accessibility.new_violation",
                    category="accessibility",
                    message=(
                        f"New {impact} accessibility violation {rule_id}"
                        + (f" at {selector}" if selector else "")
                    ),
                    severity=(
                        Severity.BLOCKER
                        if impact == "critical"
                        else Severity.CRITICAL
                    ),
                    selector=selector or None,
                    expected=None,
                    actual={
                        "rule_id": rule_id,
                        "impact": impact,
                        "help": violation.get("help"),
                    },
                    metadata={
                        "rule_id": rule_id,
                        "impact": impact,
                    },
                )
            )
    return AccessibilityComparison(
        passed=not findings,
        findings=tuple(findings),
        new_serious_or_critical=len(findings),
    )


diff_accessibility = compare_accessibility_issues
