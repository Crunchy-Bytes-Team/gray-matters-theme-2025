"""Reusable storefront actions with conservative, bounded state changes."""

from __future__ import annotations

from typing import Any, Sequence


class ActionError(RuntimeError):
    """Raised when a requested storefront control cannot be used."""


MENU_SELECTORS = (
    "[data-open-mobile-menu]",
    "#wsnavtoggle",
    "button[aria-controls*='menu' i]",
    "button[aria-label*='menu' i]",
    ".header__icon--menu",
    "summary.header__icon--menu",
)
SEARCH_TRIGGER_SELECTORS = (
    "button[aria-label*='search' i]",
    "a[aria-label*='search' i]",
    "#top-search-toggle",
    ".header__icon--search",
    "details-modal.header__search summary",
)
SEARCH_INPUT_SELECTORS = (
    "input[type='search']:visible",
    "input[name='q']:visible",
    "[role='search'] input:visible",
)
CART_SELECTORS = (
    "button[aria-label*='cart' i]",
    "a[href='/cart']",
    "a[href*='/cart']",
    ".header__icon--cart",
)
NEWSLETTER_INPUT_SELECTORS = (
    "footer input[type='email']:visible",
    "[class*='newsletter'] input[type='email']:visible",
    "input[name='contact[email]']:visible",
)


class StoreActions:
    def __init__(self, page: Any, *, transition_settle_ms: int = 250) -> None:
        if not 0 <= transition_settle_ms <= 1_000:
            raise ValueError("transition_settle_ms must be between 0 and 1000")
        self.page = page
        self.transition_settle_ms = transition_settle_ms

    async def _first_visible(self, selectors: Sequence[str]) -> Any:
        for selector in selectors:
            matches = self.page.locator(selector)
            try:
                for index in range(await matches.count()):
                    locator = matches.nth(index)
                    if await locator.is_visible():
                        return locator
            except Exception:
                continue
        raise ActionError(f"no visible control matched: {', '.join(selectors)}")

    async def _settle(self) -> None:
        if self.transition_settle_ms:
            await self.page.wait_for_timeout(self.transition_settle_ms)
        await self.page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )

    async def open_menu(self) -> None:
        control = await self._first_visible(MENU_SELECTORS)
        expanded = await control.get_attribute("aria-expanded")
        if expanded != "true":
            await control.click()
            await self._settle()

    async def toggle_accordion(
        self,
        *,
        selector: str = "details summary",
        text: str | None = None,
        open_state: bool | None = None,
    ) -> None:
        locator = self.page.locator(selector)
        if text:
            locator = locator.filter(has_text=text)
        control = locator.first
        if not await control.is_visible():
            raise ActionError(f"accordion control is not visible: {selector}")

        details = control.locator("xpath=ancestor::details[1]")
        currently_open = False
        if await details.count():
            currently_open = await details.get_attribute("open") is not None
        if open_state is None or currently_open != open_state:
            await control.click()
            await self._settle()

    async def search(self, query: str, *, submit: bool = False) -> None:
        if not query:
            raise ValueError("search query must not be empty")
        try:
            field = await self._first_visible(SEARCH_INPUT_SELECTORS)
        except ActionError:
            try:
                trigger = await self._first_visible(SEARCH_TRIGGER_SELECTORS)
                await trigger.click()
                await self._settle()
            except ActionError:
                await self.open_menu()
            field = await self._first_visible(SEARCH_INPUT_SELECTORS)
        await field.fill(query)
        if submit:
            await field.press("Enter")
        else:
            await self._settle()

    async def open_cart(self) -> None:
        control = await self._first_visible(CART_SELECTORS)
        await control.click()
        await self._settle()

    async def reach_footer(self) -> None:
        footer = self.page.locator("footer").first
        if not await footer.is_visible():
            raise ActionError("footer is not visible")
        await footer.scroll_into_view_if_needed()
        await self._settle()

    async def newsletter(self, email: str, *, submit: bool = False) -> None:
        if "@" not in email:
            raise ValueError("newsletter email must contain '@'")
        await self.reach_footer()
        field = await self._first_visible(NEWSLETTER_INPUT_SELECTORS)
        await field.fill(email)
        if submit:
            form = field.locator("xpath=ancestor::form[1]")
            button = form.locator("button[type='submit'], input[type='submit']").first
            if not await button.is_visible():
                raise ActionError("newsletter submit control is not visible")
            await button.click()
        await self._settle()

    async def reset_state(self) -> None:
        """Close transient UI while preserving cookies and server-side state."""

        await self.page.keyboard.press("Escape")
        await self.page.evaluate(
            """() => {
                document.querySelectorAll('details[open]').forEach(node => {
                    node.removeAttribute('open');
                    node.dispatchEvent(new Event('toggle'));
                });
                document.querySelectorAll(
                    'input[type="search"], [role="search"] input'
                ).forEach(input => {
                    input.value = '';
                    input.dispatchEvent(new Event('input', {bubbles: true}));
                });
                if (document.activeElement instanceof HTMLElement) {
                    document.activeElement.blur();
                }
                window.scrollTo(0, 0);
            }"""
        )
        await self._settle()


async def open_menu(page: Any, **options: Any) -> None:
    await StoreActions(page, **options).open_menu()


async def toggle_accordion(page: Any, **options: Any) -> None:
    action_options = {
        key: options.pop(key)
        for key in tuple(options)
        if key in {"transition_settle_ms"}
    }
    await StoreActions(page, **action_options).toggle_accordion(**options)


async def perform_search(page: Any, query: str, **options: Any) -> None:
    action_options = {
        key: options.pop(key)
        for key in tuple(options)
        if key in {"transition_settle_ms"}
    }
    await StoreActions(page, **action_options).search(query, **options)


async def open_cart(page: Any, **options: Any) -> None:
    await StoreActions(page, **options).open_cart()


async def reach_footer(page: Any, **options: Any) -> None:
    await StoreActions(page, **options).reach_footer()


async def fill_newsletter(page: Any, email: str, **options: Any) -> None:
    action_options = {
        key: options.pop(key)
        for key in tuple(options)
        if key in {"transition_settle_ms"}
    }
    await StoreActions(page, **action_options).newsletter(email, **options)


async def reset_state(page: Any, **options: Any) -> None:
    await StoreActions(page, **options).reset_state()
