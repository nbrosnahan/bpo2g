.PHONY: setup build lint format typecheck test sync bootstrap preflight lint-markdown lint-markdown-fix

MARKDOWNLINT_CONFIG := $(HOME)/.claude/.markdownlint-cli2.jsonc

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

# Lint every Markdown file — zero warnings required.
lint-markdown:
	markdownlint-cli2 --config $(MARKDOWNLINT_CONFIG) '**/*.md'

# Auto-fix fixable Markdown issues (rewrites files in place).
lint-markdown-fix:
	markdownlint-cli2 --fix --config $(MARKDOWNLINT_CONFIG) '**/*.md'

# Full local pre-merge gate.
preflight: lint typecheck test lint-markdown
