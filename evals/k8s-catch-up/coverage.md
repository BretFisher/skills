# Eval coverage

Which assertion in `evals.json` proves each part of the skill, and what kind of check decides it.
`eN#k` = eval N, assertion k (1-based, order in `evals.json`). Grading is deterministic first
(AGENTS.md, "Deterministic checks before model judgment"): `checks.py` decides every assertion a regex
over the produced YAML, the answer, the transcript, or the work repo can decide, and leaves
`passed: null` with excerpts for the model grader. Kinds: **program** (decided by `checks.py`),
**split** (the program decides the mechanical half and can fail the assertion outright; the residual
goes to the model), **model** (judgment only).

## What the skill is and what the evals measure

The skill is knowledge, not rules: one file per feature under `references/<category>/` (twelve categories, removals included), linked from an index in `SKILL.md` that `k8s-features.py index` generates that describe the
features that reached beta or GA in v1.35 through v1.37. The knowledge evals (e0 to e10, and e13 for removals) each hand a
task that needs at least one of those features to a model whose reliable knowledge cutoff (Haiku 4.5,
Feb 2025) predates all three releases, and run it with and without the skill. A pass without the skill
means the model already knew the feature; a pass only with the skill is the skill's value. The two
updater evals (e11, e12) exercise `references/how-to-update.md` and `scripts/k8s-features.py` on the
first-run model (Sonnet 5) and run only with the skill, because the task has no meaning without it.

## Coverage map

First pass: one eval per category directory. The features each eval touches are named; every other feature
in that directory is a coverage gap until the per-feature eval set is generated from the script's table.

| Skill part                                            | Features exercised                                                         | Assertions              | Gap                                            |
| ----------------------------------------------------- | -------------------------------------------------------------------------- | ----------------------- | ---------------------------------------------- |
| `references/pods/`                                    | container restart rules, image volumes, env vars from a file               | e0#1 e0#2 e0#3 e0#4     | the other 10                                   |
| `references/workloads-autoscaling/`                   | per-HPA tolerance                                                          | e1#1 e1#2 e1#3          | the other 5                                    |
| `references/scheduling/`                              | gang scheduling (Workload API, `GenericWorkload` gate off)                 | e2#1 e2#2 e2#3          | the other 6                                    |
| `references/dra/`                                     | prioritized list, `resource.k8s.io/v1`                                     | e3#1 e3#2 e3#3          | the other 12                                   |
| `references/storage/`                                 | volume group snapshots                                                     | e4#1 e4#2 e4#3          | the other 7                                    |
| `references/networking/`                              | PreferSameNode traffic distribution                                        | e5#1 e5#2 e5#3          | the other 2                                    |
| `references/auth-security/`                           | Pod certificates                                                           | e6#1 e6#2 e6#3          | the other 7                                    |
| `references/api-admission/`                           | mutating admission policies GA                                             | e7#1 e7#2 e7#3          | the other 8                                    |
| `references/kubectl-cli/`                             | kuberc, KYAML                                                              | e8#1 e8#2 e8#3          | command metadata in HTTP headers               |
| `references/observability/`                           | `/statusz`, `/flagz` (beta since v1.36)                                    | e9#1 e9#2 e9#3          | the other 5                                    |
| `references/node-kubelet/`                            | CrashLoopBackOff max, imageMaximumGCAge, drop-in config dir                | e10#1 e10#2 e10#3       | the other 9                                    |
| `references/removals/`                                | gitRepo driver off, `externalIPs` deprecated, kube-proxy `ipvs` deprecated | e13#1 e13#2 e13#3 e13#4 | the other 4                                    |
| SKILL.md working style 4 (removals table, unprompted) | `externalIPs` in a normal Service task, an explicit `ipvs` request         | e14#1 e14#2 e14#3       | the other 5 table rows                         |
| SKILL.md working style 2 (say the stage and gate)     | gate off by default → caution                                              | e2#2 e6#3 e9#2          | not tested for on-by-default gates             |
| SKILL.md working style 3 (cluster version check)      | —                                                                          | —                       | no eval names a cluster older than the feature |
| `how-to-update.md` step 1 (window from cutoffs)       | Haiku 4.5 → Feb 2025 → v1.33+                                              | e11#1                   | non-Claude model lookup                        |
| `how-to-update.md` step 2 (`k8s-features.py table`)   | script run with the window                                                 | e11#2 e11#3 e12#2       | blog-gaps and inconsistent-kep.yaml triage     |
| `how-to-update.md` step 3 (write-up format)           | restored KYAML section: Status, example, Docs                              | e12#1 e12#4             | a brand-new release (no fixture yet)           |
| `how-to-update.md` step 4 (SKILL.md date and lists)   | Updated date, feature list line                                            | e12#3                   | Covers line                                    |
| `scripts/k8s-features.py` subcommands                 | table, kep, blog, docs                                                     | e11#2 e12#2             | releases, --format json, --include-alpha       |

