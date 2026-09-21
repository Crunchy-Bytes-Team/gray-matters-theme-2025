from __future__ import annotations

import hashlib
import json
import posixpath
import random
import re
import xml.etree.ElementTree as ET
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import (
    parse_qsl,
    urlencode,
    urljoin,
    urlsplit,
    urlunsplit,
)

from store_parity.models import Page

from .classification import classify_page_type, classify_template, feature_signature
from .models import InventoryResult


FetchText = Callable[[str], Any]
_SUPPORTED_PREFIXES = ("/products/", "/collections/", "/pages/", "/blogs/")
_TRACKING_PARAMETERS = {
    "_pos",
    "_sid",
    "_ss",
    "fbclid",
    "gclid",
    "preview_theme_id",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
    "variant",
}
_SOURCE_PRIORITY = {"seed": 0, "sitemap": 1, "crawl": 2, "manual": 3}


@dataclass(frozen=True, slots=True)
class DiscoveryLimits:
    max_sitemaps: int = 100
    max_pages: int = 10_000
    max_link_pages: int = 25
    max_links_per_page: int = 100
    max_catalog_pages: int = 100

    def __post_init__(self) -> None:
        for name in (
            "max_sitemaps",
            "max_pages",
            "max_link_pages",
            "max_links_per_page",
            "max_catalog_pages",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")


def canonicalize_url(
    url: str,
    base_url: str | None = None,
    *,
    keep_query: bool = False,
) -> str:
    """Return a stable absolute HTTP URL with tracking state removed."""

    absolute = urljoin(base_url or url, url)
    split = urlsplit(absolute)
    scheme = split.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError(f"unsupported URL scheme: {split.scheme!r}")

    host = (split.hostname or "").lower().encode("idna").decode("ascii")
    if not host:
        raise ValueError("URL must include a host")
    port = split.port
    netloc = host
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"

    path = re.sub(r"/{2,}", "/", split.path or "/")
    path = posixpath.normpath(path)
    if not path.startswith("/"):
        path = f"/{path}"
    if path != "/":
        path = path.rstrip("/")

    query = ""
    if keep_query:
        kept = [
            (key, value)
            for key, value in parse_qsl(split.query, keep_blank_values=True)
            if key.lower() not in _TRACKING_PARAMETERS
        ]
        query = urlencode(sorted(kept))
    return urlunsplit((scheme, netloc, path, query, ""))


def same_origin(left: str, right: str) -> bool:
    left_parts = urlsplit(canonicalize_url(left))
    right_parts = urlsplit(canonicalize_url(right, left))
    return (left_parts.scheme, left_parts.netloc) == (
        right_parts.scheme,
        right_parts.netloc,
    )


def parse_sitemap(xml: str | bytes) -> tuple[str, tuple[str, ...]]:
    """Parse either a Shopify sitemap index or URL set."""

    root = ET.fromstring(xml)
    kind = _local_name(root.tag)
    if kind not in {"sitemapindex", "urlset"}:
        raise ValueError(f"unsupported sitemap root: {kind}")
    urls: list[str] = []
    for element in root.iter():
        if _local_name(element.tag) == "loc" and element.text:
            candidate = element.text.strip()
            if candidate:
                urls.append(candidate)
    return kind, tuple(urls)


def extract_document_urls(html: str, page_url: str) -> tuple[str | None, tuple[str, ...]]:
    parser = _DocumentLinkParser()
    parser.feed(html)
    parser.close()
    canonical = urljoin(page_url, parser.canonical) if parser.canonical else None
    links = tuple(urljoin(page_url, href) for href in parser.links)
    return canonical, links


def enrich_page_from_rendered_html(page: Page, html: str) -> Page:
    """Attach DOM-only signatures; this is the sole PageFly activation point."""

    canonical, _ = extract_document_urls(html, page.url)
    effective_url = page.url
    if canonical and same_origin(page.url, canonical):
        effective_url = canonicalize_url(canonical, page.url)
    path = urlsplit(effective_url).path
    page_type = classify_page_type(path, html)
    template = classify_template(path, html, page_type=page_type)
    signature = feature_signature(html, page_type=page_type, template=template)
    metadata = dict(page.metadata)
    metadata.update(signature.to_dict())
    metadata["canonical_url"] = effective_url
    metadata["rendered_signature"] = True
    return Page(
        id=_page_id(effective_url),
        url=effective_url,
        path=path,
        page_type=page_type,
        source=page.source,
        discovered_at=page.discovered_at,
        metadata=metadata,
    )


class InventoryDiscoverer:
    """Recursive Shopify sitemap and bounded same-origin HTML discovery."""

    def __init__(
        self,
        base_url: str,
        fetch_text: FetchText,
        *,
        limits: DiscoveryLimits | None = None,
        random_seed: int | str = 0,
        sitemap_path: str = "/sitemap.xml",
    ) -> None:
        self.base_url = canonicalize_url(base_url)
        self.fetch_text = fetch_text
        self.limits = limits or DiscoveryLimits()
        self.random_seed = random_seed
        self.sitemap_url = canonicalize_url(sitemap_path, self.base_url)

    def discover(self) -> InventoryResult:
        pages: dict[str, Page] = {}
        sitemap_urls: list[str] = []
        errors: list[str] = []
        truncated = False

        self._add_synthetic_pages(pages)
        pending = deque([self.sitemap_url])
        visited_sitemaps: set[str] = set()
        while pending:
            if len(visited_sitemaps) >= self.limits.max_sitemaps:
                truncated = True
                break
            sitemap_url = canonicalize_url(pending.popleft(), self.base_url, keep_query=True)
            if sitemap_url in visited_sitemaps or not same_origin(self.base_url, sitemap_url):
                continue
            visited_sitemaps.add(sitemap_url)
            sitemap_urls.append(sitemap_url)
            try:
                kind, locations = parse_sitemap(_response_text(self.fetch_text(sitemap_url)))
            except Exception as error:  # A failed child sitemap must not erase useful inventory.
                errors.append(f"{sitemap_url}: {error}")
                continue
            if kind == "sitemapindex":
                for location in locations:
                    if same_origin(self.base_url, location):
                        pending.append(location)
                continue
            for location in locations:
                if len(pages) >= self.limits.max_pages:
                    truncated = True
                    break
                self._add_candidate(pages, location, "sitemap", discovered_from=sitemap_url)

        crawl_queue = deque(
            page.url
            for page in sorted(pages.values(), key=_page_sort_key)
            if page.page_type != "other"
        )
        visited_documents: set[str] = set()
        while crawl_queue and len(visited_documents) < self.limits.max_link_pages:
            requested_url = crawl_queue.popleft()
            if requested_url in visited_documents:
                continue
            visited_documents.add(requested_url)
            try:
                html = _response_text(self.fetch_text(requested_url))
            except Exception as error:
                errors.append(f"{requested_url}: {error}")
                continue

            canonical, links = extract_document_urls(html, requested_url)
            effective_url = requested_url
            if canonical and same_origin(self.base_url, canonical):
                effective_url = canonicalize_url(canonical, self.base_url)
            existing = pages.get(requested_url)
            source = existing.source if existing else "crawl"
            if effective_url != requested_url:
                pages.pop(requested_url, None)
            self._add_candidate(
                pages,
                effective_url,
                source,
                html=html,
                discovered_from=requested_url,
            )

            accepted = 0
            for link in links:
                if accepted >= self.limits.max_links_per_page:
                    truncated = True
                    break
                if len(pages) >= self.limits.max_pages:
                    truncated = True
                    break
                added = self._add_candidate(
                    pages,
                    link,
                    "crawl",
                    discovered_from=effective_url,
                )
                if added:
                    accepted += 1
                    crawl_queue.append(canonicalize_url(link, self.base_url))

        ordered = tuple(sorted(pages.values(), key=_page_sort_key))
        return InventoryResult(
            pages=ordered,
            sitemap_urls=tuple(sitemap_urls),
            truncated=truncated,
            errors=tuple(errors),
        )

    def _add_synthetic_pages(self, pages: dict[str, Page]) -> None:
        for path in ("/", "/collections/all", "/search", "/cart"):
            self._add_candidate(pages, path, "seed", synthetic=True)
        rng = random.Random(str(self.random_seed))
        suffix = "".join(rng.choice("0123456789abcdef") for _ in range(16))
        self._add_candidate(
            pages,
            f"/__store-parity-404-{suffix}",
            "seed",
            synthetic=True,
            forced_page_type="other",
        )

    def _add_candidate(
        self,
        pages: dict[str, Page],
        url: str,
        source: str,
        *,
        html: str | None = None,
        discovered_from: str | None = None,
        synthetic: bool = False,
        forced_page_type: str | None = None,
    ) -> bool:
        try:
            canonical = canonicalize_url(url, self.base_url)
        except ValueError:
            return False
        if not same_origin(self.base_url, canonical):
            return False
        path = urlsplit(canonical).path
        if not synthetic and not _is_inventory_path(path):
            return False

        page_type = forced_page_type or classify_page_type(path, html)
        template = classify_template(path, html, page_type=page_type)
        signature = feature_signature(html, page_type=page_type, template=template)
        existing = pages.get(canonical)
        if existing and _SOURCE_PRIORITY[existing.source] <= _SOURCE_PRIORITY[source] and html is None:
            return False

        metadata: dict[str, Any] = dict(existing.metadata) if existing else {}
        metadata.update(signature.to_dict())
        metadata["canonical_url"] = canonical
        metadata["synthetic"] = synthetic or bool(metadata.get("synthetic"))
        if discovered_from:
            metadata["discovered_from"] = discovered_from
        pages[canonical] = Page(
            id=_page_id(canonical),
            url=canonical,
            path=path,
            page_type=page_type,
            source=existing.source if existing and source == "crawl" else source,
            metadata=metadata,
        )
        return existing is None


def discover_catalog_products(
    base_url: str,
    fetch_json: Callable[[str], Any],
    *,
    max_pages: int = 100,
    page_size: int = 250,
) -> tuple[str, ...]:
    """Paginate Shopify's public catalog endpoint when it is explicitly used."""

    if max_pages < 0 or not 1 <= page_size <= 250:
        raise ValueError("max_pages must be non-negative and page_size must be 1..250")
    base = canonicalize_url(base_url)
    urls: list[str] = []
    seen_handles: set[str] = set()
    for page_number in range(1, max_pages + 1):
        endpoint = urljoin(
            f"{base}/",
            f"products.json?limit={page_size}&page={page_number}",
        )
        raw = fetch_json(endpoint)
        if isinstance(raw, (str, bytes, bytearray)):
            payload = json.loads(raw)
        elif isinstance(raw, Mapping):
            payload = raw
        else:
            payload = json.loads(_response_text(raw))
        products = payload.get("products", [])
        if not isinstance(products, list):
            raise ValueError("catalog response 'products' must be a list")
        for product in products:
            if not isinstance(product, Mapping):
                continue
            handle = str(product.get("handle", "")).strip("/")
            if handle and handle not in seen_handles:
                seen_handles.add(handle)
                urls.append(canonicalize_url(f"/products/{handle}", base))
        if len(products) < page_size:
            break
    return tuple(urls)


def _is_inventory_path(path: str) -> bool:
    return path == "/" or any(path.startswith(prefix) for prefix in _SUPPORTED_PREFIXES)


def _response_text(response: Any) -> str:
    if isinstance(response, str):
        return response
    if isinstance(response, (bytes, bytearray)):
        return bytes(response).decode("utf-8")
    if isinstance(response, tuple) and len(response) >= 2:
        return _response_text(response[1])
    if isinstance(response, Mapping):
        for key in ("text", "body", "content"):
            if key in response:
                return _response_text(response[key])
    text = getattr(response, "text", None)
    if callable(text):
        text = text()
    if isinstance(text, str):
        return text
    content = getattr(response, "content", None)
    if isinstance(content, (str, bytes, bytearray)):
        return _response_text(content)
    raise TypeError(f"unsupported fetch response: {type(response).__name__}")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _page_id(url: str) -> str:
    return f"page-{hashlib.sha256(url.encode('utf-8')).hexdigest()[:20]}"


def _page_sort_key(page: Page) -> tuple[int, str]:
    order = {
        "home": 0,
        "collection": 1,
        "product": 2,
        "page": 3,
        "blog": 4,
        "article": 5,
        "search": 6,
        "cart": 7,
        "other": 8,
    }
    return order.get(page.page_type, 99), page.path


class _DocumentLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonical: str | None = None
        self.links: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = {name.lower(): value or "" for name, value in attrs}
        if tag == "link" and "canonical" in values.get("rel", "").lower().split():
            self.canonical = values.get("href") or self.canonical
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
