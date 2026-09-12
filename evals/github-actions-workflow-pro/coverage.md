# Eval coverage

Which assertion in `evals.json` proves each rule the skill states. Two kinds of proof:

- **Scanner** — the rule is owned by actionlint, zizmor, poutine, or gasa. One mechanical assertion per eval ("passes actionlint, zizmor regular, poutine, and pinact -check -verify-comment with zero findings", graded by running the tools on the output) covers every scanner-owned rule at once. It carries two exceptions: poutine `default_permissions_on_risky_events` on a job with an explicit `permissions: {}`, a known false positive (see `references/audit.md`, poutine row), and zizmor `dangerous-triggers` on a `pull_request_target` the answer keeps for a stated reason (see `references/security.md`). No agent-written assertion is needed for these.
- **Agent** — no scanner checks the rule, so a named assertion reads the output for it.

`eN#k` = eval N, assertion k (1-based, order in `evals.json`). "mech" = the mechanical scanner assertion present on every eval.

Since 2026-09-09 grading is deterministic first (AGENTS.md, "Deterministic checks before model judgment"): `checks.py` grades every
assertion a program can decide and leaves `passed: null` for the model. Each assertion is one of three kinds. **program**: a YAML
key, a regex, byte equality with the fixture, or a scanner exit code decides it. **split**: the program decides the mechanical half
(and can fail the assertion outright); when that half passes, the residual goes to the model. **model**: judgment only. The table
below is the output of `checks.py --kinds`; regenerate it when `evals.json` or `checks.py` changes.

## Assertion kinds

| Eval    | Assertions | program | split  | model  | split indices    | model indices |
| ------- | ---------- | ------- | ------ | ------ | ---------------- | ------------- |
| e0      | 9          | 6       | 1      | 2      | #9               | #7 #8         |
| e1      | 8          | 6       | 1      | 1      | #8               | #6            |
| e2      | 11         | 7       | 2      | 2      | #1 #11           | #7 #8         |
| e3      | 11         | 9       | 2      | 0      | #8 #11           | —             |
| e4      | 12         | 6       | 5      | 1      | #3 #4 #5 #11 #12 | #9            |
| e5      | 11         | 9       | 2      | 0      | #5 #11           | —             |
| e6      | 12         | 7       | 2      | 3      | #2 #12           | #5 #10 #11    |
| e7      | 13         | 9       | 2      | 2      | #12 #13          | #3 #8         |
| e8      | 10         | 6       | 1      | 3      | #10              | #4 #5 #7      |
| e9      | 9          | 6       | 1      | 2      | #9               | #5 #6         |
| e10     | 9          | 7       | 2      | 0      | #4 #7            | —             |
| e11     | 10         | 6       | 2      | 2      | #2 #3            | #6 #7         |
| **all** | **125**    | **84**  | **23** | **18** |                  |               |

The two cases a program cannot see, found in the 2026-09-09 grader comparison (`runs/grader-compare/`, dashboard
`evals/_dashboard/grader-compare.html`): a SHA copied from another file and only described in transcript prose (why the transcript
assertion is split, not program), and proposed YAML that lives inside a Markdown diff rather than an output file (the scanner
assertion is vacuous there; the model reads the diff).

## SKILL.md checklist