## Assertion kinds

Output of `checks.py --kinds`; regenerate when `evals.json` or `checks.py` changes.

| Eval    | Assertions | program | split | model | split indices | model indices |
| ------- | ---------- | ------- | ----- | ----- | ------------- | ------------- |
| e0      | 5          | 4       | 0     | 1     | —             | #4            |
| e1      | 4          | 3       | 0     | 1     | —             | #2            |
| e2      | 4          | 2       | 2     | 0     | #2 #3         | —             |
| e3      | 4          | 4       | 0     | 0     | —             | —             |
| e4      | 4          | 3       | 0     | 1     | —             | #3            |
| e5      | 4          | 3       | 0     | 1     | —             | #3            |
| e6      | 4          | 3       | 0     | 1     | —             | #3            |
| e7      | 4          | 3       | 1     | 0     | #3            | —             |
| e8      | 4          | 4       | 0     | 0     | —             | —             |
| e9      | 5          | 4       | 1     | 0     | #2            | —             |
| e10     | 4          | 4       | 0     | 0     | —             | —             |
| e11     | 3          | 3       | 0     | 0     | —             | —             |
| e12     | 4          | 4       | 0     | 0     | —             | —             |
| e13     | 5          | 4       | 0     | 1     | —             | #4            |
| e14     | 4          | 4       | 0     | 0     | —             | —             |
| **all** | **62**     | **52**  | **4** | **6** |               |               |

## Non-discriminating assertions

Iteration 1 (2026-09-17, Haiku 4.5 high, one run per arm). An assertion that passed in both arms marks
knowledge the model already has, or a check that is too loose; one that passed only with the skill is
the skill's measured value.

| Eval | Passed in both arms                                                                                    | Passed only with the skill | Failed with the skill                                                                                                         |
| ---- | ------------------------------------------------------------------------------------------------------ | -------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| e0   | —                                                                                                      | #1 #2 #3 #4                | —                                                                                                                             |
| e1   | #2 #3 (HPA shape)                                                                                      | #1                         | —                                                                                                                             |
| e2   | #1 (names the API)                                                                                     | #2 #3                      | —                                                                                                                             |
| e3   | #2 (`resource.k8s.io/v1`, guessed)                                                                     | #1 #3                      | —                                                                                                                             |
| e4   | #1 #2 (kind, class, selector; the baseline guessed `v1`)                                               | #3                         | —                                                                                                                             |
| e5   | #2 (no old mechanism)                                                                                  | #1                         | #3: the write-up said "falls back to remote endpoints" and omitted the same-zone tier; fixed in `networking.md` after the run |
| e6   | —                                                                                                      | #1 #2 #3                   | —                                                                                                                             |
| e7   | —                                                                                                      | #1 #2 (#3 pending)         | —                                                                                                                             |
| e8   | — (#2 and #3 passed in both arms until the `kyaml` regex was tightened to the flag form; graded again) | #1 #2 #3                   | —                                                                                                                             |
| e9   | —                                                                                                      | #1 #2 #3                   | —                                                                                                                             |
| e10  | —                                                                                                      | #1 #2 #3                   | —                                                                                                                             |

The "both" cells are shape checks (the HPA skeleton, the DRA API version, the snapshot kind) that
anchor the eval rather than test new knowledge; keep them, but they do not count toward the skill's
value. No write-up is a deletion candidate from this pass.

### Iteration 2 (2026-09-19, after the shrink)

References cut from about 28,000 to 16,600 words; Unconfirmed sections removed; `removals.md` added; the
skill tells the agent to run `k8s-features.py show` before opening a file. Same prompts, same baseline
runs for e0 to e10 (copied), new e13 in both arms. Results: every with-skill assertion passed except
e9#3 (some curl examples lacked a client certificate; the grader also flagged the assertion as two
checks in one) and, before its wording was widened, e7#3 (namespace scoping through the policy's
`matchConditions` is a documented alternative to a binding selector, so the assertion now accepts
both). e5#3 passed after the PreferSameNode fallback fix. e13 passed 4 of 4 with the skill and 1 of 4
without: the baseline dated the gitRepo removal to v1.25 and invented a KubeProxyConfiguration API
version problem. The with-skill knowledge runs used about 5 percent fewer tokens and 10 percent less time than in iteration 1; the executors often read the whole category file anyway, so the `show` path is the next lever to enforce.

