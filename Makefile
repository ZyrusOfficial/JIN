# JARVIS Makefile
# `make check` runs the full test suite. `make check-fast` runs the <60s subset.
.PHONY: check check-fast lint lint-fix format type-check test test-contract test-logic \
	test-property test-security test-simulation test-mutation run-skeleton clean \
	install-dev secrets-scan dep-scan

PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
TEST_PATH := src/python
export PYTHONPATH := src/python:$(PYTHONPATH)

# ---------------------------------------------------------------------------
# Top-level gates
# ---------------------------------------------------------------------------

check: lint type-check test-contract test-logic test-property test-security test-simulation test-mutation
	@echo "=== make check: ALL GATES PASSED ==="

check-fast: lint type-check test-contract test-logic
	@echo "=== make check-fast: FAST SUBSET PASSED ==="

# ---------------------------------------------------------------------------
# Lint and format
# ---------------------------------------------------------------------------

lint:
	@echo "--- ruff check ---"
	$(PYTHON) -m ruff check $(TEST_PATH) src/python/jarvis
	@echo "--- ruff format --check ---"
	$(PYTHON) -m ruff format --check $(TEST_PATH) src/python/jarvis

lint-fix:
	$(PYTHON) -m ruff check --fix $(TEST_PATH) src/python/jarvis

format:
	$(PYTHON) -m ruff format $(TEST_PATH) src/python/jarvis
	$(PYTHON) -m ruff check --fix $(TEST_PATH) src/python/jarvis

# ---------------------------------------------------------------------------
# Type checking
# ---------------------------------------------------------------------------

type-check:
	@echo "--- mypy strict ---"
	$(PYTHON) -m mypy src/python/jarvis --strict

# ---------------------------------------------------------------------------
# Security scans
# ---------------------------------------------------------------------------

secrets-scan:
	@echo "--- secret scanning ---"
	@if command -v trufflehog >/dev/null 2>&1; then \
		trufflehog filesystem . --only-verified --fail; \
	else \
		@echo "trufflehog not installed — skipping secret scan"; \
		@echo "Install: pip install trufflehog3"; \
	fi

dep-scan:
	@echo "--- dependency vulnerability scan ---"
	@if command -v safety >/dev/null 2>&1; then \
		safety check; \
	else \
		@echo "safety not installed — skipping dependency scan"; \
		@echo "Install: pip install safety"; \
	fi

# ---------------------------------------------------------------------------
# Test groups
# ---------------------------------------------------------------------------

test-contract:
	@echo "--- contract tests ---"
	$(PYTHON) -m pytest $(TEST_PATH)/tests/contract -v

test-logic:
	@echo "--- logic-flow tests ---"
	$(PYTHON) -m pytest $(TEST_PATH)/tests/logic -v

test-property:
	@echo "--- property tests ---"
	$(PYTHON) -m pytest $(TEST_PATH)/tests/property -v

test-security:
	@echo "--- security tests (prompt-injection corpus) ---"
	$(PYTHON) -m pytest $(TEST_PATH)/tests/security -v

test-simulation:
	@echo "--- simulation tests ---"
	$(PYTHON) -m pytest $(TEST_PATH)/tests/simulation -v

test-mutation:
	@echo "--- mutation tests ---"
	-$(PYTHON) -m pytest $(TEST_PATH)/tests/mutation -v || true

test: test-contract test-logic test-property test-security test-simulation test-mutation

# ---------------------------------------------------------------------------
# Walking skeleton
# ---------------------------------------------------------------------------

run-skeleton:
	@echo "--- walking skeleton: fake mic + fake LLM + TTS stub + popup ---"
	$(PYTHON) -m jarvis.skeleton

# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

clean:
	rm -rf .pytest_cache __pycache__ **/__pycache__ *.egg-info dist build
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# ---------------------------------------------------------------------------
# Install dev dependencies
# ---------------------------------------------------------------------------

install-dev:
	$(PIP) install -e ".[dev]"
