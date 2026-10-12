# OpenCode eval support

## Shared execution contract

`evals/harness/runner.py` reads the existing eval definitions and starts paired
executors. Each pair has the same prompt, fixtures, model, and tool policy. Only
the with-skill executor receives the target skill. Assertions, expected answers,
coverage maps, and past runs stay outside both executor workspaces.

The runner commits pristine fixtures with the eval identity in `evals/eval.gitconfig`.
Fixture and scanner commits are unsigned, with hooks disabled, so they need no keys
and do not invoke personal signing tools. It verifies that HEAD is unchanged after execution. Changed files and
explicit proposals are copied to `outputs/`, preserving repository-relative paths.
For an audit, proposals can be saved without changing the original files.

Use `make eval-plan` before model execution. A definition can use `fixture_map`
to override the default mapping of source files to work paths. Definitions with
procedural `setup` instructions need a tested setup adapter; the runner rejects
unknown adapters rather than executing an incomplete task. The named Kubernetes
updater adapter copies the source skill, removes its KYAML feature file, regenerates
the index, and commits that damaged copy as the pristine input. With-skill execution
loads the damaged copy too, so the installed skill cannot supply the missing file.
Both configurations receive isolated local Kubernetes source data, without Git
configuration or credentials, and use `--offline`. The manifest records source
commits and content hashes. Existing checkouts are required; `SOURCE_CACHE` overrides
the default `~/.cache/k8s-catch-up`. Host source checkouts remain unchanged.

## Context isolation

OpenCode runs with `--standalone`, a temporary home, and a private configuration.
Credential access remains in the native OpenCode data store. Credentials are not
copied to the eval artifacts. Config sources are checked against the temporary
home. The target skill is copied to that home's skill directory; all other skill
permissions are denied, including built-in skills.

The `gha-audit` wrapper also receives its declared `github-actions-workflow-pro`
dependency. Its fixture map can reuse that dependency's fixtures, and the manifest
records the dependency hash. The no-skill baseline receives neither skill.

The runner records the registered skill catalog and effective permissions.
Registered skills are not necessarily advertised skills: permissions determine
what the agent can load. The baseline has no allowed skills. Global and ancestor
instructions from this repo are excluded by the temporary workspace location.
Fixture `AGENTS.md` files remain task inputs and can be discovered normally.
OpenCode V2 does not automatically load fixture `CLAUDE.md` files.

This is context isolation, not an operating-system sandbox. Shell tools can access
the host. Use a separate container or machine for untrusted tasks; tool permissions
alone are not a filesystem security boundary. Failed workspaces are retained at
the path in `run.json` for diagnosis. Remove them manually when no longer needed.

The Claude Code adapter uses `--safe-mode`, explicit tools, an exact model ID, and
`--effort`. It preserves native credential access. Its task-quality tests read an
explicit skill snapshot because normal skill discovery is disabled. Live Claude
adapter validation remains pending.

## Evidence and usage

Each successful run saves:

- `run.json`: status, requested model, fixture commit, workspace, and fingerprint.
- `session-export.json` for OpenCode, or `raw-transcript.jsonl` for Claude.
- `evidence.json`: versioned, normalized tool input/result events.
- `transcript.md`: captured inputs and result summaries, not executor claims.
- `timing.json`: execution time, native usage components, and observed models.
- `work/` and `outputs/`: task repository and deliverables.

The evidence reader pairs tool inputs with results and orders OpenCode events by
their execution timestamps. Simultaneous results are valid; a cross-call input/result
tie cannot establish provenance. Unsupported logs, unfinished calls, ambiguous ordering,
and opaque Code Mode or subagent wrappers cannot support deterministic grading.
They stop the run rather than produce a successful verdict. Historical runs with
no native log retain their existing fallback behavior.

The compatibility token total sums input, output, cache-read, and cache-write
components. Reasoning is retained separately and is not added again. This formula
is recorded in the artifact; provider accounting can differ, so the total is not
a billing estimate. Model and variant are checked against every assistant message.
Use harness, version, model, and variant together when comparing results.

