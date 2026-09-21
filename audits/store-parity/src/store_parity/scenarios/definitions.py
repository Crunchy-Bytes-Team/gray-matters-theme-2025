from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


ALL_PAGE_TYPES = (
    "home",
    "collection",
    "product",
    "page",
    "blog",
    "article",
    "search",
    "cart",
    "other",
)


@dataclass(frozen=True, slots=True)
class Landmark:
    name: str
    selector: str
    required: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ScenarioStep:
    action: str
    target: str | None = None
    value: str | int | float | bool | None = None
    required: bool = True
    wait_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ScenarioDefinition:
    name: str
    required: bool
    page_types: tuple[str, ...]
    viewport_kinds: tuple[str, ...]
    landmarks: tuple[Landmark, ...]
    steps: tuple[ScenarioStep, ...] = ()
    feature: str | None = None
    description: str = ""

    def applies_to(self, page_type: str, viewport_kind: str) -> bool:
        return (
            page_type in self.page_types
            and viewport_kind in self.viewport_kinds
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "required": self.required,
            "page_types": list(self.page_types),
            "viewport_kinds": list(self.viewport_kinds),
            "landmarks": [landmark.to_dict() for landmark in self.landmarks],
            "steps": [step.to_dict() for step in self.steps],
            "feature": self.feature,
            "description": self.description,
        }


HEADER = Landmark(
    "header",
    "[data-site-header], #shopify-section-header, .shopify-section-header, "
    "header.header, [data-header], header",
    True,
)
ANNOUNCEMENT = Landmark(
    "announcement",
    ".announcement-bar, #shopify-section-announcement-bar, [data-announcement-bar]",
    False,
)
MOBILE_MENU = Landmark(
    "mobile-menu",
    "#MobileMenu, .wsmenucontainer, .wsmenu, nav[aria-label='Mobile menu'], "
    "menu-drawer, #menu-drawer, .menu-drawer, [data-mobile-menu]",
    True,
)
SEARCH_DIALOG = Landmark(
    "desktop-search",
    "details-modal.header__search, search-modal, .search-modal, [role='search']",
    True,
)
CART = Landmark(
    "cart",
    "main-cart-items, cart-drawer, #main-cart-items, [data-cart], "
    "#shopify-section-cart-template, .cart-template",
    True,
)
FOOTER = Landmark(
    "footer",
    "#shopify-section-footer, footer.footer, [data-footer], footer",
    True,
)


def _scenario(
    name: str,
    *,
    required: bool,
    page_types: tuple[str, ...] = ALL_PAGE_TYPES,
    viewport_kinds: tuple[str, ...] = ("mobile", "desktop", "breakpoint"),
    landmarks: tuple[Landmark, ...],
    steps: tuple[ScenarioStep, ...] = (),
    feature: str | None = None,
    description: str,
) -> ScenarioDefinition:
    return ScenarioDefinition(
        name=name,
        required=required,
        page_types=page_types,
        viewport_kinds=viewport_kinds,
        landmarks=landmarks,
        steps=steps,
        feature=feature,
        description=description,
    )


