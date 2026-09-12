# Bret's DevOps and \*Ops Skills

A bunch of skills for daily work in DevOps, found in `./skills/`

Installable via `npx skills add https://github.com/bretfisher/skills` and mark the ones you want to install. Add `-g` to command to install them globally.

## Skills

| Name                          | Purpose                                                                                                                                                                                                                                                                              |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `docker-pro`                  | Light up all the best docker features and security best practices for dockerizing a repo. From a Docker Captain.                                                                                                                                                                     |
| `github-actions-workflow-pro` | Create, edit, audit, and speed up GitHub Actions workflows with opinionated security and speed defaults. Fires on its own whenever a `.github/workflows/*` file is in play. Ships `references/` (security, speed, audit) and `scripts/run-stats.py`; pinning is delegated to pinact. |
| `gha-audit`                   | Type `/gha-audit [file]` to run the audit path of `github-actions-workflow-pro` on demand: tools first (`actionlint`, `zizmor`, `poutine`, `pinact`, `gasa`), then a report split into correctness, hard findings, speed, and opinions, plus a proposed diff. User-invoked only.     |
| `screencapture`               | Captures the macOS screen, a window, or a region with the built-in `screencapture` CLI and reads the image back so the agent can see native GUI apps (SwiftUI, AppKit, Electron, Qt). For non-web apps; web pages go to a browser automation tool.                                   |
| `super-linting`               | Picks the right linter for every file type in a project and wires them into a `make lint` target plus an agent-guide contract so code is linted before every commit. Focused on local developer/agent linting, not CI.                                                               |

## Repo layout

| Path                             | What                                                                                                                                                                                                              | Committed?    |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- |
| `skills/<name>/SKILL.md`         | The skill itself: description (the trigger), working style, checklist, validate step, done-when                                                                                                                   | ✅ yes        |
| `skills/<name>/references/*.md`  | Detail the skill reads only when a branch needs it (rules + the why, audit procedure)                                                                                                                             | ✅ yes        |
| `skills/<name>/scripts/*`        | Deterministic helpers the skill runs instead of re-deriving (`run-stats.py`; `scan.sh` runs zizmor/pinact with the GitHub token set inside its own process, so `gh auth token` never appears in a command or log) | ✅ yes        |
| `evals/<name>/evals.json`        | Eval **definitions** (prompts + assertions) — the test contract. Outside `skills/` so an installer copies only the skill                                                                                          | ✅ yes        |
| `evals/<name>/fixtures/`         | Input files some evals hand to the agent (a deliberately insecure or slow workflow)                                                                                                                               | ✅ yes        |
| `evals/<name>/runs/iteration-N/` | Eval **run artifacts** (transcripts, gradings, timings, benchmarks)                                                                                                                                               | ❌ gitignored |

## Makefile

`make help` lists everything. Tools are checked, never installed; a missing one prints its `brew install` formula.

| Target                                          | What it does                                                                                                                                                                                                                                                                                                                                                            |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `make lint`                                     | Pre-commit gate: `markdownlint`, `prettier --check`, and `yamllint` (configs in `.github/linters/`, the same rules super-linter applies in CI), `shellcheck` on `skills/*/scripts/*.sh`, `py_compile` on `skills/*/scripts/*.py`, and `actionlint` + `zizmor` + `poutine` + `pinact -check` on this repo's workflows (actionlint also on the well-formed eval fixtures) |
| `make fmt`                                      | `prettier --write` on all Markdown and JSON, so tables and JSON match what CI expects                                                                                                                                                                                                                                                                                   |
| `make eval-check [SKILL=… ITER=…]`              | Program-grade every run in the latest iteration with `evals/<skill>/checks.py`: writes each `grading.json` with the mechanical verdicts filled in and `passed: null` on the assertions left for the model grader. Runs the scanners itself. `FLAGS=--force` to overwrite an existing grading.json                                                                       |
| `make eval-batch [SKILL=… ITER=… BUDGET=60000]` | Group the runs that still have `passed: null` under an excerpt-byte budget and write one grader prompt per group to `grader-batches/batch-N.md`; spawn one grader subagent per file                                                                                                                                                                                     |
| `make eval-finalize [SKILL=… ITER=…]`           | After the model grader filled the nulls, recompute every `grading.json` summary; exits 1 if any assertion is still null                                                                                                                                                                                                                                                 |
| `make eval-benchmark [SKILL=… ITER=…]`          | Aggregate the latest `evals/<skill>/runs/iteration-N/` into `benchmark.json` + `benchmark.md` via the skill-creator plugin                                                                                                                                                                                                                                              |
| `make eval-view [SKILL=… ITER=…]`               | Open the skill-creator review viewer on that iteration                                                                                                                                                                                                                                                                                                                  |
| `make pin [FILES=…]`                            | Pin this repo's workflows with pinact: newest release at least 7 days old, SHA plus version comment                                                                                                                                                                                                                                                                     |
| `make run-stats [RUNS=3] [REPO=owner/repo]`     | Rank a repo's workflows and jobs by mean duration over the last few runs, flag inconsistent timing and recent failures                                                                                                                                                                                                                                                  |

