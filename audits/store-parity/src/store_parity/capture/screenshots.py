"""Bounded, lossless PNG screenshot primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class ScreenshotSet:
    viewport: bytes
    full_page: bytes
    components: Mapping[str, bytes] = field(default_factory=dict)
    missing_components: tuple[str, ...] = ()


async def capture_viewport_png(page: Any) -> bytes:
    return await page.screenshot(
        type="png",
        full_page=False,
        animations="disabled",
        caret="hide",
    )


async def _document_dimensions(page: Any) -> dict[str, float]:
    return await page.evaluate(
        """() => ({
            width: Math.max(
                document.documentElement.scrollWidth,
                document.documentElement.clientWidth,
                document.body?.scrollWidth || 0
            ),
            height: Math.max(
                document.documentElement.scrollHeight,
                document.documentElement.clientHeight,
                document.body?.scrollHeight || 0
            )
        })"""
    )


async def capture_full_page_png(
    page: Any,
    *,
    max_width: int = 4_096,
    max_height: int = 16_384,
) -> bytes:
    """Capture the whole page when safe, otherwise a deterministic bounded clip."""

    if max_width <= 0 or max_height <= 0:
        raise ValueError("full-page bounds must be positive")
    dimensions = await _document_dimensions(page)
    width = min(float(dimensions["width"]), float(max_width))
    height = min(float(dimensions["height"]), float(max_height))
    if width == float(dimensions["width"]) and height == float(dimensions["height"]):
        return await page.screenshot(
            type="png",
            full_page=True,
            animations="disabled",
            caret="hide",
        )
    return await page.screenshot(
        type="png",
        full_page=False,
        clip={"x": 0, "y": 0, "width": width, "height": height},
        animations="disabled",
        caret="hide",
    )


async def capture_region_png(
    page: Any,
    selector: str,
    *,
    padding: int = 0,
    max_width: int = 4_096,
    max_height: int = 8_192,
) -> bytes | None:
    if padding < 0:
        raise ValueError("padding cannot be negative")
    locator = page.locator(selector).first
    if not await locator.is_visible():
        return None
    box = await locator.bounding_box()
    if not box:
        return None
    if (
        padding == 0
        and float(box["width"]) <= float(max_width)
        and float(box["height"]) <= float(max_height)
    ):
        return await locator.screenshot(
            type="png",
            animations="disabled",
            caret="hide",
        )

    dimensions = await _document_dimensions(page)
    x = max(0.0, float(box["x"]) - padding)
    y = max(0.0, float(box["y"]) - padding)
    width = min(
        float(box["width"]) + padding * 2,
        float(max_width),
        float(dimensions["width"]) - x,
    )
    height = min(
        float(box["height"]) + padding * 2,
        float(max_height),
        float(dimensions["height"]) - y,
    )
    if width <= 0 or height <= 0:
        return None
    return await page.screenshot(
        type="png",
        full_page=False,
        clip={"x": x, "y": y, "width": width, "height": height},
        animations="disabled",
        caret="hide",
    )


async def capture_component_regions(
    page: Any,
    selectors: Mapping[str, str] | Sequence[str],
    *,
    padding: int = 0,
    max_width: int = 4_096,
    max_height: int = 8_192,
) -> tuple[dict[str, bytes], tuple[str, ...]]:
    entries = (
        selectors.items()
        if isinstance(selectors, Mapping)
        else ((selector, selector) for selector in selectors)
    )
    captures: dict[str, bytes] = {}
    missing: list[str] = []
    for name, selector in entries:
        capture = await capture_region_png(
            page,
            selector,
            padding=padding,
            max_width=max_width,
            max_height=max_height,
        )
        if capture is None:
            missing.append(str(name))
        else:
            captures[str(name)] = capture
    return captures, tuple(missing)


async def capture_screenshot_set(
    page: Any,
    *,
    component_selectors: Mapping[str, str] | Sequence[str] = (),
    component_padding: int = 0,
    max_full_width: int = 4_096,
    max_full_height: int = 16_384,
    max_component_width: int = 4_096,
    max_component_height: int = 8_192,
) -> ScreenshotSet:
    viewport = await capture_viewport_png(page)
    full_page = await capture_full_page_png(
        page,
        max_width=max_full_width,
        max_height=max_full_height,
    )
    components, missing = await capture_component_regions(
        page,
        component_selectors,
        padding=component_padding,
        max_width=max_component_width,
        max_height=max_component_height,
    )
    return ScreenshotSet(
        viewport=viewport,
        full_page=full_page,
        components=components,
        missing_components=missing,
    )