SCENARIO_DEFINITIONS: Mapping[str, ScenarioDefinition] = {
    scenario.name: scenario
    for scenario in (
        _scenario(
            "baseline",
            required=True,
            landmarks=(Landmark("main", "main, #MainContent, [role='main']", True), HEADER, FOOTER),
            description="Settled page with no interaction.",
        ),
        _scenario(
            "announcement-header-scroll",
            required=True,
            landmarks=(HEADER, ANNOUNCEMENT),
            steps=(
                ScenarioStep("scroll", target="window", value=600),
                ScenarioStep("wait_stable"),
            ),
            feature="header",
            description="Announcement and sticky header before and after scrolling.",
        ),
        _scenario(
            "mobile-menu-closed",
            required=True,
            viewport_kinds=("mobile", "breakpoint"),
            landmarks=(HEADER, MOBILE_MENU),
            feature="mobile_menu",
            description="Mobile navigation in its initial closed state.",
        ),
        _scenario(
            "mobile-menu-open",
            required=True,
            viewport_kinds=("mobile", "breakpoint"),
            landmarks=(HEADER, MOBILE_MENU),
            steps=(ScenarioStep("open", target="mobile-menu"),),
            feature="mobile_menu",
            description="Mobile navigation after opening the drawer.",
        ),
        _scenario(
            "mobile-menu-collection-open",
            required=False,
            viewport_kinds=("mobile", "breakpoint"),
            landmarks=(
                MOBILE_MENU,
                Landmark(
                    "collection-accordion",
                    "#MobileMenuCollection, .mobile_menu_top_sapce .wsmenu-submenu, "
                    "[data-menu='collection'], summary:has-text('Collection')",
                    False,
                ),
            ),
            steps=(
                ScenarioStep("open", target="mobile-menu"),
                ScenarioStep("open_accordion", target="Collection", required=False),
            ),
            feature="mobile_menu",
            description="Collection accordion expanded in the mobile menu.",
        ),
        _scenario(
            "mobile-menu-language-open",
            required=False,
            viewport_kinds=("mobile", "breakpoint"),
            landmarks=(
                MOBILE_MENU,
                Landmark(
                    "language-accordion",
                    "#MobileMenuLanguage, "
                    ".third_main_menu_li_mobile_only .wsmenu-submenu, "
                    "[data-menu='language'], summary:has-text('Language')",
                    False,
                ),
            ),
            steps=(
                ScenarioStep("open", target="mobile-menu"),
                ScenarioStep("open_accordion", target="Language", required=False),
            ),
            feature="localization",
            description="Language accordion expanded in the mobile menu.",
        ),
        _scenario(
            "mobile-menu-client-services-open",
            required=False,
            viewport_kinds=("mobile", "breakpoint"),
            landmarks=(
                MOBILE_MENU,
                Landmark(
                    "client-services-accordion",
                    "#MobileMenuClientService, "
                    ".third_main_menu_li .wsmenu-submenu, "
                    "[data-menu='client-services'], "
                    "summary:has-text('Client Services')",
                    False,
                ),
            ),
            steps=(
                ScenarioStep("open", target="mobile-menu"),
                ScenarioStep(
                    "open_accordion",
                    target="Client Services",
                    required=False,
                ),
            ),
            feature="mobile_menu",
            description="Client Services accordion expanded in the mobile menu.",
        ),
        _scenario(
            "desktop-search",
            required=True,
            viewport_kinds=("desktop", "breakpoint"),
            landmarks=(HEADER, SEARCH_DIALOG),
            steps=(
                ScenarioStep("open", target="desktop-search"),
                ScenarioStep("focus", target="search-input"),
            ),
            feature="desktop_search",
            description="Desktop search dialog opened and focused.",
        ),
        _scenario(
            "cart-empty",
            required=True,
            page_types=("cart",),
            landmarks=(
                CART,
                Landmark(
                    "empty-cart",
                    ".cart__empty-text, .cart--empty-message, [data-cart-empty]",
                    True,
                ),
            ),
            steps=(ScenarioStep("ensure_empty_cart"),),
            description="Cart route with an explicitly empty cart.",
        ),
        _scenario(
            "newsletter-timed",
            required=False,
            landmarks=(
                Landmark(
                    "newsletter",
                    "[data-newsletter-popup], .newsletter-popup, .klaviyo-form, .mc-modal",
                    False,
                ),
            ),
            steps=(ScenarioStep("advance_time", value=15_000, required=False),),
            feature="newsletter",
            description="Optional timed newsletter popup after deterministic clock advance.",
        ),
        _scenario(
            "footer-accordion",
            required=False,
            viewport_kinds=("mobile", "breakpoint"),
            landmarks=(
                FOOTER,
                Landmark("footer-accordion", "footer details, [data-footer-accordion]", False),
            ),
            steps=(ScenarioStep("open_first_accordion", target="footer", required=False),),
            feature="footer_accordion",
            description="First available footer accordion expanded.",
        ),
        _scenario(
            "collection-state",
            required=True,
            page_types=("collection",),
            landmarks=(
                Landmark(
                    "collection-grid",
                    "#product-grid, [data-product-grid], #Collection, #listing-main",
                    True,
                ),
                Landmark("collection-facets", "facet-filters-form, .facets-container", False),
            ),
            description="Collection grid and optional filters in their default state.",
        ),
        _scenario(
            "search-state",
            required=True,
            page_types=("search",),
            landmarks=(
                Landmark("search-input", "input[type='search'], [name='q']", True),
                Landmark("search-results", "#product-grid, [data-search-results]", False),
            ),
            steps=(ScenarioStep("submit_search", value="shoe"),),
            description="Search route after a deterministic query.",
        ),
        _scenario(
            "product-state",
            required=True,
            page_types=("product",),
            landmarks=(
                Landmark(
                    "product-info",
                    "product-info, .product__info-container, .product_sec_right",
                    True,
                ),
                Landmark("product-form", "product-form, form[action*='/cart/add']", True),
            ),
            description="Product detail page with its default sellable variant.",
        ),
        _scenario(
            "cart-state",
            required=True,
            page_types=("cart",),
            landmarks=(CART,),
            description="Cart route base state.",
        ),
        _scenario(
            "page-state",
            required=True,
            page_types=("page", "blog", "article", "other"),
            landmarks=(Landmark("page-content", "main, article, .rte, [role='main']", True),),
            description="Editorial, blog/article, or not-found content state.",
        ),
    )
}


def get_scenario(name: str) -> ScenarioDefinition:
    try:
        return SCENARIO_DEFINITIONS[name]
    except KeyError as error:
        raise ValueError(f"unknown scenario: {name}") from error
