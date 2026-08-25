# Bret's DevOps and *Ops Skills

A bunch of skills for daily work in DevOps, found in `./skills/`

Installable via `npx skills add https://github.com/bretfisher/skills` and mark the ones you want to install. Add `-g` to command to install them globally.

## Skills

| Name | Purpose |
| --- | --- |
| `docker-pro` | Light up all the best docker features and security best practices for dockerizing a repo. From a Docker Captain. |
| `github-actions-workflow-pro` | Create, edit, audit, and speed up GitHub Actions workflows with opinionated security and speed defaults. Fires on its own whenever a `.github/workflows/*` file is in play. Ships `references/` (security, speed, audit) and `scripts/pin-action.sh`. |
| `gha-audit` | Type `/gha-audit [file]` to run the audit path of `github-actions-workflow-pro` on demand: tools first (`actionlint`, `zizmor`, `gasa`), then a report split into correctness, hard findings, speed, and opinions, plus a proposed diff. User-invoked only. |
| `super-linting` | Picks the right linter for every file type in a project and wires them into a `make lint` target plus an agent-guide contract so code is linted before every commit. Focused on local developer/agent linting, not CI. |

## Repo layout

| Path | What | Committed? |
| --- | --- | --- |
| `skills/<name>/SKILL.md` | The skill itself: description (the trigger), working style, checklist, validate step, done-when | ✅ yes |
| `skills/<name>/references/*.md` | Detail the skill reads only when a branch needs it (rules + the why, audit procedure) | ✅ yes |
| `skills/<name>/scripts/*.sh` | Deterministic helpers the skill runs instead of re-deriving (e.g. `pin-action.sh`) | ✅ yes |
| `skills/<name>/evals/evals.json` | Eval **definitions** (prompts + assertions) — the test contract | ✅ yes |
| `skills/<name>/evals/fixtures/` | Input files some evals hand to the agent (a deliberately insecure or slow workflow) | ✅ yes |
| `.evals/<name>/iteration-N/` | Eval **run artifacts** (transcripts, gradings, timings, benchmarks) | ❌ gitignored |

## Makefile

`make help` lists everything. Tools are checked, never installed; a missing one prints its `brew install` formula.

| Target | What it does |
| --- | --- |
| `make lint` | Pre-commit gate: `markdownlint` and `yamllint` (configs in `.github/linters/`, the same files super-linter reads in CI), `shellcheck` on `skills/*/scripts/*.sh`, `py_compile` on `skills/*/scripts/*.py`, and `actionlint` + `zizmor` + `poutine` on this repo's workflows (actionlint also on the well-formed eval fixtures) |
| `make eval-benchmark [SKILL=… ITER=…]` | Aggregate the latest `.evals/<skill>/iteration-N/` into `benchmark.json` + `benchmark.md` via the skill-creator plugin |
| `make eval-view [SKILL=… ITER=…]` | Open the skill-creator review viewer on that iteration |
| `make pin ACTION=owner/repo[@ref]` | Print a SHA-pinned `uses:` line for an action, newest release at least 7 days old |
| `make run-stats [RUNS=3] [REPO=owner/repo]` | Rank a repo's workflows and jobs by mean duration over the last few runs, flag inconsistent timing and recent failures |

`SKILL` defaults to `github-actions-workflow-pro`; `ITER` defaults to the highest iteration present.

### Skill evals

Eval *definitions* live next to each skill (`skills/<name>/evals/evals.json`) and are committed —
they document what each skill is supposed to do and let anyone re-run the evals to catch regressions.

Eval *run artifacts* (the output of executing those evals) are written to `.evals/<name>/iteration-N/`
at the repo root, which is gitignored. They're regenerated on every run and machine-specific, so they
aren't source of truth. When running the skill-creator eval loop, point its workspace at
`.evals/<name>/` rather than the default `<name>-workspace/` sibling.

See [AGENTS.md](./AGENTS.md) for the full convention (also symlinked as `CLAUDE.md`), and [PLAN.md](./PLAN.md) for the roadmap.
