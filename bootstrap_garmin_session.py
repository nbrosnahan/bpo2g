#!/usr/bin/env python3
# Copyright 2026 Tumbling Potato
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Mint/refresh the Garmin Connect OAuth token session.

Why this exists
---------------
Garmin blocks the mobile/password login endpoint with HTTP 429, so a session
must be minted via Garmin's Cloudflare-protected web SSO. As of garminconnect
0.3.x this workaround is **built in**: ``Garmin.login()`` runs a multi-strategy
chain (mobile + SSO-embed-widget + portal-web, all via ``curl_cffi`` Chrome TLS
impersonation) and persists a native ``garmin_tokens.json`` to the token store.

This script just drives that credential login once and saves the session. The
bpo2g upload command then resumes it **token-only** (no credentials). The
session lasts ~1 year, so this is a roughly-yearly step.

Usage
-----
    uv run python bootstrap_garmin_session.py [--tokenstore PATH]

Reads GARMIN_USERNAME and GARMIN_PASSWORD from a local ``.env`` file (via
python-dotenv) or the ambient environment — so you can also run it under a
secrets manager, e.g.:

    op run --env-file=.env -- uv run python bootstrap_garmin_session.py

If the account has MFA enabled, you'll be prompted for the code interactively.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError,
)

# Where bpo2g loads the session from (Garmin().login(tokenstore=...)).
DEFAULT_TOKENSTORE = os.getenv("GARMINTOKENS", "~/.garminconnect")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bootstrap")


def _prompt_mfa() -> str:
    return input("Garmin MFA code: ").strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mint/refresh the Garmin OAuth token session. Needs "
        "GARMIN_USERNAME/GARMIN_PASSWORD (in .env or the environment). See the "
        "module docstring for the full rationale.",
    )
    parser.add_argument(
        "--tokenstore",
        default=DEFAULT_TOKENSTORE,
        help="Directory to write the Garmin token session into "
        "(default: $GARMINTOKENS or ~/.garminconnect). Must match the "
        "--tokenstore bpo2g loads from.",
    )
    args = parser.parse_args()

    # Load GARMIN_USERNAME / GARMIN_PASSWORD from a local .env if present.
    load_dotenv()
    email = os.environ.get("GARMIN_USERNAME")
    password = os.environ.get("GARMIN_PASSWORD")
    if not email or not password:
        log.error(
            "GARMIN_USERNAME and GARMIN_PASSWORD must be set (in .env or the "
            "environment)."
        )
        sys.exit(1)

    session_dir = str(Path(args.tokenstore).expanduser())
    log.info("Session dir: %s", session_dir)
    os.makedirs(session_dir, exist_ok=True)

    # garminconnect's login() reuses a valid cached session if one exists, and
    # otherwise runs its Cloudflare-aware strategy chain and dumps a fresh
    # garmin_tokens.json into session_dir.
    garmin = Garmin(email, password, prompt_mfa=_prompt_mfa)
    try:
        garmin.login(tokenstore=session_dir)
    except GarminConnectTooManyRequestsError:
        log.error(
            "Garmin returned HTTP 429 (rate limited). Wait a few minutes and "
            "try again — avoid repeated login attempts."
        )
        sys.exit(1)
    except GarminConnectAuthenticationError as e:
        log.error("Authentication failed: %s", e)
        sys.exit(1)
    except Exception as e:  # noqa: BLE001 — top-level, report and exit nonzero
        log.error("Login failed: %s", e)
        sys.exit(1)

    log.info("Success! Session saved to %s", session_dir)
    print(f"User: {garmin.get_full_name()}")


if __name__ == "__main__":
    main()