`SKILL` defaults to `github-actions-workflow-pro`; `ITER` defaults to the highest iteration present.

### Skill evals

Eval _definitions_ (`evals/<name>/evals.json`, fixtures, `checks.py`, `coverage.md`) are committed and sit
outside `skills/<name>/` so an installer copies only the skill. Eval _run artifacts_
(`evals/<name>/runs/iteration-N/`) are gitignored. Grading is deterministic first: a program grades every
assertion it can decide and a model judges only the rest.

To learn how a run works end to end, what a program does and what a model does, and how with-skill and
without-skill runs differ, read [docs/eval-walkthrough.md](docs/eval-walkthrough.md). For the short list
of what made the skill and its evals cheaper, faster, and provable, with the numbers, read
[docs/lessons-learned.md](docs/lessons-learned.md).

### Skill eval results

I run each skill's evals on the models below so you know the skill still produces good output on
the model you use, even a cheap, less accurate one. I only record a result here after a full run of
every eval against the current assertion set (106 assertions as of 2026-09-09). Both columns are from
2026-09-09, graded deterministic-first (iterations 13 and 14). Haiku ran before eval 5 gained its
eleventh assertion, so its cells are out of 105. The effort row records the reasoning effort
the executor subagent ran at. Iterations 13 and 14 inherited the session's `effortLevel: high` from
`~/.claude/settings.json`; from now on every run uses an agent definition in `.claude/agents/` that pins
model and effort, so the cell names what actually ran. "Without skill" is the
same model, same prompts, same grader, with the skill not installed: it is the baseline the skill has to beat,
and an assertion that passes without the skill on every model is a rule the skill may not need (see
`evals/<name>/coverage.md`).

#### github-actions-workflow-pro

|                 | Haiku 4.5 | Sonnet 5 | Opus 4.8 | Opus 5 | GPT 5.6 Sol | GPT 5.6 Luna | Kimi K2.7 Code | Kimi K3 | Grok 4.6 | GLM 5.3 Flash | MiniMax M3 | Qwen 3.8 27B |
| --------------- | --------- | -------- | -------- | ------ | ----------- | ------------ | -------------- | ------- | -------- | ------------- | ---------- | ------------ |
| Executor effort | high      | high     | —        | —      | —           | —            | —              | —       | —        | —             | —          | —            |
| Without skill   | 49/105    | 63/106   | —        | —      | —           | —            | —              | —       | —        | —             | —          | —            |
| With skill      | 85/105    | 96/106   | —        | —      | —           | —            | —              | —       | —        | —             | —          | —            |

Evals 10 and 11 (parallel steps, slow-step audit; 19 assertions) were added on 2026-09-12 and ran on their own,
Sonnet 5 at high effort: 19/19 with the skill, 12/19 without. The cells above are still the 106-assertion set
and get their next refresh from a full 125-assertion run.

I build and test these skills on Fable 5 — that's my baseline, not one of the target models above.
For comparison, the same models with no skill at all scored 55/101 (Sonnet 5) and 36/101 (Haiku 4.5).

See [AGENTS.md](./AGENTS.md) for the full convention (also symlinked as `CLAUDE.md`), and [PLAN.md](./PLAN.md) for the roadmap.