| Line                                                                       | Proof                                                                  | Assertions                                                                                     |
| -------------------------------------------------------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `permissions: {}` + least-privilege per job                                | scanner (zizmor `excessive-permissions`, gasa) + agent                 | mech; e0#2 e1#3 e2#2 e3#3 e5#1 e7#11 (keys) e7#12 (non-empty top-level grant reported as Hard) |
| `checkout` needs `contents: read`                                          | agent (runtime failure, no scanner)                                    | e5#1, and any eval whose output checks out and passes mech                                     |
| `persist-credentials: false`                                               | scanner (zizmor `artipacked`)                                          | mech; e5#3 e7#6                                                                                |
| Third-party `uses:` SHA + version comment                                  | scanner (zizmor `unpinned-uses`, `ref-version-mismatch`; gasa)         | mech; e3#4 e5#2                                                                                |
| Version comment alone on the line                                          | agent (Dependabot behaviour, no scanner)                               | e3#10                                                                                          |
| Release at least 7 days old                                                | scanner (pinact `-verify-min-age`)                                     | mech (pinact `-min-age 7 -verify-min-age` in the grader's run)                                 |
| Same-owner `@main` replaced, or reported high                              | scanner (gasa, zizmor)                                                 | mech; tagless-upstream case not asserted (needs a live repo)                                   |
| OIDC over static cloud keys                                                | agent                                                                  | e2#4 e7#1                                                                                      |
| Secrets scoped to an environment                                           | scanner (zizmor `secrets-outside-env`, auditor) + agent                | e7#4                                                                                           |
| Cloud credentials configured after install and build                       | agent (SKILL.md + security.md)                                         | e7#10                                                                                          |
| `github.event.*` through `env:`                                            | scanner (actionlint, zizmor, poutine)                                  | mech; e3#2                                                                                     |
| `pull_request` not `pull_request_target`                                   | scanner (zizmor, gasa, poutine)                                        | mech; e2#1 e3#1                                                                                |
| Dependabot entry with cooldown                                             | scanner (zizmor `dependabot-cooldown`, gasa `updates/*`) + agent offer | e7#7                                                                                           |
| Superseded runs cancel (CI)                                                | scanner (zizmor `concurrency-limits`, pedantic) + agent                | e0#3 e4#1                                                                                      |
| Deploy/release in a non-cancelling group                                   | agent                                                                  | e6#6 e7#2 (key) e7#3 (reason)                                                                  |
| Cheap jobs first and parallel                                              | agent                                                                  | e4#5 e5#5 e8#2                                                                                 |
| Parallel steps inside one job (`parallel`, `background`, `wait`, `cancel`) | agent (new GitHub syntax, no scanner)                                  | e10#1 e10#2 e10#3 e10#5 e10#7; e10#6 covers the actionlint schema lag                          |
| Cache via setup action                                                     | agent                                                                  | e0#4 e4#2 e5#3                                                                                 |
| `timeout-minutes`                                                          | agent                                                                  | e0#5 e4#6 e5#4 e7#6                                                                            |
| Path filters only when correct; none on new CI                             | agent                                                                  | e5#7 e8#6 (compound: path filters and dispatch triggers in one assertion)                      |
| Ask before manual/remote triggers                                          | agent                                                                  | e5#7 e8#6 (same compound assertions as the row above)                                          |

## Building a workflow

| Line                                               | Proof                                         | Assertions                                                                   |
| -------------------------------------------------- | --------------------------------------------- | ---------------------------------------------------------------------------- |
| Ask only about decisions; infer facts              | agent                                         | e0#8 e8#5                                                                    |
| Runtime version from `.nvmrc` / `engines`          | agent                                         | e8#1                                                                         |
| Conventional filenames                             | agent                                         | e1#7 (docker.yml, from the prompt)                                           |
| pinact for every third-party `uses:`               | scanner                                       | mech (pinact `-check` clean means every pin is a SHA with a correct comment) |
| SHAs come from `pinact run`, never a hand lookup   | agent                                         | every eval, last assertion (transcript; split: the program can only fail it) |
| `-update` scoped on an already-pinned file         | agent                                         | e5#6 (edit path: setup-node `# v4.4.0` must survive); e6#9 (audit path)      |
| Reusable-workflow offer; repo's own linter wins    | agent                                         | e8#2 e8#3 (names it) e8#4 (asks)                                             |
| Prompt's commands and filenames kept               | agent (no rule line; adherence to the prompt) | e0#1 e1#7 e5#9                                                               |
| Existing triggers unchanged unless the prompt asks | agent (SKILL.md triggers line)                | e4#11                                                                        |

## Maintainable YAML and Container images

| Line                                                                                                                                              | Proof                                                     | Assertions                  |
| ------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | --------------------------- |
| Friendly names                                                                                                                                    | scanner (zizmor `anonymous-definition`, pedantic) + agent | e0#5 e5#4                   |
| Explicit triggers                                                                                                                                 | agent                                                     | e1#1                        |
| `set -euo pipefail`                                                                                                                               | agent                                                     | e7#5                        |
| Trusted refs only for publish (two jobs; `packages: write` only on the publish job); buildx/metadata/build-push; ghcr; gha cache; provenance/SBOM | agent                                                     | e1#1–#4 e1#6 e2#9 e4#7 e8#9 |
| Deploy consumes the image by digest from the build job                                                                                            | agent (SKILL.md container images)                         | e2#10                       |

## Validate and Done-when

| Line                                                   | Proof                                        | Assertions                                                           |
| ------------------------------------------------------ | -------------------------------------------- | -------------------------------------------------------------------- |
| Scanners run or named absent                           | agent                                        | e3#6 e6#4 (Tools line, ran/absent; on build evals mech is the proof) |
| Every job has `permissions:`; `permissions: {}` at top | scanner + agent                              | mech; e0#2 e5#1                                                      |
| Every third-party `uses:` SHA-pinned                   | scanner                                      | mech                                                                 |
| Placeholders listed                                    | agent                                        | e2#7 e7#8                                                            |
| Hand-back explains each default                        | agent (done-when: the why, not what it does) | e0#7 e1#6 e2#7 e4#9 e8#7                                             |

## audit.md

| Line                                                                                                                                                                                                          | Proof                                                     | Assertions                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Covers every workflow in the repo                                                                                                                                                                             | agent                                                     | e6#6 e9#7                                                                           |
| Run history: failures documented, still-failing → ask to troubleshoot                                                                                                                                         | agent                                                     | not asserted; live-repo gap                                                         |
| Disabled workflows and unlisted files reported as Correctness                                                                                                                                                 | agent                                                     | not asserted; live-repo gap                                                         |
| Speed ranking, spread ratio, one-sentence fix or ask                                                                                                                                                          | agent                                                     | e6#6 partial; full ranking needs the live-repo gap                                  |
| Steps at or over 2m each get a named cause; `Set up job` reported as runner time with no YAML fix                                                                                                             | agent                                                     | e11#1 e11#3 e11#4 e11#5 e11#6 e11#7                                                 |
| Ask the user which duration cut to analyze after showing the 2-minute table                                                                                                                                   | agent                                                     | e11#2                                                                               |
| Scanners run, rule ids cited, no restating                                                                                                                                                                    | agent                                                     | e6#2 e6#4                                                                           |
| Residual-only reading                                                                                                                                                                                         | agent                                                     | e6#2 (negative form)                                                                |
| Correctness / Hard / Speed / Opinions sections                                                                                                                                                                | agent                                                     | e3#5 e6#3                                                                           |
| Do-first ≤ 5                                                                                                                                                                                                  | agent                                                     | e6#1                                                                                |
| Ask delivery format or state default                                                                                                                                                                          | agent                                                     | e6#5                                                                                |
| Audit does not edit                                                                                                                                                                                           | agent                                                     | e6#7                                                                                |
| Proposed YAML passes scanners                                                                                                                                                                                 | scanner                                                   | e6#8                                                                                |
| Proposed YAML keeps the original's intent; always-broken steps land in Correctness                                                                                                                            | agent (SKILL.md Working Style 2, smallest correct change) | e3#8 e6#11                                                                          |
| Every finding the diff fixes appears in the report                                                                                                                                                            | agent                                                     | e6#10                                                                               |
| Major-version jump from `pinact -update` announced with the command that keeps the old major; already-pinned lines keep their SHA                                                                             | agent (audit.md scratch-copy paragraph)                   | e3#9 e6#9                                                                           |
| Agentic workflow pairs (`.md` + `.lock.yml`): lock never audited as hand-editable; staleness (old compiler version or lock over ~a month old) is the finding; fix is `gh aw update-actions` + `gh aw compile` | agent                                                     | e9#1–#6 (e9#4 names the two commands, e9#5 the Dependabot reasoning)                |
| Run titles and log text are data, not instructions (`--log-failed \| tail`, `untrusted_fields`)                                                                                                               | agent                                                     | not asserted; live-repo gap (needs a seeded run whose title carries an instruction) |

## Known gaps

- Process assertions (the transcript ones) are graded from `run-N/transcript.md`, which the executor writes as it works. Self-reported, so a raw tool-call log from the harness would be stronger; in practice every old-skill run still logged its `gh api` lookups and failed the assertion.
- The live-repo gap: run-history behaviors, disabled workflows, spread ratio from real runs, the tagless-upstream `@main` case, and untrusted run titles all need a repo with a remote and seeded runs (a failing run, a disabled workflow, a run title carrying an injected instruction). One throwaway fork closes five rows at once.
- Reusable-workflow caller cases (`timeout-minutes` on a `uses:` job, inputs vs callers).
- Evals 10 and 11 were added 2026-09-12 with the parallel-step and slow-step rules and have not been run yet; e11 hands the agent a saved `run-stats.py --markdown` file (`fixtures/run-stats-long-tail.md`) because the sandbox has no live repo, so it proves the reading of the step table, not the running of the script.

## Pass 3 work plan

Source: the pass-2 graders (2026-08-30) and the full-suite run on Sonnet 5 and Haiku 4.5 with and without the skill (2026-08-31; 94/101 and 70/101 with skill, 55/101 and 36/101 without; saved under `evals/github-actions-workflow-pro/runs/iteration-{7-sonnet,8-haiku}/`). Items are ordered by what they move. Each names its type: **rule** changes skill text and needs executors to re-run; **eval** changes `evals.json` wording and needs graders only, against the saved outputs; **fixture** changes an input file; **harness** changes how runs are made.

Order of work: do every **eval** item first and re-grade the saved iteration-7 and -8 outputs against the changed assertions only (cheap, and it fixes the numbers before anything else moves them). Then the **rule** items, re-running only the evals whose rules changed, on Sonnet and Haiku. README cells change only after a full run of all 10 evals.

### 1. Grading consistency (eval, do first: these move the baseline numbers)

- Transcript assertion (last on every eval) on a run that wrote no SHA: graders split between vacuous PASS and FAIL across iterations 7 and 8. Add the clause "a run that wrote no new SHA passes this assertion" so the number is comparable. e9#8 is the extreme case (an audit that pins nothing).
- e6#10 / e6#11 / e3#8: say whether "Correctness" is a literal section title or substance (a baseline with no sections was graded on substance once, on the title once), and whether a narrowed branch filter counts as a behavior change (align with e4#11).
- e4#11: the escape clause needs the question to name the dropped coverage; a nearby unrelated question does not count.
- e7#10: the Hard label is load-bearing, not only the reason.

### 2. Assertions that let a wrong output through (eval)

- e1#2 / e2#9 / e8#8 trusted refs: name the second failing shape seen on Haiku e8 — two jobs, but the unprivileged build job still carries `push: ${{ github.event_name != 'pull_request' }}` with no login, so trusted-ref pushes fail and the publish job never runs.
- e3#6 / e6#4 Tools line: Haiku invented four of five tool versions in two runs with no version command in the transcript. Resolved 2026-08-31 by removing versions from the line (ran/absent/skipped only); the line records coverage, and a version slot was only a place to fabricate.
- e3 / e6 reported counts: Haiku reported `poutine: 0` with 3 findings in its own saved output. Add: every scanner count in the report matches the tool output the grader reproduces.
- e9#3 staleness: Haiku passed on a guess ("likely 2+ months old"). Require the latest gh-aw tag or the lock's commit date to appear.
- e9#4 Dependabot: say the report must state that Dependabot PRs against the lock are closed, not merged (rule now in audit.md), while a repo `dependabot.yml` for normal workflows stays correct.
- e9#2: allow a compiler-produced lock (the output of `gh aw compile` on the edited `.md`) — only hand edits fail it.
- e9#7 (mech): exempt disclosed compiler-authored nits inside a recompiled lock (schema lag on `queue`, SC2129).
- e1#7: allow the image name to reach `metadata-action` through an env variable.
- Intent preservation (e3#8): an invented step that hard-fails on an unverified artifact (`if-no-files-found: error` on every PR) fails it.
- Recheck e8#5 on the iteration-4 with-skill output: both workflows carried `paths-ignore`; likely a pass-1 grading miss.

### 3. Skill rules the run showed are missing or too quiet (rule)

- Hand-back reasons — **applied and verified 2026-08-31**: the done-when names the defaults and placeholders. Re-runs of e1, e2, e7, e8: Sonnet passed the reasons assertion on all four (was failing three); Haiku passed on three of four (e2 gave 8 of 9 whys — one still drops sometimes). Was the most frequent with-skill miss on both models.
- Deploy by digest — **applied and verified 2026-08-31**: the SKILL.md bullet spells the three-line wiring. Sonnet e2 re-run wired it end to end (had deferred the principle-only version as "a gap"); Haiku e2 wired two of the three lines and left the digest output dangling — shape rules raise Haiku's floor, they do not guarantee the last step.
- Trusted refs — **applied and verified 2026-08-31** with a caveat: SKILL.md says the build job's `push:` is the literal `false`, never an event expression. Sonnet followed it and quoted it; Haiku e8 followed it (its previous failure), but Haiku e1 and e2 re-runs produced the event-expression single job anyway. On Haiku this rule lands in roughly half of runs — score movement is within single-run variance, so treat any one Haiku run as a sample, not a verdict.
- Tools line — **dropped 2026-08-31**: versions removed from the Tools line and the version commands from audit.md instead of a paste-never-recall rule. Versions served no reader; ran/absent/skipped is what the line is for. e3#6 and e6#4 reworded to match.
- Credentials after build — **applied and verified 2026-08-31**: the SKILL.md OIDC checklist line says the cloud credentials step runs after `npm ci`, `pip install`, and the build, or the build is its own job without `id-token: write`, with the why. Haiku e7 had configured AWS before `npm ci` twice with the bullet only in security.md; on the full run e7#9 passed on both models and both quoted the reason back (Haiku: "acquires AWS credentials only after untrusted install scripts have finished running"). A Sonnet e1 grader caught that the first wording named "a registry login" as a credentials step, which contradicts the Container images pattern (`docker/login-action` precedes `build-push-action`); the line now says cloud credentials, and adds that a registry login before `build-push-action` is fine because the Dockerfile's install runs inside BuildKit, not on the runner.
- Agentic pair section — **applied and verified 2026-08-31**: the audit.md report template has an `## Agentic workflows` section with the pair line (compiler version vs latest, git-log date, fresh/stale, update-actions + compile fix, lock findings folded in); with no pair it reads `none` like every other empty section (a first draft said omit, which contradicted the template rule on line 80). Full run: Sonnet e9 8/8 (was 7/8), section followed in shape; Haiku e9 6/8 (was 4/8), e9#1-#4 now pass, but Haiku still listed the lock findings a second time under Hard (e9#5) and proposed an invalid step-level `permissions` key in the `.md` frontmatter (e9#7).

### 4. Fixtures (fixture)

- `evals/github-actions-workflow-pro/fixtures/node-repo/package-lock.json` has an empty packages map, so any correct CI fails at `npm ci`. Replace with a valid minimal lockfile.
- e5 input is already fully pinned, so assertions 1–9 do not discriminate (both configs matched byte for byte). Add one tag-pinned action to `good-ci.yml` so the edit path has something to pin.
- e9: add a `dependabot.yml` to the fixture repo so the Dependabot-vs-lock point is forced, and replace the sed-downgraded lock with a real old-compiler artifact if the version-comment mismatch ever confuses a run (accepted wart today: `github/gh-aw-actions/setup` carries a v0.79.0 comment on a v0.86.2 SHA).
- e9 uncovered outcome: every audit run caught `good-ci.yml` referencing `.nvmrc` / `package.json` that do not exist in the fixture repo; add the assertion or add the files.

### Verification result for section 3 items 1-3 (2026-08-31, iterations 9 and 10)

With-skill re-runs of e1, e2, e7, e8. Sonnet: 39/39 (was 35/39) — all three rules followed, quoted, every touched eval now perfect. Haiku: 27/39 (was 25/39) — hand-back list mostly holds, digest wiring lands partially, `push:` literal-false lands in about half of runs; failures move between runs more than they persist, so Haiku conclusions need more than one run per eval. Items 3.4-3.6 were deliberately left unimplemented; Haiku e7's re-run failed credentials-before-build again with the rule still only in security.md, which is the control result item 3.5 predicts.

### Full run after pass-3 rules (2026-08-31)

With skill, all ten evals, one run each (iteration-11-sonnet-full, iteration-12-haiku-full) against iteration-7/8. Sonnet 94 → 97/101: gains e1#6, e2#10, e6#10, e9#4; one flip down, e6#12 (the executor typed a setup-node SHA from another file after reverting pinact's major bump; in iteration-7 it re-ran pinact instead — same intent, and the rule already names a cross-file copy as a hand lookup). Haiku 70 → 83/101: 17 assertions up, 4 down (e2#10 digest wiring absent this time, e3#11 the `pinact run` command missing from the transcript, e6#12 hand-invented SHAs, e9#7 above). None of the five flips traces to the edited text; they are the run-to-run variance already noted under section 3, so a future full run may move them again. README cells updated to 97/101 and 83/101. Grader suggestions worth keeping from this run: assertion e6#12 should name the cross-file copy explicitly (as e9 in section 2 does for the reverse); e7#7 and e2#7 pass on hand-backs that miss one named default — the graders read "each default" strictly, which is the intent; Haiku ran zizmor and pinact bare instead of through `scripts/scan.sh` in four runs (no token leaked, but an assertion could require the wrapper); Haiku e5 ran poutine on a bare file outside `.github/workflows/`, which scans nothing and reports clean.

### 5. Harness (harness)

- `transcript.md` is executor-authored and Haiku omitted commands it ran (correct SHAs with no `pinact run` in the table, e2). A raw tool-call log from the harness would make the process assertions verifiable; until then the assertion text should say what counts as evidence.
- Session rate limits kill graders mid-write. Recovery that worked: validate every surviving `grading.json` (expectation count matches `expectations.json`, fields `text`/`passed`/`evidence`, no `timing`), then relaunch only the missing runs with "skip a run that already has a valid grading.json".
- Unreproduced: a Sonnet e6 executor claimed zizmor's directory form dropped 15 of 20 findings; the grader's directory run returned all 20. Leave audit.md as is unless it recurs.

Rejected, so graders stop re-suggesting them:

- Lockfile content validation (empty `package-lock.json` not flagged): ecosystem-specific; the skill does not carry rules per package manager or language.
- e0 ordering (`npm ci` before `npm test`, same job): prompt-fidelity tightening with no observed failure; the npm commands come from the eval prompt, not from a skill rule.

## Pass 4 (2026-09-09): deterministic-first grading

Source: the grader comparison in `runs/grader-compare/` (ten iteration-11 Sonnet 5 outputs graded model-first and deterministic-first;
grader tokens −29%, grader wall time −60%, program agreed with the model-first grader on 82 of 84 verdicts; two model graders agreed
with each other on 99 of 101). Changes made:

- `checks.py` added; `make eval-check` / `make eval-finalize` wrap it. Assertion kinds recorded above.
- **eval** rewordings so the pass condition is the literal a program tests: e0#5 (workflow `name:`, every job `name:` + `timeout-minutes:`,
  every `uses:` step named), e2#5 (every job `timeout-minutes:`, a `concurrency:` block, a cache key), e3#5 and e6#3 (the audit.md
  template headings by name), e3#6 (`## Tools` heading). These are stricter than the model was: Haiku iteration-12 had passed e0#5 with an
  unnamed job and e2#5 with two jobs lacking timeouts; under the new wording both fail.
