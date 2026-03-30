# CLAUDE.md

## Project Metadata
- GitHub Repo: nbrosnahan/bpo2g (public — Apache 2.0)
- Assignee: Nick Brosnahan

## Project Overview

bpo2g (Blood Pressure Omron to Garmin) is a Python CLI that parses blood pressure CSV reports exported from the Omron Connect app and uploads readings to Garmin Connect. Supports dry-run mode, batch processing, configurable request delays, and basic statistics output.

## Tech Stack

- **Python 3.10+** with `uv` as package manager
- **Click** — CLI argument parsing
- **garminconnect / garth** — Garmin Connect API integration
- **pydantic** — data validation
- **ruff** — linting and formatting
- **pytest** — testing

## Build & Run

```bash
# Initial setup (installs uv, creates venv, installs deps)
make setup

# Build the package
make build

# Lint
make lint

# Format
make format

# Sync dependencies
make sync

# Run
python3 src/bpo2g.py -c <csv_directory> -u <garmin_email> [--dry_run] [--requestdelayms <ms>]
```

## Testing

```bash
# Run tests
pytest
```

Tests are in `tests/` with fixtures in `tests/fixtures/`. Config in `tests/conftest.py`.

## CI / GitHub Actions

- Workflow: `.github/workflows/python-package.yml`
- Triggers on push and PR to `main`
- Matrix: Python 3.10, 3.11
- Steps: install deps, lint with flake8, run pytest

## Project Structure

```
bpo2g/
├── src/
│   └── bpo2g.py              # Main application (~240 lines)
├── tests/
│   ├── conftest.py            # pytest fixtures
│   ├── test_bpo2g.py          # Test suite
│   └── fixtures/
│       └── sample.json
├── .github/workflows/
│   └── python-package.yml     # CI config
├── Makefile                   # Build targets
├── pyproject.toml             # Package metadata
├── requirements.txt           # Dependencies
└── README.md                  # Documentation
```

## Key Details

- `BPReading` is a NamedTuple: (time, systolic, diastolic, bpm)
- Garmin password is prompted securely at runtime (not stored in config)
- Rate limiting: avoid running more than 8-10 times per day
- Duplicate uploads are not prevented — user must track what's been synced
