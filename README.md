# Job Applications Bot

Automated job application bot that parses your CV and fills application forms on job sites using browser automation.

## Features

- **CV Parsing** — Extracts structured data from PDF, DOCX, and TXT resumes
- **Smart Form Filling** — Detects form fields and maps them to your CV data automatically
- **Multi-Platform Support** — LinkedIn Easy Apply, Indeed, and any generic career page
- **Browser Automation** — Uses Playwright for reliable, headless browser control
- **CLI Interface** — Simple commands to search, apply, and manage applications

## Quick Start

### Local Installation

```bash
# Install dependencies
pip install -e .
playwright install chromium --with-deps

# Create config file
job-bot init

# Edit config.yaml with your CV path and credentials
# Then search and apply:
job-bot search --query "software engineer" --location "Remote"

# Or apply to specific URLs directly:
job-bot apply https://company.com/careers/job-123
```

### Running from a Phone or Tablet

Since the bot requires a server environment to run Playwright, use one of these cloud options:

**GitHub Codespaces (recommended)**
1. Go to this repo on GitHub
2. Click **Code > Codespaces > Create codespace**
3. Dependencies install automatically via `.devcontainer`. Once ready, run:
   ```bash
   job-bot init
   # Edit config.yaml, then:
   job-bot search -q "developer" -l "Remote"
   ```

**Other cloud options**
- **Google Cloud Shell** — Free browser-based Linux VM with terminal access
- **Gitpod** — Open the repo URL prefixed with `gitpod.io/#` for an instant workspace
- **Any VPS** — Set up on a small cloud server and run on a schedule with cron

> **Note:** When running in the cloud, set `headless: true` in `config.yaml` since there is no visible display.

## Commands

| Command | Description |
|---------|-------------|
| `job-bot init` | Create a default `config.yaml` |
| `job-bot search` | Search for jobs and apply automatically |
| `job-bot apply <urls>` | Apply to specific job page URLs |
| `job-bot parse <cv>` | Test CV parsing and see extracted data |

### Options

```
job-bot search -q "data scientist" -l "New York" -p linkedin -n 5
job-bot apply -c my_config.yaml https://company.com/jobs/123
job-bot parse my_resume.pdf
```

| Flag | Description |
|------|-------------|
| `-q`, `--query` | Job search keywords (overrides config) |
| `-l`, `--location` | Job location (overrides config) |
| `-p`, `--platform` | Platform to use: `linkedin`, `indeed` |
| `-n`, `--max-apps` | Max number of applications per run |
| `-c`, `--config` | Path to config file (default: `config.yaml`) |
| `-v`, `--verbose` | Enable debug logging |

## Configuration

Copy `config/example_config.yaml` to `config.yaml` and edit:

```yaml
cv_path: "my_resume.pdf"        # Path to your resume (PDF/DOCX/TXT)
headless: false                  # Set true for cloud/server environments
max_applications: 10             # Limit per platform per run

search:
  query: "software engineer"
  location: "Remote"

platforms:
  linkedin:
    enabled: true
    credentials:
      email: "your-email@example.com"
      password: "your-password"
  indeed:
    enabled: false
    credentials:
      email: "your-email@example.com"
      password: "your-password"
```

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
2. **Open Browser** — Launches a headless Chromium instance via Playwright
3. **Search Jobs** — Queries the platform for matching positions
4. **Fill Forms** — Detects input fields, matches them to CV data, and fills them
5. **Submit** — Submits the application (with safety checks on generic sites)

## Requirements

- Python 3.10+
- Chromium (installed automatically via `playwright install chromium --with-deps`)
- ~1 GB RAM minimum for headless browser
