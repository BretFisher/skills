# Evals

This folder holds the evals for each skill and the harness that runs them.
An eval runs one prompt with the skill and without it, on the same model, and then grades both results.
The difference in score is the measured benefit, which the [main README](../README.md#does-the-skill-help) shows for each skill.

## Read first

| Guide                                              | What it tells you                                                                               |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| [eval-design.md](../docs/eval-design.md)           | Why the evals work this way: goals, history, decisions, the layout of a run, and the known gaps |
| [eval-walkthrough.md](../docs/eval-walkthrough.md) | One eval from the prompt to a score, step by step                                               |
| [eval-opencode.md](../docs/eval-opencode.md)       | The CLI runner, its harness adapters, and its `make` commands                                   |
| [lessons-learned.md](../docs/lessons-learned.md)   | What made the skills and the evals cheaper, faster, and easier to prove                         |
| [Terms](../docs/README.md#terms)                   | The meaning of eval, run, iteration, executor, grader, and kind                                 |

## What is in this folder

| Path                  | What it holds                                                                    | In git |
| --------------------- | -------------------------------------------------------------------------------- | ------ |
| `<skill>/evals.json`  | The prompts and assertions: the test contract for the skill                      | yes    |
| `<skill>/fixtures/`   | Input files that the evals give to the executor                                  | yes    |
| `<skill>/checks.py`   | The program grader: it decides each assertion that a program can decide          | yes    |
| `<skill>/coverage.md` | Which assertion proves each rule of the skill, and the notes for each iteration  | yes    |
| `<skill>/runs/`       | The results of each run: outputs, logs, grades, timing, benchmarks               | no     |
| `harness/`            | The runner, evidence reader, grading, reporting, and pull code, with their tests | yes    |
| `eval.gitconfig`      | The eval identity for fixture commits: unsigned, with no hooks                   | yes    |
| `_dashboard/`         | Local report scripts and their output                                            | no     |

The full layout of a run is in [eval-design.md](../docs/eval-design.md#current-layout).

## Skills with evals

| Skill                         | Coverage and results                                                               |
| ----------------------------- | ---------------------------------------------------------------------------------- |
| `docker-pro`                  | [coverage.md](docker-pro/coverage.md)                                              |
| `gha-audit`                   | [coverage.md](gha-audit/coverage.md)                                               |
| `github-actions-workflow-pro` | [coverage.md](github-actions-workflow-pro/coverage.md)                             |
| `k8s-catch-up`                | [coverage.md](k8s-catch-up/coverage.md), [benchmark.md](k8s-catch-up/benchmark.md) |
| `k8s-podspec-pro`             | [coverage.md](k8s-podspec-pro/coverage.md)                                         |
| `super-linting`               | [coverage.md](super-linting/coverage.md)                                           |

## Commands

Run `make help` from the repo root for every `eval-*` target.
The order of the commands for one iteration is in [eval-design.md](../docs/eval-design.md#one-iteration-from-start-to-end).
`make eval-test` runs the harness tests with no model calls.
