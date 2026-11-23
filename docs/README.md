# Docs

These guides are for people who maintain this repo or study how it tests its skills.
To install and use the skills, read the [main README](../README.md).
Agents that edit this repo follow [AGENTS.md](../AGENTS.md).

## Evals

Each skill has evals that measure how much the skill helps: the same prompt runs with the skill and without it, and a grader checks the result.
Read these guides in this order:

| Guide                                      | What it tells you                                                                                    | Read it when                                        |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| [eval-design.md](eval-design.md)           | Goals, history, design decisions with their reasons, the file layout of a run, and the known gaps    | You want to know why the evals work the way they do |
| [eval-walkthrough.md](eval-walkthrough.md) | One eval from the prompt to a score: which steps a program does and which steps a model does         | You run or grade evals for the first time           |
| [eval-opencode.md](eval-opencode.md)       | The repo-owned CLI runner: commands, the OpenCode and Claude Code adapters, isolation, and reporting | You run `make eval-run` or compare harnesses        |
| [lessons-learned.md](lessons-learned.md)   | What made the skills and the evals cheaper, faster, and easier to prove, with the measurements       | You write a new skill or a new eval                 |

The eval definitions and the harness code are in [`evals/`](../evals/).

## Repo checks

| Guide                                | What it tells you                                                                                  | Read it when                                          |
| ------------------------------------ | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| [lint.md](lint.md)                   | The 12 lint checks that `make lint` and Dagger Cloud Checks run, and how to add or change a linter | Lint fails, or you add a linter                       |
| [install-tests.md](install-tests.md) | How `make test-install` installs the skills into each agent harness in containers                  | You change the repo layout, a plugin, or a skill name |

## Terms

The eval guides use these words with these meanings.

| Term           | Meaning                                                                                                 |
| -------------- | ------------------------------------------------------------------------------------------------------- |
| Eval           | One prompt, its fixture files, and its assertions                                                       |
| Assertion      | One pass/fail statement about the result. Scores count assertions                                       |
| Fixture        | An input file that an eval gives to the executor, for example an insecure workflow                      |
| Configuration  | `with_skill` or `without_skill`. `old_skill` and `new_skill` compare two versions of a skill            |
| Run            | One execution of one eval in one configuration, plus its grading                                        |
| Iteration      | A set of runs made together, usually one model on one harness after one change                          |
| Executor       | The agent that does the task: a Claude Code subagent, or a harness CLI that the runner starts           |
| Grader         | First `checks.py`, which decides each assertion that a program can decide; then a model, for the rest   |
| Kind           | Who can decide an assertion: `program`, `split` (a program half and a model half), or `model`           |
| Discriminating | An assertion that fails without the skill and passes with it. These assertions show what the skill adds |
| Mech           | Short name in `coverage.md` for the scanner assertion that every `github-actions-workflow-pro` eval has |
