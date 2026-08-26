# Auditing existing workflows

Read this when the user hands you one or more workflows to review, harden, secure, or speed up, or asks "what's wrong with my CI". The audit covers every workflow in the repo unless the user names specific files. The output is a prioritized report in the template below plus a proposed diff, delivered in the format the user picks in step 5. The SKILL.md checklist still applies to any YAML you propose.

## 1. Gate

Before reading any YAML:

- Locate the files: every `.github/workflows/*.yml` and `*.yaml`, or the files the user pointed at. No files is a finding in itself: say so and stop.
- Check the tools: `command -v actionlint shellcheck zizmor poutine pinact gasa gh`. For each one missing, ask the user before going on: install it now (`brew install actionlint shellcheck zizmor poutine pinact`; gasa from <https://github.com/bretfisher/gasa>), or skip it and have the report say "absent" for that tool. Installing is their call, so wait for the answer; when the user is unavailable, skip and report absent. (Running the scanners from their container images with the repo bind-mounted is planned; see the root `PLAN.md`.) `actionlint` runs shellcheck on `run:` blocks only when shellcheck is installed, so a clean actionlint without shellcheck says less than it looks.
- `gasa` and `scripts/run-stats.py` work through the GitHub API (both infer `owner/repo` from the remote) and need `gh auth status` to pass. If auth fails or the repo has no remote, run the file-level tools only and say which steps were skipped.
- Ask now, in the same message as any tool question, how the user wants the report delivered: in the chat reply, as an HTML dashboard (one self-contained file, ranked tables sortable, findings grouped by section), as a Markdown file in the repo (suggest `docs/actions-audit-YYYY-MM-DD.md`), or a combination. Asking here, before the work, means the answer shapes the output instead of forcing a rewrite at the end. When the user is unavailable, write one line at the top of the report: "Delivered in chat by default; an HTML dashboard or a Markdown file is available on request."

## 2. Run history: failures and speed

Run `scripts/run-stats.py --markdown` (JSON without the flag; `--runs N` for more than the default 3 completed runs per workflow; `--branch main` to ignore PR runs). It ranks workflows and jobs by mean duration, longest first, flags inconsistent timing, lists recent failures with whether the latest run is still failing, and lists disabled workflows and workflow files the API does not know about.

- **Failures.** Record every failed run in the report (workflow, run id, title, date, URL). For any workflow whose latest run is still failing, read the failed log (`gh run view <id> --log-failed`) far enough to name the failing step, then **ask the user whether they want you to troubleshoot it** before going deeper. A workflow that does not run has no security or speed to audit, so this question comes before the rest of the report.
- **Disabled.** Each workflow under `Disabled workflows` is a Correctness finding, severity high: the YAML may be fine and nothing runs. `disabled_inactivity` is GitHub's rule for scheduled workflows after 60 days without repo activity; the fix is `gh workflow enable <name>`, with a note that a schedule-only workflow will be disabled again after the next idle stretch. `disabled_manually` means a person chose it, so report it and ask instead of proposing to re-enable. Give each file under `Workflow files GitHub does not list` a sentence too (only on a branch, or never run).
- **Speed.** A `spread_ratio` above about 1.5 means the runs disagree with each other; say so and name the slow run rather than optimizing an average that hides a cache miss or a queue wait. For each of the slowest workflows and jobs, write one sentence: the fix when it is obvious from the YAML (no cache, serial cheap jobs, `fetch-depth: 0`, duplicate matrix cells, plain `docker build`), or "needs a look at the run log to say" when it is not. **Ask before doing that deeper research**; the user may already know the cause.

## 3. Run the scanners, then read only for what they cannot see

Five deterministic tools cover most of `security.md` and part of `speed.md`. They are the source of truth for those rules: run them, cite their rule ids, and spend your own reading only on the residual list below. Re-deriving a tool's finding by hand costs tokens and adds nothing.

```bash
actionlint .github/workflows/*.y*ml
GH_TOKEN=$(gh auth token) zizmor --persona auditor --collect=all --format json .github/workflows $(ls .github/dependabot.yml 2>/dev/null)   # explicit paths, see below; token enables online audits; auditor = every audit
poutine analyze_local . --format json --quiet --disable-version-check              # supply-chain rules; no token needed locally; reads .github/workflows only
gasa run --format json                                                             # repo + settings via API; read-only, so a security audit runs it in full
GITHUB_TOKEN=$(gh auth token) pinact run -check -verify-comment -min-age 7 -verify-min-age   # unpinned, wrong version comment, pin younger than 7 days; edits nothing
```

Every tool above scopes itself to `.github/workflows` except zizmor, which scans whatever paths it is given: with `.` it walks the whole tree, so a repo's test fixtures land in the same JSON as its real workflows (on a scanner's own repo, 35 of 44 findings came from `testdata/`). The explicit path list keeps them out; a missing path is an error, hence the `ls` for `dependabot.yml`. Workflow files that live elsewhere on purpose (`templates/`, `testdata/`, `evals/fixtures/`) are a separate scope: scan them only when the gate put them in scope, and report them under their own heading so a deliberately bad fixture never reads as a finding against the repo.

