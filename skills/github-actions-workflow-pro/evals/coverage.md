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

## Backlog (pass 3 candidates, from the pass-2 graders)

In scope, not yet applied:

- e1#7: allow the image name to reach `metadata-action` via an env variable, not only the literal expression.
- e3#8 and e6#11: say whether a narrowed branch filter counts as a behavior change (align with e4#11).
- e4#11: the escape clause needs the question to name the dropped coverage; a nearby unrelated question does not count.
- e6#10 and e6#11: say whether "Correctness" means a literal section title or substance (a baseline report with no sections was graded on substance).
- e7#10: say the Hard label is load-bearing, not just the reason.
- Intent preservation: an invented step that hard-fails on an unverified artifact (`if-no-files-found: error` on every PR) should fail e3#8.
- Recheck e8#5 against the iteration-4 with-skill output: both delivered workflows carry `paths-ignore`, which that assertion says must not be added; likely a pass-1 grading miss, not an assertion gap.
- Fixture repair: `evals/fixtures/node-repo/package-lock.json` has an empty packages map, so any correct CI fails at `npm ci` in real life. Fix the fixture; see Rejected for why it is not a rule.

Rejected, so graders stop re-suggesting them:

- Lockfile content validation (empty `package-lock.json` not flagged): ecosystem-specific; the skill does not carry rules per package manager or language.
- e0 ordering (`npm ci` before `npm test`, same job): prompt-fidelity tightening with no observed failure; the npm commands come from the eval prompt, not from a skill rule.
