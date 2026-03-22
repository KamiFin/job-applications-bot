"""Base connector interface for job platforms."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod

from playwright.async_api import Page

from job_bot.browser import BrowserEngine
from job_bot.form_filler import FormFiller
from job_bot.models import ApplicationResult, ApplicationStatus, CVData, JobListing

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """Abstract base class for job site connectors."""

    platform_name: str = "unknown"

    def __init__(self, browser: BrowserEngine, cv: CVData, cv_file_path: str):
        self.browser = browser
        self.cv = cv
        self.cv_file_path = cv_file_path
        self.form_filler = FormFiller(cv)

    @abstractmethod
    async def login(self, page: Page, credentials: dict) -> bool:
        """Log in to the job platform."""
        ...

    @abstractmethod
    async def search_jobs(self, page: Page, query: str, location: str) -> list[JobListing]:
        """Search for job listings."""
        ...

    @abstractmethod
    async def apply_to_job(self, page: Page, job: JobListing) -> ApplicationResult:
        """Apply to a specific job listing."""
        ...

    async def _safe_apply(self, page: Page, job: JobListing) -> ApplicationResult:
        """Wrapper that catches errors and returns a result."""
        try:
            return await self.apply_to_job(page, job)
        except Exception as e:
            logger.error("Failed to apply to %s at %s: %s", job.title, job.company, e)
            return self._result(job, ApplicationStatus.FAILED, str(e))

    def _result(
        self, job: JobListing, status: ApplicationStatus, message: str = ""
    ) -> ApplicationResult:
        return ApplicationResult(job=job, status=status, message=message)

    async def _walk_multistep_form(
        self,
        page: Page,
        job: JobListing,
        submit_selector: str,
        next_selector: str,
        max_steps: int = 10,
        success_message: str = "Application submitted",
    ) -> ApplicationResult:
        """Shared multi-step form loop: fill fields, click next/submit on each step."""
        for step in range(max_steps):
            await self.form_filler.fill_form(page, self.cv_file_path)

            submit_btn = await page.query_selector(submit_selector)
            if submit_btn:
                await submit_btn.click()
                await asyncio.sleep(2)
                logger.info("Submitted application for %s at %s", job.title, job.company)
                return self._result(job, ApplicationStatus.SUBMITTED, success_message)

            next_btn = await page.query_selector(next_selector)
            if next_btn:
                await next_btn.click()
                await asyncio.sleep(1)
            else:
                break

        return self._result(job, ApplicationStatus.FAILED, "Could not complete multi-step form")
