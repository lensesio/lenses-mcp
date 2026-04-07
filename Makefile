.PHONY: help install lint format format-check typecheck test test-cov security vulnerabilities licenses \
       build-container pre-commit clean ci

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Setup ──────────────────────────────────────
install: ## Install all dependencies (dev included)
	uv sync --locked --all-extras --dev
	uvx pre-commit install

# ── Quality ────────────────────────────────────
lint: ## Run ruff linter
	uv run ruff check .

format: ## Run ruff formatter (fix mode)
	uv run ruff format .

format-check: ## Check formatting without fixing
	uv run ruff format --check .

typecheck: ## Run mypy type checker
	uv run mypy src/

# ── Testing ────────────────────────────────────
test: ## Run tests
	uv run pytest -x -q

test-cov: ## Run tests with coverage
	uv run pytest --cov=src --cov-report=xml --cov-report=term-missing --cov-fail-under=0 -x -q

# ── Security & Compliance ──────────────────────
security: ## Run Bandit security rules via Ruff
	uv run ruff check --select S .

vulnerabilities: ## Scan for known vulnerabilities
	uv run pip-audit

licenses: ## Check dependency licenses
	uv run pip-licenses \
		--fail-on="GNU General Public License v3 (GPLv3);GNU Affero General Public License v3 (AGPLv3)" \
		--allow-only="MIT;MIT License;MIT style;DFSG approved; MIT License;BSD License;BSD-2-Clause;BSD-3-Clause;Apache Software License;Apache-2.0;ISC License (ISCL);Mozilla Public License 2.0 (MPL 2.0);Python Software Foundation License;PSF-2.0;The Unlicense (Unlicense);Apache Software License; MIT License;BSD License; GNU General Public License (GPL); Public Domain;Apache-2.0 OR BSD-3-Clause;Apache-2.0 OR BSD-2-Clause;Apache-2.0 AND BSD-2-Clause"

# ── Container ──────────────────────────────────
build-container: ## Build Docker image locally
	docker build -t app:local .

# ── CI (run all checks locally) ────────────────
ci: lint format-check typecheck security test-cov vulnerabilities licenses ## Run all CI checks locally

# ── Pre-commit ────────────────────────────────
pre-commit: ## Run all pre-commit hooks
	uvx pre-commit run --all-files

# ── Cleanup ────────────────────────────────────
clean: ## Remove build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache coverage.xml htmlcov dist .venv
