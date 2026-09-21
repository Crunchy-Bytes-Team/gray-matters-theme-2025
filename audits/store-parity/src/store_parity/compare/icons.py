from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Mapping

from store_parity.issues import DetectorFinding, Severity


def _local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1].lower()


def _normalize_path(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace(",", " ")).strip()


def _canonical_element(element: ET.Element) -> dict[str, Any]:
    attributes = {
        _local_name(name): (
            _normalize_path(value)
            if _local_name(name) in {"d", "points", "transform"}
            else " ".join(value.split())
        )
        for name, value in sorted(element.attrib.items())
        if _local_name(name) not in {"id", "class", "data-name"}
    }
    return {
        "tag": _local_name(element.tag),
        "attributes": attributes,
        "text": " ".join((element.text or "").split()),
        "children": [_canonical_element(child) for child in element],
    }


def normalize_icon(icon: Any) -> str:
    if isinstance(icon, bytes):
        try:
            icon = icon.decode("utf-8")
        except UnicodeDecodeError:
            return f"sha256:{hashlib.sha256(icon).hexdigest()}"
    if isinstance(icon, str):
        value = icon.strip()
        if value.startswith("<"):
            try:
                canonical: Any = _canonical_element(ET.fromstring(value))
            except ET.ParseError:
                canonical = " ".join(value.split())
        else:
            canonical = value
    else:
        canonical = icon
    return json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


@dataclass(frozen=True, slots=True)
class IconComparison:
    passed: bool
    findings: tuple[DetectorFinding, ...]
    compared: int


def compare_icons(
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> IconComparison:
    findings: list[DetectorFinding] = []
    selectors = sorted(set(baseline) | set(candidate))
    for selector in selectors:
        expected = normalize_icon(baseline[selector]) if selector in baseline else None
        actual = normalize_icon(candidate[selector]) if selector in candidate else None
        if expected == actual:
            continue
        findings.append(
            DetectorFinding(
                detector="icon",
                code=(
                    "icon.missing"
                    if expected is None or actual is None
                    else "icon.identity_mismatch"
                ),
                category="theme",
                message=f"Icon identity differs for {selector}",
                severity=Severity.MAJOR,
                selector=selector,
                expected=expected,
                actual=actual,
                metadata={"identity_scope": "theme"},
                exact_identity=True,
            )
        )
    return IconComparison(
        passed=not findings,
        findings=tuple(findings),
        compared=len(selectors),
    )


compare_icon_identity = compare_icons
