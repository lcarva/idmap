PYTHON ?= python3

.DEFAULT_GOAL := help

.PHONY: help compile test build ci

help:
	@echo "Available targets:"
	@echo "  compile  Compile Python files"
	@echo "  test     Run unit tests"
	@echo "  build    Build the sdist and wheel (requires the 'build' package)"
	@echo "  ci       Run compile, test, and build"

compile:
	@$(PYTHON) -m py_compile idmap.py test_idmap.py

test:
	@$(PYTHON) -m unittest discover -v

build:
	@$(PYTHON) -c "import build" 2>/dev/null || { \
		echo "The 'build' package is required: $(PYTHON) -m pip install build"; \
		exit 1; \
	}
	@$(PYTHON) -m build

ci: compile test build
