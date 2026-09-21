from __future__ import annotations

from dataclasses import dataclass

import pytest

from store_parity.browser.runtime import (
    BrowserProfile,
    BrowserRuntime,
    RuntimeOptions,
    TargetSession,
    ThemeIdentityError,
)


@dataclass
class FakeResponse:
    status: int = 200


class FakePage:
    def __init__(self, theme_id: str) -> None:
        self.theme_id = theme_id
        self.url = "about:blank"
        self.handlers: dict[str, object] = {}
        self.navigation_calls: list[tuple[str, str, int]] = []

    def on(self, event: str, handler: object) -> None:
        self.handlers[event] = handler

    def set_default_timeout(self, value: int) -> None:
        self.default_timeout = value

    def set_default_navigation_timeout(self, value: int) -> None:
        self.default_navigation_timeout = value

    async def goto(self, url: str, *, wait_until: str, timeout: int) -> FakeResponse:
        self.url = url
        self.navigation_calls.append((url, wait_until, timeout))
        return FakeResponse()

    async def evaluate(self, _script: str) -> dict[str, object]:
        return {
            "themeId": self.theme_id,
            "previewedThemeId": "",
            "designMode": False,
        }


class FakeContext:
    def __init__(self, theme_id: str, options: dict) -> None:
        self.page = FakePage(theme_id)
        self.options = options
        self.closed = False

    async def new_page(self) -> FakePage:
        return self.page

    async def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(self) -> None:
        self.contexts: list[FakeContext] = []
        self.closed = False

    async def new_context(self, **options: object) -> FakeContext:
        theme_id = "live-theme" if not self.contexts else "187054457141"
        context = FakeContext(theme_id, options)
        self.contexts.append(context)
        return context

    async def close(self) -> None:
        self.closed = True


class FakePlaywright:
    def __init__(self) -> None:
        self.stopped = False

    async def stop(self) -> None:
        self.stopped = True


def runtime_options() -> RuntimeOptions:
    return RuntimeOptions(
        live_base_url="https://example.test",
        preview_base_url="https://example.test",
        preview_theme_id=187054457141,
    )


@pytest.mark.asyncio
async def test_pair_uses_isolated_mobile_contexts_without_extra_navigation() -> None:
    browser = FakeBrowser()
    runtime = BrowserRuntime(runtime_options())
    runtime._browser = browser

    pair = await runtime.create_pair(
        BrowserProfile(name="mobile", width=390, height=844, mobile=True)
    )

    assert pair.live.context is not pair.preview.context
    assert len(browser.contexts) == 2
    assert all(context.options["is_mobile"] is True for context in browser.contexts)
    assert all(context.options["has_touch"] is True for context in browser.contexts)
    assert all(
        context.options["viewport"] == {"width": 390, "height": 844}
        for context in browser.contexts
    )
    assert pair.live.navigations == []
    assert pair.preview.navigations == []


@pytest.mark.asyncio
async def test_navigation_records_requested_and_final_urls_and_checks_theme() -> None:
    context = FakeContext("187054457141", {})
    session = TargetSession(
        target="preview",
        context=context,
        page=context.page,
        base_url="https://example.test",
        preview_theme_id="187054457141",
        preview_query_parameter="preview_theme_id",
        navigation_timeout_ms=1_000,
    )

    record = await session.navigate("/products/shoe?color=red")

    assert record.requested_url == (
        "https://example.test/products/shoe?color=red&preview_theme_id=187054457141"
    )
    assert record.final_url == record.requested_url
    assert record.theme_id == "187054457141"

    context.page.theme_id = "wrong-theme"
    with pytest.raises(ThemeIdentityError, match="preview theme verification failed"):
        await session.navigate("/products/boot")


@pytest.mark.asyncio
async def test_live_navigation_strips_preview_and_rejects_preview_identity() -> None:
    context = FakeContext("live-theme", {})
    session = TargetSession(
        target="live",
        context=context,
        page=context.page,
        base_url="https://example.test",
        preview_theme_id="187054457141",
        preview_query_parameter="preview_theme_id",
        navigation_timeout_ms=1_000,
    )

    record = await session.navigate("/?preview_theme_id=187054457141&sort=best")
    assert record.requested_url == "https://example.test/?sort=best"

    context.page.theme_id = "187054457141"
    with pytest.raises(ThemeIdentityError, match="live target rendered a preview theme"):
        await session.navigate("/")


def test_telemetry_keeps_console_and_failed_first_party_requests_only() -> None:
    context = FakeContext("live-theme", {})
    context.page.url = "https://example.test/products/shoe"
    session = TargetSession(
        target="live",
        context=context,
        page=context.page,
        base_url="https://example.test",
        preview_theme_id="187054457141",
        preview_query_parameter="preview_theme_id",
        navigation_timeout_ms=1_000,
    )

    console = type("Console", (), {"type": "error", "text": "broken widget"})()
    first_party = type(
        "Request",
        (),
        {
            "url": "https://example.test/assets/missing.js",
            "method": "GET",
            "resource_type": "script",
            "failure": "net::ERR_FAILED",
        },
    )()
    third_party = type(
        "Request",
        (),
        {
            "url": "https://analytics.invalid/pixel",
            "method": "GET",
            "resource_type": "image",
            "failure": "net::ERR_FAILED",
        },
    )()

    context.page.handlers["console"](console)
    context.page.handlers["requestfailed"](first_party)
    context.page.handlers["requestfailed"](third_party)

    assert session.telemetry.console_errors == [
        {"text": "broken widget", "url": "https://example.test/products/shoe"}
    ]
    assert [item["url"] for item in session.telemetry.failed_first_party_requests] == [
        "https://example.test/assets/missing.js"
    ]


@pytest.mark.asyncio
async def test_runtime_close_stops_started_playwright_instance() -> None:
    browser = FakeBrowser()
    playwright = FakePlaywright()
    runtime = BrowserRuntime(runtime_options())
    runtime._browser = browser
    runtime._playwright = playwright
    runtime._playwright_manager = object()

    await runtime.close()

    assert browser.closed is True
    assert playwright.stopped is True
    assert runtime._playwright is None
    assert runtime._playwright_manager is None
