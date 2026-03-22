# Job Applications Bot

Automated job application bot that parses your CV and fills application forms on job sites using browser automation.

## Features

- **CV Parsing** — Extracts structured data from PDF, DOCX, and TXT resumes
- **Smart Form Filling** — Detects form fields and maps them to your CV data automatically
- **Multi-Platform Support** — LinkedIn Easy Apply, Indeed, and any generic career page
- **Browser Automation** — Uses Playwright for reliable, headless browser control
- **CLI Interface** — Simple commands to search, apply, and manage applications

## Quick Start

```bash
# Install dependencies
pip install -e .
playwright install chromium

# Create config file
job-bot init

# Edit config.yaml with your CV path and credentials
# Then search and apply:
job-bot search --query "software engineer" --location "Remote"

# Or apply to specific URLs directly:
job-bot apply https://company.com/careers/job-123
```

## Commands

| Command | Description |
|---------|-------------|
| `job-bot init` | Create a default `config.yaml` |
| `job-bot search` | Search for jobs and apply automatically |
| `job-bot apply <urls>` | Apply to specific job page URLs |
| `job-bot parse <cv>` | Test CV parsing and see extracted data |

## Configuration

Copy `config/example_config.yaml` to `config.yaml` and edit:

- `cv_path` — Path to your resume (PDF/DOCX/TXT)
- `headless` — Set `false` to watch the browser in real-time
- `max_applications` — Limit per run
- `platforms` — Enable/disable platforms and set credentials
- `search.query` / `search.location` — Default search parameters

## Project Structure

```
job_bot/
├── cli.py              # CLI entry point
├── orchestrator.py     # Main bot coordinator
├── cv_parser.py        # Resume/CV parser (PDF, DOCX, TXT)
├── browser.py          # Playwright browser engine
├── form_filler.py      # Form detection and auto-filling
├── models.py           # Data models
└── connectors/
    ├── base.py         # Base connector interface
    ├── linkedin.py     # LinkedIn Easy Apply
    ├── indeed.py       # Indeed applications
    └── generic.py      # Any job page
```

## How It Works

1. **Parse CV** — Extracts your name, email, phone, skills, experience, education
2. **Open Browser** — Launches a Chromium instance via Playwright
3. **Search Jobs** — Queries the platform for matching positions
4. **Fill Forms** — Detects input fields, matches them to CV data, and fills them
5. **Submit** — Submits the application (with safety checks on generic sites)
