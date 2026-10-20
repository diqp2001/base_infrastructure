# AGENTS.md — rules for coding agents working on base_infrastructure

These rules apply to every autonomous or semi-autonomous coding agent (and to humans following the same
workflow). They complement `CLAUDE.md` (project overview) and the per-folder `CLAUDE.md` files. The
prioritised work list is [`BACKLOG.txt`](BACKLOG.txt) (repository root); testing details are
in [`docs/TESTING.md`](docs/TESTING.md).

---

## 1. Architecture rules (enforced by `lint-imports`, see `[tool.importlinter]` in `pyproject.toml`)

| Layer | May import | Must never import |
|---|---|---|
| `src/domain` | stdlib, pure libraries (dateutil, numpy where needed) | `src.infrastructure`, `src.application`, `src.interfaces`, `sqlalchemy`, `ibapi` |
| `src/application` | `src.domain`, repository ports / the `RepositoryFactory` | `src.infrastructure.models` (ORM) — go through a repository |
| `src/infrastructure` | `src.domain`, SQLAlchemy, IBKR / external SDKs | `src.application` |
| `src/interfaces` | `src.application`, `src.domain` | — (nothing else may import `src.interfaces`) |

- The `ignore_imports` lists in `pyproject.toml` are **recorded technical debt**. Never add an entry to make a
  change pass; remove entries when you fix them (BI-007).
- Financial factor dependencies (`calculate_dependencies` / `DependencySpec`) describe **financial data only**.
  ML training, artifacts and model providers are injected (e.g. `_provider`), never declared as factor
  dependencies.
- Point-in-time correctness: raw bars are stamped at their start and usable only once closed; a decision at
  time T uses `bar_calendar.bar_is_current` (no stale bar standing for a missing one) and never a value stamped
  after T. A missing input yields **no value** — never a hard-coded fallback (rate, price, volatility, …).
- A use case writing through several repositories wraps them in `unit_of_work.atomic(session)` (one owner of
  commit / rollback; see `src/infrastructure/repositories/CLAUDE.md`). Never call `session.commit()` in between.
- New factor classes follow the checklist in `src/CLAUDE.md` §1 (entity, library entry, ORM model, mapper,
  port, local + IBKR repository, factory registration, `DISCRIMINATOR_CLASS_MAP`).
- Do not create parallel frameworks or persistence layers: extend the existing repository / factory /
  resolution-service pattern. Prefer an existing dependency (e.g. `pandas_market_calendars`) to new code.
- The monitoring dashboard (`/monitor`, `monitoring_app.py`, compose service `monitor`) is **read-only**: no
  routes that mutate data or reach order submission.

## 2. Standard commands

Windows checkout (repository root, project venv):

```bash
# fast suite (what CI stage 2 runs), with coverage
PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest -m "not integration and not sql_server and not ibkr and not performance" --cov -q
# stage 1: architecture + unit
./.venv/Scripts/lint-imports
PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest -m "unit or architecture" -q
# one area
PYTHONUTF8=1 ./.venv/Scripts/python.exe -m pytest tests/component/factor_context -q -p no:cacheprovider --no-cov
```

Linux dev container (`docker compose exec app …`, working dir `/workspaces/base_infrastructure`):

```bash
python -m pytest -m "not integration and not sql_server and not ibkr and not performance" -q
lint-imports
# SQL Server tests: ONLY against a *_test database
DB_NAME=base_infra_test python -m pytest -m sql_server -q
```

Markers (assigned from the test location in `tests/conftest.py`): `unit`, `component`, `contract`,
`architecture`, `integration`, `sql_server`, `ibkr`, `e2e`, `property`, `performance`, `concurrency`, `slow`.
Fast tests need no database server, broker or network. `ibkr` tests run only with `IBKR_LIVE_SMOKE=1` and are
read-only.

Definition of "green" for a change: `lint-imports` 4/4 contracts kept, the fast suite passes with coverage at or
above `fail_under` in `pyproject.toml` (it includes the ruff ratchet `tests/architecture/test_lint_baseline.py`: no
new finding; lower `ruff_baseline.json` when you fix some), and the tests of the touched area pass. `python -m mypy
src` is report-only. Report the exact counts.

## 3. Task isolation and workflow

1. **One backlog item per task.** Before coding, write down: the BI id, scope, dependencies (must be done or
   explicitly waived), and the acceptance criteria you will test.
2. **Branch per item** from up-to-date `main`: `bi-0NN-short-name` (or `feature/…`, `bugfix/…`). Use a git
   worktree when another task is in progress in the main checkout. Never work directly on `main`.
3. **Never overwrite unrelated working-tree changes.** Check `git status` first; leave files you did not change
   untouched (e.g. a locally edited `src/main.py`) and never commit them.
4. Small commits with a message that says what changed and why. Do not commit generated files
   (`results/`, `weights/`, `mlruns/`, `.monitor/`, `*.db`, `__pycache__/`, `.coverage`).
5. **Tests with every behaviour change.** A verified defect that is not fixed in the task is pinned as a strict
   `xfail` / `expectedFailure` with the reason, so fixing it flips the test.
6. Never weaken a test, lower `fail_under`, add an import-linter exception, or mark a failing test skipped to
   get CI green.
7. **Report** at the end of every task: files changed, commands run with their results (counts), tests
   added, anything deferred or still failing, and the next eligible backlog item.

## 4. Retry limits

- At most **3 attempts** at the same failing command / approach. After that, stop, record the failure
  (command, error, what was tried) in the report and in the backlog item, and move on or ask.
- A test that fails intermittently twice is reported as flaky — never re-run until green.
- External services (IBKR, SQL Server, Docker): one connection attempt per diagnosis; if it fails, report the
  error instead of looping.

## 5. Approval gates — ask the user first

- Deleting or rewriting rows in any non-test database (including the app database `base_infra`), schema
  migrations, or the factor-value dedup script with `--apply`.
- `git push`, merging into `main`, force-push, rewriting history, deleting branches.
- Creating / closing GitHub issues or PRs, posting comments.
- Recreating / restarting Docker services (`ibkr` needs a phone 2FA approval; `app` may have VS Code attached),
  changing `.env` / `docker-compose.yml` secrets.
- Any connection to a live IBKR account, and any change to order-submission, risk or reconciliation code paths.
- Adding a new runtime dependency.

## 6. Prohibited actions

- Placing, modifying or cancelling orders (paper or live) during development or testing; enabling autonomous
  live trading; setting `IBKR_ALLOW_LIVE=yes` or `IBKR_ACCOUNT_MODE=live`.
- Production data mutations or production deployments.
- Committing secrets: `.env`, `.env.windows`, `secrets/`, `.monitor/`, API keys, passwords, tokens. Never
  print a secret value in logs, reports or issues.
- Writing `@claude` in GitHub issue / PR / comment text (it triggers the `claude.yml` workflow).
- Bypassing the import contracts, test markers or coverage threshold.
- Reusing a TWS / Gateway client id that another running process holds (the second connection fails); stop
  only processes you started yourself.
