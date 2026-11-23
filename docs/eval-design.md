# Eval design: history, decisions, layout, and gaps

This document is for people who build or compare skill eval systems.
It tells why the evals in this repo work the way they do, what files each run makes, and what is not solved yet.
The [docs index](README.md) lists the other eval guides and defines the terms that this one uses.

## Goals

1. **Prove that each skill helps and does not hurt.** Each eval runs on the same model with the skill and without it. The gain is the difference.
2. **Keep a regression contract.** The eval definitions tell a reviewer what behavior must hold. Anyone can run them again after a change.
3. **Make a verdict repeatable.** A program decides each assertion that a program can decide. A model decides only the rest.
4. **Spend the fewest tokens and the least time per run.** Grading must not cost more than it needs to.
5. **Make results comparable.** Each result records the harness, the harness version, the model, and the effort. If one of these is unknown, you cannot compare the result with the next one.
6. **Be neutral to the harness.** The same definitions and grading files work for each agent harness that has an adapter.

## History

| Date (2026) | Change                                                                                                                                                                                                 | Why                                                                                                                                                                               |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| By Aug 26   | First `evals.json` for `github-actions-workflow-pro`, a coverage matrix, and one scanner assertion on every eval. A Claude Code session ran the skill-creator workflow with subagents.                 | The skill needed a test contract before more rules were added.                                                                                                                    |
| Aug 25–30   | Iterations 2 to 4 used `old_skill` as the baseline: a snapshot of the previous skill version.                                                                                                          | To see if a skill edit made the result better or worse.                                                                                                                           |
| Aug 31      | Iterations 7 and 8 used a true `without_skill` baseline on Sonnet and Haiku.                                                                                                                           | Only a no-skill run shows which rules the model follows without the skill. Those rules can be removed.                                                                            |
| Sep 5       | Eval definitions moved out of the skill folder to `evals/<skill>/`. Runs moved to `evals/<skill>/runs/`, which git ignores.                                                                            | Installers copy the whole skill folder. Users must not get eval files.                                                                                                            |
| Sep 9       | `checks.py` grades first, and a model grades only the null assertions. Then excerpts and batched grader calls.                                                                                         | Grader tokens went from 774k to 196k and grader time from 32 to 5.4 minutes on the same ten runs.                                                                                 |
| Sep 11      | Agent definitions in `.claude/agents/` pin the model and the effort of each executor and grader.                                                                                                       | The Agent tool has no effort parameter. A subagent otherwise gets the effort of the session.                                                                                      |
| Sep 19–30   | `k8s-catch-up` evals. Each run keeps the raw harness log (`raw-transcript.jsonl`), and process assertions read tool calls from that log. Eval names describe the task, not the thing under test.       | The transcript that an executor writes about itself was not reliable enough to grade. The executor can see its run path, and a name that told the test intent changed the result. |
| Oct 9–11    | Full suites on Haiku 5.5, Sonnet 5.5, and Opus 5.5.                                                                                                                                                    | Measure each skill on the current model family.                                                                                                                                   |
| Oct 12      | A repo-owned CLI runner (`evals/harness/`) with an OpenCode adapter. New files per run: `manifest.json`, `run.json`, `evidence.json`. Full suites on GPT-6.1 Sol.                                      | Subagents work only in Claude Code. A CLI runner can drive any harness and record what the harness really did.                                                                    |
| Oct 22      | First live run of the Claude Code adapter in the CLI runner.                                                                                                                                           | Bring Claude Code results into the same schema as OpenCode results.                                                                                                               |
| Nov 4       | The scanners run by default, and a program assertion that is still null never goes to a model. Seven hand-back assertions became program checks. The runner finds skills in `plugins/<group>/skills/`. | A model must not decide a scanner result. More program checks give repeatable verdicts.                                                                                           |
| Nov 6–22    | `k8s-podspec-pro` and `super-linting` ran on the Claude Code adapter.                                                                                                                                  | The CLI runner is now the default way to run evals for each harness.                                                                                                              |
| Nov 23      | `make eval-pull` copies runs from another clone, verifies each file, and deletes the remote copy.                                                                                                      | Runs made in a second clone stayed there, and git did not track them. See [Gaps](#gaps-and-plans).                                                                                |
| Nov 23      | `make eval-secrets` scans each run for secrets. `make eval-export` packs a copy to share, with personal identifiers replaced and the secret scan clean.                                                | Two old runs had printed a GitHub token and a session token. Runs also hold the account email, organization ID, and home paths.                                                   |

## Decisions

Each decision has its reason. A decision with no reason is hard to change safely.

1. **Definitions are committed. Run results are not.** `evals.json`, `fixtures/`, `checks.py`, and `coverage.md` are the contract, so they are in git. Runs are large, machine-specific, and made again on each run, so `runs/` is ignored. A curated `benchmark.md` can be committed as a scorecard.
2. **Paired runs on the same model.** The with-skill run and the without-skill run get the same prompt, fixtures, model, effort, tool policy, and grader. Only the skill is different, so the difference in score comes from the skill.
3. **Program first, model second.** Each assertion has a kind. A `program` assertion is decided by a key, a regex, a byte comparison, or an exit code. A `split` assertion has a program half that can fail it and a model half that judges the rest. A `model` assertion is judgment only. A program gives the same verdict each time, so a change in score means that the skill changed. `coverage.md` records the kind of each assertion.
4. **Write assertions as the literal that a program tests.** Name the key, the value, or the heading. This lets a program decide, and a reviewer sees exactly what must be in the file.
5. **The model grader gets excerpts in batches.** `checks.py` attaches only the excerpts that each null assertion needs. One grader call grades several runs, because each call has a fixed base cost of about 45k tokens.
6. **Pin the harness, the model, and the effort, and verify them.** The CLI runner takes an exact model ID and effort, and checks the model against each assistant message in the native log. The subagent workflow uses one agent definition per model and effort.
7. **Keep the native log, and normalize it.** Each run keeps the log that the harness wrote (`raw-transcript.jsonl` for Claude Code, `session-export.json` for OpenCode). `evidence.json` converts it to one event schema for each harness. Process assertions read tool inputs from this file, not from text that the executor wrote.
8. **Hash everything that can change a result.** `manifest.json` records hashes of the skill, the definitions, the runner, and each fixture. `make eval-benchmark` refuses an iteration if the assertion texts changed after the run, or if the runs mix harnesses, models, or efforts.
9. **Isolate the context, and say that it is not a sandbox.** The executor works in a temporary folder with a temporary home, and it can load only the target skill. The without-skill run can load no skill. Shell tools can still reach the host, so untrusted tasks need a container or a separate machine.
10. **Make each fixture repo safe and repeatable.** The runner commits the pristine fixtures as the first commit, with an eval identity, unsigned commits, and no hooks. The grader can then use `git show HEAD:<path>` to see the original.
11. **Do not edit the upstream skill-creator.** It is installed as a dependency and stays read-only. Repo-owned adapters in `evals/harness/` call its unchanged functions. An upstream update cannot then replace our validation.
12. **Use a cheap model first while you build an eval.** The first runs of a new rule mostly find bugs in the fixture, the assertion, or `checks.py`. Sonnet finds them for less cost than Opus. Use Opus when the eval is stable, and Haiku for the cheap-model pass.
13. **Publish a score only after a full suite.** A README row shows only the model and the two scores. The run details, limits, and partial results go in the skill's `coverage.md`.

## Current layout

```text
evals/
  eval.gitconfig                    eval identity, unsigned commits, no hooks (included by each fixture repo)
  harness/                          repo-owned runner, evidence reader, grading, reporting, pull, scrub, and their tests
  <skill>/                          COMMITTED
    evals.json                      prompts, fixture files, assertions
    fixtures/                       input files that an eval gives to the executor
    checks.py                       program grader
    coverage.md                     rule-to-assertion map, assertion kinds, notes for each iteration
    benchmark.md                    optional curated scorecard
    runs/                           IGNORED BY GIT
      iteration-<N>[-<label>]/      one iteration
        manifest.json               (runner) harness, version, model, effort, repeats, hashes, fixture map
        benchmark.json, .md         pass rate, time, and tokens for each configuration (mean, stddev, min, max)
        review.html                 static viewer page
        grader-batches/             model-grader prompts, evidence, and usage
        retry-provenance.json       (optional) which run was retried, from which iteration, and why
        grade.log                   (optional) output of the model-grading command
        eval-<id>-<name>/
          prompt.md                 the eval prompt
          eval_metadata.json        the prompt and the assertion texts at run time
          with_skill/ | without_skill/
            run-<k>/                one repeat
              executor-prompt.md    the exact prompt that the executor got
              work/                 the fixture repo that the executor changed
              outputs/              the answer and each changed file, with repo-relative paths
              raw-transcript.jsonl  native Claude Code log (session-export.json for OpenCode)
              transcript.md         readable form of the captured tool calls
              evidence.json         (runner) normalized tool inputs and results
              timing.json           duration, token usage, observed models
              grading.json          each assertion: text, passed, graded_by, evidence; and a summary
              run.json              (runner) status, fingerprint, harness, model, fixture commit
              effective-config.json (runner) effort and safety flags that the harness used
              cli-output.jsonl, cli-stderr.log   (runner) raw CLI streams
  _dashboard/                       IGNORED BY GIT: local report scripts and their HTML output
```

Files marked "(runner)" exist only in iterations that the CLI runner made.
Iterations from the subagent workflow (before October 2026) have no `manifest.json`, `run.json`, or `evidence.json`.
The `<label>` after the number is free text, for example `-opus55` or `-opencode-sol`.
`manifest.json` is the reliable record of the harness and the model.

### One iteration, from start to end

| Step | Command               | Model call | Result                                                        |
| ---- | --------------------- | ---------- | ------------------------------------------------------------- |
| 1    | `make eval-plan`      | no         | Validates the fixture maps and prints the plan                |
| 2    | `make eval-run`       | yes        | Executors write `work/`, `outputs/`, logs, and `timing.json`  |
| 3    | `make eval-check`     | no         | `checks.py` writes `grading.json` with nulls and excerpts     |
| 4    | `make eval-grade`     | yes        | A model grader fills the nulls from the excerpts              |
| 5    | `make eval-finalize`  | no         | Recomputes the summaries; fails if a null stays               |
| 6    | `make eval-benchmark` | no         | Validates the iteration and writes `benchmark.json` and `.md` |
| 7    | `make eval-view`      | no         | Writes `review.html`                                          |
| 8    | `make eval-pull`      | no         | Brings runs from another clone to this one (when needed)      |
| 9    | `make eval-export`    | no         | Packs a scrubbed, secret-scanned copy to share (when needed)  |

### What is the same for each harness, and what is different

| Same for each harness                                  | Different for each harness                           |
| ------------------------------------------------------ | ---------------------------------------------------- |
| `evals.json`, fixtures, `checks.py`, assertion kinds   | The native log format and how the adapter reads it   |
| `evidence.json` event schema                           | The usage fields in the native log                   |
| `grading.json`, `timing.json`, `benchmark.json` shapes | The flags that isolate the context and pin the model |
| Run folder names and the with/without pair             | How the skill is installed into the temporary home   |

Adapters exist for Claude Code and OpenCode.

## Gaps and plans

These problems are known. Each item tells what can go wrong today.

1. **An iteration ID is unique only on one machine.** `iteration-<N>` is a counter in each clone. Two machines can make two different `iteration-27` folders. Plan: give each iteration a globally unique ID (a timestamp and a random part) and keep `N` only as a display label.
2. **The manifest does not record the machine.** Two iterations from two machines look the same. Plan: record a machine ID and the OS in `manifest.json`.
3. **There is no central store for runs.** Runs stay in the clone that made them. If you delete a clone or a git worktree, its runs are deleted too, because git ignores them. `make eval-pull` is a temporary fix: it copies runs, checks each file's SHA-256, and only then deletes the remote copy. Plan: write runs to a store outside the clone, or keep an index of which runs exist and where.
4. **Labels in folder names repeat the manifest.** Labels like `-opus55` are not checked against `manifest.json`, and older iterations have no manifest. The Makefile's default `ITER` takes the highest number, so when two folders have the same number, the choice depends on the label text. Plan: select iterations by manifest fields, not by folder name.
5. **There are two schema generations.** The reporting code reads the subagent iterations with fallbacks and records unknown values as `null`. Plan: a one-time conversion that writes a minimal `manifest.json` for each old iteration from `coverage.md`.
6. **Only two harness adapters exist.** Codex, Cursor, GitHub Copilot, and Pi have no adapter yet. Each adapter needs a native-log reader that feeds `evidence.json`, model verification, and context isolation.
7. **Most results have one repeat.** The variance of a with/without pair is not measured for most cells. Plan: run `REPEAT=3` on the evals whose assertions changed result between iterations.
8. **The dashboards are legacy.** The scripts in `evals/_dashboard/` read the subagent layout and are not validated against the runner layout. `benchmark.json` and `review.html` are the validated reports.
9. **A changed assertion invalidates an iteration.** This is correct, but it means that a reworded assertion needs a new full run before the score can be published. Plan: version each assertion, so that an unchanged assertion keeps its results.
10. **History is prose.** The results of each iteration are in `coverage.md` as text. No machine-readable table shows the score of each skill, model, and harness over time. Plan: build that table from the `benchmark.json` files of the validated iterations.
11. **Description-trigger tests still use the upstream skill-creator.** They call `claude -p` and work only with Claude Code.

## Copy runs from another clone

Use this command when you run evals on a second machine that has its own clone of this repo:

```bash
make eval-pull REMOTE_HOST=<ssh host> REMOTE_REPO=<repo path on that host> DRY_RUN=1
```

- `REMOTE_HOST` is a host from your SSH config. `REMOTE_REPO` is absolute, or relative to the remote home.
- Each iteration gets the name `<remote name>-<SUFFIX>` on this machine, so it cannot collide with a local iteration. `SUFFIX` is the host name by default.
- The command copies with `rsync`, compares the SHA-256 of each file on both sides, and deletes the remote iteration only when all hashes match. `KEEP=1` keeps the remote copy.
- It skips an iteration that has a file changed in the last 60 minutes (`MIN_AGE=`), because that run can still be in progress.
- It stops on an iteration when a different local copy with the same name exists, and it keeps the remote copy.
- `SKILL=` and `ITER=` limit the command to one skill or one iteration. The remote needs `python3` and `rsync`.

## Share runs

Run data holds tool output and harness logs, so it can hold a credential or a personal identifier.
Two runs printed one before: a grader with `set -x` printed a GitHub token, and an executor printed the whole process environment.
Use these commands before you give runs to another person:

```bash
make eval-secrets
```

```bash
make eval-export
```

- `make eval-secrets` scans every run in place and changes nothing. It reads each file, and each object in the nested `work/.git` repos, because git compresses objects and a text search cannot see into them. It exits 1 on a finding.
- `make eval-export` copies the eval definitions, the harness, and the runs to `evals/_export/`. It leaves out the nested `.git` folders, because their commits hold author emails and cannot be edited in place.
- In the copy, it replaces email addresses (not example or `noreply` ones), home paths, account and organization IDs, and `USER` and `LOGNAME` values with placeholders such as `<email>` and `/Users/<user>`.
- It also replaces this machine's host name, and each line of `evals/.export-redact`, in file contents and in path names. That file is gitignored: put other machine names there, because the repo must not name them.
- It then scans the copy for secrets and for any identifier that is still there. It writes `skill-evals-<time>.tar.gz` only when that scan is clean. If not, it prints the findings masked and keeps the copy for you to examine.
- Both commands first plant fake secrets in a file and in a git commit, and stop if the scanner misses one. A scanner that finds nothing must prove that it can find something.
- Findings print only the first and last four characters and a short hash, so a full secret does not go into a terminal or a log.
- Not replaced: the `sessionId` of each Claude Code log line. It is a random ID for one session, not a person or an account.
- `EXPORT.json` in the tarball records the source commit, the skills, the file count, and the number of replacements of each kind.
