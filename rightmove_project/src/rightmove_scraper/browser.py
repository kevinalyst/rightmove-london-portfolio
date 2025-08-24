from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from .config import AppConfig


@asynccontextmanager
async def browser_context(config: AppConfig) -> AsyncIterator[tuple[Browser, BrowserContext, Page]]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=config.headless)
        context = await browser.new_context(
            user_agent=config.user_agent or None,
            viewport={"width": 1366, "height": 900},
        )
        page = await context.new_page()
        page.set_default_timeout(config.request_timeout_sec * 1000)
        # Block heavy resources for speed
        try:
            await context.route("**/*", lambda route: route.abort() if route.request.resource_type in {"image", "media", "font"} else route.continue_())
        except Exception:
            pass
        try:
            yield browser, context, page
        finally:
            await context.close()
            await browser.close()


async def open_page(page: Page, url: str) -> None:
    await page.goto(url, wait_until="domcontentloaded")
    # Try accept cookies if present
    try:
        await page.get_by_role("button", name="Accept all").click(timeout=1500)
    except Exception:
        pass


async def wait_for_text(page: Page, text: str) -> None:
    await page.get_by_text(text, exact=False).first.wait_for()


async def maybe_click(page: Page, text: str) -> bool:
    locator = page.get_by_text(text, exact=False).first
    if await locator.count() > 0:
        try:
            await locator.click()
            return True
        except Exception:
            return False
    return False


