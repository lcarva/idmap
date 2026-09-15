PYTHON ?= python3

.DEFAULT_GOAL := help

.PHONY: help compile test ci

help:
	@echo "Available targets:"
	@echo "  compile  Compile Python files"
	@echo "  test     Run unit tests"
	@echo "  ci       Run compile and test"

compile:
	@$(PYTHON) -m py_compile idmap test_idmap.py

test:
	@$(PYTHON) -m unittest discover -v

ci: compile test
