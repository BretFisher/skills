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

Run `make eval-test` to test the harness and Docker checker regressions without model calls.
It accepts Claude Code logs and OpenCode V2 session exports. Unsupported or
incomplete logs stop deterministic tool grading instead of producing a pass.

### Eval commands

The repo-owned runner uses OpenCode V2 by default. Set an exact model and variant;
use a new iteration ID for each experiment. These commands make model calls only
at `eval-run` and `eval-grade`:

```bash
make eval-plan SKILL=k8s-catch-up ITER=26-opencode MODEL='openai/gpt-6.1-sol#low' EVALS=1
make eval-run SKILL=k8s-catch-up ITER=26-opencode MODEL='openai/gpt-6.1-sol#low' EVALS=1
make eval-check SKILL=k8s-catch-up ITER=26-opencode
make eval-grade SKILL=k8s-catch-up ITER=26-opencode GRADER_MODEL='openai/gpt-6.1-sol#low'
make eval-finalize SKILL=k8s-catch-up ITER=26-opencode
make eval-benchmark SKILL=k8s-catch-up ITER=26-opencode
make eval-view SKILL=k8s-catch-up ITER=26-opencode OPEN=1
```

`EVALS` selects comma-separated IDs. `REPEAT` sets repeated pairs; `JOBS` limits
parallel executors. `RESUME=1` skips matching completed runs and retains failed
runs. For Claude Code, set `HARNESS=claude`, `MODEL` to a full Claude model ID,
and `EFFORT=high`. The Claude adapter has offline tests but no live validation yet.

The Kubernetes updater task needs existing local source checkouts under
`~/.cache/k8s-catch-up/{enhancements,website}`. Set `SOURCE_CACHE=<directory>` to
use another location. The runner verifies and copies source data, records hashes,
and directs the executor to use the copies offline. It does not clone, fetch, or
change the host checkouts. Its damaged skill copy is committed as a pristine input.

For a completed model session that failed only during evidence collection, use
`make eval-recover RUN=<run-directory>`. It validates the retained evidence and
workspace before collecting files; it makes no model call and preserves the failure
record. Other failed runs require a new iteration.

See [OpenCode eval support](docs/eval-opencode.md) for isolation, evidence, and
report validation. `eval-view` writes a static review page with nested files,
grades, and benchmark data. Set `PREVIOUS` to an earlier iteration directory to
include its outputs and feedback. For an old-skill comparison, use
`PRIMARY=new_skill BASELINE=old_skill` on the reporting commands.

The installed `.agents/skills/skill-creator/` stays read-only. Repo-owned adapters
in `evals/harness/` validate the data and call its unchanged viewer functions.

Each skill's evals run on a model twice: once with the skill installed and once without. Same prompts, same
grader. The score is the share of assertions passed.

### github-actions-workflow-pro

| Model                       | Without skill | With skill |
| --------------------------- | ------------- | ---------- |
| Haiku 4.5                   | 47%           | 81%        |
| Haiku 5.5                   | 60%           | 98%        |
| Sonnet 5                    | 59%           | 92%        |
| Sonnet 5.5                  | 64%           | 95%        |
| Opus 5.5                    | 62%           | 97%        |
| GPT-6.1 Sol (low, OpenCode) | 53%           | 86%        |

GPT-6.1 Sol: 77/145 assertions without the skill and 125/145 with it, a gain of
33.1 percentage points. OpenCode v2.0.26; one repeat per task across all 15 tasks
in iteration `27-opencode-sol-retry`. One baseline was retried after a provider
transport error; the other 29 executors were retained. This is a preliminary
result. Fixture mappings and grading defects were corrected, so this is not a
controlled comparison with earlier model rows. See
[GitHub Actions eval coverage](evals/github-actions-workflow-pro/coverage.md).

### k8s-catch-up

| Model                       | Without skill | With skill |
| --------------------------- | ------------- | ---------- |
| Haiku 4.5                   | 21%           | 100%       |
| Haiku 5.5                   | 80%           | 100%       |
| Sonnet 5                    | 74%           | 100%       |
| Sonnet 5.5                  | 89%           | 96%        |
| Opus 5.5                    | 91%           | 96%        |
| GPT-6.1 Sol (low, OpenCode) | 90%           | 98%        |

GPT-6.1 Sol: 57/63 assertions without the skill and 62/63 with it, a gain of
7.9 percentage points. OpenCode v2.0.26; one repeat per task across all 15 tasks
in iteration `28-opencode-sol`. The updater task received identical damaged skill
and local-source inputs in both configurations. Checker defects were corrected;
this preliminary result is not a controlled comparison with earlier model rows.
The remaining skill failure omitted the command to confirm the served group-snapshot
API version. See [Kubernetes eval coverage](evals/k8s-catch-up/coverage.md).

The newer the model, the more it already knows, so the gap shrinks. What a newer model still gets wrong
without `k8s-catch-up` is mostly the stage of a feature (beta or GA, and in which version) and recent
deprecations.

### docker-pro

| Model                       | Without skill | With skill |
| --------------------------- | ------------- | ---------- |
| Haiku 5.5                   | 68%           | 96%        |
| Sonnet 5.5                  | 56%           | 100%       |
| Opus 5.5                    | 72%           | 100%       |
| GPT-6.1 Sol (low, OpenCode) | 36%           | 100%       |

GPT-6.1 Sol: 9/25 assertions without the skill and 25/25 with it, a gain of
64 percentage points. OpenCode v2.0.26; one repeat per task across all three tasks
in iteration `5-opencode-fixes`. This is a preliminary result, not a stable quality
estimate. The skill and checkers changed from earlier runs, so these rows are not
a controlled model comparison. See [Docker eval coverage](evals/docker-pro/coverage.md).

### super-linting

| Model                       | Without skill | With skill |
| --------------------------- | ------------- | ---------- |
| Haiku 5.5                   | 41%           | 100%       |
| Sonnet 5.5                  | 35%           | 100%       |
| Opus 5.5                    | 35%           | 100%       |
| GPT-6.1 Sol (low, OpenCode) | 6%            | 94%        |

GPT-6.1 Sol: 1/17 assertions without the skill and 16/17 with it, a gain of
88.2 percentage points. OpenCode v2.0.26; one repeat per task across all three tasks
in iteration `5-opencode-sol`. The remaining skill failure was an omitted hook
question. The checker was corrected to follow a shell helper called by `make lint`.
This is a preliminary result. OpenCode does not automatically load fixture
`CLAUDE.md` instructions, which limits comparison with Claude Code runs. See
[Linting eval coverage](evals/super-linting/coverage.md).

### gha-audit

| Model                       | Without skill | With skill |
| --------------------------- | ------------- | ---------- |
| Haiku 5.5                   | 71%           | 100%       |
| Sonnet 5.5                  | 71%           | 100%       |
| Opus 5.5                    | 43%           | 100%       |
| GPT-6.1 Sol (low, OpenCode) | 71%           | 100%       |

GPT-6.1 Sol: 5/7 assertions without the skill and 7/7 with it, a gain of
28.6 percentage points. OpenCode v2.0.26; one repeat per task across both tasks
in iteration `5-opencode-sol`. With-skill runs include the wrapper's required
`github-actions-workflow-pro` dependency; the baseline receives neither skill.
This is a preliminary result. See [Audit eval coverage](evals/gha-audit/coverage.md).

`screencapture` has no evals yet.

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
| `make eval-key`                          | Compatibility target; eval commits are unsigned and need no key                       |
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
