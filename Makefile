setup:
	./python_uv_setup.sh

build:
	uv pip install build
	uv run python -m build

lint:
	uv pip install ruff
	uv run ruff check

format:
	uv pip install ruff
	uv run ruff format