- **eval** splits into a program half and a model half: e7#2/#3 (cancel-in-progress false / the reason), e7#11/#12 (permissions keys /
  reported as Hard), e8#3/#4 (names docker-build-workflow / asks), e9#4/#5 (the two gh aw commands / the Dependabot reasoning).
  Assertion count 101 → 105; e7, e8, e9 indices after the splits shifted by one or two.
- **eval** transcript assertion (last on every eval): now says a run that wrote no new SHA passes (closes pass-3 item 1), names `git ls-remote`
  and a cross-file copy as hand lookups (closes the e6#12 suggestion), and is graded as split.
- README results cells still show the 101-assertion scores; the next full run replaces them.
- `checks.py` attaches `context` excerpts to every null entry so the residual grader works from `grading.json` alone; `--finalize`
  strips them. Measured on evals 2 and 6: time −30% and −19%, tokens −15% and +7% against a residual grader that read the files,
  same verdicts. The floor is the subagent's base context (~45k tokens), so batching residuals across runs is the next cut.

### Iteration 13 (2026-09-09): first full run through the deterministic-first pipeline, Haiku 4.5

Ten evals, with and without the skill, 210 assertions. Program pass: 167 decided, 43 left for the model, 25 s of wall time
for the scanners. Five batched Sonnet graders judged the 43 residuals for 435k tokens in 16.5 minutes (21.7k tokens per run;
the model-first graders of iteration 11 averaged 77k per run). Every grading.json validated (count, text, no null, no timing).
Result: **with skill 85/105, without skill 49/105**.

- Discriminating (pass with, fail without): 41, of which 34 program-decided. Pass in both: 44. Fail in both: 15. Worse with the
  skill: 5 (e2#8 placeholders, e4#8 existing pins not preserved, e6#10, e6#12 provenance, e9#6).
- e5 passes 10/10 in both configurations, the fixture issue already listed under pass-3 section 4: `good-ci.yml` is fully pinned
  and clean, so adding a lint job needs no skill. Add one tag-pinned action to the fixture.
- The no-skill e3 baseline produced two `impostor-commit` findings from zizmor: SHAs that do not belong to the tagged release the
  comment names. The skill's pinact rule exists for exactly this; the scanner assertion caught it with no model call.
- Two baseline runs put files where the executor prompt did not say (nested `outputs/.github/workflows/`, a second `transcript.md`
  under `outputs/`); the loader now reads `outputs/**`. One grader found the eval-4 baseline excerpts too thin; the extractor now
  falls back to the whole answer when matched sections total under 600 characters.
- 2026-09-09, after iteration 13: eval 5 now takes `fixtures/good-ci-tagged.yml` (good-ci.yml plus a tag-pinned
  `actions/upload-artifact@v4` in the test job) and gains assertion #10: that line is SHA-pinned in the output with a scoped
  `pinact -i`, and #6 exempts only that line from the byte-for-byte check. Assertion count 105 → 106; e5's transcript assertion is #11.
  good-ci.yml itself is unchanged because eval 9 audits it as a clean file.
- Every run directory from iteration 13 on carries `raw-transcript.jsonl`: the executor subagent's full log (thinking blocks, every
  tool call and result). It is the real tool-call record the provenance assertion has lacked; the executor-written `transcript.md`
  stays as the human-readable summary.

### Iteration 14 (2026-09-09): Sonnet 5, 106 assertions, deterministic-first

Ten evals, with and without the skill, 212 assertions. Program pass: 164 decided, 48 left for the model. Five batched Sonnet
graders: 483k tokens, 15.8 minutes (24k per run). Three executors died on a session rate limit mid-run and were reset and rerun
from the initial commit. Result: **with skill 96/106, without skill 63/106**.

- Eval 5 with the new tagged fixture now fails #8 and #10 in both configurations on Sonnet: the with-skill executor saw the unpinned
  `actions/upload-artifact@v4`, reported it with the SHA pinact suggests, and left it in place because the prompt said to keep
  everything else as it is. That is a skill gap on the edit path, not a fixture problem: SKILL.md does not say that an unpinned
  action already in a file being edited gets pinned too (scoped `-i`) and the hand-back says so. Candidate rule for pass 5.
- Eval 3 with the skill scored 7/11, below the baseline's 6/11 by one: the executor split the PR comment into a `workflow_run`
  workflow and never named the `gh pr comment`-on-push bug it was working around; the report also lacked the template headings.
  The baseline named the bug. Second run in a row where the Correctness section reads "none" with the skill; see e3#8 / e6#11.
- The eval 6 with-skill executor found that zizmor in online mode, handed a directory, returned 105 findings mis-attributed to a
  lock file from a sibling run directory (a `~/.cache/zizmor` collision). `checks.py` now passes explicit file paths to zizmor.
  This is the reproduction the pass-3 "Unreproduced" note asked for.
- Grader cost per run, model-first (iteration 11) → deterministic-first batched: 77k → 24k tokens on Sonnet outputs.
- Effort for iterations 13 and 14: executors and graders inherited the session `effortLevel: high` (`~/.claude/settings.json`);
  no agent definition pinned it. From now on the harness spawns `.claude/agents/eval-executor-<model>-<effort>` and
  `eval-grader-<model>-<effort>` so the effort is explicit and recorded.

### Pass 5 (2026-09-09): rule fixes, trims, validate.sh, raw-log provenance

- **rule** SKILL.md: the pin line on the build path now says pinning is scoped (`-i` per action) and that an action already on a
  tag in an edited file gets pinned too, whatever "keep everything else" covers, named in the hand-back; done-when says the same
  (eval 5 finding, iteration 14). audit.md Correctness: a step that cannot succeed on one of its triggers is a Correctness line
  even when the proposed diff removes or reshapes it (e3#8 / e6#11, two runs in a row).
- **rule** trims from the chopping block (both models pass without the skill): the duplicate "ask only about decisions" sentence
  (Working Style 3 keeps the rule), the obvious filenames, `checkout` needs `contents: read`, `github.event.*` through `env:`
  (scanner-owned), the first sentence of the triggers line, the path-filter and manual-trigger lines. `pull_request_target` shortened
  to the exception and the zizmor note. Kept on purpose despite passing both: the major-version-jump paragraph in audit.md (Haiku
  hand-copied a SHA in iteration 12) and the scoped-update rule (item 3 strengthens it). SKILL.md 70 → 69 lines, about 200 fewer
  tokens per invocation.
- **skill script** `scripts/validate.sh`: actionlint, zizmor (via scan.sh), poutine, and `pinact -check` in one call with one summary
  line; the Validate section and audit.md point to it. Measure with `raw-log-stats.py` whether turns per run drop.
- **harness** SHA provenance is program-graded when `raw-transcript.jsonl` exists: fail on a SHA-returning lookup command or on a
  new SHA whose first appearance is in a tool input (typed) rather than a tool result (produced by pinact, then copied); pass
  otherwise. Agreed with the model grader on every run of iterations 13 and 14 but one (the eval 2 baseline on Sonnet, which the model failed and the raw log passes).
- **fixture** eval 9 repo gains `.github/dependabot.yml` (normal github-actions entry) plus `.nvmrc` and `package.json`, so the
  Dependabot-versus-lock point is forced and `good-ci.yml`'s `.nvmrc` reference resolves. `node-repo/package-lock.json` is a real
  lockfile now (87 packages), so a correct CI no longer fails at `npm ci`.
- **harness** grader agent is `eval-grader-opus-high`; executors `eval-executor-<model>-high`. Definitions load at session start.
- Reruns of evals 3, 4, 5 on both models: `runs/iteration-15-sonnet-e345`, `runs/iteration-16-haiku-e345`.

### Iterations 15 and 16 (2026-09-09): evals 3, 4, 5 rerun after pass 5, Sonnet 5 and Haiku 4.5

Six executors per model through the Agent tool with `model:` (the `.claude/agents/` definitions load at the next session; effort
inherited high, same as iterations 13 and 14). Program pass, one batch each, two Opus graders (122k tokens for 12 residuals).

| model  | eval | with skill before → after | without skill before → after |
| ------ | ---- | ------------------------- | ---------------------------- |
| Sonnet | e3   | 7/11 → 11/11              | 6/11 → 6/11                  |
| Sonnet | e4   | 12/12 → 12/12             | 9/12 → 9/12                  |
| Sonnet | e5   | 9/11 → 11/11              | 9/11 → 9/11                  |
| Haiku  | e3   | 9/11 → 8/11               | 4/11 → 3/11                  |
| Haiku  | e4   | 10/12 → 11/12             | 6/12 → 6/12                  |
| Haiku  | e5   | 10/10 → 11/11             | 10/10 → 9/11                 |

- The edit-path pin rule landed on both models: eval 5 with the skill pins the pre-existing `upload-artifact@v4` (scoped, named in
  the hand-back) and the baseline does not, so eval 5 discriminates for the first time.
- The Correctness rule landed on Sonnet: eval 3 names the `gh pr comment`-on-push bug and scores 11/11. On Haiku the same run kept
  `pull_request_target` for the comment job and failed #1, #7, #8; the trimmed trigger line had lost its opening sentence, so
  "`pull_request` for PR triggers." is back (four words). One run, so treat the Haiku drop as a sample.
- `validate.sh` cut with-skill turns on the two evals with a validation loop: Haiku audit 82 → 58, Haiku speed-up 72 → 52, Sonnet
  audit 76 → 61; eval 5 unchanged. All six with-skill transcripts show it in use.
- Skill error found by the Sonnet eval 3 executor and fixed: pinact's `-i` is a regex over the action name, so audit.md's
  `-i 'actions/checkout@v4'` matched nothing; the way to keep a major is to write the tag in the file and run `pinact run` without
  `-update`. e3#9 reworded to match, and its check now fails a hand-back that quotes the old form.
- Grader feedback to act on next: e3#8 bundles three conditions (events kept, comment step safe, bug named) and its "no
  pull_request_target" clause contradicts e3#7's stated exception; split it. e4#5 (test no longer needs lint) now checks the test job
  only, so it settles without a model when the build job legitimately needs both.
