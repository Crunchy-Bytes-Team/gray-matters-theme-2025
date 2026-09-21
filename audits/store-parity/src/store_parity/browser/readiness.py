"""Deterministic page readiness checks used before every capture."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from typing import Any, Sequence


FREEZE_STYLESHEET = """
*, *::before, *::after {
  animation-delay: 0s !important;
  animation-duration: 0s !important;
  animation-iteration-count: 1 !important;
  caret-color: transparent !important;
  scroll-behavior: auto !important;
  transition-delay: 0s !important;
  transition-duration: 0s !important;
}
"""


@dataclass(frozen=True, slots=True)
class ReadinessOptions:
    timeout_ms: int = 5_000
    font_checks: tuple[str, ...] = ()
    strict_fonts: bool = True
    wait_for_images: bool = True
    lazy_scroll_enabled: bool = True
    lazy_scroll_max_steps: int = 30
    stability_frames: int = 3
    landmark_selectors: tuple[str, ...] = ("header", "main", "footer")
    pagefly_detect_selectors: tuple[str, ...] = (
        "[data-pf-type]",
        ".__pf",
        "[class*='pagefly']",
    )
    pagefly_wait_for_network_idle: bool = True
    pagefly_extra_stable_frames: int = 3

    def __post_init__(self) -> None:
        if self.timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")
        if self.stability_frames < 1 or self.pagefly_extra_stable_frames < 1:
            raise ValueError("stability frame counts must be positive")


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    fonts_ready: bool
    font_checks: dict[str, bool]
    visible_images: int
    decoded_images: int
    failed_images: tuple[str, ...]
    stable_frames: int
    pagefly: str
    pagefly_selector: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


async def freeze_dynamic_content(page: Any) -> None:
    """Disable motion and carets without changing element geometry."""

    try:
        await page.add_style_tag(content=FREEZE_STYLESHEET)
    except Exception:
        # Third-party accelerated-checkout frames can transiently reject style
        # injection under their CSP. The audit remains valid without animation
        # freezing, so this optional stabilization must not block capture.
        return


async def lazy_scroll(page: Any, *, max_steps: int = 30) -> int:
    """Trigger viewport-based lazy loaders, then restore the page to the top."""

    return int(
        await page.evaluate(
            """async ({maxSteps}) => {
                const frame = () => new Promise(resolve => requestAnimationFrame(resolve));
                let steps = 0;
                let previousHeight = 0;
                while (steps < maxSteps) {
                    const height = Math.max(
                        document.documentElement.scrollHeight,
                        document.body?.scrollHeight || 0
                    );
                    const bottom = Math.max(0, height - window.innerHeight);
                    if (window.scrollY >= bottom && height === previousHeight) break;
                    previousHeight = height;
                    window.scrollTo(0, Math.min(bottom, window.scrollY + window.innerHeight * 0.8));
                    steps += 1;
                    await frame();
                    await frame();
                }
                window.scrollTo(0, 0);
                await frame();
                return steps;
            }""",
            {"maxSteps": max_steps},
        )
    )


async def _wait_for_fonts(page: Any, options: ReadinessOptions) -> dict[str, bool]:
    async def evaluate() -> dict[str, bool]:
        return await page.evaluate(
            """async checks => {
                if (!document.fonts) return Object.fromEntries(checks.map(item => [item, true]));
                await document.fonts.ready;
                return Object.fromEntries(checks.map(item => [item, document.fonts.check(item)]));
            }""",
            list(options.font_checks),
        )

    result = await asyncio.wait_for(evaluate(), timeout=options.timeout_ms / 1_000)
    normalized = {str(key): bool(value) for key, value in result.items()}
    missing = [font for font, loaded in normalized.items() if not loaded]
    if missing and options.strict_fonts:
        raise RuntimeError(f"required fonts did not load: {', '.join(missing)}")
    return normalized


async def _decode_visible_images(page: Any, timeout_ms: int) -> dict[str, Any]:
    async def evaluate() -> dict[str, Any]:
        return await page.evaluate(
            """async () => {
                const visible = [...document.images].filter(image => {
                    const style = getComputedStyle(image);
                    const rect = image.getBoundingClientRect();
                    return style.display !== 'none' && style.visibility !== 'hidden'
                        && Number(style.opacity) !== 0 && rect.width > 0 && rect.height > 0;
                });
                const failed = [];
                await Promise.all(visible.map(async image => {
                    try {
                        if (!image.complete) {
                            await new Promise((resolve, reject) => {
                                image.addEventListener('load', resolve, {once: true});
                                image.addEventListener('error', reject, {once: true});
                            });
                        }
                        await image.decode();
                        if (!image.naturalWidth || !image.naturalHeight) throw new Error('empty image');
                    } catch (_) {
                        failed.push(image.currentSrc || image.src || '');
                    }
                }));
                return {visible: visible.length, decoded: visible.length - failed.length, failed};
            }"""
        )

    return await asyncio.wait_for(evaluate(), timeout=timeout_ms / 1_000)


async def _stable_layout(
    page: Any,
    *,
    selectors: Sequence[str],
    required_frames: int,
    timeout_ms: int,
) -> int:
    result = await page.evaluate(
        """({selectors, requiredFrames, timeoutMs}) => new Promise((resolve, reject) => {
            const started = performance.now();
            let previous = '';
            let stable = 0;
            const sample = () => JSON.stringify({
                width: document.documentElement.scrollWidth,
                height: document.documentElement.scrollHeight,
                landmarks: selectors.map(selector => {
                    const node = document.querySelector(selector);
                    if (!node) return null;
                    const rect = node.getBoundingClientRect();
                    return [
                        Math.round(rect.x * 100) / 100,
                        Math.round(rect.y * 100) / 100,
                        Math.round(rect.width * 100) / 100,
                        Math.round(rect.height * 100) / 100
                    ];
                })
            });
            const check = () => {
                const current = sample();
                stable = current === previous ? stable + 1 : 0;
                previous = current;
                if (stable >= requiredFrames) return resolve(stable);
                if (performance.now() - started >= timeoutMs) {
                    return reject(new Error(`layout did not stabilize within ${timeoutMs}ms`));
                }
                requestAnimationFrame(check);
            };
            requestAnimationFrame(check);
        })""",
        {
            "selectors": list(selectors),
            "requiredFrames": required_frames,
            "timeoutMs": timeout_ms,
        },
    )
    return int(result)


async def _detect_pagefly(page: Any, selectors: Sequence[str]) -> str | None:
    return await page.evaluate(
        """selectors => selectors.find(selector => {
            try { return Boolean(document.querySelector(selector)); }
            catch (_) { return false; }
        }) || null""",
        list(selectors),
    )


async def wait_for_readiness(
    page: Any,
    options: ReadinessOptions | None = None,
) -> ReadinessResult:
    """Wait for render prerequisites and return auditable readiness evidence."""

    options = options or ReadinessOptions()
    await freeze_dynamic_content(page)
    font_checks = await _wait_for_fonts(page, options)

    if options.lazy_scroll_enabled:
        await lazy_scroll(page, max_steps=options.lazy_scroll_max_steps)

    image_result: dict[str, Any] = {"visible": 0, "decoded": 0, "failed": []}
    if options.wait_for_images:
        try:
            image_result = await _decode_visible_images(page, options.timeout_ms)
        except TimeoutError:
            image_result = {
                "visible": 0,
                "decoded": 0,
                "failed": ["__visible_image_decode_timeout__"],
            }

    pagefly_selector = await _detect_pagefly(page, options.pagefly_detect_selectors)
    pagefly_status = "not_applicable"
    required_frames = options.stability_frames
    if pagefly_selector:
        pagefly_status = "ready"
        required_frames += options.pagefly_extra_stable_frames
        if options.pagefly_wait_for_network_idle:
            try:
                await page.wait_for_load_state("networkidle", timeout=options.timeout_ms)
            except Exception:
                # Third-party storefront connections can remain open indefinitely.
                pagefly_status = "network_idle_timeout"

    stable_frames = await _stable_layout(
        page,
        selectors=options.landmark_selectors,
        required_frames=required_frames,
        timeout_ms=options.timeout_ms,
    )
    return ReadinessResult(
        fonts_ready=True,
        font_checks=font_checks,
        visible_images=int(image_result["visible"]),
        decoded_images=int(image_result["decoded"]),
        failed_images=tuple(str(item) for item in image_result["failed"]),
        stable_frames=stable_frames,
        pagefly=pagefly_status,
        pagefly_selector=pagefly_selector,
    )


# A concise alias for callers that model readiness as a verb.
wait_until_ready = wait_for_readiness
