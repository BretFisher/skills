# Agent guide for this repo

This repo holds reusable [Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills) for DevOps / platform work.
Read this before creating, editing, or evaluating a skill.

## Layout

```text
skills/<skill-name>/          # SOURCE — committed
  SKILL.md                    #   the skill itself: description, working style, checklist, validate, done-when
  references/*.md             #   detail read only when a branch needs it (rules + why, procedures)
  scripts/*                   #   deterministic helpers the skill runs (linted, --help, structured output)
  evals/evals.json            #   eval DEFINITIONS (prompts + assertions) — committed, this is the test contract
  evals/fixtures/             #   input files some evals hand to the agent
.evals/<skill-name>/          # RUN ARTIFACTS — gitignored, never committed
  iteration-N/                #   one dir per eval run: transcripts, grading.json, timing.json, benchmark.*
```

## Where skill evals go — important

There are two different things, and they live in two different places:

- **Eval definitions** — the prompts and assertions that *define* each test.
  These live next to the skill at `skills/<skill-name>/evals/evals.json` and **are committed**.
  They are the contract for the skill: a reviewer reads them to know what behavior must hold,
  and they let anyone re-run the evals later to catch regressions.

- **Eval run artifacts** — the *output* of executing those evals (transcripts, gradings,
  timings, `benchmark.json`/`benchmark.md`, viewer logs).
  These go in **`.evals/<skill-name>/iteration-N/`** at the repo root, which is **gitignored**.
  They are regenerated on every run and are machine-specific, so they are not source of truth.

When running the skill-creator eval loop, point the workspace at `.evals/<skill-name>/`
instead of the tool's default `<skill-name>-workspace/` sibling. Every skill-creator script
(`generate_review.py`, `aggregate_benchmark`) takes the workspace path as an explicit argument,
so this is just a matter of passing the right path — e.g.:

```bash
python -m scripts.aggregate_benchmark .evals/<skill-name>/iteration-N --skill-name <skill-name>
```

`make eval-benchmark SKILL=<skill-name>` and `make eval-view SKILL=<skill-name>` wrap those two
scripts with the right paths (see the Makefile; `ITER` defaults to the highest iteration present).

If you want to publish a quality scorecard, copy a single curated `benchmark.md` into the
skill folder and commit just that — do not commit the rest of `.evals/`.

## Before committing

Run `make lint`. It runs `markdownlint` and `yamllint` (configs in `.github/linters/`, the same files super-linter reads in CI), `shellcheck` on every
`skills/*/scripts/*.sh`, `py_compile` on `skills/*/scripts/*.py`, and `actionlint` + `zizmor` + `poutine` + `pinact -check` on this repo's workflows (actionlint also on the well-formed eval fixtures).
Tools are never installed by the Makefile; a missing one prints its `brew install` formula.

## Writing skills

When advice on skill structure conflicts, prefer Matt Pocock's `writing-for-agents` rules, then
Anthropic's skill-creator and docs, then other sources. In practice: the description is the trigger
(one clause per branch, plus a non-trigger), inline only what every branch needs and push the rest
to `references/` with a "read when" clause at the point of use, phrase rules positively with the
reason attached, co-locate a gotcha with its rule instead of a separate Gotchas section, and end
steps in a checkable done-when list. Run the skill on real tasks and read the transcripts before
touching evals; evals are the regression contract, not the design tool.
