from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from store_parity.issues import DetectorFinding, Severity


@dataclass(frozen=True, slots=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    @classmethod
    def from_value(cls, value: Rect | Mapping[str, Any]) -> Rect:
        if isinstance(value, cls):
            return value
        x = value.get("x", value.get("left"))
        y = value.get("y", value.get("top"))
        width = value.get("width")
        height = value.get("height")
        if width is None and x is not None and value.get("right") is not None:
            width = float(value["right"]) - float(x)
        if height is None and y is not None and value.get("bottom") is not None:
            height = float(value["bottom"]) - float(y)
        if x is None or y is None or width is None or height is None:
            raise ValueError("geometry requires x/y/width/height")
        return cls(float(x), float(y), float(width), float(height))

    def to_dict(self) -> dict[str, float]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True, slots=True)
class GeometryComparison:
    passed: bool
    findings: tuple[DetectorFinding, ...]
    compared: int


def compare_geometry(
    baseline: Mapping[str, Rect | Mapping[str, Any]],
    candidate: Mapping[str, Rect | Mapping[str, Any]],
    *,
    position_tolerance_px: float = 2.0,
    size_tolerance_px: float = 2.0,
) -> GeometryComparison:
    if position_tolerance_px < 0 or size_tolerance_px < 0:
        raise ValueError("geometry tolerances must be non-negative")
    findings: list[DetectorFinding] = []
    selectors = sorted(set(baseline) | set(candidate))
    for selector in selectors:
        if selector not in baseline or selector not in candidate:
            findings.append(
                DetectorFinding(
                    detector="geometry",
                    code="geometry.element_missing",
                    category="layout",
                    message=f"Element presence differs for {selector}",
                    severity=Severity.MAJOR,
                    selector=selector,
                    expected=selector in baseline,
                    actual=selector in candidate,
                )
            )
            continue
        expected = Rect.from_value(baseline[selector])
        actual = Rect.from_value(candidate[selector])
        deltas = {
            "x": abs(actual.x - expected.x),
            "y": abs(actual.y - expected.y),
            "width": abs(actual.width - expected.width),
            "height": abs(actual.height - expected.height),
        }
        exceeded = {
            key: delta
            for key, delta in deltas.items()
            if delta
            > (
                position_tolerance_px
                if key in {"x", "y"}
                else size_tolerance_px
            )
        }
        if exceeded:
            findings.append(
                DetectorFinding(
                    detector="geometry",
                    code="geometry.tolerance_exceeded",
                    category="layout",
                    message=f"Geometry differs beyond tolerance for {selector}",
                    severity=Severity.MAJOR,
                    selector=selector,
                    expected=expected.to_dict(),
                    actual=actual.to_dict(),
                    metadata={
                        "deltas": exceeded,
                        "position_tolerance_px": position_tolerance_px,
                        "size_tolerance_px": size_tolerance_px,
                    },
                )
            )
    return GeometryComparison(
        passed=not findings,
        findings=tuple(findings),
        compared=len(selectors),
    )


compare_layout_geometry = compare_geometry
