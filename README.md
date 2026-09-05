# Bret's DevOps and \*Ops Skills

A bunch of skills for daily work in DevOps, found in `./skills/`

Installable via `npx skills add https://github.com/bretfisher/skills` and mark the ones you want to install. Add `-g` to command to install them globally.

## Skills

| Name                          | Purpose                                                                                                                                                                                                                                                                              |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `docker-pro`                  | Light up all the best docker features and security best practices for dockerizing a repo. From a Docker Captain.                                                                                                                                                                     |
| `github-actions-workflow-pro` | Create, edit, audit, and speed up GitHub Actions workflows with opinionated security and speed defaults. Fires on its own whenever a `.github/workflows/*` file is in play. Ships `references/` (security, speed, audit) and `scripts/run-stats.py`; pinning is delegated to pinact. |
| `gha-audit`                   | Type `/gha-audit [file]` to run the audit path of `github-actions-workflow-pro` on demand: tools first (`actionlint`, `zizmor`, `poutine`, `pinact`, `gasa`), then a report split into correctness, hard findings, speed, and opinions, plus a proposed diff. User-invoked only.     |
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

| Target                                      | What it does                                                                                                                                                                                                                                                                                                                                                            |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `make lint`                                 | Pre-commit gate: `markdownlint`, `prettier --check`, and `yamllint` (configs in `.github/linters/`, the same rules super-linter applies in CI), `shellcheck` on `skills/*/scripts/*.sh`, `py_compile` on `skills/*/scripts/*.py`, and `actionlint` + `zizmor` + `poutine` + `pinact -check` on this repo's workflows (actionlint also on the well-formed eval fixtures) |
| `make fmt`                                  | `prettier --write` on all Markdown and JSON, so tables and JSON match what CI expects                                                                                                                                                                                                                                                                                   |
| `make eval-benchmark [SKILL=… ITER=…]`      | Aggregate the latest `evals/<skill>/runs/iteration-N/` into `benchmark.json` + `benchmark.md` via the skill-creator plugin                                                                                                                                                                                                                                              |
| `make eval-view [SKILL=… ITER=…]`           | Open the skill-creator review viewer on that iteration                                                                                                                                                                                                                                                                                                                  |
| `make pin [FILES=…]`                        | Pin this repo's workflows with pinact: newest release at least 7 days old, SHA plus version comment                                                                                                                                                                                                                                                                     |
| `make run-stats [RUNS=3] [REPO=owner/repo]` | Rank a repo's workflows and jobs by mean duration over the last few runs, flag inconsistent timing and recent failures                                                                                                                                                                                                                                                  |

`SKILL` defaults to `github-actions-workflow-pro`; `ITER` defaults to the highest iteration present.

### Skill evals

Eval _definitions_ live at `evals/<name>/evals.json` with input files in `evals/<name>/fixtures/`, and
are committed. They document what each skill is supposed to do and let anyone re-run the evals to catch
regressions. They sit outside `skills/<name>/` on purpose: installers copy the whole skill directory, so
a user who installs a skill gets only the files the skill needs at runtime. The Agent Skills spec names
no location for evals, so this costs nothing in compatibility.

Eval _run artifacts_ (the output of executing those evals) are written to `evals/<name>/runs/iteration-N/`,
which is gitignored. They're regenerated on every run and machine-specific, so they
aren't source of truth. When running the skill-creator eval loop, point its workspace at
`evals/<name>/runs/` rather than the default `<name>-workspace/` sibling.

### Skill eval results

I run each skill's evals on the models below so you know the skill still produces good output on
the model you use, even a cheap, less accurate one. I only record a result here after a full run of
every eval against the current assertion set (101 assertions as of 2026-08-31).

#### github-actions-workflow-pro

|        | Haiku 4.5 | Sonnet 5 | Opus 4.8 | Opus 5 | GPT 5.6 Sol | GPT 5.6 Luna | Kimi K2.7 Code | Kimi K3 | Grok 4.6 | GLM 5.3 Flash | MiniMax M3 | Qwen 3.8 27B |
| ------ | --------- | -------- | -------- | ------ | ----------- | ------------ | -------------- | ------- | -------- | ------------- | ---------- | ------------ |
| Result | 83/101    | 97/101   | —        | —      | —           | —            | —              | —       | —        | —             | —          | —            |

I build and test these skills on Fable 5 — that's my baseline, not one of the target models above.
For comparison, the same models with no skill at all scored 55/101 (Sonnet 5) and 36/101 (Haiku 4.5).

See [AGENTS.md](./AGENTS.md) for the full convention (also symlinked as `CLAUDE.md`), and [PLAN.md](./PLAN.md) for the roadmap.
