from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from store_parity.issues import DetectorFinding, Severity


def _normalize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _normalize_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in {"duration_ms", "started_at", "completed_at", "timestamp"}
        }
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    if isinstance(value, str):
        return " ".join(value.split())
    return value


def _contracts(
    value: Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {
            str(action): _normalize_value(contract)
            for action, contract in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    contracts: dict[str, Any] = {}
    for index, contract in enumerate(value):
        action = str(
            contract.get("action", contract.get("name", contract.get("id", index)))
        )
        contracts[action] = _normalize_value(contract)
    return contracts


@dataclass(frozen=True, slots=True)
class BehaviorComparison:
    passed: bool
    findings: tuple[DetectorFinding, ...]
    compared_contracts: int


def compare_behavior_contracts(
    baseline: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    candidate: Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> BehaviorComparison:
    expected_contracts = _contracts(baseline)
    actual_contracts = _contracts(candidate)
    findings: list[DetectorFinding] = []
    for action in sorted(set(expected_contracts) | set(actual_contracts)):
        expected = expected_contracts.get(action)
        actual = actual_contracts.get(action)
        if expected == actual:
            continue
        findings.append(
            DetectorFinding(
                detector="behavior-contract",
                code=(
                    "behavior.contract_missing"
                    if expected is None or actual is None
                    else "behavior.contract_mismatch"
                ),
                category="interaction",
                message=f"Behavior contract differs for {action}",
                severity=Severity.CRITICAL,
                expected=expected,
                actual=actual,
                metadata={
                    "action": action,
                    "identity_scope": "interaction",
                },
                exact_identity=True,
            )
        )
    return BehaviorComparison(
        passed=not findings,
        findings=tuple(findings),
        compared_contracts=len(set(expected_contracts) | set(actual_contracts)),
    )


compare_behaviors = compare_behavior_contracts
