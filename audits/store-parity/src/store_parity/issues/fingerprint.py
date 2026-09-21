from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from store_parity.issues.models import DetectorFinding, Severity


_VOLATILE_SELECTOR_ID = re.compile(
    r"(?:[a-f0-9]{8,}|\d{4,}|shopify-section-[\w-]+-\d+)", re.IGNORECASE
)
_NTH_SELECTOR = re.compile(r":nth-(?:child|of-type)\(\d+\)")


def normalize_selector(selector: str | None) -> str | None:
    if selector is None:
        return None
    normalized = " ".join(selector.strip().split())
    normalized = _NTH_SELECTOR.sub(":nth-*", normalized)
    normalized = _VOLATILE_SELECTOR_ID.sub("*", normalized)
    return normalized or None


def _canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        values = [_canonical(item) for item in value]
        if isinstance(value, (set, frozenset)):
            return sorted(values, key=lambda item: json.dumps(item, sort_keys=True))
        return values
    if isinstance(value, float):
        return round(value, 8)
    return value


def normalize_finding(
    finding: DetectorFinding | Mapping[str, Any],
) -> DetectorFinding:
    if isinstance(finding, DetectorFinding):
        return finding
    return DetectorFinding(
        detector=str(finding.get("detector", "unknown")).strip().lower(),
        code=str(finding.get("code", "unknown")).strip().lower(),
        category=str(finding.get("category", "runtime")).strip().lower(),
        message=str(finding.get("message", finding.get("description", "Finding"))),
        severity=Severity(str(finding.get("severity", Severity.MAJOR.value)).lower()),
        confidence=float(finding.get("confidence", 1.0)),
        selector=(
            str(finding["selector"]) if finding.get("selector") is not None else None
        ),
        expected=finding.get("expected"),
        actual=finding.get("actual"),
        metadata=_canonical(finding.get("metadata", {})),
        exact_identity=bool(finding.get("exact_identity", False)),
    )


def stable_fingerprint(
    finding: DetectorFinding | Mapping[str, Any],
    *,
    scope: Sequence[str] = (),
) -> str:
    normalized = normalize_finding(finding)
    metadata = normalized.metadata
    explicit_fields = metadata.get("fingerprint_fields", {})
    identity = {
        "version": 1,
        "scope": list(scope),
        "detector": normalized.detector.strip().lower(),
        "code": normalized.code.strip().lower(),
        "category": normalized.category.strip().lower(),
        "selector": normalize_selector(normalized.selector),
        "identity_scope": metadata.get("identity_scope"),
        "rule_id": metadata.get("rule_id"),
        "property": metadata.get("property"),
        "action": metadata.get("action"),
        "request": metadata.get("request"),
        "fields": explicit_fields,
    }
    encoded = json.dumps(
        _canonical(identity),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
