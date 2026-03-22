"""LinkedIn job application connector."""

from __future__ import annotations

import asyncio
import logging

from playwright.async_api import Page

from job_bot.connectors.base import BaseConnector
from job_bot.models import ApplicationStatus, JobListing

logger = logging.getLogger(__name__)


class LinkedInConnector(BaseConnector):
    """Connector for LinkedIn Easy Apply jobs."""

    platform_name = "linkedin"
    BASE_URL = "https://www.linkedin.com"

    async def login(self, page: Page, credentials: dict) -> bool:
        """Log in to LinkedIn."""
        await self.browser.navigate(page, f"{self.BASE_URL}/login")
        await asyncio.sleep(2)

        try:
            await self.browser.fill_field(page, "#username", credentials["email"])
            await self.browser.fill_field(page, "#password", credentials["password"])
            await self.browser.wait_and_click(page, 'button[type="submit"]')
            await asyncio.sleep(3)

            # Check if login was successful
            if "/feed" in page.url or "/in/" in page.url:
                logger.info("Successfully logged in to LinkedIn")
                return True

            logger.warning("LinkedIn login may have failed (url: %s)", page.url)
            return False
        except Exception as e:
            logger.error("LinkedIn login failed: %s", e)
            return False

    async def search_jobs(self, page: Page, query: str, location: str) -> list[JobListing]:
        """Search for Easy Apply jobs on LinkedIn."""
        search_url = (
            f"{self.BASE_URL}/jobs/search/?"
            f"keywords={query}&location={location}&f_AL=true"  # f_AL=true filters Easy Apply
        )
        await self.browser.navigate(page, search_url)
        await asyncio.sleep(3)

        jobs = await page.evaluate("""() => {
            const cards = document.querySelectorAll('.job-card-container, .jobs-search-results__list-item');
            return Array.from(cards).slice(0, 25).map(card => {
                const titleEl = card.querySelector('.job-card-list__title, a[class*="job-card"]');
                const companyEl = card.querySelector('.job-card-container__primary-description, .artdeco-entity-lockup__subtitle');
                const locationEl = card.querySelector('.job-card-container__metadata-item, .artdeco-entity-lockup__caption');
                const linkEl = card.querySelector('a[href*="/jobs/view/"]');
                return {
                    title: titleEl ? titleEl.innerText.trim() : '',
                    company: companyEl ? companyEl.innerText.trim() : '',
                    location: locationEl ? locationEl.innerText.trim() : '',
                    url: linkEl ? linkEl.href : '',
                    platform: 'linkedin',
                    description: '',
                };
            }).filter(j => j.title && j.url);
        }""")

        return [JobListing(**j) for j in jobs]

    async def apply_to_job(self, page: Page, job: JobListing) -> ApplicationResult:
        """Apply to a LinkedIn Easy Apply job."""
        await self.browser.navigate(page, job.url)
        await asyncio.sleep(2)

        easy_apply_btn = await page.query_selector(
            'button.jobs-apply-button, button[aria-label*="Easy Apply"]'
        )
        if not easy_apply_btn:
            return self._result(job, ApplicationStatus.SKIPPED, "No Easy Apply button found")

        await easy_apply_btn.click()
        await asyncio.sleep(2)

        return await self._walk_multistep_form(
            page,
            job,
            submit_selector='button[aria-label*="Submit"], button[aria-label*="submit"]',
            next_selector=(
                'button[aria-label*="Next"], button[aria-label*="Review"], '
                'button[aria-label*="Continue"]'
            ),
            max_steps=10,
            success_message="Successfully submitted via Easy Apply",
        )
