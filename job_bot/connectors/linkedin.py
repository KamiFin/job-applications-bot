"""LinkedIn job application connector."""

from __future__ import annotations

import asyncio
import logging

from playwright.async_api import Page

from job_bot.connectors.base import BaseConnector
from job_bot.models import ApplicationResult, ApplicationStatus, JobListing

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

        try:
            # Click the Easy Apply button
            easy_apply_btn = await page.query_selector(
                'button.jobs-apply-button, button[aria-label*="Easy Apply"]'
            )
            if not easy_apply_btn:
                return ApplicationResult(
                    job=job,
                    status=ApplicationStatus.SKIPPED,
                    message="No Easy Apply button found",
                )

            await easy_apply_btn.click()
            await asyncio.sleep(2)

            # Fill the multi-step application form
            max_steps = 10
            for step in range(max_steps):
                # Fill any form fields on the current step
                result = await self.form_filler.fill_form(page, self.cv_file_path)
                logger.info("Step %d: filled %d fields", step + 1, result["filled"])

                # Look for submit or next button
                submit_btn = await page.query_selector(
                    'button[aria-label*="Submit"], button[aria-label*="submit"]'
                )
                if submit_btn:
                    await submit_btn.click()
                    await asyncio.sleep(2)
                    logger.info("Application submitted for %s at %s", job.title, job.company)
                    return ApplicationResult(
                        job=job,
                        status=ApplicationStatus.SUBMITTED,
                        message="Successfully submitted via Easy Apply",
                    )

                # Click next/review button to continue
                next_btn = await page.query_selector(
                    'button[aria-label*="Next"], button[aria-label*="Review"], '
                    'button[aria-label*="Continue"]'
                )
                if next_btn:
                    await next_btn.click()
                    await asyncio.sleep(1)
                else:
                    break

            return ApplicationResult(
                job=job,
                status=ApplicationStatus.FAILED,
                message="Could not complete multi-step form",
            )

        except Exception as e:
            return ApplicationResult(
                job=job,
                status=ApplicationStatus.FAILED,
                message=str(e),
            )
