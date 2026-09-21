"""Async Playwright runtime with isolated, theme-verified target sessions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse


class ThemeIdentityError(RuntimeError):
    """Raised when a page renders with the wrong Shopify theme."""


@dataclass(frozen=True, slots=True)
class BrowserProfile:
    """Browser context properties fixed before the first navigation."""

    name: str
    width: int
    height: int
    device_scale_factor: float = 1
    mobile: bool = False
    touch: bool = False
    user_agent: str | None = None

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("profile width and height must be positive")
        if self.device_scale_factor <= 0:
            raise ValueError("device_scale_factor must be positive")
        if self.mobile and not self.touch:
            object.__setattr__(self, "touch", True)

    @classmethod
    def from_mapping(cls, name: str, value: Mapping[str, Any]) -> BrowserProfile:
        mobile = bool(value.get("mobile", name.lower().startswith("mobile")))
        return cls(
            name=name,
            width=int(value["width"]),
            height=int(value["height"]),
            device_scale_factor=float(value.get("device_scale_factor", 1)),
            mobile=mobile,
            touch=bool(value.get("touch", mobile)),
            user_agent=value.get("user_agent"),
        )

    def context_options(self) -> dict[str, Any]:
        options: dict[str, Any] = {
            "viewport": {"width": self.width, "height": self.height},
            "device_scale_factor": self.device_scale_factor,
            "is_mobile": self.mobile,
            "has_touch": self.touch,
        }
        if self.user_agent:
            options["user_agent"] = self.user_agent
        return options


@dataclass(frozen=True, slots=True)
class RuntimeOptions:
    live_base_url: str
    preview_base_url: str
    preview_theme_id: int | str
    preview_query_parameter: str = "preview_theme_id"
    navigation_timeout_ms: int = 30_000
    action_timeout_ms: int = 10_000
    headless: bool = True
    chromium_args: tuple[str, ...] = (
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-gpu",
    )

    def __post_init__(self) -> None:
        for name, value in (
            ("live_base_url", self.live_base_url),
            ("preview_base_url", self.preview_base_url),
        ):
            if urlparse(value).scheme not in {"http", "https"}:
                raise ValueError(f"{name} must be an HTTP URL")
        if not str(self.preview_theme_id):
            raise ValueError("preview_theme_id is required")


@dataclass(frozen=True, slots=True)
class NavigationRecord:
    target: str
    requested_url: str
    final_url: str
    theme_id: str
    status: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RuntimeTelemetry:
    console_errors: list[dict[str, Any]] = field(default_factory=list)
    failed_first_party_requests: list[dict[str, Any]] = field(default_factory=list)

    def snapshot(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "console_errors": [dict(item) for item in self.console_errors],
            "failed_first_party_requests": [
                dict(item) for item in self.failed_first_party_requests
            ],
        }

    def clear(self) -> None:
        self.console_errors.clear()
        self.failed_first_party_requests.clear()


def _with_query_parameter(url: str, key: str, value: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query[key] = value
    return urlunparse(parsed._replace(query=urlencode(query)))


def _without_query_parameter(url: str, key: str) -> str:
    parsed = urlparse(url)
    query = [(name, value) for name, value in parse_qsl(parsed.query) if name != key]
    return urlunparse(parsed._replace(query=urlencode(query)))


class TargetSession:
    """A page bound to either live or preview, with guarded navigation."""

    def __init__(
        self,
        *,
        target: str,
        context: Any,
        page: Any,
        base_url: str,
        preview_theme_id: str,
        preview_query_parameter: str,
        navigation_timeout_ms: int,
    ) -> None:
        if target not in {"live", "preview"}:
            raise ValueError("target must be 'live' or 'preview'")
        self.target = target
        self.context = context
        self.page = page
        self.base_url = base_url.rstrip("/") + "/"
        self.preview_theme_id = preview_theme_id
        self.preview_query_parameter = preview_query_parameter
        self.navigation_timeout_ms = navigation_timeout_ms
        self.navigations: list[NavigationRecord] = []
        self.telemetry = RuntimeTelemetry()
        self._install_telemetry()

    def _install_telemetry(self) -> None:
        def on_console(message: Any) -> None:
            if getattr(message, "type", None) != "error":
                return
            self.telemetry.console_errors.append(
                {
                    "text": str(getattr(message, "text", "")),
                    "url": self.page.url,
                }
            )

        def on_request_failed(request: Any) -> None:
            request_url = str(getattr(request, "url", ""))
            if not self._is_first_party(request_url):
                return
            failure = getattr(request, "failure", None)
            self.telemetry.failed_first_party_requests.append(
                {
                    "url": request_url,
                    "method": str(getattr(request, "method", "")),
                    "resource_type": str(getattr(request, "resource_type", "")),
                    "error": str(failure or "request failed"),
                }
            )

        self.page.on("console", on_console)
        self.page.on("requestfailed", on_request_failed)

    def _is_first_party(self, url: str) -> bool:
        return urlparse(url).netloc == urlparse(self.base_url).netloc

    def requested_url(self, path_or_url: str) -> str:
        url = urljoin(self.base_url, path_or_url)
        if self.target == "preview":
            return _with_query_parameter(
                url, self.preview_query_parameter, self.preview_theme_id
            )
        return _without_query_parameter(url, self.preview_query_parameter)

    async def navigate(
        self,
        path_or_url: str,
        *,
        wait_until: str = "domcontentloaded",
    ) -> NavigationRecord:
        requested_url = self.requested_url(path_or_url)
        response = await self.page.goto(
            requested_url,
            wait_until=wait_until,
            timeout=self.navigation_timeout_ms,
        )
        theme_id = await self.assert_theme_identity()
        record = NavigationRecord(
            target=self.target,
            requested_url=requested_url,
            final_url=str(self.page.url),
            theme_id=theme_id,
            status=getattr(response, "status", None),
        )
        self.navigations.append(record)
        return record

    async def assert_theme_identity(self) -> str:
        identity = await self.page.evaluate(
            """() => ({
                themeId: String(window.Shopify?.theme?.id ?? ''),
                previewedThemeId: String(window.Shopify?.previewed_theme_id ?? ''),
                designMode: Boolean(window.Shopify?.designMode)
            })"""
        )
        theme_id = str((identity or {}).get("themeId", ""))
        if self.target == "preview":
            if theme_id != self.preview_theme_id:
                raise ThemeIdentityError(
                    "preview theme verification failed: "
                    f"expected {self.preview_theme_id}, rendered {theme_id or 'unknown'} "
                    f"at {self.page.url}"
                )
        else:
            final_query = dict(parse_qsl(urlparse(str(self.page.url)).query))
            previewed_id = str((identity or {}).get("previewedThemeId", ""))
            if not theme_id:
                raise ThemeIdentityError(
                    "live theme verification failed: rendered unknown "
                    f"at {self.page.url}"
                )
            if (
                theme_id == self.preview_theme_id
                or previewed_id == self.preview_theme_id
                or self.preview_query_parameter in final_query
            ):
                raise ThemeIdentityError(
                    "live target rendered a preview theme "
                    f"({theme_id or previewed_id or 'query parameter'}) at {self.page.url}"
                )
        return theme_id

    async def close(self) -> None:
        await self.context.close()


@dataclass(slots=True)
class PairedSession:
    profile: BrowserProfile
    live: TargetSession
    preview: TargetSession

    async def close(self) -> None:
        await self.live.close()
        await self.preview.close()


class BrowserRuntime:
    """Own a Chromium instance and create isolated live/preview context pairs."""

    def __init__(self, options: RuntimeOptions) -> None:
        self.options = options
        self._playwright_manager: Any = None
        self._playwright: Any = None
        self._browser: Any = None
        self._pairs: list[PairedSession] = []

    @property
    def browser(self) -> Any:
        if self._browser is None:
            raise RuntimeError("browser runtime has not been started")
        return self._browser

    async def start(self) -> BrowserRuntime:
        if self._browser is not None:
            return self
        from playwright.async_api import async_playwright

        self._playwright_manager = async_playwright()
        self._playwright = await self._playwright_manager.start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.options.headless,
            args=list(self.options.chromium_args),
        )
        return self

    async def __aenter__(self) -> BrowserRuntime:
        return await self.start()

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def create_pair(self, profile: BrowserProfile) -> PairedSession:
        context_options = profile.context_options()
        live_context = await self.browser.new_context(**context_options)
        try:
            preview_context = await self.browser.new_context(**context_options)
        except BaseException:
            await live_context.close()
            raise

        try:
            live_page = await live_context.new_page()
            preview_page = await preview_context.new_page()
            for page in (live_page, preview_page):
                page.set_default_timeout(self.options.action_timeout_ms)
                page.set_default_navigation_timeout(self.options.navigation_timeout_ms)

            pair = PairedSession(
                profile=profile,
                live=TargetSession(
                    target="live",
                    context=live_context,
                    page=live_page,
                    base_url=self.options.live_base_url,
                    preview_theme_id=str(self.options.preview_theme_id),
                    preview_query_parameter=self.options.preview_query_parameter,
                    navigation_timeout_ms=self.options.navigation_timeout_ms,
                ),
                preview=TargetSession(
                    target="preview",
                    context=preview_context,
                    page=preview_page,
                    base_url=self.options.preview_base_url,
                    preview_theme_id=str(self.options.preview_theme_id),
                    preview_query_parameter=self.options.preview_query_parameter,
                    navigation_timeout_ms=self.options.navigation_timeout_ms,
                ),
            )
            self._pairs.append(pair)
            return pair
        except BaseException:
            await live_context.close()
            await preview_context.close()
            raise

    async def close_pair(self, pair: PairedSession) -> None:
        if pair in self._pairs:
            self._pairs.remove(pair)
        await pair.close()

    async def close(self) -> None:
        pairs, self._pairs = self._pairs, []
        for pair in reversed(pairs):
            try:
                await pair.close()
            except Exception:
                pass
        if self._browser is not None:
            try:
                is_connected = getattr(self._browser, "is_connected", None)
                if is_connected is None or is_connected():
                    await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
            self._playwright_manager = None
