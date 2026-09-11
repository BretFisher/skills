# Lessons learned: making a dev skill cheaper, faster, and provable

Advice for the next agent, or person, who builds and evaluates a developer-oriented skill. Every item
below was tried on `github-actions-workflow-pro` on 2026-09-09 and has a number behind it; the numbers
are in the second section. Read [eval-walkthrough.md](eval-walkthrough.md) first if the words run,
assertion, executor, or grader are new.

## The short list

1. **Grade with programs first.** A regex, a YAML key, a byte comparison, or a scanner exit code decides
   every assertion it can; a model judges only what is left.
2. **Write each assertion as the literal a program tests.** Name the key, the value, the heading text.
   A paraphrase makes a model interpret; a literal makes a program decide and a reviewer agree.
3. **Split an assertion that mixes a check with a judgment.** Two assertions: the program takes the
   first, the model reads only the second.
4. **Hand the grader excerpts, then batch the graders.** A grader call carries about 45k tokens of base
   context before it reads anything; pay it once for several runs, not once per run.
5. **Keep the raw subagent log with every run.** It has every tool call and result. It made SHA provenance
   a program verdict and it is the only honest record of where tokens go.
6. **Always run the no-skill baseline.** It is the only way to know which rules the model follows anyway,
   and those rules are what you cut.
7. **Pin model and effort with an agent definition.** A results cell without a known effort cannot be
   compared with the next one.
8. **Put the skill's validation loop in one script.** Turns cost more than words; four tool calls became
   one and runs got 20 to 30% shorter.
9. **Measure tokens from the raw log, not from the skill's word count.** Cost is turns times context. The
   skill text is a small part of it.
10. **Cut rules both models follow without the skill; keep the assertion one more round.** The
    assertion is the safety net for the cut.
11. **Let the eval find the skill's factual errors.** An executor following a wrong command literally is
    the fastest way to learn the command is wrong.
12. **Treat one run as a sample.** Two model graders reading the same file disagreed on 2 of 101 verdicts;
    the same model with the same skill flipped verdicts between runs.
13. **Keep eval definitions outside the skill directory, and make fixtures discriminate.** An input that
    is already clean teaches nothing about the skill.
14. **Record cost the moment a subagent finishes, and reset a killed run to its first commit before
    rerunning it.** Task notifications are the only place token counts exist; a half-finished run graded
    as if complete is a false score.

## The details

### 1. Grade with programs first

The starting point was a model grader that read every assertion of every run and ran four security
scanners by hand. It cost 60k to 110k tokens and two to six minutes per run, and it built a scratch
git repo and typed about twenty tool calls each time.

`checks.py` now grades every assertion a program can decide and writes `grading.json` with
`passed: null` on the rest. Of 106 assertions, 71 are program kind, 19 are split, 16 need a model. The
scanner assertion, once a paragraph of instructions for the grader, is a subprocess call with the two
known false-positive exemptions applied by rule id.

Measured on the same ten Sonnet outputs graded both ways: grader tokens 774k to 550k with one grader
call per run, then to 196k with batching; wall time 32 minutes to 5.4. Verdicts matched the model
grader on 82 of 84 program-decided assertions, and where they differed the program was following the
skill's rule more strictly than the model did.

### 2. Write each assertion as the literal a program tests

"The test job has a timeout and clear names" let a model pass a job with no `name:`. "Every job has
`name:` and `timeout-minutes:`; every step that uses an action has `name:`" does not. "Concurrency,
caching, and timeouts where appropriate" let two jobs without timeouts through; "every job has
`timeout-minutes:`, a `concurrency:` block exists, the build caches" does not. "Separates hard findings
from opinions under distinct headings" was satisfied by "Critical Findings (Hard)"; naming the template
headings makes the template the contract.

The rewording also documents the rule better for a human reviewer, who now sees exactly what must be
in the file instead of a description of its spirit.

### 3. Split an assertion that mixes a check with a judgment

"The deploy job's concurrency no longer cancels in-progress runs, with the reason given" is a key
check plus a judgment. As two assertions, the program grades `cancel-in-progress: false` and the model
reads only the reason. Four such assertions were split; the count went from 101 to 105 and the model's
share fell. A bundled assertion also hides which half failed, which is what you need to know to fix
the skill.

### 4. Hand the grader excerpts, then batch the graders

`checks.py` attaches to every null entry the excerpts the assertion needs: answer sections by heading,
transcript sections, the produced YAML, the new SHAs. The grader prompt says judge from these and open
a file only if one is insufficient, and say so. Excerpts alone cut time (30% and 19% on the two evals
measured) but not always tokens, because the cost floor is the subagent's base context, about 45k
tokens per call before it reads anything.

Batching pays that once. `checks.py --batch` groups the runs that still have nulls under an
excerpt-byte budget and writes one prompt file per group. On the ten-run comparison two batched calls
graded 26 residual assertions for 196k tokens against 550k for nine separate calls, verdicts identical
but for one judgment call two earlier graders had already split on. In practice a 60k-character budget
gives one grader two to eight runs; past about eight files one grader gets sloppy, so lower the budget
for a run set with small excerpts.

### 5. Keep the raw subagent log with every run

