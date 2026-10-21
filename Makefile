.PHONY: help test lint

help:
	@echo "Tillegal AI Service Makefile"

test:
	pytest

lint:
	ruff check .
