from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from store_parity.models import Page

from .models import metadata_signature


PROFILE_PAGE_TYPES: Mapping[str, tuple[str, ...]] = {
    "mobile-p0": ("home", "collection", "product"),
    "smoke": (
        "home",
        "collection",
        "product",
        "page",
        "blog",
        "article",
        "search",
        "cart",
        "other",
    ),
    "full": (
        "home",
        "collection",
        "product",
        "page",
        "blog",
        "article",
        "search",
        "cart",
        "other",
    ),
}


def page_coverage_tokens(page: Page) -> frozenset[str]:
    signature = metadata_signature(page.metadata)
    tokens = {
        f"type:{page.page_type}",
        f"source:{page.source}",
        *signature.tokens(),
    }
    if page.metadata.get("synthetic"):
        tokens.add("route:synthetic")
    if page.path == "/collections/all":
        tokens.add("route:catalog")
    elif page.path == "/search":
        tokens.add("route:search")
    elif page.path == "/cart":
        tokens.add("route:cart")
    elif "404" in page.path:
        tokens.add("route:404")
    return frozenset(tokens)


def greedy_set_cover(
    pages: Iterable[Page],
    required_tokens: Iterable[str] | None = None,
    *,
    limit: int | None = None,
) -> tuple[Page, ...]:
    """Choose stable representatives using gain, route priority, then path."""

    candidates = tuple(_deduplicate_pages(pages))
    if limit is not None and limit < 0:
        raise ValueError("limit must be non-negative")
    if not candidates or limit == 0:
        return ()

    token_map = {page.id: page_coverage_tokens(page) for page in candidates}
    uncovered = (
        set(required_tokens)
        if required_tokens is not None
        else set().union(*(token_map[page.id] for page in candidates))
    )
    selected: list[Page] = []
    remaining = list(candidates)
    while uncovered and remaining and (limit is None or len(selected) < limit):
        ranked = sorted(
            remaining,
            key=lambda page: (
                -len(token_map[page.id] & uncovered),
                _route_priority(page),
                page.path,
                page.url,
            ),
        )
        winner = ranked[0]
        gain = token_map[winner.id] & uncovered
        if not gain:
            break
        selected.append(winner)
        uncovered.difference_update(gain)
        remaining.remove(winner)
    return tuple(selected)


def select_profile_routes(
    pages: Sequence[Page] | Iterable[Page],
    profile: str,
    *,
    max_representatives: int | None = None,
) -> tuple[Page, ...]:
    if profile not in PROFILE_PAGE_TYPES:
        raise ValueError(f"unknown inventory profile: {profile}")
    ordered = tuple(sorted(_deduplicate_pages(pages), key=_page_sort_key))
    allowed = set(PROFILE_PAGE_TYPES[profile])
    eligible = tuple(page for page in ordered if page.page_type in allowed)
    if profile == "full":
        return eligible if max_representatives is None else eligible[:max_representatives]

    required_types = {
        f"type:{page_type}"
        for page_type in PROFILE_PAGE_TYPES[profile]
        if any(page.page_type == page_type for page in eligible)
    }
    if profile == "mobile-p0":
        default_limit = 3
        required = required_types
    else:
        default_limit = 12
        required = required_types | set().union(
            *(page_coverage_tokens(page) for page in eligible)
        )
    limit = default_limit if max_representatives is None else max_representatives
    selected = list(greedy_set_cover(eligible, required, limit=limit))

    # Route type coverage is a hard invariant even when feature-rich pages win first.
    selected_ids = {page.id for page in selected}
    for page_type in PROFILE_PAGE_TYPES[profile]:
        if any(page.page_type == page_type for page in selected):
            continue
        representative = next(
            (page for page in eligible if page.page_type == page_type),
            None,
        )
        if representative and representative.id not in selected_ids:
            if max_representatives is not None and len(selected) >= max_representatives:
                break
            selected.append(representative)
            selected_ids.add(representative.id)
    return tuple(sorted(selected, key=_page_sort_key))


def profile_coverage(
    selected: Iterable[Page],
    inventory: Iterable[Page],
) -> dict[str, Any]:
    selected_pages = tuple(selected)
    inventory_pages = tuple(inventory)
    available = set().union(*(page_coverage_tokens(page) for page in inventory_pages))
    covered = set().union(*(page_coverage_tokens(page) for page in selected_pages))
    return {
        "selected_routes": len(selected_pages),
        "inventory_routes": len(inventory_pages),
        "covered_tokens": sorted(covered),
        "uncovered_tokens": sorted(available - covered),
        "page_types": {
            page_type: sum(page.page_type == page_type for page in selected_pages)
            for page_type in sorted({page.page_type for page in inventory_pages})
        },
    }


def _deduplicate_pages(pages: Iterable[Page]) -> list[Page]:
    by_url: dict[str, Page] = {}
    for page in pages:
        by_url.setdefault(page.url, page)
    return list(by_url.values())


def _route_priority(page: Page) -> tuple[int, int]:
    type_order = {
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
    synthetic = 1 if page.metadata.get("synthetic") else 0
    return type_order.get(page.page_type, 99), synthetic


def _page_sort_key(page: Page) -> tuple[int, int, str, str]:
    return (*_route_priority(page), page.path, page.url)