### Iteration 3 (2026-09-19, lookup path)

Question tested: does the agent use `k8s-features.py show` instead of reading a whole category file,
and can it name the feature well enough for `show` to find it? Changes: `show` matches on words (every
query word must appear in the heading, Where line, or first paragraph; a heading that holds every word
outranks body matches; a miss prints the nearest headings), `verify` fails unless every phrase listed
in SKILL.md resolves to exactly one section (95 of 95 do), SKILL.md step 1 tells the agent to copy a
phrase from the list into `show`, and a process assertion on every knowledge eval reads the transcript.

| Iteration | Runs that ran `show` before any file read | Mean tokens per with-skill run |
| --------- | ----------------------------------------- | ------------------------------ |
| 1         | 0 of 11 (no `show` yet)                   | 45,600                         |
| 2         | 2 of 12                                   | 43,300                         |
| 3         | 6 of 12                                   | 41,800                         |

The twelve queries the agents typed were either a SKILL.md phrase copied verbatim ("environment
variables from a file", "image GC by unused age") or a field or gate name ("PreferSameNode", "KYAML",
"gitRepo"); every one resolved. The six runs that still read a file first did so on their own habit,
not because `show` failed; the process assertion now records that per run, so the next lever (removing
the file links from the category paragraphs, or a stronger leading word) can be measured.

### Iteration 4 (2026-09-19, one file per feature)

Structure change: the twelve category files became 96 feature files under `references/<category>/`,
`SKILL.md` links every file from a generated index (`index --write`), `verify` checks Status claims
plus dead and unlinked files, and `show` is gone because the link is the lookup. The process
assertion now reads: only per-feature files were read, at most four.

| Iteration | Lookup path                                | Process assertion | Content assertions with skill | Mean tokens |
| --------- | ------------------------------------------ | ----------------- | ----------------------------- | ----------- |
| 3         | `show` named in SKILL.md, category files   | 6 of 12           | 2 failures (e4#3, e7#3)       | 41,800      |
| 4         | one file per feature, linked from SKILL.md | 12 of 12          | 0 failures                    | 41,500      |

Every run read exactly the feature files its task needed (one to three), named by the link text in
`SKILL.md`; no run read anything else. Both updater evals passed: the Sonnet updater restored the
deleted KYAML file, regenerated the index, and ran `verify --strict`, `index`, and `check` unprompted.
The token mean barely moved because the executor's fixed cost (system prompt, SKILL.md, writing the
answer) dominates; the saving shows in what was read, not in the total.

### Iterations 5 and 6 (2026-09-30, Sonnet 5 and Sonnet 5.5)

Question tested: how much of the skill a newer model already knows. Same skill as iteration 4, same twelve
knowledge prompts, both arms run again, no web access. Executors pinned to full model IDs
(`eval-executor-sonnet-5-high` = `claude-sonnet-5`, reliable cutoff Jan 2026;
`eval-executor-sonnet-5-5-high` = `claude-sonnet-5-5`, cutoff Jun 2026); residual grader
`eval-grader-sonnet-5-high`, the same model as iterations 1 to 4. Counts exclude the process assertion,
which the no-skill arm passes as vacuous.

