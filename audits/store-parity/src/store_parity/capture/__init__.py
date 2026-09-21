"""Lossless screenshots and semantic browser evidence collectors."""

from store_parity.capture.collectors import (
    CaptureBundle,
    CaptureOptions,
    capture_page,
    collect_dom_snapshot,
    collect_icon_fingerprints,
    collect_landmarks,
    collect_overflow_offenders,
    collect_runtime_failures,
)
from store_parity.capture.screenshots import (
    ScreenshotSet,
    capture_component_regions,
    capture_full_page_png,
    capture_region_png,
    capture_viewport_png,
)

__all__ = [
    "CaptureBundle",
    "CaptureOptions",
    "ScreenshotSet",
    "capture_component_regions",
    "capture_full_page_png",
    "capture_page",
    "capture_region_png",
    "capture_viewport_png",
    "collect_dom_snapshot",
    "collect_icon_fingerprints",
    "collect_landmarks",
    "collect_overflow_offenders",
    "collect_runtime_failures",
]
