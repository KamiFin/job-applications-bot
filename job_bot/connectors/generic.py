"""Generic connector for any job application website."""

from __future__ import annotations

import asyncio
import logging

from playwright.async_api import Page

from job_bot.connectors.base import BaseConnector
from job_bot.models import ApplicationStatus, JobListing

logger = logging.getLogger(__name__)


class GenericConnector(BaseConnector):
    """Generic connector that works with any job application page.

    Navigates to the provided URL, detects forms, and fills them
    using CV data. Best for direct company career pages.
    """

    platform_name = "generic"

    async def login(self, page: Page, credentials: dict) -> bool:
        """No login needed for direct application pages."""
        return True

    async def search_jobs(self, page: Page, query: str, location: str) -> list[JobListing]:
        """Not applicable for generic connector - use direct URLs instead."""
        return []

    async def apply_to_job(self, page: Page, job: JobListing) -> ApplicationResult:
        """Fill and submit application form on a generic job page."""
        await self.browser.navigate(page, job.url)
        await asyncio.sleep(3)

        try:
            # Fill all detected form fields
            result = await self.form_filler.fill_form(page, self.cv_file_path)
            logger.info(
                "Form fill result: %d filled, %d skipped, %d failed",
                result["filled"],
                result["skipped"],
                result["failed"],
            )

            if result["filled"] == 0:
                return self._result(job, ApplicationStatus.SKIPPED, "No fillable fields found on page")

            # Look for a submit button
            submit_btn = await page.query_selector(
                'button[type="submit"], '
                'input[type="submit"], '
                'button:has-text("Submit"), '
                'button:has-text("Apply"), '
                'button:has-text("Send")'
            )

            if submit_btn:
                logger.info(
                    "Form filled for %s. Found submit button but waiting for confirmation.",
                    job.url,
                )
                return self._result(
                    job, ApplicationStatus.IN_PROGRESS,
                    f"Form filled ({result['filled']} fields). Review before submitting.",
                )

            return self._result(
                job, ApplicationStatus.IN_PROGRESS,
                f"Form filled ({result['filled']} fields). No submit button found.",
            )

        except Exception as e:
            return self._result(job, ApplicationStatus.FAILED, str(e))

    async def apply_to_url(self, page: Page, url: str) -> ApplicationResult:
        """Convenience method to apply directly to a URL."""
        job = JobListing(url=url, platform="generic")
        return await self.apply_to_job(page, job)
