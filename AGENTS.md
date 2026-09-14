# Agent guide for this repo

This repo holds reusable [Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills) for DevOps / platform work.
Read this before creating, editing, or evaluating a skill.

## Layout

```text
skills/<skill-name>/          # SOURCE — committed; this directory is all an installer copies
  SKILL.md                    #   the skill itself: description, working style, checklist, validate, done-when
  references/*.md             #   detail read only when a branch needs it (rules + why, procedures)
  scripts/*                   #   deterministic helpers the skill runs (linted, --help, structured output)
evals/<skill-name>/           # EVAL DEFINITIONS — committed; outside the skill so installers never ship them
  evals.json                  #   prompts + assertions — the test contract
  fixtures/                   #   input files some evals hand to the agent
  checks.py                   #   program grader: decides every assertion it can, leaves passed: null for the model
  coverage.md                 #   maps every rule line to the assertion that proves it, or names the gap; records each assertion's kind
  runs/iteration-N/           #   RUN ARTIFACTS — gitignored: transcripts, grading.json, timing.json, benchmark.*
evals/_dashboard/             # gitignored: build-dashboard.py and the dashboard.html it builds from every run
docs/                         # human-facing guides: eval-walkthrough.md (how a run works), lessons-learned.md (what improved the skill and evals)
```

## Where skill evals go — important

Eval files live outside the skill directory. Installers (`git clone`, `npx skills add`, a plugin
marketplace) copy the whole `skills/<skill-name>/` directory, so a user who installs a skill pulls in
every file under it. The Agent Skills spec names no location for evals, and the skill-creator scripts
take the skill path and the workspace path as explicit arguments, so nothing needs them inside the skill.

There are two different things, and they live in two different places:

- **Eval definitions** — the prompts and assertions that _define_ each test.
  These live at `evals/<skill-name>/evals.json` with their input files in `evals/<skill-name>/fixtures/`
  and **are committed**. They are the contract for the skill: a reviewer reads them to know what behavior
  must hold, and they let anyone re-run the evals later to catch regressions. Every `files` entry in
  `evals.json` is a path from the repo root (`evals/<skill-name>/fixtures/<file>`), not from the skill.

- **Eval run artifacts** — the _output_ of executing those evals (transcripts, gradings,
  timings, `benchmark.json`/`benchmark.md`, viewer logs, canary audits of real repos).
  These go in **`evals/<skill-name>/runs/iteration-N/`**, which is **gitignored**.
  They are regenerated on every run and are machine-specific, so they are not source of truth.

When running the skill-creator eval loop, point the workspace at `evals/<skill-name>/runs/`
instead of the tool's default `<skill-name>-workspace/` sibling, and tell it where `evals.json` is:
its own SKILL.md assumes `evals/evals.json` inside the skill. Every skill-creator script
(`generate_review.py`, `aggregate_benchmark`) takes the workspace path as an explicit argument,
so this is just a matter of passing the right path — e.g.:

```bash
python -m scripts.aggregate_benchmark evals/<skill-name>/runs/iteration-N --skill-name <skill-name>
```

`make eval-benchmark SKILL=<skill-name>` and `make eval-view SKILL=<skill-name>` wrap those two
scripts with the right paths (see the Makefile; `ITER` defaults to the highest iteration present).

Sonnet is the first-run model while a rule or an eval is being built: `eval-executor-sonnet-high` and `eval-grader-sonnet-high`. It costs a fraction of Opus per run and returns sooner, and the first runs of a new rule mostly find bugs in the fixture, the assertion, or `checks.py` rather than anything about the model, so paying Opus prices to discover a bad regex is waste. Move to Opus once the eval is stable and the question is how the strongest model behaves; drop to Haiku for the cheaper-model pass.

Executors and graders are spawned through the agent definitions in `.claude/agents/` (`eval-executor-<model>-<effort>`, `eval-grader-<model>-<effort>`), never through the bare Agent tool with a `model` argument: the Agent tool has no effort parameter, a subagent otherwise inherits the session's `effortLevel`, and a results cell without a known effort cannot be compared with the next one. Add a definition for a new model or effort before running it; the README effort row records the value.

Eval-harness notes, learned the hard way: graders never embed a `timing` object in `grading.json` (it breaks `aggregate_benchmark`; timing belongs in the sibling `timing.json`) and never use `set -x` near a token-bearing command; executors commit the pristine input files as the work repo's first commit before editing, so `git show HEAD:` still holds the original for the grader. When a rate limit kills graders mid-run, validate every surviving `grading.json` (expectation count, field names, no `timing`) and relaunch only the missing runs; do not regrade the survivors.

If you want to publish a quality scorecard, copy a single curated `benchmark.md` into
`evals/<skill-name>/` and commit just that — do not commit anything under `runs/`.

## Before committing

Run `make lint` (and `make fmt` first if prettier complains).
Tools are never installed by the Makefile; a missing one prints its `brew install` formula.

## Writing skills

When advice on skill structure conflicts, prefer Matt Pocock's `writing-for-agents` rules, then
Anthropic's skill-creator and docs, then other sources. The rules below are the ones we have settled on.

- **Pushy description, third person.** The description says what the skill does, then lists the
  situations that should activate it, one per branch, ending with "even if they don't say 'X'"; add a
  non-trigger only when another skill competes for the same prompts. Models under-trigger on keywords
  and trigger on tasks, and every extra sentence is read on every turn.
- **Positive rules with a why.** Say what to do, not what to avoid, and end every rule with its reason.
  A prohibition drags the banned behaviour into context, and the reason tells the model when the rule
  applies and when the situation is different.
- **Inline what every branch needs; disclose the rest.** SKILL.md stays under about 100 lines of body;
  a section only some tasks read moves to `references/<topic>.md`, pointed to from the sentence where
  that branch is decided. Every inline line is paid for on every call.
- **Link the skill's own files; backtick everything else.** Files the skill ships are markdown links;
  paths in the user's repo, scripts the skill runs, and rule-id citations are backticks; no `@file`
  imports. A link shows the model what it may open, and an import would inline the file and defeat
  progressive disclosure.
- **A skill names only its own files and other skills.** Never point at a path in this repo
  (`PLAN.md`, `docs/`, `evals/`), and never mention this repo's plans or backlog. An installer copies
  `skills/<skill-name>/` and nothing else, so any such path is missing on the user's machine, and our
  roadmap is not their context. A path in the _user's_ repo is fine: that is what the skill acts on.
- **Prefer tools over prompts.** When a deterministic tool already checks a rule, the skill runs the
  tool and cites its rule id instead of restating the rule. A tool call is cheaper and more predictable
  than a paragraph the model applies by reading.
- **Deterministic checks before model judgment.** Every eval assertion a regex, a CLI tool, or a program
  can decide is graded by `evals/<skill-name>/checks.py`, which writes `grading.json` with `passed: null`
  and the needed excerpts on the rest; a model grades only those, from the excerpts. The goal is the
  lowest token and time total per run, and a program's verdict never flips between runs. Write each
  assertion as the literal a program tests, split one that mixes a check with a judgment, and record the
  kind (`program`, `split`, `model`) in `coverage.md`; the walkthrough is
  [docs/eval-walkthrough.md](docs/eval-walkthrough.md).
- **Eval-driven development.** Start on the strongest model: for each failure, write the assertion that
  fails, then the rule, until green; then run on a cheaper model and refactor the rules that fail there.
  Assertions that pass without the skill on every model mark rules to delete; record them in
  `coverage.md`. Eval definitions are the regression contract; the transcript is the design tool.
