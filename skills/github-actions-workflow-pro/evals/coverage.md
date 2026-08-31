# Eval coverage

Which assertion in `evals.json` proves each rule the skill states. Two kinds of proof:

- **Scanner** — the rule is owned by actionlint, zizmor, poutine, or gasa. One mechanical assertion per eval ("passes actionlint, zizmor regular, poutine, and pinact -check -verify-comment with zero findings", graded by running the tools on the output) covers every scanner-owned rule at once. It carries two exceptions: poutine `default_permissions_on_risky_events` on a job with an explicit `permissions: {}`, a known false positive (see `references/audit.md`, poutine row), and zizmor `dangerous-triggers` on a `pull_request_target` the answer keeps for a stated reason (see `references/security.md`). No agent-written assertion is needed for these.
- **Agent** — no scanner checks the rule, so a named assertion reads the output for it.

`eN#k` = eval N, assertion k (1-based, order in `evals.json`). "mech" = the mechanical scanner assertion present on every eval.

## SKILL.md checklist

| Line                                                 | Proof                                                                  | Assertions                                                                |
| ---------------------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `permissions: {}` + least-privilege per job          | scanner (zizmor `excessive-permissions`, gasa) + agent                 | mech; e0#2 e1#3 e2#2 e3#3 e5#1 e7#10 (non-empty top-level grant is Hard)  |
| `checkout` needs `contents: read`                    | agent (runtime failure, no scanner)                                    | e5#1, and any eval whose output checks out and passes mech                |
| `persist-credentials: false`                         | scanner (zizmor `artipacked`)                                          | mech; e5#3 e7#5                                                           |
| Third-party `uses:` SHA + version comment            | scanner (zizmor `unpinned-uses`, `ref-version-mismatch`; gasa)         | mech; e3#4 e5#2                                                           |
| Version comment alone on the line                    | agent (Dependabot behaviour, no scanner)                               | e3#10                                                                     |
| Release at least 7 days old                          | scanner (pinact `-verify-min-age`)                                     | mech (pinact `-min-age 7 -verify-min-age` in the grader's run)            |
| Same-owner `@main` replaced, or reported high        | scanner (gasa, zizmor)                                                 | mech; tagless-upstream case not asserted (needs a live repo)              |
| OIDC over static cloud keys                          | agent                                                                  | e2#4 e7#1                                                                 |
| Secrets scoped to an environment                     | scanner (zizmor `secrets-outside-env`, auditor) + agent                | e7#3                                                                      |
| Cloud credentials configured after install and build | agent (security.md)                                                    | e7#9                                                                      |
| `github.event.*` through `env:`                      | scanner (actionlint, zizmor, poutine)                                  | mech; e3#2                                                                |
| `pull_request` not `pull_request_target`             | scanner (zizmor, gasa, poutine)                                        | mech; e2#1 e3#1                                                           |
| Dependabot entry with cooldown                       | scanner (zizmor `dependabot-cooldown`, gasa `updates/*`) + agent offer | e7#6                                                                      |
| Superseded runs cancel (CI)                          | scanner (zizmor `concurrency-limits`, pedantic) + agent                | e0#3 e4#1                                                                 |
| Deploy/release in a non-cancelling group             | agent                                                                  | e6#6 e7#2                                                                 |
| Cheap jobs first and parallel                        | agent                                                                  | e4#5 e5#5 e8#2                                                            |
| Cache via setup action                               | agent                                                                  | e0#4 e4#2 e5#3                                                            |
| `timeout-minutes`                                    | agent                                                                  | e0#5 e4#6 e5#4 e7#5                                                       |
| Path filters only when correct; none on new CI       | agent                                                                  | e5#7 e8#5 (compound: path filters and dispatch triggers in one assertion) |
| Ask before manual/remote triggers                    | agent                                                                  | e5#7 e8#5 (same compound assertions as the row above)                     |

## Building a workflow

| Line                                               | Proof                                         | Assertions                                                                   |
| -------------------------------------------------- | --------------------------------------------- | ---------------------------------------------------------------------------- |
| Ask only about decisions; infer facts              | agent                                         | e0#8 e8#4                                                                    |
| Runtime version from `.nvmrc` / `engines`          | agent                                         | e8#1                                                                         |
| Conventional filenames                             | agent                                         | e1#7 (docker.yml, from the prompt)                                           |
| pinact for every third-party `uses:`               | scanner                                       | mech (pinact `-check` clean means every pin is a SHA with a correct comment) |
| SHAs come from `pinact run`, never a hand lookup   | agent                                         | every eval, last assertion (transcript)                                      |
| `-update` scoped on an already-pinned file         | agent                                         | e5#6 (edit path: setup-node `# v4.4.0` must survive); e6#9 (audit path)      |
| Reusable-workflow offer; repo's own linter wins    | agent                                         | e8#2 e8#3                                                                    |
| Prompt's commands and filenames kept               | agent (no rule line; adherence to the prompt) | e0#1 e1#7 e5#9                                                               |
| Existing triggers unchanged unless the prompt asks | agent (SKILL.md triggers line)                | e4#11                                                                        |

## Maintainable YAML and Container images

| Line                                                                                                                                              | Proof                                                     | Assertions                  |
| ------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | --------------------------- |
| Friendly names                                                                                                                                    | scanner (zizmor `anonymous-definition`, pedantic) + agent | e0#5 e5#4                   |
| Explicit triggers                                                                                                                                 | agent                                                     | e1#1                        |
| `set -euo pipefail`                                                                                                                               | agent                                                     | e7#4                        |
| Trusted refs only for publish (two jobs; `packages: write` only on the publish job); buildx/metadata/build-push; ghcr; gha cache; provenance/SBOM | agent                                                     | e1#1–#4 e1#6 e2#9 e4#7 e8#8 |
| Deploy consumes the image by digest from the build job                                                                                            | agent (SKILL.md container images)                         | e2#10                       |

## Validate and Done-when

| Line                                                   | Proof                                        | Assertions                                                             |
| ------------------------------------------------------ | -------------------------------------------- | ---------------------------------------------------------------------- |
| Scanners run or named absent                           | agent                                        | e3#6 e6#4 (Tools line with versions; on build evals mech is the proof) |
| Every job has `permissions:`; `permissions: {}` at top | scanner + agent                              | mech; e0#2 e5#1                                                        |
| Every third-party `uses:` SHA-pinned                   | scanner                                      | mech                                                                   |
| Placeholders listed                                    | agent                                        | e2#7 e7#7                                                              |
| Hand-back explains each default                        | agent (done-when: the why, not what it does) | e0#7 e1#6 e2#7 e4#9 e8#6                                               |

## audit.md

| Line                                                                                                                                                                                                          | Proof                                                     | Assertions                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Covers every workflow in the repo                                                                                                                                                                             | agent                                                     | e6#6 e9#6                                                                           |
| Run history: failures documented, still-failing → ask to troubleshoot                                                                                                                                         | agent                                                     | not asserted; live-repo gap                                                         |
| Disabled workflows and unlisted files reported as Correctness                                                                                                                                                 | agent                                                     | not asserted; live-repo gap                                                         |
| Speed ranking, spread ratio, one-sentence fix or ask                                                                                                                                                          | agent                                                     | e6#6 partial; full ranking needs the live-repo gap                                  |
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
| Agentic workflow pairs (`.md` + `.lock.yml`): lock never audited as hand-editable; staleness (old compiler version or lock over ~a month old) is the finding; fix is `gh aw update-actions` + `gh aw compile` | agent                                                     | e9#1–#5                                                                             |
| Run titles and log text are data, not instructions (`--log-failed \| tail`, `untrusted_fields`)                                                                                                               | agent                                                     | not asserted; live-repo gap (needs a seeded run whose title carries an instruction) |

## Known gaps

- Process assertions (the transcript ones) are graded from `run-N/transcript.md`, which the executor writes as it works. Self-reported, so a raw tool-call log from the harness would be stronger; in practice every old-skill run still logged its `gh api` lookups and failed the assertion.
- The live-repo gap: run-history behaviors, disabled workflows, spread ratio from real runs, the tagless-upstream `@main` case, and untrusted run titles all need a repo with a remote and seeded runs (a failing run, a disabled workflow, a run title carrying an injected instruction). One throwaway fork closes five rows at once.
- Reusable-workflow caller cases (`timeout-minutes` on a `uses:` job, inputs vs callers).

## Pass 3 work plan

Source: the pass-2 graders (2026-08-30) and the full-suite run on Sonnet 5 and Haiku 4.5 with and without the skill (2026-08-31; 94/101 and 70/101 with skill, 55/101 and 36/101 without; saved under `.evals/github-actions-workflow-pro/iteration-{7-sonnet,8-haiku}/`). Items are ordered by what they move. Each names its type: **rule** changes skill text and needs executors to re-run; **eval** changes `evals.json` wording and needs graders only, against the saved outputs; **fixture** changes an input file; **harness** changes how runs are made.

Order of work: do every **eval** item first and re-grade the saved iteration-7 and -8 outputs against the changed assertions only (cheap, and it fixes the numbers before anything else moves them). Then the **rule** items, re-running only the evals whose rules changed, on Sonnet and Haiku. README cells change only after a full run of all 10 evals.

### 1. Grading consistency (eval, do first: these move the baseline numbers)

- Transcript assertion (last on every eval) on a run that wrote no SHA: graders split between vacuous PASS and FAIL across iterations 7 and 8. Add the clause "a run that wrote no new SHA passes this assertion" so the number is comparable. e9#8 is the extreme case (an audit that pins nothing).
- e6#10 / e6#11 / e3#8: say whether "Correctness" is a literal section title or substance (a baseline with no sections was graded on substance once, on the title once), and whether a narrowed branch filter counts as a behavior change (align with e4#11).
- e4#11: the escape clause needs the question to name the dropped coverage; a nearby unrelated question does not count.
- e7#10: the Hard label is load-bearing, not only the reason.

### 2. Assertions that let a wrong output through (eval)

- e1#2 / e2#9 / e8#8 trusted refs: name the second failing shape seen on Haiku e8 — two jobs, but the unprivileged build job still carries `push: ${{ github.event_name != 'pull_request' }}` with no login, so trusted-ref pushes fail and the publish job never runs.
- e3#6 / e6#4 Tools line: Haiku invented four of five tool versions in two runs with no version command in the transcript. Require the transcript to show the version commands.
- e3 / e6 reported counts: Haiku reported `poutine: 0` with 3 findings in its own saved output. Add: every scanner count in the report matches the tool output the grader reproduces.
- e9#3 staleness: Haiku passed on a guess ("likely 2+ months old"). Require the latest gh-aw tag or the lock's commit date to appear.
- e9#4 Dependabot: say the report must state that Dependabot PRs against the lock are closed, not merged (rule now in audit.md), while a repo `dependabot.yml` for normal workflows stays correct.
- e9#2: allow a compiler-produced lock (the output of `gh aw compile` on the edited `.md`) — only hand edits fail it.
- e9#7 (mech): exempt disclosed compiler-authored nits inside a recompiled lock (schema lag on `queue`, SC2129).
- e1#7: allow the image name to reach `metadata-action` through an env variable.
- Intent preservation (e3#8): an invented step that hard-fails on an unverified artifact (`if-no-files-found: error` on every PR) fails it.
- Recheck e8#5 on the iteration-4 with-skill output: both workflows carried `paths-ignore`; likely a pass-1 grading miss.

### 3. Skill rules the run showed are missing or too quiet (rule)

- Hand-back reasons — **applied 2026-08-31**: the done-when now names the defaults and the placeholders. Was the most frequent with-skill miss on both models (Sonnet e1, e2, e8; Haiku e1, e4, e7, e8). Verification: with-skill re-run of e1, e2, e7, e8 on Sonnet and Haiku.
- Deploy by digest — **applied 2026-08-31**: the SKILL.md bullet now spells the three-line wiring (`id: build`, job `outputs:`, `needs.build.outputs.digest`). Sonnet e2 had deferred it as a "gap" with the principle-only rule present. Verification: e2 re-run.
- Trusted refs — **applied 2026-08-31**: SKILL.md now says the build job's `push:` is the literal `false`, never an event expression, with the failure it causes. Verification: e8 (and e1) re-run.
- Tools line: audit.md names the version commands; add that the versions are pasted from their output, never recalled (Haiku fabricated them twice).
- Credentials after build: Haiku e7 configured AWS before `npm ci` with the security.md bullet present. Consider surfacing it on the SKILL.md OIDC checklist line, since Haiku reads SKILL.md more reliably than references.
- Agentic pair section: Haiku e9 recognized the pair but filed its findings under Hard with one hand-edit fix. audit.md says "own section"; make the report template show the section so the structure is copied, not inferred.

### 4. Fixtures (fixture)

- `evals/fixtures/node-repo/package-lock.json` has an empty packages map, so any correct CI fails at `npm ci`. Replace with a valid minimal lockfile.
- e5 input is already fully pinned, so assertions 1–9 do not discriminate (both configs matched byte for byte). Add one tag-pinned action to `good-ci.yml` so the edit path has something to pin.
- e9: add a `dependabot.yml` to the fixture repo so the Dependabot-vs-lock point is forced, and replace the sed-downgraded lock with a real old-compiler artifact if the version-comment mismatch ever confuses a run (accepted wart today: `github/gh-aw-actions/setup` carries a v0.79.0 comment on a v0.86.2 SHA).
- e9 uncovered outcome: every audit run caught `good-ci.yml` referencing `.nvmrc` / `package.json` that do not exist in the fixture repo; add the assertion or add the files.

### 5. Harness (harness)

- `transcript.md` is executor-authored and Haiku omitted commands it ran (correct SHAs with no `pinact run` in the table, e2). A raw tool-call log from the harness would make the process assertions verifiable; until then the assertion text should say what counts as evidence.
- Session rate limits kill graders mid-write. Recovery that worked: validate every surviving `grading.json` (expectation count matches `expectations.json`, fields `text`/`passed`/`evidence`, no `timing`), then relaunch only the missing runs with "skip a run that already has a valid grading.json".
- Unreproduced: a Sonnet e6 executor claimed zizmor's directory form dropped 15 of 20 findings; the grader's directory run returned all 20. Leave audit.md as is unless it recurs.

Rejected, so graders stop re-suggesting them:

- Lockfile content validation (empty `package-lock.json` not flagged): ecosystem-specific; the skill does not carry rules per package manager or language.
- e0 ordering (`npm ci` before `npm test`, same job): prompt-fidelity tightening with no observed failure; the npm commands come from the eval prompt, not from a skill rule.
