from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

from .models import (
    PAGEFLY_APPLICABLE,
    PAGEFLY_CONDITIONAL,
    PAGEFLY_NOT_APPLICABLE,
    FeatureSignature,
)


_TEMPLATE_RE = re.compile(
    r"(?:template(?:--|[-_:]))"
    r"(index|product|collection|page|blog|article|search|cart|404)\b",
    re.IGNORECASE,
)
_DATA_TEMPLATE_RE = re.compile(
    r"\b(?:data-template|data-page-type)\s*=\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)


def classify_page_type(url_or_path: str, html: str | None = None) -> str:
    path = urlsplit(url_or_path).path or "/"
    parts = [part for part in path.split("/") if part]
    if path == "/":
        return "home"
    if parts[:1] == ["products"]:
        return "product"
    if parts[:1] == ["collections"]:
        return "collection"
    if parts[:1] == ["pages"]:
        return "page"
    if parts[:1] == ["blogs"]:
        return "article" if len(parts) >= 3 else "blog"
    if parts[:1] == ["search"]:
        return "search"
    if parts[:1] == ["cart"]:
        return "cart"
    if "404" in path or (html and _has_404_marker(html)):
        return "other"
    return "other"


def classify_template(
    url_or_path: str,
    html: str | None = None,
    *,
    page_type: str | None = None,
) -> str:
    fallback = page_type or classify_page_type(url_or_path, html)
    if not html:
        return fallback

    data_match = _DATA_TEMPLATE_RE.search(html)
    if data_match:
        candidate = _normalize_template(data_match.group(1))
        if candidate:
            return candidate

    template_match = _TEMPLATE_RE.search(html)
    if template_match:
        return "home" if template_match.group(1).lower() == "index" else template_match.group(1).lower()

    page_type_match = re.search(
        r"[\"']pageType[\"']\s*:\s*[\"']([^\"']+)[\"']",
        html,
        re.IGNORECASE,
    )
    if page_type_match:
        candidate = _normalize_template(page_type_match.group(1))
        if candidate:
            return candidate
    return fallback


def feature_signature(
    html: str | None,
    *,
    page_type: str,
    template: str | None = None,
) -> FeatureSignature:
    resolved_template = template or page_type
    if not html:
        return FeatureSignature(
            template=resolved_template,
            pagefly=PAGEFLY_NOT_APPLICABLE,
        )

    parser = _SignatureParser()
    parser.feed(html)
    parser.close()
    text = " ".join(parser.tokens).lower()
    features: set[str] = set()

    signatures = {
        "announcement_bar": ("announcement-bar", "announcement_bar"),
        "header": ("site-header", "header-wrapper", "shopify-section-header"),
        "mobile_menu": ("menu-drawer", "mobile-menu", "menu_drawer"),
        "localization": ("localization-form", "localization-selector", "language-selector"),
        "desktop_search": ("predictive-search", "search-modal", "desktop-search"),
        "cart_drawer": ("cart-drawer", "cart-notification"),
        "newsletter": ("newsletter", "mailchimp", "klaviyo", "email-signup"),
        "footer_accordion": ("footer-accordion", "footer__blocks-wrapper", "footer details"),
        "collection_facets": ("facets-container", "facet-filters", "facets-form"),
        "product_form": ("product-form", "product__info", "product-info"),
        "breadcrumbs": ("breadcrumb",),
    }
    for feature, needles in signatures.items():
        if any(needle in text for needle in needles):
            features.add(feature)

    has_pagefly = parser.has_pagefly
    if has_pagefly:
        features.add("pagefly")
    pagefly = (
        PAGEFLY_APPLICABLE
        if has_pagefly and page_type == "home"
        else PAGEFLY_CONDITIONAL
        if has_pagefly
        else PAGEFLY_NOT_APPLICABLE
    )
    return FeatureSignature(
        template=resolved_template,
        features=tuple(sorted(features)),
        pagefly=pagefly,
    )


def classify_rendered_page(url_or_path: str, html: str) -> tuple[str, FeatureSignature]:
    page_type = classify_page_type(url_or_path, html)
    template = classify_template(url_or_path, html, page_type=page_type)
    return page_type, feature_signature(html, page_type=page_type, template=template)


def _normalize_template(value: str) -> str | None:
    value = value.strip().lower().replace("_", "-")
    if value in {"index", "template-index"}:
        return "home"
    for candidate in (
        "product",
        "collection",
        "page",
        "blog",
        "article",
        "search",
        "cart",
        "404",
    ):
        if candidate in value:
            return candidate
    return None


def _has_404_marker(html: str) -> bool:
    lowered = html.lower()
    return "template-404" in lowered or 'data-template="404"' in lowered


class _SignatureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tokens: list[str] = []
        self.has_pagefly = False
        self._footer_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        normalized = {name.lower(): value or "" for name, value in attrs}
        values = " ".join((tag, *normalized.keys(), *normalized.values()))
        if self._footer_depth and tag == "details":
            values += " footer details"
        self.tokens.append(values)

        if tag == "footer":
            self._footer_depth += 1
        class_value = normalized.get("class", "").lower()
        if (
            "data-pf-type" in normalized
            or any(part.startswith("__pf") for part in class_value.split())
            or "pagefly" in class_value
        ):
            self.has_pagefly = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "footer" and self._footer_depth:
            self._footer_depth -= 1