| Model      | Iteration | Without skill | With skill | Process (with skill) | Mean tokens with / without | Mean seconds with / without |
| ---------- | --------- | ------------- | ---------- | -------------------- | -------------------------- | --------------------------- |
| Haiku 4.5  | 4         | 8/38          | 38/38      | 12/12                | 41,500 / 36,000            | 71 / 72                     |
| Sonnet 5   | 5         | 29/39         | 39/39      | 11/12                | 53,600 / 47,800            | 106 / 118                   |
| Sonnet 5.5 | 6         | 35/39         | 38/39      | 11/12                | 41,900 / 32,500            | 32 / 31                     |

Per-assertion result, by the iteration-1 table's columns:

| Eval | Sonnet 5: both arms | Sonnet 5: only with skill | Sonnet 5.5: both arms | Sonnet 5.5: only with skill | Sonnet 5.5: failed with skill |
| ---- | ------------------- | ------------------------- | --------------------- | --------------------------- | ----------------------------- |
| e0   | #1 #2 #3 #4         | —                         | #1 #2 #3 #4           | —                           | —                             |
| e1   | #1 #2 #3            | —                         | #1 #2 #3              | —                           | —                             |
| e2   | #1                  | #2 #3                     | #1 #3                 | #2 (gate off by default)    | —                             |
| e3   | #1 #2 #3            | —                         | #1 #2 #3              | —                           | —                             |
| e4   | #1 #2 #3            | —                         | #1 #2 #3              | —                           | —                             |
| e5   | #1 #2               | #3                        | #1 #2                 | #3 (GA in v1.35)            | —                             |
| e6   | #1 #2               | #3                        | #1 #2                 | #3 (GA in v1.37)            | —                             |
| e7   | #1 #2 #3            | —                         | #1 #2 #3              | —                           | —                             |
| e8   | #2 #3               | #1                        | #1 #2 #3              | —                           | —                             |
| e9   | #1 #4               | #2 #3                     | #1 #4                 | #2 (beta since v1.36)       | #3 (curl with `...` creds)    |
| e10  | #1 #2 #3            | —                         | #1 #2 #3              | —                           | —                             |
| e13  | #1                  | #2 #3 #4                  | #1 #2 #3 #4           | —                           | —                             |

What it shows:

- On Sonnet 5.5 the skill's measured value is four stage claims (e2#2, e5#3, e6#3, e9#2). The model
  knows the fields and kinds of every feature tested; what it gets wrong is the stage, and it hedges
  ("I believe beta", "unverified") where the skill states the stage. A Sonnet 5.5 build of the skill
  could keep the Status line of the e0, e1, e3, e4, e7, e8, e10, and e13 features and drop the field
  detail. These are trim candidates for a per-model build, not deletions: Haiku 4.5 still fails them.
