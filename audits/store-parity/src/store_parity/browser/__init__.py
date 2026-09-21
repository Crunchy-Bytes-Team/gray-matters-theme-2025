"""Deterministic Playwright runtime and storefront interaction helpers."""

from store_parity.browser.actions import (
    ActionError,
    StoreActions,
    fill_newsletter,
    open_cart,
    open_menu,
    perform_search,
    reach_footer,
    reset_state,
    toggle_accordion,
)
from store_parity.browser.readiness import (
    ReadinessOptions,
    ReadinessResult,
    freeze_dynamic_content,
    lazy_scroll,
    wait_for_readiness,
)
from store_parity.browser.runtime import (
    BrowserProfile,
    BrowserRuntime,
    NavigationRecord,
    PairedSession,
    RuntimeOptions,
    TargetSession,
    ThemeIdentityError,
)

__all__ = [
    "ActionError",
    "BrowserProfile",
    "BrowserRuntime",
    "NavigationRecord",
    "PairedSession",
    "ReadinessOptions",
    "ReadinessResult",
    "RuntimeOptions",
    "StoreActions",
    "TargetSession",
    "ThemeIdentityError",
    "fill_newsletter",
    "freeze_dynamic_content",
    "lazy_scroll",
    "open_cart",
    "open_menu",
    "perform_search",
    "reach_footer",
    "reset_state",
    "toggle_accordion",
    "wait_for_readiness",
]
