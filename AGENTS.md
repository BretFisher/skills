# Agent guide for this repo

This repo holds reusable [Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills) for DevOps / platform work.
Read this before creating, editing, or evaluating a skill.

## Layout

```
skills/<skill-name>/          # SOURCE — committed
  SKILL.md                    #   the skill itself
  evals/evals.json            #   eval DEFINITIONS (prompts + assertions) — committed, this is the test contract
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

If you want to publish a quality scorecard, copy a single curated `benchmark.md` into the
skill folder and commit just that — do not commit the rest of `.evals/`.
