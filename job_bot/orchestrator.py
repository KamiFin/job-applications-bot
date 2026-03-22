"""Main orchestrator that coordinates the job application workflow."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path

from job_bot.browser import BrowserEngine
from job_bot.connectors.generic import GenericConnector
from job_bot.connectors.indeed import IndeedConnector
from job_bot.connectors.linkedin import LinkedInConnector
from job_bot.cv_parser import parse_cv
from job_bot.models import ApplicationResult, ApplicationStatus, CVData, JobListing

logger = logging.getLogger(__name__)

CONNECTORS = {
    "linkedin": LinkedInConnector,
    "indeed": IndeedConnector,
    "generic": GenericConnector,
}


class JobBot:
    """Main bot that orchestrates searching and applying to jobs."""

    def __init__(self, config: dict):
        self.config = config
        self.cv: CVData | None = None
        self.cv_file_path: str = config.get("cv_path", "")
        self.results: list[ApplicationResult] = []
        self.headless = config.get("headless", False)
        self.max_applications = config.get("max_applications", 10)

    def load_cv(self) -> CVData:
        """Parse and load the CV."""
        if not self.cv_file_path:
            raise ValueError("No CV file path configured. Set 'cv_path' in config.")
        self.cv = parse_cv(self.cv_file_path)
        logger.info(
            "CV loaded for %s (%s)",
            self.cv.full_name(),
            self.cv.personal.email,
        )
        return self.cv

    async def run_platform(
        self,
        platform: str,
        query: str,
        location: str,
        credentials: dict | None = None,
    ) -> list[ApplicationResult]:
        """Search and apply to jobs on a specific platform."""
        if not self.cv:
            self.load_cv()

        connector_cls = CONNECTORS.get(platform)
        if not connector_cls:
            raise ValueError(f"Unknown platform: {platform}. Available: {list(CONNECTORS.keys())}")

        results = []
        async with BrowserEngine(headless=self.headless) as browser:
            connector = connector_cls(browser, self.cv, self.cv_file_path)
            page = await browser.new_page()

            if credentials:
                logged_in = await connector.login(page, credentials)
                if not logged_in:
                    logger.error("Failed to log in to %s", platform)
                    return results

            jobs = await connector.search_jobs(page, query, location)
            logger.info("Found %d jobs on %s", len(jobs), platform)

            target = jobs[: self.max_applications]
            for i, job in enumerate(target):
                logger.info("[%d/%d] Applying to: %s at %s", i + 1, len(target), job.title, job.company)
                result = await connector._safe_apply(page, job)
                results.append(result)
                self.results.append(result)
                await asyncio.sleep(2)

        return results

    async def apply_to_urls(self, urls: list[str]) -> list[ApplicationResult]:
        """Apply to specific job URLs using the generic connector."""
        if not self.cv:
            self.load_cv()

        results = []
        async with BrowserEngine(headless=self.headless) as browser:
            connector = GenericConnector(browser, self.cv, self.cv_file_path)
            page = await browser.new_page()

            for i, url in enumerate(urls):
                logger.info("[%d/%d] Applying to: %s", i + 1, len(urls), url)
                job = JobListing(url=url, platform="generic")
                result = await connector._safe_apply(page, job)
                results.append(result)
                self.results.append(result)
                await asyncio.sleep(2)

        return results

    def print_summary(self) -> None:
        """Print a summary of all application results."""
        counts = Counter(r.status for r in self.results)

        logger.info("=" * 50)
        logger.info("APPLICATION SUMMARY")
        logger.info("=" * 50)
        logger.info("Total:       %d", len(self.results))
        logger.info("Submitted:   %d", counts[ApplicationStatus.SUBMITTED])
        logger.info("In Progress: %d", counts[ApplicationStatus.IN_PROGRESS])
        logger.info("Skipped:     %d", counts[ApplicationStatus.SKIPPED])
        logger.info("Failed:      %d", counts[ApplicationStatus.FAILED])
        logger.info("=" * 50)

    def save_results(self, output_path: str = "results.json") -> None:
        """Save application results to a JSON file."""
        data = []
        for r in self.results:
            data.append({
                "job_title": r.job.title,
                "company": r.job.company,
                "url": r.job.url,
                "platform": r.job.platform,
                "status": r.status.value,
                "message": r.message,
                "timestamp": datetime.now().isoformat(),
            })

        path = Path(output_path)
        path.write_text(json.dumps(data, indent=2))
        logger.info("Results saved to %s", path)
