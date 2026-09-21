from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image

from store_parity.issues import DetectorFinding, Severity


@dataclass(frozen=True, slots=True)
class DynamicMask:
    x: int
    y: int
    width: int
    height: int
    reason: str

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("dynamic mask dimensions must be positive")
        if not self.reason.strip():
            raise ValueError("dynamic masks must include an explicit reason")

    @classmethod
    def from_value(cls, value: DynamicMask | Mapping[str, Any]) -> DynamicMask:
        if isinstance(value, cls):
            return value
        return cls(
            x=int(value["x"]),
            y=int(value["y"]),
            width=int(value["width"]),
            height=int(value["height"]),
            reason=str(value.get("reason", "")),
        )


@dataclass(frozen=True, slots=True)
class VisualDiffResult:
    passed: bool
    changed_pixel_ratio: float
    mean_delta: float
    changed_pixels: int
    compared_pixels: int
    masked_pixel_ratio: float
    dimensions_mismatch: bool
    baseline_size: tuple[int, int]
    candidate_size: tuple[int, int]
    overlay_png: bytes
    heatmap_png: bytes
    pixel_threshold: float
    max_changed_pixel_ratio: float
    max_mean_delta: float

    @property
    def overlay_bytes(self) -> bytes:
        return self.overlay_png

    @property
    def heatmap_bytes(self) -> bytes:
        return self.heatmap_png

    def findings(self, selector: str | None = None) -> tuple[DetectorFinding, ...]:
        findings: list[DetectorFinding] = []
        if self.dimensions_mismatch:
            findings.append(
                DetectorFinding(
                    detector="visual",
                    code="visual.dimensions_mismatch",
                    category="layout",
                    message=(
                        f"Screenshot dimensions differ: {self.baseline_size} "
                        f"!= {self.candidate_size}"
                    ),
                    severity=Severity.MAJOR,
                    selector=selector,
                    expected=self.baseline_size,
                    actual=self.candidate_size,
                    metadata={"identity_scope": "visual"},
                )
            )
        if (
            self.changed_pixel_ratio > self.max_changed_pixel_ratio
            or self.mean_delta > self.max_mean_delta
        ):
            findings.append(
                DetectorFinding(
                    detector="visual",
                    code="visual.threshold_exceeded",
                    category="visual",
                    message=(
                        "Visual difference exceeds configured thresholds "
                        f"({self.changed_pixel_ratio:.6f} changed, "
                        f"{self.mean_delta:.3f} mean delta)"
                    ),
                    severity=Severity.MAJOR,
                    selector=selector,
                    expected={
                        "max_changed_pixel_ratio": self.max_changed_pixel_ratio,
                        "max_mean_delta": self.max_mean_delta,
                    },
                    actual={
                        "changed_pixel_ratio": self.changed_pixel_ratio,
                        "mean_delta": self.mean_delta,
                    },
                )
            )
        return tuple(findings)


ImageSource = Image.Image | bytes | bytearray | memoryview | str | Path


def _open_image(source: ImageSource) -> Image.Image:
    if isinstance(source, Image.Image):
        image = source.copy()
    elif isinstance(source, (bytes, bytearray, memoryview)):
        image = Image.open(BytesIO(bytes(source)))
    else:
        image = Image.open(Path(source))
    image.load()
    return image.convert("RGBA")


