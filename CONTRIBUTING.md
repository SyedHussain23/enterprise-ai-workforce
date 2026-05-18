# Contributing to Enterprise AI Workforce

Thank you for taking the time to contribute. This document explains how to get involved, set up your development environment, and submit high-quality changes.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Reporting Bugs](#reporting-bugs)
3. [Proposing Features](#proposing-features)
4. [Development Setup](#development-setup)
5. [Frontend Setup](#frontend-setup)
6. [Branch Strategy](#branch-strategy)
7. [Commit Message Format](#commit-message-format)
8. [Pull Request Checklist](#pull-request-checklist)
9. [Code Style](#code-style)
10. [Testing](#testing)
11. [Merging Policy](#merging-policy)

---

## Code of Conduct

This project is governed by the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to abide by its terms. Violations may be reported to **hussainbold1997@gmail.com**.

---

## Reporting Bugs

Found a bug? Please [open a GitHub Issue](../../issues/new?template=bug_report.md) using the **Bug Report** template. Before filing, search existing issues to avoid duplicates.

Include as much detail as possible:

- A clear, descriptive title prefixed with `[BUG]`
- Steps to reproduce the problem
- Expected vs. actual behaviour
- Environment details (OS, Python version, Node version, Docker version)
- Relevant log output and/or screenshots

For security-sensitive bugs, **do not open a public issue**. Instead, follow the [Security Policy](SECURITY.md).

---

## Proposing Features

Have an idea? [Open a Feature Request issue](../../issues/new?template=feature_request.md) using the **Feature Request** template.

A good proposal includes:

- The problem your feature solves (from a user's perspective)
- A clear description of the proposed solution
- Alternatives you have considered
- Which component(s) are affected (Backend, Frontend, RAG pipeline, Agents, DevOps, Docs)

Proposals are discussed in the issue before any code is written. Starting implementation before discussion may result in a PR being declined.

---

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20 LTS
- Docker & Docker Compose
- Git

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/SyedHussain23/enterprise-ai-workforce.git
cd enterprise-ai-workforce

# 2. Copy the environment template and fill in your values
cp .env.example .env

# 3. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # macOS / Linux
# venv\Scripts\activate           # Windows

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Apply database migrations
alembic upgrade head

# 6. Build the vector database (requires documents in data/)
python build_vector_db.py

# 7. Start the backend development server
uvicorn app.api.server:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs are at `http://localhost:8000/docs`.

### Using Docker Compose (optional)

```bash
docker compose up --build
```

This starts the backend, Redis, and PostgreSQL together.

---

## Frontend Setup

```bash
# From the repository root
cd frontend

# Install dependencies
npm install

# Start the development server (proxies /api to localhost:8000)
npm run dev
```

The frontend will be available at `http://localhost:5173`.

To run a production build locally:

```bash
npm run build
npm run preview
```

---

## Branch Strategy

| Branch | Purpose | Protected |
|--------|---------|-----------|
| `main` | Production-ready code. Every commit is deployable. | Yes — PRs only |
| `develop` | Integration branch for completed features before release | No |
| `feature/xxx` | New features and enhancements, branched from `develop` | No |
| `fix/xxx` | Bug fixes, branched from `develop` (or `main` for hotfixes) | No |
| `docs/xxx` | Documentation-only changes | No |

### Guidelines

- Branch names use lowercase kebab-case: `feature/add-agent-scheduler`, `fix/jwt-expiry-crash`.
- Keep branches short-lived. Open a draft PR early to signal work in progress.
- Rebase onto `develop` (not merge) to keep history linear before requesting review.
- Delete branches after merging.

---

## Commit Message Format

This project follows [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

```
<type>(<optional scope>): <short imperative summary>

[optional body — explain *why*, not *what*]

[optional footer(s) — BREAKING CHANGE:, Closes #xxx]
```

### Allowed types

| Type | When to use |
|------|-------------|
| `feat` | A new feature visible to users or API consumers |
| `fix` | A bug fix |
| `docs` | Documentation changes only (no code) |
| `chore` | Build system, dependency updates, tooling |
| `test` | Adding or correcting tests |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `ci` | Changes to CI/CD pipeline configuration |
| `perf` | Performance improvements |

### Examples

```
feat(agents): add support for scheduled agent execution

Introduces a cron-based trigger system so agents can run on a fixed
schedule without user interaction.

Closes #42
```

```
fix(auth): resolve JWT expiry race condition on token refresh

Token refresh was invalidating the old token before issuing the new one,
causing a brief window of 401 errors for concurrent requests.
```

```
docs: add CONTRIBUTING guide and branch strategy

BREAKING CHANGE: none
```

```
chore(deps): bump langchain to 0.2.14
```

### Rules

- Subject line: 72 characters maximum, no full stop at the end.
- Use the imperative mood: "add feature", not "added feature" or "adds feature".
- Reference issues in the footer: `Closes #123`, `Fixes #456`.
- Mark breaking changes in the footer: `BREAKING CHANGE: <description>`.

---

## Pull Request Checklist

Before marking a PR as ready for review, confirm all of the following:

- [ ] All existing tests pass (`pytest` for backend, `npm run test` for frontend if applicable)
- [ ] TypeScript type-checks without errors (`npx tsc --noEmit` inside `frontend/`)
- [ ] `npm run build` completes successfully
- [ ] Code style checks pass (`ruff check .` and `black --check .` for Python; `npx eslint .` for TypeScript)
- [ ] The PR description clearly explains **what** changed and **why**
- [ ] Screenshots or screen recordings are attached for any UI changes
- [ ] No secrets, API keys, or `.env` values are committed
- [ ] `.env.example` is updated if new environment variables were introduced
- [ ] A database migration is included if the schema changed (`alembic revision --autogenerate`)
- [ ] A `CHANGELOG` entry is added under `[Unreleased]`

Use the [PR template](.github/PULL_REQUEST_TEMPLATE.md) — it is loaded automatically when you open a pull request.

---

## Code Style

### Python

- **Formatter:** [Black](https://black.readthedocs.io/) — default settings, line length 88.
- **Linter:** [Ruff](https://docs.astral.sh/ruff/) — configured in `pyproject.toml`.
- Run both before committing:

```bash
black .
ruff check . --fix
```

### TypeScript / React

- **Linter:** [ESLint](https://eslint.org/) — configured via `.eslintrc.cjs` in `frontend/`.
- Run before committing:

```bash
cd frontend
npx eslint . --fix
npx tsc --noEmit
```

Pre-commit hooks (via `pre-commit`) are defined in `.pre-commit-config.yaml` and will run these checks automatically if installed:

```bash
pip install pre-commit
pre-commit install
```

---

## Testing

### Backend

Tests live in `tests/` and are run with [pytest](https://pytest.org/):

```bash
pytest                        # run all tests
pytest tests/unit/            # unit tests only
pytest tests/integration/     # integration tests only
pytest -k "test_auth"         # filter by name
pytest --cov=app              # with coverage report
```

The test suite covers:

- **Authentication** — login, token refresh, role enforcement, JWT expiry
- **Agent execution** — task dispatch, result handling, error propagation
- **RAG pipeline** — document ingestion, retrieval accuracy, answer generation
- **API endpoints** — request validation, response schemas, HTTP status codes
- **Database layer** — CRUD operations, migration correctness
- **Security helpers** — `_safe_path()` traversal protection, secret enforcement

New code must ship with tests. Bug fixes must include a regression test that would have caught the bug.

### Frontend

Run type-checking and lint as your primary quality gates:

```bash
cd frontend
npx tsc --noEmit
npx eslint .
npm run build
```

---

## Merging Policy

- **Squash merges only.** Every PR lands as a single, clean commit on the target branch. The commit message must follow the Conventional Commits format described above.
- **Linear history.** Force-push and merge commits are disabled on `main`. Rebase your branch before merging.
- **Minimum one approval** from a maintainer before merge.
- **All CI checks must be green** before merge is permitted.
- The PR author is responsible for resolving conflicts and keeping the branch up to date.

---

Thank you for helping make Enterprise AI Workforce better.
