# Eval coverage

Which assertion in `evals.json` proves each rule the skill states. Two kinds of proof:

- **Scanner** — the rule is owned by actionlint, zizmor, poutine, or gasa. One mechanical assertion per eval ("passes actionlint, zizmor regular, poutine, and pinact -check -verify-comment with zero findings", graded by running the tools on the output) covers every scanner-owned rule at once. It carries one exception: poutine `default_permissions_on_risky_events` on a job with an explicit `permissions: {}`, a known false positive (see `references/audit.md`, poutine row). No agent-written assertion is needed for these.
- **Agent** — no scanner checks the rule, so a named assertion reads the output for it.

`eN#k` = eval N, assertion k (1-based, order in `evals.json`). "mech" = the mechanical scanner assertion present on every eval.

## SKILL.md checklist

| Line                                           | Proof                                                                  | Assertions                                                     |
| ---------------------------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------- |
| `permissions: {}` + least-privilege per job    | scanner (zizmor `excessive-permissions`, gasa) + agent                 | mech; e0#2 e1#4 e2#2 e3#3 e5#1                                 |
| `checkout` needs `contents: read`              | agent (runtime failure, no scanner)                                    | e5#1, and any eval whose output checks out and passes mech     |
| `persist-credentials: false`                   | scanner (zizmor `artipacked`)                                          | mech; e5#3 e7#5                                                |
| Third-party `uses:` SHA + version comment      | scanner (zizmor `unpinned-uses`, `ref-version-mismatch`; gasa)         | mech; e3#4 e5#2                                                |
| Version comment alone on the line              | agent (Dependabot behaviour, no scanner)                               | not asserted; candidate for e3 (fixture has no such line yet)  |
| Release at least 7 days old                    | scanner (pinact `-verify-min-age`)                                     | mech (pinact `-min-age 7 -verify-min-age` in the grader's run) |
| Same-owner `@main` replaced, or reported high  | scanner (gasa, zizmor)                                                 | mech; tagless-upstream case not asserted (needs a live repo)   |
| OIDC over static cloud keys                    | agent                                                                  | e2#4 e3#5 e7#1                                                 |
| Secrets scoped to an environment               | scanner (zizmor `secrets-outside-env`, auditor) + agent                | e7#3                                                           |
| `github.event.*` through `env:`                | scanner (actionlint, zizmor, poutine)                                  | mech; e3#2                                                     |
| `pull_request` not `pull_request_target`       | scanner (zizmor, gasa, poutine)                                        | mech; e2#1 e3#1                                                |
| Dependabot entry with cooldown                 | scanner (zizmor `dependabot-cooldown`, gasa `updates/*`) + agent offer | e7#6                                                           |
| Superseded runs cancel (CI)                    | scanner (zizmor `concurrency-limits`, pedantic) + agent                | e0#3 e4#1                                                      |
| Deploy/release in a non-cancelling group       | agent                                                                  | e6#6 e7#2                                                      |
| Cheap jobs first and parallel                  | agent                                                                  | e4#5 e5#5 e8#2                                                 |
| Cache via setup action                         | agent                                                                  | e0#4 e4#2 e5#3                                                 |
| `timeout-minutes`                              | agent                                                                  | e0#5 e4#6 e5#4 e7#5                                            |
| Path filters only when correct; none on new CI | agent                                                                  | e5#7 e8#6                                                      |
| Ask before manual/remote triggers              | agent                                                                  | e5#7 e8#6                                                      |

## Building a workflow

| Line                                             | Proof   | Assertions                                                                        |
| ------------------------------------------------ | ------- | --------------------------------------------------------------------------------- |
| Ask only about decisions; infer facts            | agent   | e0#9 e8#4                                                                         |
| Runtime version from `.nvmrc` / `engines`        | agent   | e8#1                                                                              |
| Conventional filenames                           | agent   | e8#5 (e0/e1 name the file in the prompt)                                          |
| pinact for every third-party `uses:`             | scanner | mech (pinact `-check` clean means every pin is a SHA with a correct comment)      |
| SHAs come from `pinact run`, never a hand lookup | agent   | every eval, last assertion (transcript); ungraded until runs save `transcript.md` |
| `-update` scoped on an already-pinned file       | agent   | e4#4 e5#6 (setup-node `# v4.4.0` must survive)                                    |
| Reusable-workflow offer; repo's own linter wins  | agent   | e8#2 e8#3                                                                         |

## Maintainable YAML and Container images

| Line                                                                                                                  | Proof                                                     | Assertions        |
| --------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- | ----------------- |
| Friendly names                                                                                                        | scanner (zizmor `anonymous-definition`, pedantic) + agent | e0#5 e5#4         |
| Explicit triggers                                                                                                     | agent                                                     | e0#1 e1#1         |
| `set -euo pipefail`                                                                                                   | agent                                                     | e7#4              |
| Trusted refs only for publish; buildx/metadata/build-push; ghcr; `packages: write` scoped; gha cache; provenance/SBOM | agent                                                     | e1#1–#5 e1#8 e4#7 |

## Validate and Done-when

| Line                                                   | Proof           | Assertions                     |
| ------------------------------------------------------ | --------------- | ------------------------------ |
| Scanners run or named absent                           | agent           | e0#7 e1#7 e2#7 e3#7 e4#11 e5#8 |
| Every job has `permissions:`; `permissions: {}` at top | scanner + agent | mech; e0#2 e5#1                |
| Every third-party `uses:` SHA-pinned                   | scanner         | mech                           |
| Placeholders listed                                    | agent           | e2#8 e7#7                      |
| Hand-back explains each default                        | agent           | e0#8 e1#8 e2#8 e4#9 e8#7       |

## audit.md

| Line                                                                  | Proof   | Assertions                                                               |
| --------------------------------------------------------------------- | ------- | ------------------------------------------------------------------------ |
| Covers every workflow in the repo                                     | agent   | e6#6                                                                     |
| Run history: failures documented, still-failing → ask to troubleshoot | agent   | not asserted (fixture repos have no remote). Gap: needs a live-repo eval |
| Disabled workflows and unlisted files reported as Correctness         | agent   | not asserted; same live-repo gap (example-voting-app is the canary)      |
| Speed ranking, spread ratio, one-sentence fix or ask                  | agent   | e6#6 partial                                                             |
| Scanners run, rule ids cited, no restating                            | agent   | e6#2 e6#4                                                                |
| Residual-only reading                                                 | agent   | e6#2 (negative form)                                                     |
| Correctness / Hard / Speed / Opinions sections                        | agent   | e3#6 e6#3                                                                |
| Do-first ≤ 5                                                          | agent   | e6#1                                                                     |
| Ask delivery format or state default                                  | agent   | e6#5                                                                     |
| Audit does not edit                                                   | agent   | e6#7                                                                     |
| Proposed YAML passes scanners                                         | scanner | e6#8                                                                     |

## Known gaps

- Process assertions (the transcript ones) need `run-N/transcript.md`, the skill-creator grader's `transcript_path`: the executor writes every shell command it ran and its result there. Iteration-3 runs saved only `outputs/`, so those assertions are ungraded until the next iteration's executor prompt asks for the file. They exist because agents follow fewer instructions as the rule count grows; the eval, not the rule, is what catches a hand `gh api` SHA lookup.

- Run-history behaviors (failures documented, troubleshoot question, ranking from real runs) need a repo with a remote and run history; candidate: a throwaway fork with seeded runs.
- Reusable-workflow caller cases (`timeout-minutes` on a `uses:` job, inputs vs callers).