`make eval-test` checks the evidence and runner contracts without model calls.
`make eval-run` supports explicit repetitions, bounded parallel execution, and
resume of completed runs with matching fingerprints. Failed runs are retained;
use a new iteration to retry them. Skill, fixture, definition, and runner changes
invalidate the fingerprint.

`make eval-recover RUN=<run-directory>` can finish collection after a retained
OpenCode evidence-reader failure without another model call. It requires a completed
native session, verified model/usage, unchanged fixture HEAD, and task files not
modified after session completion. It preserves the original failure and records
the reader version in `recovery.json`. It does not recover provider errors or
overwrite collected files.

## Grading

Run `make eval-check` first. `make eval-grade` sends only pending assertions and
their context excerpts to the model. OpenCode graders have no tool permissions.
The runner validates every returned key and boolean before updating grading files.
Program verdicts remain unchanged. Missing or insufficient excerpts stop grading.

Grader evidence and usage are retained under `grader-batches/`. Per-run grader
usage is an equal share of its batch, recorded explicitly; executor time and tokens
remain separate. `make eval-finalize` removes residual context and requires final
boolean verdicts.

## Reporting boundary

`.agents/skills/skill-creator/` is an installed dependency and stays read-only.
The Makefile selects this local installation instead of requiring a Claude plugin
marketplace path. `evals/harness/reporting.py` owns benchmark validation and viewer
input preparation. It calls the unchanged upstream `embed_file` and `generate_html`
functions. It does not copy, patch, or write bytecode into the installed skill.

`make eval-benchmark` validates the complete pair and repeat set. Runner iterations
must have completed executors, matching fingerprints, observed models, native
evidence, usage, and final grades. Recorded model and token totals are checked
against native evidence. Paired prompts and assertions must agree.
Mixed harness/model/effort comparisons and incorrect grading summaries are rejected.
The primary configuration is first, and the delta is primary minus baseline.

Historical repeated and flat runs remain readable. Missing historical token or
time measurements are `null`, not zero or output-character counts. A summary
metric remains unknown if any run lacks a measurement, so a partial average cannot
hide an expensive missing run. Historical reports state their metadata limits.
Use `PRIMARY=new_skill BASELINE=old_skill` when those are the comparison labels.

`make eval-view` rebuilds the validated benchmark and writes a static `review.html`.
It does not start a server or terminate a process on an occupied port. `OPEN=1`
opens the file in the default browser. `PREVIOUS=<iteration-directory>` adds prior
outputs and any prior `feedback.json`. Run IDs remain compatible with upstream
feedback. Download the feedback from the static viewer and place `feedback.json`
in the iteration directory before the next review.

The adapter reads nested outputs and dotfiles, preserves their relative names,
and renders Dockerfiles, Makefiles, and HCL as text. It locates metadata at the eval
directory as well as at the run. Unknown summary measurements are omitted from
viewer input because the unchanged renderer expects numbers; the benchmark notes
explain the omission. Embedded JSON escapes HTML delimiters so task output cannot
close the viewer's script element.

## Live validation

`evals/k8s-catch-up/runs/iteration-25-opencode-smoke/` contains a completed HPA eval
pair on `openai/gpt-6.1-sol#low`. Both runs retained native tool evidence, usage,
and verified model selection. Program grading and residual model grading completed.
This checks execution compatibility; one task does not measure overall skill quality.

`evals/docker-pro/runs/iteration-4-opencode-sol/` contains all three Docker tasks,
each with and without the skill, on the same model. All six runs completed native
collection, program grading, residual grading, and report validation. One collection
failure was recovered from retained evidence after fixing simultaneous-result
timestamps; no replacement model call was needed. The average task pass rate was
84.3% with the skill and 41.2% without it. Each task has one repeat, so these results
are preliminary, not a stable quality estimate. The static viewer was checked in
a browser for file content, configuration order, grades, and benchmark values.

Full OpenCode suites also completed for GitHub Actions, super-linting, gha-audit,
and k8s-catch-up. Their final scores and run limits are in `README.md` and each
skill's `coverage.md`. Each task has one repeat; repeatability remains untested.

The Claude adapter, dashboards, and description-trigger optimization remain
unvalidated. Description optimization still invokes `claude -p` inside the
installed skill-creator and needs a separate OpenCode adapter.
