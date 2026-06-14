**bpo2g** - Parse blood pressure reports exported from Omron as .csv files then import them into Garmin Connect

This is a simple python program that loads files that have been exported from OMRON containing blood pressure history data.

**WARNING!!** It does not check for existing data in Garmin Connect, so if you run it twice, it will create duplicate data.

First, you need to use the Omron app to request a historical report of BP readings.

In the Omron Connect app, go to History > Blood Pressure and tap the Share button in the upper right corner.

Select only Blood Pressure and the period you want, then choose the CSV format and request Omron to email you the report.

Once you receive the emailed .csv report, download the CSV report attachment into a local directory.  The bpo2g tool will work with multiple CSV reports.  

**WARNING!!** Make sure they have non-overlapping date ranges so you don't end up with duplicate data in Garmin Connect.

The Omron BP reports are named like this (in English):
```
Your Requested OMRON Report from Jan 01 2025 to Jan 22 2025.csv
```

And the format should be this: 
```
Date,Time,Systolic (mmHg),Diastolic (mmHg),Pulse (bpm),Symptoms,Consumed,TruRead,Notes
Jan 12 2025,08:12,114,74,47,-,-,-,-
Jan 10 2025,07:49,114,71,47,-,-,-,-
Jan 6 2025,08:46,117,76,50,-,-,-,-
```

Once you have all the reports you want to migrate downloaded, you can proceed to set up the requirements to run the script.

## Setup

This project uses [`uv`](https://docs.astral.sh/uv/) and requires Python 3.12+.

```bash
make setup      # uv sync — create/update the venv from uv.lock
```

Makefile targets:

- `setup` / `sync`: create/update the uv-managed venv from `uv.lock`
- `build`: build the python package
- `lint`: ruff lint
- `format`: ruff format
- `typecheck`: mypy
- `test`: pytest
- `preflight`: lint + typecheck + test (run before pushing)
- `bootstrap`: mint/refresh the Garmin token session (see below)

## Authenticating to Garmin Connect

> **Why this is a two-step process:** Garmin blocks its mobile/password login
> endpoint (HTTP 429). The `garminconnect` library works around this internally
> — its login tries several strategies (including Garmin's web sign-in widget
> via a browser-impersonating TLS client) and saves a reusable token session.
> bpo2g mints that session once (it lasts ~1 year) with
> `bootstrap_garmin_session.py`, then the upload command authenticates from the
> saved session and never needs your password again.

**Step 1 — mint the token session (roughly yearly):**

```bash
cp .env.example .env        # then fill in GARMIN_USERNAME / GARMIN_PASSWORD
make bootstrap              # uv run python bootstrap_garmin_session.py
```

This writes the token session to `~/.garminconnect` by default (override with
`--tokenstore PATH` or the `GARMINTOKENS` env var). If your account has MFA
enabled, you'll be prompted for the code. If your `.env` stores credentials as
`op://` references (1Password), run it under `op run`:

```bash
op run --env-file=.env -- uv run python bootstrap_garmin_session.py
```

**Step 2 — upload your readings (any time, no login):**

```bash
uv run python src/bpo2g.py -c <csv_directory> [--dry_run] [--requestdelayms <ms>]
```

bpo2g loads the saved session and uploads each reading. If the session is
missing or expired it will tell you to re-run the bootstrap. It uploads using
the [garminconnect](https://pypi.org/project/garminconnect/) library.

> **Rate limit:** avoid running more than ~8–10 times per day, and remember
> bpo2g does **not** de-duplicate — don't upload overlapping date ranges.




