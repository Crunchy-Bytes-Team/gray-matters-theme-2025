from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from playwright.async_api import Page, async_playwright

from store_parity.browser.actions import StoreActions
from store_parity.browser.readiness import ReadinessOptions
from store_parity.capture import CaptureOptions, capture_page


HTML_FIXTURE = """
<!doctype html>
<html lang="en">
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      body { margin: 0; font-family: serif; }
      header, main, footer { padding: 8px; }
      main { min-height: 700px; }
      .component { width: 120px; height: 50px; background: rgb(1, 2, 3); }
      .wide { width: 700px; height: 10px; }
      .font-icon::before { content: "★"; font-family: serif; }
    </style>
  </head>
  <body>
    <header>
      <button class="header__icon--menu" aria-label="Menu" aria-expanded="false">Menu</button>
      <button class="header__icon--cart" aria-label="Cart">Cart</button>
      <input type="search" name="q">
    </header>
    <main>
      <details><summary>Materials</summary><p>Leather</p></details>
      <div class="component">Component</div>
      <div class="wide"></div>
      <svg class="icon-star" viewBox="0 0 10 10">
        <path d="M0 0 L10 10"></path>
      </svg>
      <span class="font-icon"></span>
      <img
        class="icon-image"
        alt="pixel"
        src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
      >
    </main>
    <footer>
      <form class="newsletter"><input type="email" name="contact[email]"></form>
    </footer>
    <script>
      document.querySelector('.header__icon--menu').addEventListener('click', event => {
        event.currentTarget.setAttribute('aria-expanded', 'true');
      });
    </script>
  </body>
</html>
"""


@pytest_asyncio.fixture
async def local_page() -> AsyncIterator[Page]:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True,
        )
        page = await context.new_page()
        await page.set_content(HTML_FIXTURE, wait_until="domcontentloaded")
        try:
            yield page
        finally:
            await context.close()
            await browser.close()


@pytest.mark.asyncio
async def test_capture_collects_local_browser_evidence(local_page: Page) -> None:
    options = CaptureOptions(
        landmark_selectors={"header": "header", "component": ".component"},
        component_selectors={"component": ".component", "missing": ".not-here"},
        readiness=ReadinessOptions(
            timeout_ms=2_000,
            font_checks=("16px serif",),
            lazy_scroll_max_steps=5,
            stability_frames=1,
            pagefly_extra_stable_frames=1,
        ),
    )

    bundle = await capture_page(
        local_page,
        requested_url="fixture://storefront",
        options=options,
    )

    assert bundle.requested_url == "fixture://storefront"
    assert bundle.final_url == "about:blank"
    assert bundle.screenshots.viewport.startswith(b"\x89PNG\r\n\x1a\n")
    assert bundle.screenshots.full_page.startswith(b"\x89PNG\r\n\x1a\n")
    assert bundle.screenshots.components["component"].startswith(b"\x89PNG")
    assert bundle.screenshots.missing_components == ("missing",)
    assert bundle.readiness.pagefly == "not_applicable"
    assert bundle.readiness.font_checks == {"16px serif": True}
    assert bundle.readiness.visible_images == 1
    assert bundle.dom["language"] == "en"
    assert bundle.landmarks["component"]["matches"][0]["geometry"]["width"] == 120
    assert any(icon["kind"] == "svg" and icon["paths"] for icon in bundle.icons)
    assert any(icon["kind"] == "img" and icon["naturalWidth"] == 1 for icon in bundle.icons)
    assert any(
        icon["kind"] == "font" and icon["before"]["content"] == '"★"'
        for icon in bundle.icons
        if icon.get("before")
    )
    assert any(item["scrollWidth"] >= 700 for item in bundle.overflow_offenders)


@pytest.mark.asyncio
async def test_store_actions_and_safe_reset_on_local_fixture(local_page: Page) -> None:
    actions = StoreActions(local_page, transition_settle_ms=0)

    await actions.open_menu()
    assert (
        await local_page.locator(".header__icon--menu").get_attribute("aria-expanded")
        == "true"
    )
    await actions.toggle_accordion(text="Materials", open_state=True)
    assert await local_page.locator("details").get_attribute("open") == ""
    await actions.search("boots")
    assert await local_page.locator("input[type='search']").input_value() == "boots"
    await actions.reach_footer()
    await actions.newsletter("audit@example.test")
    assert (
        await local_page.locator("input[type='email']").input_value()
        == "audit@example.test"
    )

    await actions.reset_state()
    assert await local_page.locator("details").get_attribute("open") is None
    assert await local_page.locator("input[type='search']").input_value() == ""
