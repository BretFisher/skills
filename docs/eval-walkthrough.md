# How a skill eval runs in this repo

A walkthrough for people new to skill evals. It follows one eval from the prompt in `evals.json` to a
cell in the README results table, and shows which steps a program does and which steps a model does.
The examples come from `github-actions-workflow-pro`, the skill with the most eval history here.

## What an eval is

An eval is one realistic task a user would give the skill, plus a list of assertions that must hold in
the result. A run is one execution of that task by a model, followed by grading. A skill's evals are
its regression contract: a reviewer reads them to know what behavior must hold, and anyone can re-run
them later to see whether a change to the skill broke something.

Two things have different homes, and the split matters:

| Thing                | Where                             | Committed | Why                                                                                                                              |
| -------------------- | --------------------------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Eval **definitions** | `evals/<skill>/evals.json`        | yes       | The contract. Outside `skills/<skill>/` because installers copy the whole skill directory and users need none of this at runtime |
| Fixture inputs       | `evals/<skill>/fixtures/`         | yes       | Input files an eval hands to the agent (an insecure workflow, a slow one, a small Node repo)                                     |
| Program checks       | `evals/<skill>/checks.py`         | yes       | Grades every assertion a program can decide                                                                                      |
| Coverage map         | `evals/<skill>/coverage.md`       | yes       | Maps each rule in the skill to the assertion that proves it, and records each assertion's kind                                   |
| Run **artifacts**    | `evals/<skill>/runs/iteration-N/` | no        | Transcripts, outputs, gradings, timings. Regenerated on every run and machine-specific, so not source of truth                   |
| Dashboards           | `evals/_dashboard/`               | no        | Built from every run on disk                                                                                                     |

The Agent Skills spec names no location for evals, so keeping them outside the skill costs nothing in
compatibility. The skill-creator scripts take the skill path and the workspace path as explicit
arguments, so nothing needs them inside the skill either.

## The pieces

There is no runner program. The harness is a Claude Code session following the skill-creator's
`SKILL.md`, spawning subagents and writing files. The only programs in the loop are the ones in the
last row group of the table.

| Piece                                               | What it is                                                                                           | Who writes it                    |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------------- |
| `evals.json`                                        | Ten prompts, their fixture files, their assertions                                                   | You and the session, committed   |
| `runs/iteration-N/eval-N-<name>/`                   | One directory per eval per iteration: `prompt.md`, `expectations.json`, `eval_metadata.json`         | The orchestrating session        |
| `.../with_skill/run-1/`, `.../without_skill/run-1/` | One directory per configuration: `work/`, `outputs/`, `transcript.md`, `timing.json`, `grading.json` | Executor, then grader            |
| `grader.md`                                         | The grading instructions, shipped inside the skill-creator                                           | Anthropic                        |
| `checks.py`                                         | The program grader                                                                                   | Committed with the skill's evals |
| `aggregate_benchmark.py`, `generate_review.py`      | Roll gradings up into `benchmark.json`, open the viewer                                              | skill-creator                    |
| `build-dashboard.py`, `build-grader-compare.py`     | Build the repo dashboards from every run                                                             | `evals/_dashboard/`, gitignored  |

## One eval run, step by step

**1. Set up the work repo.** The session creates `work/`, runs `git init`, copies the fixture files to
the paths the prompt names, and commits them as the first commit. `eval_metadata.json` records the
mapping, for example `fixtures/insecure-ci.yml` placed at `.github/workflows/ci.yml`. The grader later
uses `git show HEAD:<path>` to see the original and `git status` to see whether the executor edited the
repo.

**2. Spawn the executor.** The session spawns one subagent per configuration, in the same turn, using
the agent definitions in `.claude/agents/` (`eval-executor-<model>-<effort>`). The Agent tool can pick a
model but has no effort parameter; a subagent otherwise inherits the session's `effortLevel` from
`~/.claude/settings.json`, and effort changes output quality enough that a results cell is meaningless
without it. The definition pins both, and the README effort row records the value. Claude Code reads
`.claude/agents/` when a session starts, so a definition added mid-session is available from the next
session. Each executor gets a prompt of this shape:

