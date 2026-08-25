# Auditing existing workflows

Read this when the user hands you one or more workflows to review, harden, secure, or speed up, or asks "what's wrong with my CI". The output is a report in the template below plus a proposed diff. The SKILL.md checklist still applies to any YAML you propose.

## 1. Gate

Before reading any YAML:

- Locate the files: `.github/workflows/*.yml` and `*.yaml`, or the file the user pointed at. No files is a finding in itself: say so and stop.
- Check the tools: `command -v actionlint zizmor gasa gh`. Report by name anything missing and continue with what is present. Recommend the missing tool at the end, do not install it.
- `gasa` scans a repository, not a file, and needs `gh auth status` to pass. If auth fails, run the file-level tools only and say gasa was skipped.

## 2. Run the tools, then read the YAML

The tools are the source of truth for hard findings; run them first so your own reading fills gaps instead of duplicating rules the tools already enforce.

```bash
actionlint -format '{{json .}}' .github/workflows/*.y*ml
zizmor --format json --offline .github/workflows/
gasa run --format json --category workflows            # repo-level; add settings,updates if gh auth passes and the user wants admin checks
```

- `actionlint`: syntax, expression types, shellcheck on `run:` blocks, unknown runner labels.
- `zizmor`: template injection, secrets outside environments, dangerous triggers, unpinned uses, excessive permissions. `--offline` skips audits that need the API; drop it when `gh auth status` passes and you want impostor-commit and stale-ref checks.
- `gasa`: pinning, permissions, `pull_request_target`, Dependabot coverage, and (with `settings`) repo admin settings such as default token permissions and fork-PR approval. Run `gasa rules` for the current list and each rule's doc URL rather than restating them here.

Then read each workflow once, top to bottom, against `references/security.md` and `references/speed.md`. Note anything the tools cannot see: a deploy job sharing a cancel-in-progress group with CI, a matrix of identical cells, a `write` grant no step uses, a release workflow with a path filter.

## 3. Sort findings into hard and opinion

- **Hard**: a tool rule fired, or the YAML violates a rule in `security.md` that has a concrete failure mode (injection, unpinned third-party action, `write-all`, `pull_request_target` in a public repo, static cloud keys). Cite the rule id (`zizmor: template-injection`, `gasa: workflows/action-version-pinning`, `security.md: pinned`) and `file:line`.
- **Speed**: a rule from `speed.md` not applied where it would obviously help. Quantify when you can ("build job has no timeout; last run was 41 min").
- **Opinion**: Bret's conventions with no failure mode attached: friendly names, filename conventions, `ghcr.io` default, reusable-workflow suggestions. Label each "opinion". A convention the repo already follows consistently overrides the opinion; say so instead of proposing churn.

Skip anything a tool already enforces and reports cleanly; the reader has the tool output. Skip anything the repo has explicitly configured away (a `.gasa.yml` ignore, a `# zizmor: ignore[...]` comment) unless the ignore itself looks wrong.

## 4. Report

Use this shape. Empty sections stay in with "none".

```markdown
## Hard findings
- <severity> `<rule id>` <file>:<line> — <what is wrong in one line>. Fix: <the change>.

## Speed
- <file>:<line> — <what is slow and why>. Fix: <the change>.

## Opinions
- <file> — <convention>, opinion. <one-line why it helps>.

## Proposed diff
<unified diff, or the full corrected file when most lines change>

## Tools
actionlint <version|absent>, zizmor <version|absent>, gasa <version|absent|skipped: reason>
```

Severity comes from the tool that reported it; for `security.md` rules use critical for injection and `pull_request_target` in public repos, high for unpinned third-party actions and `write-all`, medium otherwise.

## 5. Done when

- Every listed finding names a rule id or is labelled opinion.
- The proposed YAML passes `actionlint` and `zizmor` (re-run them on the corrected file; include the result in Tools).
- Every third-party `uses:` in the proposed YAML is a full SHA with a version comment, resolved with `scripts/pin-action.sh`.
- Placeholders you introduced (secret names, environment names, registries) are listed for the user to confirm.

## Why hard and opinion stay separate

A reader can act on hard findings without agreeing with Bret's taste, and can adopt the opinions without an incident behind them. Merging the lists would let a naming nit sit next to a shell-injection hole at the same visual weight, and the reader would rightly distrust the whole report.
