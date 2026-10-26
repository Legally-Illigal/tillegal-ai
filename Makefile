.PHONY: help install test lint run

help:
	@echo "Tillegal AI Service Makefile"
	@echo "  install   - install dependencies with uv"
	@echo "  test      - run pytest"
	@echo "  lint      - run ruff"
	@echo "  run       - run the FastAPI app"

install:
	uv sync --all-groups

test:
	uv run pytest

lint:
	uv run ruff check .

run:
	uv run python -m src.main
