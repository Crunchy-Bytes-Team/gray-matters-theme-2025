from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from store_parity.compare import DynamicMask, compare_images


def _png(
    size: tuple[int, int] = (10, 10),
    color: tuple[int, int, int, int] = (255, 255, 255, 255),
    changes: dict[tuple[int, int], tuple[int, int, int, int]] | None = None,
) -> bytes:
    image = Image.new("RGBA", size, color)
    for point, value in (changes or {}).items():
        image.putpixel(point, value)
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def test_identical_images_have_lossless_empty_diff() -> None:
    source = _png()
    result = compare_images(source, source)

    assert result.passed
    assert result.changed_pixel_ratio == 0
    assert result.mean_delta == 0
    assert Image.open(BytesIO(result.overlay_png)).format == "PNG"
    assert Image.open(BytesIO(result.heatmap_png)).getpixel((0, 0)) == (255, 0, 0, 0)


def test_one_pixel_and_region_differences_are_measured() -> None:
    baseline = _png()
    one_pixel = _png(changes={(2, 3): (0, 0, 0, 255)})
    result = compare_images(baseline, one_pixel)

    assert result.changed_pixels == 1
    assert result.changed_pixel_ratio == pytest.approx(0.01)
    assert result.mean_delta == pytest.approx(255 * 3 / 4 / 100)
    assert not result.passed
    assert Image.open(BytesIO(result.heatmap_png)).getpixel((2, 3))[0] == 255

    region = _png(
        changes={
            (x, y): (255, 0, 0, 255)
            for y in range(2)
            for x in range(5)
        }
    )
    region_result = compare_images(
        baseline,
        region,
        max_changed_pixel_ratio=0.2,
        max_mean_delta=100,
    )
    assert region_result.changed_pixels == 10
    assert region_result.changed_pixel_ratio == pytest.approx(0.1)
    assert region_result.passed


def test_dimension_mismatch_always_fails() -> None:
    result = compare_images(_png((10, 10)), _png((11, 10)))

    assert result.dimensions_mismatch
    assert not result.passed
    assert result.changed_pixels == 10
    assert result.findings()[0].code == "visual.dimensions_mismatch"


def test_dynamic_masks_are_explicit_and_capped() -> None:
    baseline = _png()
    candidate = _png(changes={(0, 0): (0, 0, 0, 255)})
    result = compare_images(
        baseline,
        candidate,
        masks=(DynamicMask(0, 0, 1, 1, "rotating promotion"),),
    )
    assert result.passed
    assert result.changed_pixels == 0
    assert result.masked_pixel_ratio == pytest.approx(0.01)

    with pytest.raises(ValueError, match="explicit reason"):
        compare_images(
            baseline,
            candidate,
            masks=({"x": 0, "y": 0, "width": 1, "height": 1},),
        )
    with pytest.raises(ValueError, match="exceeding cap"):
        compare_images(
            baseline,
            candidate,
            masks=(DynamicMask(0, 0, 5, 5, "too broad"),),
            max_masked_ratio=0.1,
        )