```text
Execute this task:
- Skill path: skills/github-actions-workflow-pro      <- absent in the without-skill run
- Task: <the eval prompt, verbatim>
- Input files: work/.github/workflows/ci.yml
- Save outputs to: <run-dir>/outputs/
- Also write transcript.md: files read in order, every shell command with cwd, exit, one-line result
```

The executor is a normal Claude subagent with all tools. It reads the skill if given one, works in
`work/`, writes its answer and any files to `outputs/`, and writes `transcript.md` itself. That
transcript is self-reported. The raw log copied in step 3 is not, and it is what the SHA-provenance
assertion is graded from: a SHA a tool produced shows up in a tool result before the model ever puts it
in a tool input, while a SHA typed from memory shows up in an input first, and a lookup against
`git/refs`, `/commits/`, or `/releases` is a command in the log. That makes provenance a program
verdict; without a raw log the assertion falls back to the split kind.

**3. Capture cost and the raw log.** When the subagent finishes, its task notification carries
`total_tokens` and `duration_ms`. The session writes them to `timing.json` at once, because they exist
nowhere else. Grader cost goes in the same file under `grader_tokens` and `grader_duration_seconds`.
The session also copies the subagent's own log into the run directory as `raw-transcript.jsonl`; Claude
Code keeps it under `~/.claude/projects/<project>/<session>/subagents/agent-<id>.jsonl`. It holds every
tool call with its input and result, the visible text, and per-turn token usage. It does not hold the
model's reasoning: thinking blocks arrive with an empty body and a signature. `evals/_dashboard/raw-log-stats.py`
turns these logs into a per-run table of turns, tool calls, and where the characters came from (skill
files, work files, command output), which is the evidence to use when trimming a skill.

**4. Grade, program first.** `make eval-check` runs `checks.py --write --scanners` on every run
directory. It parses the YAML with `yq`, runs actionlint, zizmor, poutine, and pinact in a scratch
repo, compares pinned lines with the fixture byte for byte, greps the report for the headings the
audit template names, and greps the transcript for SHA-returning lookups. It writes `grading.json`
in `evals.json` order, with `passed: null` on every assertion it cannot decide:

```json
{ "text": "The workflow defines concurrency with cancel-in-progress ...",
  "passed": true,  "graded_by": "program",
  "evidence": "program (program): concurrency.cancel-in-progress" },
{ "text": "The hand-back explains, in one line each, the reason for every ...",
  "passed": null,  "graded_by": "model",
  "evidence": "model: judgment only" }
```

**5. Grade, model second.** Each null entry carries a `context` array: the excerpts the assertion
needs, cut from the answer by heading, from the transcript by heading, or the produced YAML, plus the
list of new SHAs for the provenance check. `make eval-batch` groups the runs that still have nulls under
an excerpt-byte budget and writes one prompt file per group to `grader-batches/`; the session spawns one
grader subagent per file with "Read `<file>` and follow it". A grader call carries about 45k tokens of
base context before it reads anything, so one call that grades several runs pays that once. The prompt
in each file has this shape:

```text
Read this one file: <run-dir>/grading.json
Its `residual` object lists the null indices and the task prompt. Each null entry has a `context`
array of excerpts. Judge each from the excerpts: set `passed`, replace `evidence` with quoted
evidence, set `graded_by` to "model". Open a source file only if an excerpt is insufficient, and
say so in `evidence`. Leave every other entry untouched, recompute `summary`, write the file back.
No `timing` object, no `claims`; `eval_feedback` only if an assertion looked weak.
```