What each one owns:

| Tool         | Owns (rule ids you will cite)                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Notes                                                                                                                                                                                                                                                                                                                                                                                       |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `actionlint` | YAML schema and typos, expression typing, `needs:` cycles, duplicate matrix values, invalid runner labels, `shellcheck` on `run:` (when shellcheck is installed), script injection, deprecated `::set-output` and outdated action runtimes                                                                                                                                                                                                                                      | Syntax correctness lives here; anything it reports is Hard or Correctness                                                                                                                                                                                                                                                                                                                   |
| `zizmor`     | `excessive-permissions`, `unpinned-uses`, `ref-version-mismatch`, `artipacked`, `template-injection`, `dangerous-triggers`, `secrets-outside-env`, `dependabot-cooldown`, `concurrency-limits`, `cache-poisoning`, `known-vulnerable-actions`, `impostor-commit`, `typosquat-uses`, `archived-uses`, `overprovisioned-secrets`, `unredacted-secrets`, `github-env`, `bot-conditions`, `unsound-condition`, `secrets-inherit`, `unpinned-images`, and the rest of its ~40 audits | Persona decides the bucket: `regular` findings are Hard; `pedantic`/`auditor`-only findings are Opinion, except `secrets-outside-env` (Hard), `concurrency-limits` (Speed), and `ref-version-mismatch` for a missing comment (Hard), because those are `security.md`/`speed.md` rules. Inline `# zizmor: ignore[...]` comments and `zizmor.yml` suppress; see the precedence rule in step 4 |
| `poutine`    | `injection`, `untrusted_checkout_exec`, `confused_deputy_auto_merge`, `default_permissions_on_risky_events`, `job_all_secrets`, `unverified_script_exec` (`curl \| bash`), `known_vulnerability_in_build_component`, `pr_runs_on_self_hosted`, `unpinnable_action`, `github_action_from_unverified_creator_used`, `if_always_true`, `debug_enabled`                                                                                                                             | Overlaps zizmor on injection and dangerous triggers; report each finding once, citing both ids. `error` is Hard, `warning` is Hard, `note` is Opinion                                                                                                                                                                                                                                       |
| `pinact`     | unpinned `uses:` (prints the pin it would write), wrong or missing version comment (`-verify-comment`), pin younger than the minimum age (`-verify-min-age`, logged as `min-age violation`), branch refs it cannot pin (`action can't be pinned`)                                                                                                                                                                                                                               | The only tool that knows release age. Overlaps zizmor `unpinned-uses` and gasa on the bare "not a SHA" case; cite both. Its proposed pins go straight into the diff (`pinact run -update -min-age 7` on the scratch copy)                                                                                                                                                                   |
| `gasa`       | `workflows/pull-request-target`, `workflows/action-version-pinning` (incl. same-owner branch refs), `workflows/workflow-permissions`, `workflows/write-all-permissions`, `updates/*` (Dependabot or Renovate present, `github-actions` ecosystem, cooldown, SHA-pin support), `actions/permissions/*` (repo settings: default token permissions, fork-PR approval, allowed actions, SHA-pin requirement, actions approving PRs)                                                 | The only tool that sees repository settings. Each finding carries `doc_url`; run `gasa rules` only when one does not                                                                                                                                                                                                                                                                        |

Then read each workflow once, top to bottom, for the **residual list**, the rules no tool checks:

- Static cloud credentials where OIDC is available (`security.md: OIDC`). Tools flag secrets, not the choice of auth method.
- A job that checks out but grants nothing (fails at runtime; no linter models it), or a `write` grant no step in the job uses.
- Extra text after the version comment on a SHA-pinned `uses:` line (`# v7.0.1 # zizmor: ignore[...]`): Dependabot then stops updating the comment (`security.md: pinned`). Propose the `.github/zizmor.yml` move for ignores and a line above the step for notes.
- Deploy or release workflows sharing a `cancel-in-progress: true` group with CI; release, security, or deploy workflows with path filters; a required-check workflow with a path filter.
- Cheap jobs chained behind each other, a cache the setup action would provide but does not, `fetch-depth: 0` where nothing reads history, no `timeout-minutes` on network or deploy jobs, matrix cells that alias the same runner (`ubuntu-latest` and `ubuntu-24.04`).
- Multi-line `run:` without `set -euo pipefail`; names that are not human-friendly; a reusable workflow whose inputs cannot express what its callers need; images built with plain `docker build` instead of Buildx with `type=gha` cache.
- Anything the run history in step 2 pointed at that the tools did not explain.

## 4. Sort and prioritize

Sections, in the order they appear in the report:

