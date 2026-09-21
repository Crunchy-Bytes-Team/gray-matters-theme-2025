from __future__ import annotations

from store_parity.inventory import (
    DiscoveryLimits,
    InventoryDiscoverer,
    PAGEFLY_CONDITIONAL,
    PAGEFLY_NOT_APPLICABLE,
    canonicalize_url,
    classify_rendered_page,
    discover_catalog_products,
    enrich_page_from_rendered_html,
)
from store_parity.models import Page


SITEMAP_INDEX = """\
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://shop.example/sitemap_products_1.xml?from=1&amp;to=9</loc></sitemap>
  <sitemap><loc>https://shop.example/sitemap_collections_1.xml</loc></sitemap>
  <sitemap><loc>https://outside.example/ignored.xml</loc></sitemap>
</sitemapindex>
"""

PRODUCT_SITEMAP = """\
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://shop.example/products/boot?variant=123</loc></url>
  <url><loc>https://shop.example/pages/about/</loc></url>
  <url><loc>https://shop.example/blogs/news</loc></url>
  <url><loc>https://shop.example/blogs/news/launch</loc></url>
</urlset>
"""

COLLECTION_SITEMAP = """\
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://shop.example/collections/summer</loc></url>
</urlset>
"""

HOME_HTML = """\
<html class="template-index">
  <head><link rel="canonical" href="https://shop.example/"></head>
  <body>
    <header class="header-wrapper"><a href="/pages/contact?utm_source=test">Contact</a></header>
    <a href="https://outside.example/products/no">External</a>
  </body>
</html>
"""


def test_recursive_sitemap_and_bounded_same_origin_link_discovery() -> None:
    fixtures = {
        "https://shop.example/sitemap.xml": SITEMAP_INDEX,
        "https://shop.example/sitemap_products_1.xml?from=1&to=9": PRODUCT_SITEMAP,
        "https://shop.example/sitemap_collections_1.xml": COLLECTION_SITEMAP,
        "https://shop.example/": HOME_HTML,
    }

    def fetch(url: str) -> str:
        return fixtures.get(url, "<html><main>fixture</main></html>")

    result = InventoryDiscoverer(
        "https://SHOP.example/",
        fetch,
        limits=DiscoveryLimits(max_link_pages=10, max_links_per_page=5),
        random_seed=42,
    ).discover()

    paths = result.by_path()
    assert {
        "/",
        "/collections/all",
        "/collections/summer",
        "/products/boot",
        "/pages/about",
        "/pages/contact",
        "/blogs/news",
        "/blogs/news/launch",
        "/search",
        "/cart",
    } <= paths.keys()
    assert all(page.url.startswith("https://shop.example/") for page in result.pages)
    assert not any("outside.example" in page.url for page in result.pages)
    assert len([path for path in paths if "__store-parity-404-" in path]) == 1
    assert len(result.sitemap_urls) == 3


def test_canonicalization_and_rendered_pagefly_are_deliberate() -> None:
    assert (
        canonicalize_url(
            "HTTPS://Shop.Example:443/products/../products/boot/?utm_source=x&variant=2"
        )
        == "https://shop.example/products/boot"
    )
    page_type, plain = classify_rendered_page(
        "/pages/about",
        '<body class="template-page"><main class="rte">About</main></body>',
    )
    assert page_type == "page"
    assert plain.pagefly == PAGEFLY_NOT_APPLICABLE

    _, pagefly = classify_rendered_page(
        "/pages/campaign",
        '<body class="template-page"><div data-pf-type="Section"></div></body>',
    )
    assert pagefly.pagefly == PAGEFLY_CONDITIONAL
    assert "pagefly" in pagefly.features


def test_rendered_dom_enrichment_activates_conditional_pagefly() -> None:
    page = Page(
        id="campaign",
        url="https://shop.example/pages/campaign?utm_source=inventory",
        path="/pages/campaign",
        page_type="page",
        source="sitemap",
        metadata={"pagefly": PAGEFLY_NOT_APPLICABLE},
    )
    enriched = enrich_page_from_rendered_html(
        page,
        """
        <html data-template="page.campaign">
          <head><link rel="canonical" href="/pages/campaign"></head>
          <body><section class="__pf"><div data-pf-type="Column"></div></section></body>
        </html>
        """,
    )
    assert enriched.url == "https://shop.example/pages/campaign"
    assert enriched.metadata["pagefly"] == PAGEFLY_CONDITIONAL
    assert enriched.metadata["rendered_signature"] is True


def test_catalog_endpoint_is_paginated_until_short_page() -> None:
    requested: list[str] = []

    def fetch_json(url: str) -> dict[str, object]:
        requested.append(url)
        if "page=1" in url:
            return {"products": [{"handle": "one"}, {"handle": "two"}]}
        return {"products": [{"handle": "three"}]}

    urls = discover_catalog_products(
        "https://shop.example",
        fetch_json,
        page_size=2,
    )
    assert urls == (
        "https://shop.example/products/one",
        "https://shop.example/products/two",
        "https://shop.example/products/three",
    )
    assert len(requested) == 2