Measured on two runs against the same grader reading files itself: eval 2 (four residuals, 14k chars
of excerpts) went from 60k tokens and 65 s to 51k and 45 s; eval 6 (four residuals, 44k chars of
excerpts) went from 80k tokens and 188 s to 86k and 153 s. Verdicts were identical. Excerpts save time
in both cases and tokens only when the residual is small, because the cost floor is the subagent's own
base context, about 45k tokens per call, not the files it reads. The remaining lever is to batch the
residuals of several runs into one grader call so that base cost is paid once. A run with no nulls
gets no grader call. Then `make eval-finalize` recomputes every summary, strips the excerpts, and
refuses to finish if a null remains.

**6. Aggregate and view.** `make eval-benchmark` runs `aggregate_benchmark.py` over the iteration and
writes `benchmark.json` and `benchmark.md` with pass rate, tokens, and time per configuration.
`make eval-view` opens the skill-creator viewer. `python3 evals/_dashboard/build-dashboard.py`
rebuilds the repo dashboard from every iteration on disk.

## With skill versus without skill

Only step 2 differs, and only by one line in the executor prompt. Everything else is identical:
same prompt, same fixtures, same work repo, same grader instructions, same assertions.

|                               | With skill                                                                               | Without skill                                                                                                         |
| ----------------------------- | ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Executor prompt               | names the skill path                                                                     | omits it                                                                                                              |
| What the executor reads first | `SKILL.md`, then the references it routes to (`audit.md`, `security.md`), then the input | the input only                                                                                                        |
| Tools it runs                 | `scan.sh` wrapping zizmor and pinact, actionlint, poutine, run-stats, gasa               | whatever it decides on its own; one saved baseline used `curl` against the GitHub API to resolve tags to SHAs by hand |
| Grader                        | identical                                                                                | identical                                                                                                             |

The without-skill run is the control group. It answers one question: which assertions does the model
pass on its own? An assertion that passes without the skill on every model is a rule the skill may not
need to carry. `coverage.md` records those candidates.

Older iterations used a third configuration, `old_skill`: when improving an existing skill, the
baseline was a snapshot of the previous skill version instead of no skill. Iterations 2 to 4 used that.
Iterations 7 and 8 used the true no-skill baseline, which is the row in the README results table.

## What is a program and what is a model call

| Step                                     | Program or model                          | Cost                                                    |
| ---------------------------------------- | ----------------------------------------- | ------------------------------------------------------- |
| Create work repo, place fixtures, commit | shell commands the session runs           | none                                                    |
| Executor                                 | one subagent per configuration            | 60k to 140k tokens, 2 to 10 minutes                     |
| Save timing                              | the session writes a file                 | none                                                    |
| `checks.py`                              | program                                   | 2 to 4 seconds per run                                  |
| Grader                                   | one subagent per run that still has nulls | 55k to 80k tokens; was 60k to 110k with no program pass |
| Aggregate, view, dashboards              | programs                                  | none                                                    |

The executor is the cost floor and is unchanged by how grading is done. The grader's remaining cost is
its base context: a subagent that judges one assertion still carries its system prompt and tool
definitions, about 45k tokens per call before it reads anything. Excerpts removed the file reads
(step 5); batching several runs' residuals into one call is the next cut.

## Why deterministic first

On 2026-09-09 the ten iteration-11 Sonnet 5 runs were graded twice: once model-first, with a grader
judging every assertion and running the scanners by hand, and once deterministic-first as described
above. Same outputs, same assertions, same grader model.

| Measure                                    | Model-first | Deterministic-first |
| ------------------------------------------ | ----------- | ------------------- |
| Grader tokens, ten runs                    | 774k        | 550k                |
| Grader wall time, program pass included    | 32.1 min    | 12.8 min            |
| Assertions decided by a program            | 0 of 101    | 84 of 101           |
| Program agrees with the model-first grader |             | 82 of 84            |
| Two model graders agree with each other    | 99 of 101   |                     |