- **Correctness**: the workflow does not do what it claims. Failing runs (from step 2), a filter that never matches, a step that breaks on multi-line input, a reusable workflow that always pushes. No rule id; severity high. These come from run logs and reading, not from linters.
- **Hard**: a tool rule fired, or the YAML violates a rule in `security.md` that has a concrete failure mode (injection, unpinned third-party action, `write-all`, `pull_request_target` in a public repo, static cloud keys). Cite the rule id (`zizmor: template-injection`, `gasa: workflows/action-version-pinning`, `security.md: pinned`) and `file:line`. gasa settings findings go here too, with their rule id.
- **Speed**: the ranked tables from step 2, then one line per finding with the number that justifies it ("build job mean 18m40s over 3 runs, no layer cache").
- **Opinion**: Bret's conventions with no failure mode attached: friendly names, filename conventions, `ghcr.io` default, reusable-workflow suggestions, zizmor pedantic items. Label each "opinion". A convention the repo already follows consistently overrides the opinion; say so instead of proposing churn.

Within each section, order by severity, then by how many workflows the fix touches. Open the report with a **Do first** list of at most five items drawn from across the sections: a still-failing workflow, then critical and high hard findings, then the single largest speed win. The reader should be able to stop after that list and have spent their time well.

Two precedence rules:

- A suppression in one tool does not cancel a finding from another. A `# zizmor: ignore[unpinned-uses]` comment silences zizmor; if gasa still fires on that line, report it and quote the ignore's stated reason so the reader can judge whether it covers this failure mode.
- A hard finding the repo has consciously accepted (documented in a comment, `dependabot.yml`, or `.gasa.yml`) is still reported. State the repo's reason next to it and hand the decision back; deciding is the user's job, hiding the finding is not yours.

Skip anything a tool already enforces and reports cleanly; the reader has the tool output.

## 5. Report

Deliver in the format the user chose in step 1 (or the stated chat default). Whatever the medium, the content follows this shape; empty sections stay in with "none".

```markdown
## Do first

1. <the one thing to fix today, with its section and file:line>
   ...

## Correctness

- high <file>:<line> — <what is broken, with the evidence: run id, log line>. Fix: <the change>.

## Recent failures

- <workflow>: run <id> "<title>" <date> <conclusion> (still failing on latest run?) — <url>

## Hard findings

- <severity> `<rule id>` <file>:<line> — <what is wrong in one line>. Fix: <the change>.

## Speed

<ranked workflow table> <ranked job table>

- <workflow / job> — <mean over N runs, spread> — <one-sentence fix, or "needs run-log research; want me to?">

## Opinions

- <file> — <convention>, opinion. <one-line why it helps>.

## Proposed diff

<unified diff, or the full corrected file when most lines change>

## Tools

actionlint <version|absent>, shellcheck <version|absent>, zizmor <version|absent> (<online|offline>, persona auditor), poutine <version|absent>, pinact <version|absent>, gasa <version|absent|skipped: reason>, run-stats <N runs|skipped: reason>
```

Severity comes from the tool that reported it, with one override: a branch ref to a reusable workflow or shared action is high even though gasa says medium, because a compromise there cascades into every caller. For `security.md` rules without a tool hit: critical for injection and `pull_request_target` in a public repo, high for an unpinned third-party action or `write-all`, medium for other same-owner branch refs and everything else.

An audit reports; it does not edit. Leave the workflow files untouched unless the user asks you to apply or fix, and validate the corrected version on a copy in a scratch directory. A user who wants the files changed says so, and then the SKILL.md Validate step runs on the real files.

Ordering matters when settings findings and workflow findings interact: turning on "require SHA pinning" in repo settings before the `@main` ref is fixed stops the workflow from running. Say which fix goes first.

## 6. Done when

- The delivery format was asked in step 1, or the report's first line states the chat default and the alternatives; any still-failing workflow got the troubleshoot question before the full report landed.
- Every listed finding names a rule id, is under Correctness with its evidence, or is labelled opinion; the Do-first list has at most five items.
- Every workflow file in scope appears in the speed ranking, the Disabled list, or the not-listed list with a sentence explaining it, or the run-stats step is marked skipped with the reason.
- The proposed YAML passes `actionlint`, `zizmor`, `poutine`, and `pinact -check` (re-run them on the corrected copy; include the result in Tools). The one report allowed to remain is pinact's `action can't be pinned` on a branch ref to a tagless repo, which the report carries in Hard with the upstream fix.
- No finding in the report restates something a tool already reported under its own id; each tool-detected item cites the id, and the residual list is the only place your own reading adds findings.
- Every third-party `uses:` in the proposed YAML is a full SHA with a version comment and nothing else on the line, written by `pinact run -update -min-age 7` on the scratch copy and clean under `pinact run -check -verify-comment -verify-min-age`. A branch ref to a tagless repo stays as written in the proposed YAML (there is no verifiable pin to write) and appears in Hard with the upstream fix: tag a release, then `pinact run --branch-to-tag`.
- Placeholders you introduced (secret names, environment names, registries) are listed for the user to confirm.

## Why the sections stay separate

A reader can act on hard findings without agreeing with Bret's taste, adopt the opinions without an incident behind them, and fix a broken workflow before caring about either. Merging the lists would let a naming nit sit next to a shell-injection hole at the same visual weight, and the reader would rightly distrust the whole report. The Do-first list is the one place they mix, and it is capped at five so it stays a triage, not a second report.