Claude Code writes every subagent's full log to
`~/.claude/projects/<project>/<session>/subagents/agent-<id>.jsonl`. The harness copies it into the run
as `raw-transcript.jsonl`. It holds every tool call with input and result, the visible text, and
per-turn token usage. It does not hold reasoning: thinking blocks arrive as an empty body and a
signature, so there is no transcript of the model debating itself to mine.

Two things it made possible. SHA provenance became a program verdict: a SHA a tool produced appears in a
tool result before the model ever puts it in a tool input, while a SHA typed from memory appears in an
input first, and a lookup against `git/refs`, `/commits/`, or `/releases` is a command in the log. The
program agreed with the model grader on every run but one. And `raw-log-stats.py` turns the logs into a
per-run table of turns, tool calls, and where the characters came from, which is the evidence for items
8 and 9.

### 6. Always run the no-skill baseline

Same prompt, same fixtures, same grader, skill not installed. It answers the one question a with-skill
run cannot: which assertions does the model pass on its own? Across Haiku 4.5 and Sonnet 5, 39 of 105
assertions passed without the skill on both models. Those map to 12 rules the skill states that the
models already follow, and 13 more it states partly for nothing. The chopping-block dashboard
(`evals/_dashboard/build-chopping-block.py`) ranks them by what cutting them saves.

The baseline also catches skill regressions that look like improvements. A Haiku eval-3 rerun with the
skill scored below its own baseline on one assertion because the skill's trimmed trigger line no longer
led with `pull_request`; the baseline made the cause visible in one comparison.

### 7. Pin model and effort with an agent definition

The Agent tool picks a model but has no effort parameter; a subagent inherits the session's
`effortLevel` from `~/.claude/settings.json`. Effort changes output quality enough that two cells run at
different efforts are not comparable. An agent definition in `.claude/agents/<name>.md` pins both in
its frontmatter (`model:` and `effort:`). Definitions load at session start, so add them, restart, then
run. The README results table carries an effort row for this reason.

### 8. Put the skill's validation loop in one script

The skill's Validate step told the model to run four scanners, each its own tool call, on the original
and again on the corrected copy. `scripts/validate.sh` runs all four with fixed flags and prints one
summary line. On the two evals with a real validation loop, turns per run fell from 82 to 58 and 72 to
52 on Haiku and 76 to 61 on Sonnet; the trivial eval did not change. Fewer turns is the direct lever on
cost (item 9), and fixed flags remove the forgotten `-verify-min-age` class of error.

### 9. Measure tokens from the raw log, not from the skill's word count

The Haiku full run read 369k characters of skill files across ten with-skill runs, about 92k tokens,
against 30.6M cache-read tokens. The with-skill runs made 40% more turns than the baselines and their
cache reads doubled, because the skill text sits in context on every one of those extra turns. So the
cost of a skill is turns times context, and shortening the loop the skill prescribes saves more than
trimming rule sentences. Trim anyway (item 10), but measure with `raw-log-stats.py` before and after.

### 10. Cut rules both models follow without the skill; keep the assertion one more round

Trimming the twelve fully covered rules saved about 200 tokens per invocation. The judgment calls: the
scoped-update rule and the major-version paragraph were kept although both models passed them, because
a Haiku run one iteration earlier had hand-copied a SHA, which is the failure those rules exist for. The
`pull_request` opener was cut and then restored after one Haiku run kept `pull_request_target`. The
assertion stays through the next full run so the cut can be reversed on evidence, not on memory.

### 11. Let the eval find the skill's factual errors

audit.md gave `pinact run -update -min-age 7 -i 'actions/checkout@v4'` as the way to keep an old major.
A Sonnet executor followed it, found that `-i` is a regex over the action name so `@v4` matches nothing,
and reported it in the transcript. The rule now says write the tag in the file and run `pinact run`
without `-update`. An executor that follows instructions literally is a free proofreader; read the
transcripts of the runs that struggled.

### 12. Treat one run as a sample

Two model graders reading the same ten outputs, same instructions, days apart, disagreed on 2 of 101
verdicts, and a third disagreed with them on 3 more. Every one was a judgment assertion or a sentence
with two readings. Executors vary too: the same skill on the same eval produced a `workflow_run` split
once and a `pull_request_target` job the next time. A program's verdict does not move, so with
program-first grading a score change means the skill changed. Confirm a rule change with a second run
of the affected evals before recording it, and say "one run" when it is one run.

### 13. Keep eval definitions outside the skill directory, and make fixtures discriminate

Installers copy the whole skill directory, so evals under it ship to every user. `evals/<skill>/`
holds definitions, fixtures, `checks.py`, and `coverage.md`; `runs/` under it is gitignored. Eval 5
passed 10 of 10 with and without the skill for three iterations because its input workflow was already
clean; one tag-pinned action added to the fixture made it the first eval to show the skill's edit-path
rule, and the rule turned out to be missing. A fixture that a baseline passes teaches nothing about the
skill.

### 14. Record cost the moment a subagent finishes, and reset a killed run before rerunning it

A subagent's task notification is the only place its `total_tokens` and `duration_ms` exist; write
`timing.json` at once, with the agent id, so the raw log can be copied too. Three Sonnet executors died
on a session rate limit with outputs half written and no transcript. Grading them would have produced
a false cell; the fix was to check each run for a transcript, reset `work/` to its initial commit, empty
`outputs/`, and rerun. The `--finalize` step refuses to close an iteration with a null verdict for the
same reason.
