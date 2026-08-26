# Auditing existing workflows

Read this when the user hands you one or more workflows to review, harden, secure, or speed up, or asks "what's wrong with my CI". The output is a report in the template below plus a proposed diff. The SKILL.md checklist still applies to any YAML you propose.

## 1. Gate

Before reading any YAML:

- Locate the files: `.github/workflows/*.yml` and `*.yaml`, or the file the user pointed at. No files is a finding in itself: say so and stop.
- Check the tools: `command -v actionlint shellcheck zizmor gasa gh`. Report by name anything missing and continue with what is present. Recommend the missing tool at the end, do not install it. `actionlint` runs shellcheck on `run:` blocks only when shellcheck is installed, so a clean actionlint without shellcheck says less than it looks.
- `gasa` scans a repository through the GitHub API (it infers `owner/repo` from the remote when run inside a clone) and needs `gh auth status` to pass. If auth fails or the repo has no remote, run the file-level tools only and say gasa was skipped.
- If the user says the workflow is failing, or `gh run list` shows red, read the failed run log (`gh run view <id> --log-failed`) before reading YAML. A broken workflow is the top finding regardless of what the linters say.

## 2. Run the tools, then read the YAML

The tools are the source of truth for hard findings; run them first so your own reading fills gaps instead of duplicating rules the tools already enforce.

```bash
actionlint .github/workflows/*.y*ml
GH_TOKEN=$(gh auth token) zizmor --format json .github/workflows/      # online audits need the token; zizmor stays offline without it
gasa run --format json                                                 # all categories; read-only, so a security audit runs settings too
gh run list --workflow <file> --limit 10 --json conclusion,startedAt,updatedAt \
  --jq '.[] | "\(.conclusion) \((.updatedAt|fromdateiso8601) - (.startedAt|fromdateiso8601))s"'
```

- `actionlint`: syntax, expression types, shellcheck on `run:` blocks, unknown runner labels.
- `zizmor`: template injection, secrets outside environments, dangerous triggers, unpinned uses, excessive permissions, checkout credential persistence. A second pass with `--persona pedantic` surfaces style-grade items; those feed the Opinions section, never Hard.
- `gasa`: pinning, permissions, `pull_request_target`, Dependabot coverage, and repository settings (default token permissions, fork-PR approval, allowed-actions policy). Each finding carries its own `doc_url`; run `gasa rules` only when one does not.
- Run history gives you failure rate and duration, which no linter sees. Quantify speed findings from it.

Then read each workflow once, top to bottom, against `references/security.md` and `references/speed.md`. Note anything the tools cannot see: a deploy job sharing a cancel-in-progress group with CI, a matrix of identical cells, a `write` grant no step uses, a release workflow with a path filter, a reusable workflow whose inputs cannot express what its callers need.

## 3. Sort findings

- **Correctness**: the workflow does not do what it claims. Failing runs, a filter that never matches, a step that breaks on multi-line input, a reusable workflow that always pushes. No rule id; severity high. These come from run logs and reading, not from linters, and they go first because a workflow that does not run has no security or speed to audit.
- **Hard**: a tool rule fired, or the YAML violates a rule in `security.md` that has a concrete failure mode (injection, unpinned third-party action, `write-all`, `pull_request_target` in a public repo, static cloud keys). Cite the rule id (`zizmor: template-injection`, `gasa: workflows/action-version-pinning`, `security.md: pinned`) and `file:line`. gasa settings findings go here too, with their rule id.
- **Speed**: a rule from `speed.md` not applied where it would obviously help. Quantify from run history ("build job has no timeout; last 10 runs took 38–41 min").
- **Opinion**: Bret's conventions with no failure mode attached: friendly names, filename conventions, `ghcr.io` default, reusable-workflow suggestions, zizmor pedantic items. Label each "opinion". A convention the repo already follows consistently overrides the opinion; say so instead of proposing churn.

Two precedence rules:

- A suppression in one tool does not cancel a finding from another. A `# zizmor: ignore[unpinned-uses]` comment silences zizmor; if gasa still fires on that line, report it and quote the ignore's stated reason so the reader can judge whether it covers this failure mode.
- A hard finding the repo has consciously accepted (documented in a comment, `dependabot.yml`, or `.gasa.yml`) is still reported. State the repo's reason next to it and hand the decision back; deciding is the user's job, hiding the finding is not yours.

Skip anything a tool already enforces and reports cleanly; the reader has the tool output.

## 4. Report

Use this shape. Empty sections stay in with "none".

```markdown
## Correctness
- high <file>:<line> — <what is broken, with the evidence: run id, log line>. Fix: <the change>.

## Hard findings
- <severity> `<rule id>` <file>:<line> — <what is wrong in one line>. Fix: <the change>.

## Speed
- <file>:<line> — <what is slow and why, with numbers>. Fix: <the change>.

## Opinions
- <file> — <convention>, opinion. <one-line why it helps>.

## Proposed diff
<unified diff, or the full corrected file when most lines change>

## Tools
actionlint <version|absent>, shellcheck <version|absent>, zizmor <version|absent> (<online|offline>), gasa <version|absent|skipped: reason>
```

Severity comes from the tool that reported it. For `security.md` rules without a tool hit: critical for injection and `pull_request_target` in a public repo, high for an unpinned third-party action or `write-all`, medium for a same-owner branch ref (matches gasa) and everything else.

When the user asked you not to edit, copy the workflows to a scratch directory, apply the diff there, and validate the copy.

Ordering matters when settings findings and workflow findings interact: turning on "require SHA pinning" in repo settings before the `@main` ref is fixed stops the workflow from running. Say which fix goes first.

## 5. Done when

- Every listed finding names a rule id, is under Correctness with its evidence, or is labelled opinion.
- The proposed YAML passes `actionlint` and `zizmor` (re-run them on the corrected copy; include the result in Tools).
- Every third-party `uses:` in the proposed YAML is a full SHA with a version comment from `scripts/pin-action.sh`. For a repo with no tags the script pins the default branch HEAD and comments `# main YYYY-MM-DD`; say in the report that Dependabot cannot bump that pin.
- Placeholders you introduced (secret names, environment names, registries) are listed for the user to confirm.

## Why the sections stay separate

A reader can act on hard findings without agreeing with Bret's taste, adopt the opinions without an incident behind them, and fix a broken workflow before caring about either. Merging the lists would let a naming nit sit next to a shell-injection hole at the same visual weight, and the reader would rightly distrust the whole report.
