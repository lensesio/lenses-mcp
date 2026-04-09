# CI/CD

## Workflows Overview

| Workflow | Trigger | Purpose |
|---|---|---|
| **ci.yml** | PRs, `workflow_call` (from cd.yaml) | Primary CI: test, lint, typecheck, security, vulnerabilities, licenses, secrets, container build |
| **cd.yaml** | Push (all branches + version tags) | Calls CI, then builds and pushes Docker images, SBOMs, license report, GCS artifacts; on tags: GitHub Release + attestations |
| **pr-title.yaml** | PR open/sync/reopen | Validates single commit + conventional commit title format |
| **pre-ci-slack.yaml** | CI started (`workflow_run`) | Slack notification: CI started |
| **post-ci-slack.yaml** | CI completed (`workflow_run`) | Slack notification: success or failure |

## CI Jobs (`ci.yml`)

All jobs run in parallel:

| Job | What it does |
|---|---|
| **test** | pytest with coverage (Python 3.12 + 3.13 matrix) |
| **lint** | Ruff linter + format check |
| **typecheck** | mypy static type analysis (non-blocking) |
| **vulnerabilities** | pip-audit dependency vulnerability scan (non-blocking) |
| **licenses** | pip-licenses allowlist check (blocks GPL/AGPL) |
| **security** | Ruff Bandit rules (SAST) |
| **secrets** | Gitleaks secret detection |
| **build-container** | Docker build validation (no push) |
| **ci-passed** | Gate job — single required check for branch protection |

## CD Pipeline (`cd.yaml`)

Triggers on every push (branches and tags). CI runs first as a called workflow; build-and-push only proceeds if CI passes and the repo belongs to the internal org.

### Development builds (branches)

- Multi-arch Docker images (amd64 + arm64) pushed to GCR and ECR
- GCR tags: `{branch}`, `{sha}`, `{git-describe}`; ECR tags: `{branch}`, `{git-describe}`
- SBOMs (Python deps + Docker image) and license report uploaded to GCS

### Release builds (tags)

Supported tag patterns: `v1.0.0`, `v1.0.0-{alpha,beta,rc,la,pre}.N`

- Docker images pushed with version tag only (no `latest` or minor — safe for backfixes)
- SBOMs + license report uploaded to GCS and attached to GitHub Release
- GitHub attestations for provenance
- Auto-generated release notes (excludes `chore` and `ci` commits)

## PR Title Validation (`pr-title.yaml`)

Enforces:
1. Exactly one commit per PR (squash before merge)
2. Conventional commit format: `type(scope?): Message`
   - Types: `feat`, `fix`, `chore`, `docs`, `test`, `tests`, `refactor`, `ci`
   - Message must start with a capital letter
3. No ticket IDs in title (put in commit body)

## Required Secrets and Variables

### Secrets

| Secret | Used by | Purpose |
|---|---|---|
| `ECR_AWS_ACCESS_KEY_ID` | cd | AWS credentials for ECR push |
| `ECR_AWS_SECRET_ACCESS_KEY` | cd | AWS credentials for ECR push |
| `SLACK_WEBHOOK_URL` | pre/post-ci-slack | Slack incoming webhook (optional — steps are skipped if unset) |

### Variables

| Variable | Used by | Purpose |
|---|---|---|
| `GH_ORG` | cd | GitHub org that owns the internal registries. Gates all internal steps. |
| `GCR_REGISTRY` | cd | GCR registry host + project |
| `ECR_REGISTRY` | cd | ECR registry URL |
| `AWS_REGION` | cd | AWS region for ECR |
| `GCS_BUCKET_DEV` | cd | GCS bucket for development build artifacts |
| `GCS_BUCKET_RELEASE` | cd | GCS bucket for release artifacts |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | cd | GCP workload identity provider for OIDC auth |
| `GCP_SA_ACCOUNT` | cd | GCP service account for GCR push and GCS upload |

## Running CI Checks Locally

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
make license-report  # generate NOTICE.txt
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
