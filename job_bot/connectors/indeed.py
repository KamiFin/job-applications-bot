"""Indeed job application connector."""

from __future__ import annotations

import asyncio
import logging

from playwright.async_api import Page

from job_bot.connectors.base import BaseConnector
from job_bot.models import ApplicationResult, ApplicationStatus, JobListing

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

        try:
            # Click apply button
            apply_btn = await page.query_selector(
                '#indeedApplyButton, button[id*="apply"], .jobsearch-IndeedApplyButton'
            )
            if not apply_btn:
                return ApplicationResult(
                    job=job,
                    status=ApplicationStatus.SKIPPED,
                    message="No apply button found - may require external application",
                )

            await apply_btn.click()
            await asyncio.sleep(3)

            # Handle Indeed's multi-step application
            max_steps = 8
            for step in range(max_steps):
                result = await self.form_filler.fill_form(page, self.cv_file_path)
                logger.info("Step %d: filled %d fields", step + 1, result["filled"])

                # Check for submit
                submit_btn = await page.query_selector(
                    'button[type="submit"]:has-text("Submit"), '
                    'button:has-text("Submit your application")'
                )
                if submit_btn:
                    await submit_btn.click()
                    await asyncio.sleep(2)
                    return ApplicationResult(
                        job=job,
                        status=ApplicationStatus.SUBMITTED,
                        message="Successfully submitted on Indeed",
                    )

                # Continue to next step
                continue_btn = await page.query_selector(
                    'button:has-text("Continue"), button:has-text("Next")'
                )
                if continue_btn:
                    await continue_btn.click()
                    await asyncio.sleep(2)
                else:
                    break

            return ApplicationResult(
                job=job,
                status=ApplicationStatus.FAILED,
                message="Could not complete application form",
            )

        except Exception as e:
            return ApplicationResult(
                job=job,
                status=ApplicationStatus.FAILED,
                message=str(e),
            )