Batching the residual grader calls was then measured on the same ten runs: two grader calls (one
holding two large runs, one holding seven small ones) graded all 26 residual assertions for 196k tokens
in 5.4 minutes, against 550k tokens and 12.4 minutes for nine separate residual calls. Against the
original model-first grading that is 75% fewer grader tokens and 83% less grader wall time, with the
program pass included. Verdicts matched the separate calls on every assertion but one judgment call,
the same one two earlier model graders had already split on.

The two model graders disagreed with each other on judgment assertions and on one sentence with two
readings. A program returns the same verdict on the same input every time, so a regression run compares
the skill, not the grader's mood. The comparison workspace and the dashboard that explains it live
under `evals/github-actions-workflow-pro/runs/grader-compare/` and `evals/_dashboard/grader-compare.html`.

## Writing assertions a program can grade

The rules are in [AGENTS.md](../AGENTS.md) under "Deterministic checks before model judgment". The
short form:

- Write the pass condition as the literal a program tests: the key, the value, the heading text.
  "Least-privilege permissions" makes a model interpret. "Top-level `permissions: {}` and every job
  has a `permissions` block" makes a program decide, and reads better to a human reviewer too.
- Split an assertion that has a mechanical half and a judgment half into two, so the model reads only
  the second.
- Run tools in `checks.py`, not in the grader prompt. A program never forgets a flag and applies the
  known false-positive exemptions by rule id.
- Each assertion has a kind, recorded in `coverage.md`: **program** (decided by a key, regex, byte
  equality, or exit code), **split** (the program decides the mechanical half and can fail the assertion
  outright; a pass on that half sends the residual to the model), **model** (judgment only). Regenerate
  the table with `evals/<skill>/checks.py --kinds` when `evals.json` or `checks.py` changes.
- Keep the model for what only a judgment can settle: whether a reason is correct, whether a question
  was necessary, whether a removal was justified.

## Running it yourself

```bash
make eval-check     SKILL=github-actions-workflow-pro ITER=13   # program pass, writes grading.json with nulls + excerpts
make eval-batch     SKILL=github-actions-workflow-pro ITER=13   # one grader prompt file per group of runs
# spawn one grader subagent per grader-batches/batch-N.md: "Read <file> and follow it"
make eval-finalize  SKILL=github-actions-workflow-pro ITER=13   # recompute summaries, strip excerpts, fail on any null
make eval-benchmark SKILL=github-actions-workflow-pro ITER=13   # benchmark.json / benchmark.md
make eval-view      SKILL=github-actions-workflow-pro ITER=13   # skill-creator viewer
```

`ITER` defaults to the highest iteration present. Tools are never installed by the Makefile; a missing
one prints its `brew install` formula. `checks.py` needs `yq`, and for `--scanners` it needs actionlint,
zizmor, poutine, pinact, and an authenticated `gh` (`scan.sh` sets the token inside its own process so
it never appears on a command line).

Harness notes learned the hard way: graders never embed a `timing` object in `grading.json` (it breaks
`aggregate_benchmark`; timing belongs in the sibling `timing.json`); never use `set -x` near a
token-bearing command; executors commit the pristine input files as the work repo's first commit before
editing. When a rate limit kills graders mid-run, validate every surviving `grading.json` (expectation
count, field names, no `timing`) and relaunch only the missing runs.

## Glossary

| Term           | Meaning                                                                              |
| -------------- | ------------------------------------------------------------------------------------ |
| Eval           | One prompt plus its fixture files and assertions                                     |
| Assertion      | One pass/fail statement about the result; the unit everything is counted in          |
| Run            | One execution of one eval in one configuration, plus its grading                     |
| Iteration      | A directory of runs made together, usually one per model or per rule change          |
| Configuration  | `with_skill`, `without_skill`, or `old_skill`                                        |
| Executor       | The subagent that performs the task                                                  |
| Grader         | The subagent that judges the assertions a program left null                          |
| Kind           | `program`, `split`, or `model`: who can decide an assertion                          |
| Mech           | Shorthand in `coverage.md` for the scanner assertion present on every eval           |
| Discriminating | An assertion that fails without the skill and passes with it; the ones worth keeping |
