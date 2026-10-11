# Bret's DevOps and \*Ops Skills

A bunch of skills for daily work in DevOps, found in `./skills/`

## Install

Two ways, pick one.

**As a Claude Code plugin** (all skills at once, updated with `/plugin`):

```text
/plugin marketplace add bretfisher/skills
/plugin install bretfisher-skills@bretfisher
```

**As individual skills** (pick only the ones you want):

```bash
npx skills add bretfisher/skills
```

Mark the ones you want to install. Add `-g` to the command to install them globally.

## Skills

| Name                          | Purpose                                                                                                                                       |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `docker-pro`                  | Light up all the best Docker features and security best practices for dockerizing a repo. From a Docker Captain.                              |
| `github-actions-workflow-pro` | Create, edit, audit, and speed up GitHub Actions workflows with opinionated security and speed defaults.                                      |
| `gha-audit`                   | Type `/gha-audit [file]` to run the audit path of `github-actions-workflow-pro` on demand: scanners first, then a report and a proposed diff. |
| `k8s-catch-up`                | Teaches the agent the Kubernetes features that reached beta or GA after its training data ended (currently v1.35 to v1.37).                   |
| `screencapture`               | Captures the macOS screen, a window, or a region so the agent can see native GUI apps. Web pages go to a browser automation tool.             |
| `super-linting`               | Picks the right linter for every file type in a project and wires them into a `make lint` target, so code is linted before every commit.      |

## Does the skill help?

Each skill's evals run on a model twice: once with the skill installed and once without. Same prompts, same
grader. The score is the share of assertions passed.

### github-actions-workflow-pro

| Model     | Without skill | With skill |
| --------- | ------------- | ---------- |
| Haiku 4.5 | 47%           | 81%        |
| Haiku 5.5 | 57%           | 96%        |
| Sonnet 5  | 59%           | 92%        |

### k8s-catch-up

| Model      | Without skill | With skill |
| ---------- | ------------- | ---------- |
| Haiku 4.5  | 21%           | 100%       |
| Haiku 5.5  | 79%           | 100%       |
| Sonnet 5   | 74%           | 100%       |
| Sonnet 5.5 | 90%           | 97%        |

The newer the model, the more it already knows, so the gap shrinks. What a newer model still gets wrong
without `k8s-catch-up` is mostly the stage of a feature (beta or GA, and in which version) and recent
deprecations.

## Repo layout

| Path                             | What                                                                         | Committed?    |
| -------------------------------- | ---------------------------------------------------------------------------- | ------------- |
| `skills/<name>/`                 | The skill: `SKILL.md`, plus `references/` and `scripts/` where it needs them | ✅ yes        |
| `evals/<name>/`                  | Eval prompts and assertions, fixtures, the program grader, coverage notes    | ✅ yes        |
| `evals/<name>/runs/iteration-N/` | Eval run output (transcripts, gradings, timings)                             | ❌ gitignored |

Evals sit outside `skills/` so an installer copies only the skill. How a run works:
[docs/eval-walkthrough.md](docs/eval-walkthrough.md). What made the skills and evals better:
[docs/lessons-learned.md](docs/lessons-learned.md). Per-assertion results: `evals/<name>/coverage.md`.

## Makefile

`make help` lists everything. Tools are checked, never installed; a missing one prints its `brew install` formula.

| Target                                   | What it does                                                                          |
| ---------------------------------------- | ------------------------------------------------------------------------------------- |
| `make lint`                              | Pre-commit gate: the same linters CI runs, plus the scanners on this repo's workflows |
| `make fmt`                               | `prettier --write` on Markdown and JSON                                               |
| `make eval-check [SKILL=… ITER=…]`       | Program-grade every run of an iteration; leaves judgment assertions for the model     |
| `make eval-batch [SKILL=… ITER=…]`       | Write one grader prompt per group of runs that still need a model grader              |
| `make eval-finalize [SKILL=… ITER=…]`    | Recompute every grading summary; fails if an assertion is still ungraded              |
| `make eval-benchmark [SKILL=… ITER=…]`   | Aggregate an iteration into `benchmark.json` and `benchmark.md`                       |
| `make eval-view [SKILL=… ITER=…]`        | Open the skill-creator review viewer on an iteration                                  |
| `make k8s-features [SINCE=… RELEASES=…]` | Print the Kubernetes features that reached beta or GA in a window                     |
| `make k8s-verify [STRICT=1]`             | Check every k8s-catch-up feature file against its upstream sources                    |
| `make k8s-check`                         | Exit 1 when a Kubernetes release newer than the skill exists                          |
| `make pin [FILES=…]`                     | Pin this repo's workflows with pinact                                                 |
| `make run-stats [RUNS=3] [REPO=…]`       | Rank a repo's workflows and jobs by duration over recent runs                         |

`SKILL` defaults to `github-actions-workflow-pro`; `ITER` defaults to the highest iteration present.

See [AGENTS.md](./AGENTS.md) for the repo conventions (also symlinked as `CLAUDE.md`). Open work is tracked in
[GitHub Issues](https://github.com/BretFisher/skills/issues), one label per skill.
