---
name: bpo2g
title: bpo2g
status: maintenance
created: 2026-06-17
color: "#614051"   # Eggplant
tags: [cli, python, fitness, health, garmin]
---
# CLAUDE.md

## Project Metadata
- GitHub Repo: nbrosnahan/bpo2g (public — Apache 2.0)
- Assignee: Nick Brosnahan

## Project Overview

bpo2g (Blood Pressure Omron to Garmin) is a Python CLI that parses blood pressure CSV reports exported from the Omron Connect app and uploads readings to Garmin Connect. Supports dry-run mode, batch processing, configurable request delays, and basic statistics output.

## Tech Stack

- **Python 3.12+** with `uv` as package manager (canonical metadata in `pyproject.toml`, locked in `uv.lock`)
- **Click** — CLI argument parsing
- **garminconnect** (0.3.x) — Garmin Connect API integration. Its `login()` is a Cloudflare-aware strategy chain that mints/persists a token session (it pulls `curl_cffi` transitively for TLS impersonation — we don't depend on it directly). Auth is via that persisted session, not credentials — see below.
- **python-dotenv** — loads bootstrap credentials from `.env`
- **ruff** — linting and formatting
- **mypy** — type checking
- **pytest** (+ `pytest-randomly`, `pytest-cov`) — testing

## Build & Run

```bash
make setup        # uv sync — create/update venv from uv.lock (incl. dev deps)
make build        # build the package
make lint         # ruff check
make format       # ruff format
make typecheck    # mypy src/
make test         # pytest
make preflight    # lint + typecheck + test (run before pushing)
make bootstrap    # mint/refresh the Garmin token session (see Garmin auth)

# Upload readings (no login — uses the persisted token session):
uv run python src/bpo2g.py -c <csv_directory> [--tokenstore <path>] [--dry_run] [--requestdelayms <ms>] [--force]
```

## Garmin auth model

**Garmin blocks the mobile/password login endpoint** (HTTP 429), so a session can't be minted by a naive `login(user, pass)`. garminconnect 0.3.x works around this internally: `Garmin.login()` runs a multi-strategy chain (mobile + **SSO embed widget** + portal web, all via `curl_cffi` Chrome TLS impersonation) — the mobile strategies 429, and it falls through to the web SSO widget, which succeeds. It then persists a native `garmin_tokens.json` to the token store. (This is why bpo2g no longer ships a hand-rolled SSO/curl_cffi bootstrap — garminconnect maintains that now. The sibling `~/Projects/WithingsSync` still has the custom version because it pins old `withings-sync`/`garth`.)

bpo2g splits this into two steps so the upload command never touches credentials:

- **`bootstrap_garmin_session.py`** — a thin wrapper that calls `Garmin(email, password).login(tokenstore=...)` once (a roughly-yearly step; the session lasts ~1 year). garminconnect mints/persists the session via the strategy chain above. Credentials come from `GARMIN_USERNAME`/`GARMIN_PASSWORD` in `.env` or the environment; MFA accounts are prompted interactively.
- **`bpo2g.py`** (upload) — loads the persisted session via `Garmin().login(tokenstore=...)`, **token-only, no credentials**. If the session is missing/expired it exits(1) with a hint to re-run the bootstrap.
- **Token store location:** defaults to `~/.garminconnect` (the garminconnect convention) — a single `garmin_tokens.json`. Override with `--tokenstore PATH` or the `GARMINTOKENS` env var. The bootstrap and the upload command must point at the same store.

Run the bootstrap under a secrets manager if `.env` holds `op://` references (as the local `.env` does):

```bash
op run --env-file=.env -- uv run python bootstrap_garmin_session.py
```

## Testing

```bash
make test   # or: uv run pytest
```

Tests live in `tests/` (`test_bpo2g.py`) with a real Omron CSV fixture in `tests/fixtures/`. Pytest config (strict markers, durations, junit xml) is in `pyproject.toml`.

## CI / GitHub Actions

- Workflow: `.github/workflows/python-package.yml`
- Triggers on push and PR to `main`
- Matrix: Python 3.12, 3.13
- Steps: `uv sync --frozen`, lint with ruff, type-check with mypy, run pytest

## Project Structure

```
bpo2g/
├── src/
│   └── bpo2g.py                  # Upload CLI (parse Omron CSV → Garmin)
├── bootstrap_garmin_session.py   # Mint/refresh the Garmin OAuth token session
├── tests/
│   ├── conftest.py               # pytest fixtures
│   ├── test_bpo2g.py             # Test suite
│   └── fixtures/
│       └── Your Requested OMRON Report ... .csv
├── .github/workflows/
│   └── python-package.yml        # CI config
├── .env.example                  # Template for bootstrap credentials
├── Makefile                      # Build targets
├── pyproject.toml                # Package metadata + deps (canonical)
├── uv.lock                       # Locked dependency graph
└── README.md                     # Documentation
```

## Key Details

- `BPReading` is a NamedTuple: (time, systolic, diastolic, bpm)
- Auth is a persisted OAuth token session (see *Garmin auth model*) — no password prompt
- Rate limiting: avoid running more than 8-10 times per day
- Duplicate detection: before uploading, bpo2g queries Garmin over the CSV's date span (`fetch_existing_bp_timestamps`, chunked into ≤28-day windows to respect Garmin's range-query cap) and skips any reading whose minute-precision timestamp already exists there; a timestamp match with *different* values (e.g. a corrected re-export) logs a WARNING but still skips rather than overwriting. Bypass entirely with `--force`. **Known limitation:** the match relies on bpo2g's own UTC-tagging convention (`datetime_to_iso_string` treats naive CSV times as UTC), so it reliably de-dupes readings bpo2g itself uploaded; readings entered by other means with a real local-timezone offset may not line up and could still be re-uploaded.
