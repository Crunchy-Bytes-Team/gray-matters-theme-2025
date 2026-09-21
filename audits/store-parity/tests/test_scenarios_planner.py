from __future__ import annotations

import json

from store_parity.inventory import greedy_set_cover, select_profile_routes
from store_parity.models import Page
from store_parity.scenarios import (
    BREAKPOINT_PROBES,
    SCENARIO_DEFINITIONS,
    ScenarioPlanner,
)


def _page(
    path: str,
    page_type: str,
    *,
    template: str | None = None,
    features: tuple[str, ...] = (),
) -> Page:
    return Page(
        id=f"page-{path.replace('/', '-') or 'home'}",
        url=f"https://shop.example{path}",
        path=path,
        page_type=page_type,
        source="sitemap",
        metadata={
            "template": template or page_type,
            "features": list(features),
            "pagefly": "not_applicable",
        },
    )


def _inventory() -> tuple[Page, ...]:
    return (
        _page("/", "home", features=("header", "mobile_menu", "newsletter")),
        _page("/collections/all", "collection", features=("collection_facets",)),
        _page("/collections/summer", "collection"),
        _page("/products/boot", "product", features=("product_form",)),
        _page("/pages/about", "page"),
        _page("/blogs/news", "blog"),
        _page("/blogs/news/launch", "article"),
        _page("/search", "search"),
        _page("/cart", "cart"),
        _page("/__store-parity-404-deadbeef", "other"),
    )


def test_profile_route_selection_and_set_cover_are_deterministic() -> None:
    inventory = _inventory()
    first = select_profile_routes(inventory, "mobile-p0")
    second = select_profile_routes(tuple(reversed(inventory)), "mobile-p0")
    assert [page.path for page in first] == [page.path for page in second]
    assert {page.page_type for page in first} == {"home", "collection", "product"}

    representatives = greedy_set_cover(inventory, limit=5)
    assert representatives == greedy_set_cover(reversed(inventory), limit=5)
    assert len(representatives) <= 5


def test_full_plan_has_exact_breakpoint_neighborhoods_and_serializes() -> None:
    expected = {
        749,
        750,
        751,
        766,
        767,
        768,
        989,
        990,
        991,
        992,
        993,
        1023,
        1024,
        1025,
    }
    assert set(BREAKPOINT_PROBES) == expected

    plan = ScenarioPlanner().plan(_inventory(), "full")
    baseline_widths = {
        case.viewport.width
        for case in plan.cases
        if case.scenario == "baseline" and case.viewport_kind == "breakpoint"
    }
    assert baseline_widths == expected
    assert plan.coverage.total_cases == len(plan.cases)
    assert plan.coverage.required_cases > 0
    assert plan.coverage.optional_cases > 0
    json.dumps(plan.to_dict())

    breakpoint_pages = {
        case.page_id
        for case in plan.cases
        if case.viewport_kind == "breakpoint"
    }
    assert len(breakpoint_pages) <= 6
    global_routes = {
        case.page_id
        for case in plan.cases
        if case.scenario == "mobile-menu-open"
    }
    assert len(global_routes) == 1
    primary_baselines = {
        case.page_type
        for case in plan.cases
        if case.scenario == "baseline" and case.viewport_kind != "breakpoint"
    }
    assert primary_baselines == {"home"}
    assert any(
        case.page_type == "product" and case.scenario == "product-state"
        for case in plan.cases
    )


def test_scenario_contracts_mark_requirements_and_landmarks() -> None:
    assert SCENARIO_DEFINITIONS["baseline"].required
    assert SCENARIO_DEFINITIONS["cart-empty"].required
    assert not SCENARIO_DEFINITIONS["newsletter-timed"].required
    assert any(
        landmark.required
        for landmark in SCENARIO_DEFINITIONS["mobile-menu-open"].landmarks
    )
    language = SCENARIO_DEFINITIONS["mobile-menu-language-open"]
    assert any(
        landmark.name == "language-accordion" and not landmark.required
        for landmark in language.landmarks
    )