def _png_bytes(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG", optimize=False, compress_level=9)
    return output.getvalue()


def _mask_pixels(
    size: tuple[int, int],
    masks: Sequence[DynamicMask | Mapping[str, Any]],
) -> tuple[set[tuple[int, int]], tuple[DynamicMask, ...]]:
    width, height = size
    normalized = tuple(DynamicMask.from_value(mask) for mask in masks)
    pixels: set[tuple[int, int]] = set()
    for mask in normalized:
        left = max(0, mask.x)
        top = max(0, mask.y)
        right = min(width, mask.x + mask.width)
        bottom = min(height, mask.y + mask.height)
        pixels.update(
            (x, y) for y in range(top, bottom) for x in range(left, right)
        )
    return pixels, normalized


def compare_images(
    baseline: ImageSource,
    candidate: ImageSource,
    *,
    masks: Sequence[DynamicMask | Mapping[str, Any]] = (),
    max_masked_ratio: float = 0.10,
    pixel_threshold: float = 0.10,
    max_changed_pixel_ratio: float = 0.005,
    max_mean_delta: float = 1.5,
    replacement_color: tuple[int, int, int, int] = (255, 0, 255, 255),
) -> VisualDiffResult:
    if not 0.0 <= max_masked_ratio <= 1.0:
        raise ValueError("max_masked_ratio must be between 0 and 1")
    if pixel_threshold < 0:
        raise ValueError("pixel_threshold must be non-negative")

    reference = _open_image(baseline)
    actual = _open_image(candidate)
    baseline_size = reference.size
    candidate_size = actual.size
    canvas_size = (
        max(baseline_size[0], candidate_size[0]),
        max(baseline_size[1], candidate_size[1]),
    )
    total_pixels = canvas_size[0] * canvas_size[1]
    if total_pixels == 0:
        raise ValueError("images must have positive dimensions")

    mask_pixels, _ = _mask_pixels(canvas_size, masks)
    masked_ratio = len(mask_pixels) / total_pixels
    if masked_ratio > max_masked_ratio:
        raise ValueError(
            f"dynamic masks cover {masked_ratio:.6f}, exceeding cap "
            f"{max_masked_ratio:.6f}"
        )

    reference_canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    actual_canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    reference_canvas.paste(reference, (0, 0))
    actual_canvas.paste(actual, (0, 0))
    reference_pixels = reference_canvas.load()
    actual_pixels = actual_canvas.load()
    heatmap = Image.new("RGBA", canvas_size, (255, 0, 0, 0))
    heatmap_pixels = heatmap.load()

    threshold = pixel_threshold * 255.0 if pixel_threshold <= 1.0 else pixel_threshold
    changed_pixels = 0
    delta_total = 0.0
    compared_pixels = total_pixels - len(mask_pixels)
    for y in range(canvas_size[1]):
        for x in range(canvas_size[0]):
            if (x, y) in mask_pixels:
                reference_pixels[x, y] = replacement_color
                actual_pixels[x, y] = replacement_color
                continue
            outside_image = (
                x >= baseline_size[0]
                or y >= baseline_size[1]
                or x >= candidate_size[0]
                or y >= candidate_size[1]
            )
            deltas = tuple(
                abs(left - right)
                for left, right in zip(
                    reference_pixels[x, y], actual_pixels[x, y], strict=True
                )
            )
            pixel_delta = sum(deltas) / len(deltas)
            if outside_image:
                pixel_delta = 255.0
            delta_total += pixel_delta
            if outside_image or max(deltas) > threshold:
                changed_pixels += 1
                alpha = max(64, min(255, round(pixel_delta)))
                heatmap_pixels[x, y] = (255, 0, 0, alpha)

    changed_ratio = changed_pixels / compared_pixels if compared_pixels else 0.0
    mean_delta = delta_total / compared_pixels if compared_pixels else 0.0
    dimensions_mismatch = baseline_size != candidate_size
    overlay = Image.blend(reference_canvas, actual_canvas, 0.5)
    passed = (
        not dimensions_mismatch
        and changed_ratio <= max_changed_pixel_ratio
        and mean_delta <= max_mean_delta
    )
    return VisualDiffResult(
        passed=passed,
        changed_pixel_ratio=changed_ratio,
        mean_delta=mean_delta,
        changed_pixels=changed_pixels,
        compared_pixels=compared_pixels,
        masked_pixel_ratio=masked_ratio,
        dimensions_mismatch=dimensions_mismatch,
        baseline_size=baseline_size,
        candidate_size=candidate_size,
        overlay_png=_png_bytes(overlay),
        heatmap_png=_png_bytes(heatmap),
        pixel_threshold=pixel_threshold,
        max_changed_pixel_ratio=max_changed_pixel_ratio,
        max_mean_delta=max_mean_delta,
    )


compare_pngs = compare_images
