# Project Work Log

## 2026-06-13 — Modernize deps + fix Garmin auth (token-session model)

**Goal:** Make the project work again — Garmin's credential login is blocked, and the libraries were stale.

**Done:**
- **Garmin auth reworked** to a persisted token session. `bpo2g.py` no longer prompts for a password; it resumes a saved session via `Garmin().login(tokenstore=...)` (`--tokenstore`, default `~/.garminconnect` / `$GARMINTOKENS`) and exits with a clear bootstrap hint if the session is missing/expired.
- **Added `bootstrap_garmin_session.py`** — a thin wrapper that calls `Garmin(email, password).login(tokenstore=...)` to mint/refresh the session; garminconnect 0.3.x does the Cloudflare-aware SSO login internally. Reads `GARMIN_USERNAME`/`GARMIN_PASSWORD` from `.env`; prompts for MFA if needed.
- **Dependency refresh:** garminconnect 0.2.40→0.3.5, click 8.3→8.4; added python-dotenv. Migrated from `requirements.txt` to the uv-project model (`pyproject.toml` deps + `uv.lock`, dev group).
- **Python floor bumped to 3.12** (garminconnect 0.3.3+ dropped 3.10/3.11). CI matrix → 3.12/3.13 on `uv sync`.
- **Real tests** replacing placeholder scaffolding — parsing, sorting, ISO conversion, stats, and the login-failure path; added a real Omron CSV fixture.
- **Bug fix:** `output_basic_stats` no longer divides by zero when no readings fall in the last 6 months.
- Fixed a packaging bug (single-module `py-modules` layout — the wheel now actually contains `bpo2g.py` + a console-script entry point), resolved leftover merge-conflict markers in `LICENSE`, and refreshed README/CLAUDE.md/Makefile/.gitignore + `.env.example`.
- **Verified live:** ran `make bootstrap` via `op run` — mobile login 429s, falls through to the SSO-embed strategy, writes `garmin_tokens.json`; dry-run upload then resumes the session token-only and lists the uploads.

**Decisions:**
- **Let garminconnect own the Cloudflare workaround.** First draft hand-rolled the web-SSO-widget + `curl_cffi` + `garth` ticket-exchange flow (copied from `WithingsSync`). But garminconnect 0.3.x already does exactly this internally (multi-strategy login: mobile → SSO-embed → portal, all over curl_cffi) and persists a native `garmin_tokens.json`. So the custom bootstrap was deleted in favor of a ~30-line credential-login wrapper, and the direct `garth`/`curl-cffi` deps were dropped (curl_cffi is transitive via garminconnect). `WithingsSync` still needs its custom script because it pins old `withings-sync`/`garth` — the two are **no longer** kept in sync.
- **Token format note:** garminconnect 0.3.x dropped garth; it reads a single `garmin_tokens.json`, not garth's `oauth1_token.json`/`oauth2_token.json`. A token store minted by an old garth-based flow won't load.
- **Python 3.12 floor:** chose latest garminconnect (0.3.5) over preserving 3.10/3.11 compatibility, since this is a personal CLI and the dev box already runs 3.14.
- **Placeholder tests replaced (not silently dropped):** `test_dummy`/`test_process_data` asserted nothing about real behavior; replaced with tests that exercise the actual parsing/auth code. Old `tests/fixtures/sample.json` removed (unused).
