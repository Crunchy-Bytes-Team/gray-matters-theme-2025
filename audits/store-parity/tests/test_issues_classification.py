from __future__ import annotations

from store_parity.issues import (
    DetectorFinding,
    GatePolicy,
    IssueStatus,
    Severity,
    classify_findings,
    evaluate_acceptance_gate,
    stable_fingerprint,
)


def _finding(**overrides: object) -> DetectorFinding:
    values = {
        "detector": "geometry",
        "code": "geometry.tolerance_exceeded",
        "category": "layout",
        "message": "Position differs",
        "severity": Severity.MAJOR,
        "selector": "#shopify-section-template-1234567890 button:nth-child(4)",
        "metadata": {"property": "x"},
    }
    values.update(overrides)
    return DetectorFinding(**values)  # type: ignore[arg-type]


def test_fingerprints_are_stable_across_messages_values_and_volatile_ids() -> None:
    first = _finding(expected=1, actual=4)
    second = _finding(
        message="Position changed again",
        expected=2,
        actual=8,
        selector="#shopify-section-template-9999999999 button:nth-child(9)",
    )

    assert stable_fingerprint(first, scope=("product",)) == stable_fingerprint(
        second, scope=("product",)
    )
    assert stable_fingerprint(first, scope=("product",)) != stable_fingerprint(
        first, scope=("collection",)
    )


def test_classification_supports_all_non_pass_issue_statuses() -> None:
    findings = tuple(
        _finding(code=f"test.{index}", selector=f"#item-{index}")
        for index in range(4)
    )
    fingerprints = [stable_fingerprint(finding) for finding in findings]
    classified = classify_findings(
        findings,
        blocked=(fingerprints[0],),
        waived=(fingerprints[1],),
        inherited_debt=(fingerprints[2],),
        flaky=(fingerprints[3],),
    )
    assert [issue.status for issue in classified] == [
        IssueStatus.BLOCKED,
        IssueStatus.WAIVED,
        IssueStatus.INHERITED_DEBT,
        IssueStatus.FLAKY,
    ]


def test_gate_fails_and_exact_identity_overrides_thresholds() -> None:
    normal = _finding()
    result = evaluate_acceptance_gate((normal,))
    assert not result.accepted
    assert result.status is IssueStatus.FAIL

    exact = _finding(
        detector="behavior-contract",
        code="behavior.contract_mismatch",
        category="interaction",
        severity=Severity.INFO,
        confidence=0.01,
        exact_identity=True,
        metadata={"identity_scope": "interaction"},
    )
    override = evaluate_acceptance_gate(
        (exact,),
        policy=GatePolicy(
            minimum_severity=Severity.BLOCKER,
            minimum_confidence=1.0,
        ),
    )
    assert not override.accepted
    assert "exact identity mismatch" in override.reasons[0]


def test_gate_passes_with_no_findings_or_only_waivers() -> None:
    assert evaluate_acceptance_gate().accepted
    finding = _finding()
    fingerprint = stable_fingerprint(finding)
    waived = classify_findings((finding,), waived=(fingerprint,))
    result = evaluate_acceptance_gate(waived)
    assert result.accepted
    assert result.status is IssueStatus.PASS
