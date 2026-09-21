from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from PIL import ImageColor

from store_parity.issues import DetectorFinding, Severity


COLOR_PROPERTIES = {
    "background-color",
    "border-bottom-color",
    "border-color",
    "border-left-color",
    "border-right-color",
    "border-top-color",
    "caret-color",
    "color",
    "fill",
    "outline-color",
    "stroke",
    "text-decoration-color",
}
FONT_PROPERTIES = {
    "font",
    "font-family",
    "font-feature-settings",
    "font-size",
    "font-stretch",
    "font-style",
    "font-variation-settings",
    "font-weight",
    "letter-spacing",
    "line-height",
    "text-transform",
}
VISIBILITY_PROPERTIES = {"display", "opacity", "visibility"}
LAYOUT_PROPERTIES = {
    "align-items",
    "bottom",
    "box-sizing",
    "column-gap",
    "display",
    "flex-direction",
    "flex-grow",
    "flex-shrink",
    "gap",
    "grid-template-columns",
    "height",
    "justify-content",
    "left",
    "margin-bottom",
    "margin-left",
    "margin-right",
    "margin-top",
    "max-height",
    "max-width",
    "min-height",
    "min-width",
    "overflow",
    "padding-bottom",
    "padding-left",
    "padding-right",
    "padding-top",
    "position",
    "right",
    "row-gap",
    "top",
    "transform",
    "width",
    "z-index",
}

_NUMBER = re.compile(r"(?<![\w-])(-?(?:\d+\.\d+|\d+|\.\d+))(px|rem|em|%|s|ms|deg)?")
_RGBA = re.compile(
    r"rgba?\(\s*([\d.]+%?)\s*[, ]\s*([\d.]+%?)\s*[, ]\s*([\d.]+%?)"
    r"(?:\s*[,/]\s*([\d.]+%?))?\s*\)",
    re.IGNORECASE,
)


def _format_decimal(value: str) -> str:
    try:
        number = Decimal(value)
    except InvalidOperation:
        return value
    if number == 0:
        return "0"
    return format(number.normalize(), "f")


