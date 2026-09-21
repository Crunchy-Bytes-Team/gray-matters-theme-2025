"""Structured page evidence collectors for store parity comparisons."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from store_parity.browser.readiness import (
    ReadinessOptions,
    ReadinessResult,
    wait_for_readiness,
)
from store_parity.capture.screenshots import ScreenshotSet, capture_screenshot_set


DEFAULT_ICON_SELECTORS = (
    "svg",
    "img[src*='icon' i]",
    "[class*='icon' i]",
    "i",
)


@dataclass(frozen=True, slots=True)
class CaptureOptions:
    landmark_selectors: Mapping[str, str] | Sequence[str] = field(
        default_factory=lambda: ("header", "main", "footer")
    )
    component_selectors: Mapping[str, str] | Sequence[str] = field(default_factory=tuple)
    icon_selectors: tuple[str, ...] = DEFAULT_ICON_SELECTORS
    max_dom_nodes: int = 10_000
    max_full_width: int = 4_096
    max_full_height: int = 16_384
    max_component_width: int = 4_096
    max_component_height: int = 8_192
    component_padding: int = 0
    readiness: ReadinessOptions = field(default_factory=ReadinessOptions)


@dataclass(frozen=True, slots=True)
class CaptureBundle:
    requested_url: str
    final_url: str
    screenshots: ScreenshotSet
    dom: Mapping[str, Any]
    landmarks: Mapping[str, Any]
    icons: tuple[Mapping[str, Any], ...]
    overflow_offenders: tuple[Mapping[str, Any], ...]
    console_errors: tuple[Mapping[str, Any], ...]
    failed_first_party_requests: tuple[Mapping[str, Any], ...]
    readiness: ReadinessResult

    def metadata(self) -> dict[str, Any]:
        """Return the JSON-safe evidence, excluding binary PNG payloads."""

        return {
            "requested_url": self.requested_url,
            "final_url": self.final_url,
            "screenshots": {
                "viewport_bytes": len(self.screenshots.viewport),
                "full_page_bytes": len(self.screenshots.full_page),
                "components": {
                    name: len(content)
                    for name, content in self.screenshots.components.items()
                },
                "missing_components": list(self.screenshots.missing_components),
            },
            "dom": dict(self.dom),
            "landmarks": dict(self.landmarks),
            "icons": [dict(item) for item in self.icons],
            "overflow_offenders": [
                dict(item) for item in self.overflow_offenders
            ],
            "console_errors": [dict(item) for item in self.console_errors],
            "failed_first_party_requests": [
                dict(item) for item in self.failed_first_party_requests
            ],
            "readiness": self.readiness.to_dict(),
        }


async def collect_dom_snapshot(page: Any, *, max_nodes: int = 10_000) -> dict[str, Any]:
    if max_nodes <= 0:
        raise ValueError("max_nodes must be positive")
    return await page.evaluate(
        """maxNodes => {
            const ignored = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE']);
            const meaningfulAttributes = [
                'alt', 'aria-checked', 'aria-current', 'aria-expanded', 'aria-hidden',
                'aria-label', 'aria-labelledby', 'aria-pressed', 'aria-selected',
                'disabled', 'for', 'href', 'name', 'open', 'placeholder', 'role',
                'src', 'title', 'type', 'value'
            ];
            const normalize = value => String(value || '').replace(/\\s+/g, ' ').trim();
            const pathFor = element => {
                const parts = [];
                let node = element;
                while (node && node.nodeType === Node.ELEMENT_NODE && parts.length < 8) {
                    let part = node.tagName.toLowerCase();
                    if (node.id) {
                        part += `#${node.id}`;
                        parts.unshift(part);
                        break;
                    }
                    const siblings = node.parentElement
                        ? [...node.parentElement.children].filter(item => item.tagName === node.tagName)
                        : [];
                    if (siblings.length > 1) part += `:nth-of-type(${siblings.indexOf(node) + 1})`;
                    parts.unshift(part);
                    node = node.parentElement;
                }
                return parts.join(' > ');
            };
            const nodes = [];
            let truncated = false;
            const walker = document.createTreeWalker(
                document.body || document.documentElement,
                NodeFilter.SHOW_ELEMENT
            );
            let element = walker.currentNode;
            while (element) {
                if (!ignored.has(element.tagName)) {
                    if (nodes.length >= maxNodes) {
                        truncated = true;
                        break;
                    }
                    const attributes = {};
                    for (const name of meaningfulAttributes) {
                        if (element.hasAttribute(name)) {
                            attributes[name] = normalize(element.getAttribute(name));
                        }
                    }
                    const directText = normalize(
                        [...element.childNodes]
                            .filter(node => node.nodeType === Node.TEXT_NODE)
                            .map(node => node.textContent)
                            .join(' ')
                    );
                    const style = getComputedStyle(element);
                    nodes.push({
                        path: pathFor(element),
                        tag: element.tagName.toLowerCase(),
                        role: element.getAttribute('role') || null,
                        text: directText || null,
                        attributes,
                        hidden: element.hidden || style.display === 'none'
                            || style.visibility === 'hidden' || style.opacity === '0'
                    });
                }
                element = walker.nextNode();
            }
            return {
                url: location.href,
                title: document.title,
                language: document.documentElement.lang || null,
                direction: document.documentElement.dir || getComputedStyle(document.documentElement).direction,
                nodes,
                truncated
            };
        }""",
        max_nodes,
    )


def _selector_entries(
    selectors: Mapping[str, str] | Sequence[str],
) -> list[tuple[str, str]]:
    if isinstance(selectors, Mapping):
        return [(str(name), str(selector)) for name, selector in selectors.items()]
    return [(str(selector), str(selector)) for selector in selectors]


async def collect_landmarks(
    page: Any,
    selectors: Mapping[str, str] | Sequence[str],
) -> dict[str, Any]:
    entries = _selector_entries(selectors)
    return await page.evaluate(
        """entries => {
            const properties = [
                'display', 'position', 'visibility', 'opacity', 'overflowX', 'overflowY',
                'color', 'backgroundColor', 'fontFamily', 'fontSize', 'fontStyle',
                'fontWeight', 'lineHeight', 'letterSpacing', 'textAlign', 'textTransform',
                'marginTop', 'marginRight', 'marginBottom', 'marginLeft',
                'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
                'borderTopWidth', 'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth',
                'borderTopColor', 'borderRightColor', 'borderBottomColor', 'borderLeftColor',
                'borderRadius', 'boxSizing', 'zIndex'
            ];
            const output = {};
            for (const [name, selector] of entries) {
                let elements = [];
                try { elements = [...document.querySelectorAll(selector)]; }
                catch (error) {
                    output[name] = {selector, error: String(error), matches: []};
                    continue;
                }
                output[name] = {
                    selector,
                    matches: elements.map((element, index) => {
                        const rect = element.getBoundingClientRect();
                        const style = getComputedStyle(element);
                        return {
                            index,
                            geometry: {
                                x: rect.x, y: rect.y,
                                documentX: rect.x + window.scrollX,
                                documentY: rect.y + window.scrollY,
                                width: rect.width, height: rect.height,
                                top: rect.top, right: rect.right,
                                bottom: rect.bottom, left: rect.left
                            },
                            style: Object.fromEntries(properties.map(property => [
                                property, style[property]
                            ]))
                        };
                    })
                };
            }
            return output;
        }""",
        entries,
    )


def _fingerprint(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


async def collect_icon_fingerprints(
    page: Any,
    selectors: Sequence[str] = DEFAULT_ICON_SELECTORS,
) -> tuple[dict[str, Any], ...]:
    raw: list[dict[str, Any]] = await page.evaluate(
        """selectors => {
            const seen = new Set();
            const elements = [];
            for (const selector of selectors) {
                try {
                    for (const element of document.querySelectorAll(selector)) {
                        if (!seen.has(element)) {
                            seen.add(element);
                            elements.push(element);
                        }
                    }
                } catch (_) {}
            }
            const cssPath = element => {
                if (element.id) return `${element.tagName.toLowerCase()}#${element.id}`;
                const classes = [...element.classList].slice(0, 3)
                    .map(value => `.${CSS.escape(value)}`).join('');
                return `${element.tagName.toLowerCase()}${classes}`;
            };
            const pseudo = (element, which) => {
                const style = getComputedStyle(element, which);
                const content = style.content;
                if (!content || content === 'none' || content === 'normal') return null;
                return {
                    content,
                    fontFamily: style.fontFamily,
                    fontSize: style.fontSize,
                    fontStyle: style.fontStyle,
                    fontWeight: style.fontWeight
                };
            };
            return elements.map(element => {
                const base = {selector: cssPath(element)};
                if (element instanceof SVGElement) {
                    const svg = element.closest('svg') || element;
                    return {
                        ...base,
                        kind: 'svg',
                        viewBox: svg.getAttribute('viewBox'),
                        paths: [...svg.querySelectorAll('path')].map(path => path.getAttribute('d') || ''),
                        uses: [...svg.querySelectorAll('use')].map(use =>
                            use.getAttribute('href') || use.getAttribute('xlink:href') || ''
                        )
                    };
                }
                if (element instanceof HTMLImageElement) {
                    return {
                        ...base,
                        kind: 'img',
                        source: element.currentSrc || element.src,
                        naturalWidth: element.naturalWidth,
                        naturalHeight: element.naturalHeight,
                        alt: element.alt
                    };
                }
                const style = getComputedStyle(element);
                return {
                    ...base,
                    kind: 'font',
                    glyph: element.textContent?.trim() || '',
                    codepoints: [...(element.textContent?.trim() || '')]
                        .map(character => character.codePointAt(0)),
                    fontFamily: style.fontFamily,
                    fontSize: style.fontSize,
                    fontStyle: style.fontStyle,
                    fontWeight: style.fontWeight,
                    before: pseudo(element, '::before'),
                    after: pseudo(element, '::after')
                };
            });
        }""",
        list(selectors),
    )
    fingerprints: list[dict[str, Any]] = []
    for item in raw:
        value = dict(item)
        value["sha256"] = _fingerprint(value)
        fingerprints.append(value)
    return tuple(fingerprints)


async def collect_overflow_offenders(page: Any) -> tuple[dict[str, Any], ...]:
    values = await page.evaluate(
        """() => {
            const viewportWidth = document.documentElement.clientWidth;
            const selector = element => {
                if (element.id) return `${element.tagName.toLowerCase()}#${element.id}`;
                const classes = [...element.classList].slice(0, 3)
                    .map(value => `.${CSS.escape(value)}`).join('');
                return `${element.tagName.toLowerCase()}${classes}`;
            };
            return [...document.querySelectorAll('body *')].flatMap(element => {
                const style = getComputedStyle(element);
                if (style.display === 'none') return [];
                const rect = element.getBoundingClientRect();
                const ownOverflow = element.scrollWidth > element.clientWidth + 1;
                const viewportOverflow = rect.left < -1 || rect.right > viewportWidth + 1;
                if (!ownOverflow && !viewportOverflow) return [];
                return [{
                    selector: selector(element),
                    rect: {
                        left: rect.left, right: rect.right,
                        width: rect.width, height: rect.height
                    },
                    clientWidth: element.clientWidth,
                    scrollWidth: element.scrollWidth,
                    ownOverflow,
                    viewportOverflow
                }];
            }).sort((left, right) =>
                (right.rect.right - viewportWidth) - (left.rect.right - viewportWidth)
            );
        }"""
    )
    return tuple(dict(item) for item in values)


def collect_runtime_failures(source: Any) -> dict[str, tuple[dict[str, Any], ...]]:
    telemetry = getattr(source, "telemetry", source)
    if hasattr(telemetry, "snapshot"):
        value = telemetry.snapshot()
    elif isinstance(telemetry, Mapping):
        value = telemetry
    else:
        value = {}
    return {
        "console_errors": tuple(
            dict(item) for item in value.get("console_errors", ())
        ),
        "failed_first_party_requests": tuple(
            dict(item) for item in value.get("failed_first_party_requests", ())
        ),
    }


async def capture_page(
    page: Any,
    *,
    session: Any | None = None,
    requested_url: str | None = None,
    options: CaptureOptions | None = None,
) -> CaptureBundle:
    options = options or CaptureOptions()
    readiness = await wait_for_readiness(page, options.readiness)
    screenshots = await capture_screenshot_set(
        page,
        component_selectors=options.component_selectors,
        component_padding=options.component_padding,
        max_full_width=options.max_full_width,
        max_full_height=options.max_full_height,
        max_component_width=options.max_component_width,
        max_component_height=options.max_component_height,
    )
    dom = await collect_dom_snapshot(page, max_nodes=options.max_dom_nodes)
    landmarks = await collect_landmarks(page, options.landmark_selectors)
    icons = await collect_icon_fingerprints(page, options.icon_selectors)
    overflow = await collect_overflow_offenders(page)
    failures = collect_runtime_failures(session or {})

    if requested_url is None and session is not None and session.navigations:
        requested_url = session.navigations[-1].requested_url
    return CaptureBundle(
        requested_url=requested_url or str(page.url),
        final_url=str(page.url),
        screenshots=screenshots,
        dom=dom,
        landmarks=landmarks,
        icons=icons,
        overflow_offenders=overflow,
        console_errors=failures["console_errors"],
        failed_first_party_requests=failures["failed_first_party_requests"],
        readiness=readiness,
    )