- Sonnet 5 sits between the two: it fails the v1.36 and v1.37 removals (e13), kuberc (e8#1), and the
  same stage claims.
- The e9#3 miss is literal: one example in prose, `curl -sk ... https://<host>:<port>/metrics`, elides
  the credentials.

Grader fixes found by these runs, both checked against every stored run of the eval:

- e9#3 read a multi-line curl (`\` continuations) as "no curl command"; `checks.py` now joins the lines
  first. Only the Sonnet 5 with-skill verdict changed (fail to pass).
- e13#2 matched `deprecat`, `1.36`, and a replacement anywhere in the answer, so an answer saying
  externalIPs is "Not deprecated" passed. The claim must now sit with externalIPs in one paragraph or
  table row, not negated. Only the Sonnet 5 no-skill verdict changed (pass to fail).

Skill findings from the executors:

- Fixed: `references/storage/volume-group-snapshots.md` said GA in v1.36 but its example used
  `v1beta2`. external-snapshotter v8.6.0 (May 2026) serves `v1` with `v1beta2` as storage version;
  the example now emits `v1` and the text names the release.
- Fixed: the kuberc file covered only `credentialPluginPolicy`. It now gives the `defaults` and
  `aliases` shapes from the kuberc docs page, and its title (the index link text) names them; the
  example alias differs from eval 8's so the file teaches the shape, not the answer.
- Both Sonnet models read every removals file for e13 (seven and eight feature files), over the process
  assertion's limit of four. Sonnet 5.5 named them in shell brace form (`removals/{a,b}.md`), which
  `process_show` did not expand, so it passed; the check now expands braces, and only that verdict changed.

### Iterations 7 and 8 (2026-09-30, removals table inline)

Question tested: does the removals check run on every task once it costs no file read, and does it stop
reading every removals file? Before the change, removals files were opened on 0 of 11 non-removals tasks
on Haiku 4.5 and 2 of 11 on each Sonnet model, and both Sonnet models read every removals file for e13.

Changes: each removals file got an `**Instead:**` line; `k8s-features.py index --write` renders the
removals category as a table (Where, Instead, link) at the end of the `SKILL.md` index, and `verify`
reports a removals file without Instead; working-style step 4 says to match the output against the table
and open the file of each matching row only. New eval 14 (`bare-metal-edge-service-kube-proxy`): a
normal Service task whose natural answer is `externalIPs`, plus an explicit request for kube-proxy
`ipvs`; the prompt never asks for a review. All four of its assertions are program checks.

| Model     | Iteration | e14 without skill | e14 with skill | e13 files read (before -> after) | e0, e5 with skill    | Process     |
| --------- | --------- | ----------------- | -------------- | -------------------------------- | -------------------- | ----------- |
| Sonnet 5  | 7         | 0/3               | 3/3            | 7 -> 3                           | 4/4, 3/3 (unchanged) | 3/4 (e14#4) |
| Haiku 4.5 | 8         | 0/3               | 3/3            | 3 -> 3                           | 4/4, 3/3 (unchanged) | 4/4         |

- Without the skill both models write `externalIPs` and `mode: ipvs` with no warning; with it both
  avoid `externalIPs`, say it is deprecated in v1.36, and flag `ipvs` (deprecated v1.35) with
  `nftables` as the replacement, while still giving the requested ipvs config where asked.
- e13 now reads exactly the three matching removals files on both models.
- The Sonnet 5 e14#4 miss: five files read, two removals rows that matched plus three networking files
  it opened during step 1 and ruled out. The removals table did its job; step 1's "open every file that
  matches" is the source. One run, so recorded, not acted on.
- Tokens: Sonnet 5 e13 fell from 63,600 to 54,200 with four fewer reads. The Haiku runs fell 15 to 22
  percent on e0 and e5 as well, where behaviour did not change, so the cross-date token deltas are not
  attributed to the skill.

Harness findings in this round:

- The run path is visible to the executor. Eval 14's first name, `removals-unprompted-service-ipvs`,
  told the Haiku no-skill run what was tested: its answer was all "removals" with invented versions
  ("IPVS removed in 1.29") and passed e14#1 by the hint. The eval was renamed and all four first eval-14
  runs were discarded (kept under `runs/discarded/`) and rerun.
- `process_show` read the executor-written `transcript.md`, whose path format varies: Haiku listed bare
  basenames (a correct three-file run failed), Sonnet 5.5 used brace paths (an eight-file run passed).
  Each run now carries `raw-transcript.jsonl`, and `checks.py` reads only its tool-call inputs (Read
  paths, Bash commands), never tool results, because the result of reading `SKILL.md` holds every
  feature link. Rechecking 505 stored program verdicts changed only i8 e13#5 (False to True) in
  iterations 5 to 8.

## Planned: full per-feature coverage

`scripts/k8s-features.py table --format json` lists every feature the skill covers. The next pass
generates one eval per row (prompt: a task that needs the feature; assertion: the field, kind, flag,
or endpoint that exists only in that feature) so the coverage map above has no "the other N" cells.
Run it on Haiku 4.5 with and without the skill; the without-skill column is the model's baseline.