def normalize_numbers(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        number = _format_decimal(match.group(1))
        unit = (match.group(2) or "").lower()
        return number if number == "0" else f"{number}{unit}"

    return _NUMBER.sub(replace, value)


def _color_channel(value: str) -> int:
    if value.endswith("%"):
        return round(float(value[:-1]) * 2.55)
    return round(float(value))


def _alpha_channel(value: str | None) -> int:
    if value is None:
        return 255
    if value.endswith("%"):
        return round(float(value[:-1]) * 2.55)
    numeric = float(value)
    return round(numeric * 255) if numeric <= 1 else round(numeric)


def normalize_color(value: str) -> str:
    lowered = value.strip().lower()
    match = _RGBA.fullmatch(lowered)
    try:
        if match:
            rgba = (
                _color_channel(match.group(1)),
                _color_channel(match.group(2)),
                _color_channel(match.group(3)),
                _alpha_channel(match.group(4)),
            )
        else:
            rgba = ImageColor.getcolor(lowered, "RGBA")
    except (ValueError, TypeError):
        return " ".join(lowered.split())
    return f"rgba({rgba[0]},{rgba[1]},{rgba[2]},{rgba[3]})"


def _normalize_font_family(value: str) -> str:
    families = []
    for family in value.split(","):
        normalized = family.strip().strip("\"'").lower()
        if normalized:
            families.append(normalized)
    return ",".join(families)


def normalize_style_value(property_name: str, value: Any) -> str:
    name = property_name.strip().lower()
    normalized = " ".join(str(value).strip().split())
    if name in COLOR_PROPERTIES:
        return normalize_color(normalized)
    if name == "font-family":
        return _normalize_font_family(normalized)
    if name == "font-weight":
        weights = {"normal": "400", "bold": "700"}
        return weights.get(normalized.lower(), normalize_numbers(normalized.lower()))
    if name in VISIBILITY_PROPERTIES:
        return normalize_numbers(normalized.lower())
    if name in FONT_PROPERTIES or name in LAYOUT_PROPERTIES:
        return normalize_numbers(normalized.lower())
    return normalize_numbers(normalized)


def normalize_computed_style(style: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(name).strip().lower(): normalize_style_value(str(name), value)
        for name, value in sorted(style.items(), key=lambda pair: str(pair[0]))
    }


def is_visible(style: Mapping[str, Any]) -> bool:
    normalized = normalize_computed_style(style)
    if normalized.get("display") == "none":
        return False
    if normalized.get("visibility") in {"hidden", "collapse"}:
        return False
    try:
        return float(normalized.get("opacity", "1")) > 0
    except ValueError:
        return True


def _rgba_channels(value: str) -> tuple[int, int, int, int] | None:
    match = re.fullmatch(r"rgba\((\d+),(\d+),(\d+),(\d+)\)", value)
    if not match:
        return None
    return tuple(int(match.group(index)) for index in range(1, 5))  # type: ignore[return-value]


def _numeric_px(value: str) -> float | None:
    match = re.fullmatch(r"(-?(?:\d+(?:\.\d+)?|\.\d+))(?:px)?", value)
    return float(match.group(1)) if match else None


@dataclass(frozen=True, slots=True)
class StyleComparison:
    passed: bool
    findings: tuple[DetectorFinding, ...]
    compared_properties: int


def compare_computed_styles(
    baseline: Mapping[str, Mapping[str, Any]],
    candidate: Mapping[str, Mapping[str, Any]],
    *,
    color_channel_tolerance: int = 3,
    number_tolerance_px: float = 0.0,
    font_size_tolerance_px: float = 1.0,
    line_height_tolerance_px: float = 1.0,
) -> StyleComparison:
    if color_channel_tolerance < 0:
        raise ValueError("color tolerance must be non-negative")
    findings: list[DetectorFinding] = []
    compared = 0
    for selector in sorted(set(baseline) | set(candidate)):
        if selector not in baseline or selector not in candidate:
            findings.append(
                DetectorFinding(
                    detector="computed-style",
                    code="style.element_missing",
                    category="layout",
                    message=f"Styled element presence differs for {selector}",
                    severity=Severity.MAJOR,
                    selector=selector,
                    expected=selector in baseline,
                    actual=selector in candidate,
                )
            )
            continue
        expected_style = normalize_computed_style(baseline[selector])
        actual_style = normalize_computed_style(candidate[selector])
        for property_name in sorted(set(expected_style) | set(actual_style)):
            compared += 1
            expected = expected_style.get(property_name)
            actual = actual_style.get(property_name)
            if expected == actual:
                continue
            equivalent = False
            if (
                property_name in COLOR_PROPERTIES
                and expected is not None
                and actual is not None
            ):
                expected_rgba = _rgba_channels(expected)
                actual_rgba = _rgba_channels(actual)
                equivalent = bool(
                    expected_rgba
                    and actual_rgba
                    and all(
                        abs(left - right) <= color_channel_tolerance
                        for left, right in zip(
                            expected_rgba, actual_rgba, strict=True
                        )
                    )
                )
            elif expected is not None and actual is not None:
                expected_number = _numeric_px(expected)
                actual_number = _numeric_px(actual)
                if expected_number is not None and actual_number is not None:
                    tolerance = {
                        "font-size": font_size_tolerance_px,
                        "line-height": line_height_tolerance_px,
                    }.get(property_name, number_tolerance_px)
                    equivalent = abs(expected_number - actual_number) <= tolerance
            if equivalent:
                continue
            category = (
                "typography"
                if property_name in FONT_PROPERTIES
                else "layout"
                if property_name in LAYOUT_PROPERTIES
                else "visual"
            )
            findings.append(
                DetectorFinding(
                    detector="computed-style",
                    code="style.property_mismatch",
                    category=category,
                    message=f"{property_name} differs for {selector}",
                    severity=Severity.MAJOR,
                    selector=selector,
                    expected=expected,
                    actual=actual,
                    metadata={"property": property_name},
                )
            )
    return StyleComparison(
        passed=not findings,
        findings=tuple(findings),
        compared_properties=compared,
    )


compare_styles = compare_computed_styles
