# CI/CD

This directory contains local development tooling that mirrors the GitHub Actions CI/CD pipeline.

## Workflows Overview

| Workflow | Trigger | Purpose |
|---|---|---|
| **ci.yml** | Push (all branches/tags), PRs | Primary CI: test, lint, typecheck, security, vulnerabilities, licenses, secrets, container build |
| **cd.yaml** | CI success (workflow_run) | Build and push multi-arch Docker images to Docker Hub (+ GCR and AWS ECR on the internal org) |
| **release.yaml** | Semantic version tags (`v*.*.*`) | Full CI + multi-arch Docker push to Docker Hub (+ GCR and AWS ECR on the internal org) + GitHub Release with release notes |
| **pr-title.yaml** | PR open/sync/reopen | Validates single commit + conventional commit title format |
| **pre-ci-slack.yaml** | CI started (workflow_run) | Slack notification: CI started |
| **post-ci-slack.yaml** | CI completed (workflow_run) | Slack notification: success or failure |

## CI Jobs (`.github/workflows/ci.yml`)

All jobs run in parallel:

| Job | What it does |
|---|---|
| **test** | pytest with coverage (Python 3.12 + 3.13 matrix) |
| **lint** | Ruff linter + format check |
| **typecheck** | mypy static type analysis (non-blocking) |
| **vulnerabilities** | pip-audit dependency vulnerability scan |
| **licenses** | pip-licenses allowlist check (blocks GPL/AGPL) |
| **security** | Ruff Bandit rules (SAST) |
| **secrets** | Gitleaks secret detection |
| **build-container** | Docker build validation (no push) |

## CD Pipeline (`.github/workflows/cd.yaml`)

Triggered when CI completes successfully. Builds multi-arch (amd64 + arm64) Docker images and pushes them to:

- **Docker Hub** (always): `lensesio/mcp:{branch}`, `lensesio/mcp:{sha}`, `lensesio/mcp:{git-describe}`
- **GCR and AWS ECR** (internal org only): `${GCR_REGISTRY}/lenses-mcp:{…}` and `${ECR_REGISTRY}/lenses-mcp:{…}` with the same three tag variants

The internal-registry steps are gated on `vars.INTERNAL_ORG` matching `github.repository_owner`, so forks automatically skip them.

## Release Pipeline (`.github/workflows/release.yaml`)

Triggered on semantic version tags. Supported patterns:

- `v1.0.0` (stable) — pushes `:{version}`, `:{major.minor}`, `:latest`
- `v1.0.0-alpha.1`, `v1.0.0-beta.1`, `v1.0.0-rc.1` (pre-release) — pushes `:{version}` only

Steps: CI checks → multi-arch Docker build + push to Docker Hub (+ GCR and AWS ECR on the internal org) → GitHub Release with auto-generated notes. The same `INTERNAL_ORG` gate as CD means forks only push to Docker Hub.

## PR Title Validation (`.github/workflows/pr-title.yaml`)

Enforces:
1. Exactly one commit per PR (squash before merge)
2. Conventional commit format: `type(scope?): Message`
   - Types: `feat`, `fix`, `chore`, `docs`, `test`, `tests`, `refactor`, `ci`
   - Message must start with a capital letter
3. No ticket IDs in title (put in commit body)

## Required Secrets and Variables

### Secrets (always required)

| Secret | Used by | Purpose |
|---|---|---|
| `DOCKERHUB_USERNAME` | cd, release | Docker Hub authentication |
| `DOCKERHUB_TOKEN` | cd, release | Docker Hub authentication |
| `SLACK_WEBHOOK_URL` | pre/post-ci-slack | Slack incoming webhook URL (optional — steps are skipped if unset) |

### Secrets (internal org only)

Used by `cd.yaml` and `release.yaml` when `vars.INTERNAL_ORG` matches the repository owner. Skipped on forks.

| Secret | Used by | Purpose |
|---|---|---|
| `ECR_AWS_ACCESS_KEY_ID` | cd, release | AWS credentials for ECR push |
| `ECR_AWS_SECRET_ACCESS_KEY` | cd, release | AWS credentials for ECR push |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | cd, release | GCP workload identity provider for OIDC auth to GCR |
| `GCP_SERVICE_ACCOUNT` | cd, release | GCP service account for GCR push |

### Variables

| Variable | Used by | Purpose |
|---|---|---|
| `INTERNAL_ORG` | cd, release | GitHub org name that owns the internal registries. Gates all ECR/GCR steps. |
| `GCR_REGISTRY` | cd, release | GCR host + project (e.g. `${GCR_REGISTRY}`). Internal org only. |
| `ECR_REGISTRY` | cd, release | ECR registry URL (e.g. `123456789.dkr.ecr.${AWS_REGION}.amazonaws.com`). Internal org only. |

## Running CI Checks Locally

From the repo root, use the Makefile in this directory:

```bash
# Run all CI checks
make ci

# Individual targets
make lint
make format          # auto-fix formatting
make format-check    # check only (CI mode)
make typecheck
make test
make test-cov
make security
make vulnerabilities
make licenses
make build-container
```

## Pre-commit Hooks

Install hooks (one-time setup):

```bash
make install
```

This runs `uv sync` and installs pre-commit hooks that enforce lint, format, type checks, and secret detection on every commit.

## Composite Action (`.github/actions/setup-uv`)

Shared setup step used by all CI jobs. Installs uv, Python, and project dependencies with caching.
