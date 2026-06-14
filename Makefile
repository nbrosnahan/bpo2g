.PHONY: setup build lint format typecheck test sync bootstrap preflight

# Create/update the uv-managed virtualenv from uv.lock (incl. dev deps).
setup sync:
	uv sync

build:
	uv run python -m build

lint:
	uv run ruff check src/ tests/ bootstrap_garmin_session.py

format:
	uv run ruff format src/ tests/ bootstrap_garmin_session.py

typecheck:
	uv run mypy src/ bootstrap_garmin_session.py

test:
	uv run pytest

# Mint/refresh the Garmin OAuth token session (needs GARMIN_USERNAME/PASSWORD).
bootstrap:
	uv run python bootstrap_garmin_session.py

# Full local pre-merge gate.
preflight: lint typecheck test
