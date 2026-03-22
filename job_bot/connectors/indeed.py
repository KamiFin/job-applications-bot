"""Indeed job application connector."""

from __future__ import annotations

import asyncio
import logging

from playwright.async_api import Page

from job_bot.connectors.base import BaseConnector
from job_bot.models import ApplicationStatus, JobListing

logger = logging.getLogger(__name__)


class IndeedConnector(BaseConnector):
    """Connector for Indeed job applications."""

    platform_name = "indeed"
    BASE_URL = "https://www.indeed.com"

    async def login(self, page: Page, credentials: dict) -> bool:
        """Log in to Indeed."""
        await self.browser.navigate(page, f"{self.BASE_URL}/account/login")
        await asyncio.sleep(2)

        try:
            await self.browser.fill_field(
                page, 'input[type="email"], #ifl-InputFormField-3', credentials["email"]
            )
            await self.browser.wait_and_click(page, 'button[type="submit"]')
            await asyncio.sleep(2)

            await self.browser.fill_field(
                page, 'input[type="password"]', credentials["password"]
            )
            await self.browser.wait_and_click(page, 'button[type="submit"]')
            await asyncio.sleep(3)

            logger.info("Indeed login attempted")
            return True
        except Exception as e:
            logger.error("Indeed login failed: %s", e)
            return False

    async def search_jobs(self, page: Page, query: str, location: str) -> list[JobListing]:
        """Search for jobs on Indeed."""
        search_url = f"{self.BASE_URL}/jobs?q={query}&l={location}"
        await self.browser.navigate(page, search_url)
        await asyncio.sleep(3)

        jobs = await page.evaluate("""() => {
            const cards = document.querySelectorAll('.job_seen_beacon, .jobsearch-ResultsList > li');
            return Array.from(cards).slice(0, 25).map(card => {
                const titleEl = card.querySelector('h2 a, .jobTitle a');
                const companyEl = card.querySelector('[data-testid="company-name"], .companyName');
                const locationEl = card.querySelector('[data-testid="text-location"], .companyLocation');
                return {
                    title: titleEl ? titleEl.innerText.trim() : '',
                    company: companyEl ? companyEl.innerText.trim() : '',
                    location: locationEl ? locationEl.innerText.trim() : '',
                    url: titleEl ? titleEl.href : '',
                    platform: 'indeed',
                    description: '',
                };
            }).filter(j => j.title && j.url);
        }""")

        return [JobListing(**j) for j in jobs]

    async def apply_to_job(self, page: Page, job: JobListing) -> ApplicationResult:
        """Apply to an Indeed job."""
        await self.browser.navigate(page, job.url)
        await asyncio.sleep(2)

        apply_btn = await page.query_selector(
            '#indeedApplyButton, button[id*="apply"], .jobsearch-IndeedApplyButton'
        )
        if not apply_btn:
            return self._result(
                job, ApplicationStatus.SKIPPED, "No apply button found - may require external application"
            )

        await apply_btn.click()
        await asyncio.sleep(3)

        return await self._walk_multistep_form(
            page,
            job,
            submit_selector=(
                'button[type="submit"]:has-text("Submit"), '
                'button:has-text("Submit your application")'
            ),
            next_selector='button:has-text("Continue"), button:has-text("Next")',
            max_steps=8,
            success_message="Successfully submitted on Indeed",
        )
