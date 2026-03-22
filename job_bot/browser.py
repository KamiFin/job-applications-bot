"""Browser automation engine using Playwright."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

logger = logging.getLogger(__name__)


class BrowserEngine:
    """Manages browser sessions for automated form filling."""

    def __init__(self, headless: bool = True, slow_mo: int = 100):
        self.headless = headless
        self.slow_mo = slow_mo
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def start(self) -> None:
        """Launch the browser."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        logger.info("Browser started (headless=%s)", self.headless)

    async def stop(self) -> None:
        """Close the browser."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser stopped")

    async def new_page(self) -> Page:
        """Open a new browser tab."""
        if not self._context:
            raise RuntimeError("Browser not started. Call start() first.")
        return await self._context.new_page()

    async def navigate(self, page: Page, url: str, wait_until: str = "domcontentloaded") -> None:
        """Navigate to a URL and wait for the page to load."""
        logger.info("Navigating to %s", url)
        await page.goto(url, wait_until=wait_until, timeout=30000)

    async def screenshot(self, page: Page, path: str) -> str:
        """Take a screenshot for debugging/logging."""
        screenshot_path = Path(path)
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info("Screenshot saved to %s", screenshot_path)
        return str(screenshot_path)

    async def wait_and_click(self, page: Page, selector: str, timeout: int = 10000) -> None:
        """Wait for an element and click it."""
        await page.wait_for_selector(selector, timeout=timeout)
        await page.click(selector)

    async def fill_field(self, page: Page, selector: str, value: str) -> None:
        """Clear and fill a form field."""
        await page.wait_for_selector(selector, timeout=5000)
        await page.fill(selector, value)

    async def upload_file(self, page: Page, selector: str, file_path: str) -> None:
        """Upload a file to a file input."""
        await page.wait_for_selector(selector, timeout=5000)
        await page.set_input_files(selector, file_path)

    async def select_option(self, page: Page, selector: str, value: str) -> None:
        """Select an option from a dropdown."""
        await page.wait_for_selector(selector, timeout=5000)
        await page.select_option(selector, value)

    async def get_page_text(self, page: Page) -> str:
        """Get all visible text on the page."""
        return await page.inner_text("body")

    async def get_page_html(self, page: Page) -> str:
        """Get the page HTML."""
        return await page.content()

    async def evaluate(self, page: Page, expression: str) -> Any:
        """Execute JavaScript in the page context."""
        return await page.evaluate(expression)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.stop()
