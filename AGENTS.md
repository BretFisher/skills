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

- **Eval definitions** — the prompts and assertions that _define_ each test.
  These live next to the skill at `skills/<skill-name>/evals/evals.json` and **are committed**.
  They are the contract for the skill: a reviewer reads them to know what behavior must hold,
  and they let anyone re-run the evals later to catch regressions.

- **Eval run artifacts** — the _output_ of executing those evals (transcripts, gradings,
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

Eval-harness notes, learned the hard way: graders never embed a `timing` object in `grading.json` (it breaks `aggregate_benchmark`; timing belongs in the sibling `timing.json`) and never use `set -x` near a token-bearing command; executors commit the pristine input files as the work repo's first commit before editing, so `git show HEAD:` still holds the original for the grader.

If you want to publish a quality scorecard, copy a single curated `benchmark.md` into the
skill folder and commit just that — do not commit the rest of `.evals/`.

## Before committing

Run `make lint` (and `make fmt` first if prettier complains). It runs `markdownlint`, `prettier --check`, and `yamllint` (configs in `.github/linters/`, the same files super-linter reads in CI), `shellcheck` on every
`skills/*/scripts/*.sh`, `py_compile` on `skills/*/scripts/*.py`, and `actionlint` + `zizmor` + `poutine` + `pinact -check` on this repo's workflows (actionlint also on the well-formed eval fixtures).
Tools are never installed by the Makefile; a missing one prints its `brew install` formula.

## Writing skills

When advice on skill structure conflicts, prefer Matt Pocock's `writing-for-agents` rules, then
Anthropic's skill-creator and docs, then other sources. The rules below are the ones we have settled on.

- **Pushy description, third person.** The description does two jobs: say what the skill does, then
  list the situations that should activate it, one "when" per branch on specific topics (create a
  workflow, edit a job, harden, speed up, publish an image, findings from a named scanner), and end
  the list with "even if they don't say 'X'" so the model triggers on the task, not the keyword. Add a
  non-trigger only when another skill genuinely competes for the same prompts; otherwise it is a sentence
  the model reads on every turn for nothing. Write it in third person; the body carries identity, the
  description carries the trigger.
- **Positive rules with a why.** Say what to do, not what to avoid: `pull_request` for PR triggers, rather
  than "never use pull_request_target". No caps-lock MUST/NEVER; a prohibition drags the banned behaviour
  into context, and a shouted rule reads as louder, not clearer. Every rule ends with the reason it exists,
  so the model can tell when the rule applies and when the situation is different.
- **Inline what every branch needs; disclose the rest.** SKILL.md stays under about 100 lines of body;
  once a section is read by only some tasks, move it to `references/<topic>.md` with a "read when" clause
  at the sentence where that branch is decided (the specs allow up to 500 lines; we split far earlier
  because every inline line is paid for on every call). Co-locate a gotcha with its rule instead of a
  separate Gotchas section, and end steps in a checkable done-when list.
- **Link the skill's own files; backtick everything else.** Pointers to files the skill ships are markdown
  links with the filename as the text: `read [audit.md](references/audit.md) and follow it`,
  `→ [security.md](references/security.md)`. Backticks are for paths in the user's repo
  (`.github/dependabot.yml`), for scripts the skill runs rather than reads (`scripts/run-stats.py`), and for
  rule-id citations a report prints (`security.md: pinned`). No `@file` imports in a skill: that is a
  CLAUDE.md feature and would inline the file, defeating progressive disclosure.
- **Prefer tools over prompts.** When a deterministic linter or scanner already checks a rule (actionlint,
  zizmor, poutine, pinact, gasa), the skill runs the tool and cites its rule id instead of restating the
  rule; a tool call is cheaper and more predictable than a paragraph the model has to apply by reading.
  The skill's own text covers only the residual list the tools cannot see, and says which tool owns each
  rule it does mention.
- **Eval-driven development.** Start on the strongest model. Run the skill on real tasks and read the
  transcripts, then for each failure or judgment you want to lock in: write the eval assertion that fails,
  write the rule in the skill, run until the assertion passes. Repeat until every rule you want has an
  assertion and the output is what you would ship. Then run the same evals on a cheaper model and refactor
  the rules that fail there. Once the evals are green on every model you need, look for assertions that
  pass on every model _without_ the skill: those rules are candidates to delete, so remove them and re-run
  everything to confirm they were not carrying weight. `evals/coverage.md` in each skill maps every rule
  line to the assertion that proves it or names the gap; a rule with no row is untested. Eval definitions
  are the regression contract; the design tool is the transcript.
