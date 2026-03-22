"""Command-line interface for the job application bot."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from job_bot.models import ApplicationStatus
from job_bot.orchestrator import JobBot

console = Console()


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=console)],
    )


def load_config(config_path: str) -> dict:
    path = Path(config_path)
    if not path.exists():
        console.print(f"[red]Config file not found: {config_path}[/red]")
        console.print("Run [bold]job-bot init[/bold] to create a default config.")
        sys.exit(1)
    with open(path) as f:
        return yaml.safe_load(f)


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging")
def main(verbose: bool) -> None:
    """Job Applications Bot - Automated job application submission."""
    setup_logging(verbose)


@main.command()
def init() -> None:
    """Create a default configuration file."""
    config_path = Path("config.yaml")
    if config_path.exists():
        console.print("[yellow]config.yaml already exists. Skipping.[/yellow]")
        return

    default_config = {
        "cv_path": "my_resume.pdf",
        "headless": False,
        "max_applications": 10,
        "platforms": {
            "linkedin": {
                "enabled": True,
                "credentials": {
                    "email": "your-email@example.com",
                    "password": "your-password",
                },
            },
            "indeed": {
                "enabled": False,
                "credentials": {
                    "email": "your-email@example.com",
                    "password": "your-password",
                },
            },
        },
        "search": {
            "query": "software engineer",
            "location": "Remote",
        },
    }

    with open(config_path, "w") as f:
        yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

    console.print("[green]Created config.yaml[/green]")
    console.print("Edit it with your CV path, credentials, and job search preferences.")


@main.command()
@click.option("-c", "--config", default="config.yaml", help="Path to config file")
@click.option("-q", "--query", default=None, help="Job search query (overrides config)")
@click.option("-l", "--location", default=None, help="Job location (overrides config)")
@click.option("-p", "--platform", default=None, help="Platform to use (linkedin, indeed)")
@click.option("-n", "--max-apps", default=None, type=int, help="Max applications to submit")
def search(
    config: str,
    query: str | None,
    location: str | None,
    platform: str | None,
    max_apps: int | None,
) -> None:
    """Search for jobs and apply automatically."""
    cfg = load_config(config)

    if max_apps:
        cfg["max_applications"] = max_apps

    search_query = query or cfg.get("search", {}).get("query", "software engineer")
    search_location = location or cfg.get("search", {}).get("location", "Remote")

    bot = JobBot(cfg)
    bot.load_cv()

    console.print(f"[bold]Searching for:[/bold] {search_query} in {search_location}")
    console.print(f"[bold]CV loaded for:[/bold] {bot.cv.full_name()}")

    platforms_to_run = []
    if platform:
        platforms_to_run = [platform]
    else:
        for name, pcfg in cfg.get("platforms", {}).items():
            if pcfg.get("enabled", False):
                platforms_to_run.append(name)

    if not platforms_to_run:
        console.print("[red]No platforms enabled. Edit config.yaml to enable platforms.[/red]")
        return

    async def _run_all_platforms():
        for plat in platforms_to_run:
            console.print(f"\n[bold blue]Running on {plat}...[/bold blue]")
            creds = cfg.get("platforms", {}).get(plat, {}).get("credentials")
            results = await bot.run_platform(plat, search_query, search_location, creds)
            _print_results_table(results)

    asyncio.run(_run_all_platforms())

    bot.save_results()
    bot.print_summary()


@main.command()
@click.option("-c", "--config", default="config.yaml", help="Path to config file")
@click.argument("urls", nargs=-1, required=True)
def apply(config: str, urls: tuple[str, ...]) -> None:
    """Apply to specific job URLs directly."""
    cfg = load_config(config)
    bot = JobBot(cfg)
    bot.load_cv()

    console.print(f"[bold]CV loaded for:[/bold] {bot.cv.full_name()}")
    console.print(f"[bold]Applying to {len(urls)} job(s)...[/bold]")

    results = asyncio.run(bot.apply_to_urls(list(urls)))
    _print_results_table(results)
    bot.save_results()
    bot.print_summary()


@main.command()
@click.argument("cv_path")
def parse(cv_path: str) -> None:
    """Parse a CV file and display extracted data (for testing)."""
    from job_bot.cv_parser import parse_cv

    cv = parse_cv(cv_path)

    console.print(f"\n[bold]Name:[/bold] {cv.full_name()}")
    console.print(f"[bold]Email:[/bold] {cv.personal.email}")
    console.print(f"[bold]Phone:[/bold] {cv.personal.phone}")
    console.print(f"[bold]LinkedIn:[/bold] {cv.personal.linkedin_url}")
    console.print(f"[bold]GitHub:[/bold] {cv.personal.github_url}")

    if cv.summary:
        console.print(f"\n[bold]Summary:[/bold]\n{cv.summary}")

    if cv.skills:
        console.print(f"\n[bold]Skills:[/bold] {', '.join(cv.skills)}")

    if cv.work_experience:
        console.print(f"\n[bold]Work Experience ({len(cv.work_experience)} entries):[/bold]")
        for exp in cv.work_experience:
            console.print(f"  - {exp.title} at {exp.company} ({exp.start_date} - {exp.end_date})")

    if cv.education:
        console.print(f"\n[bold]Education ({len(cv.education)} entries):[/bold]")
        for edu in cv.education:
            console.print(f"  - {edu.degree} at {edu.institution}")


def _print_results_table(results: list) -> None:
    """Print application results as a table."""
    table = Table(title="Application Results")
    table.add_column("Job Title", style="cyan")
    table.add_column("Company", style="green")
    table.add_column("Status", style="bold")
    table.add_column("Message")

    status_colors = {
        ApplicationStatus.SUBMITTED: "green",
        ApplicationStatus.IN_PROGRESS: "yellow",
        ApplicationStatus.SKIPPED: "dim",
        ApplicationStatus.FAILED: "red",
        ApplicationStatus.PENDING: "blue",
    }

    for r in results:
        color = status_colors.get(r.status, "white")
        table.add_row(
            r.job.title or "N/A",
            r.job.company or "N/A",
            f"[{color}]{r.status.value}[/{color}]",
            r.message[:60] if r.message else "",
        )

    console.print(table)


if __name__ == "__main__":
    main()
