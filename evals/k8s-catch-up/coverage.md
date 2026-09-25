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

| Skill part                                          | Features exercised                                                         | Assertions              | Gap                                            |
| --------------------------------------------------- | -------------------------------------------------------------------------- | ----------------------- | ---------------------------------------------- |
| `references/pods/`                                  | container restart rules, image volumes, env vars from a file               | e0#1 e0#2 e0#3 e0#4     | the other 10                                   |
| `references/workloads-autoscaling/`                 | per-HPA tolerance                                                          | e1#1 e1#2 e1#3          | the other 5                                    |
| `references/scheduling/`                            | gang scheduling (Workload API, `GenericWorkload` gate off)                 | e2#1 e2#2 e2#3          | the other 6                                    |
| `references/dra/`                                   | prioritized list, `resource.k8s.io/v1`                                     | e3#1 e3#2 e3#3          | the other 12                                   |
| `references/storage/`                               | volume group snapshots                                                     | e4#1 e4#2 e4#3          | the other 7                                    |
| `references/networking/`                            | PreferSameNode traffic distribution                                        | e5#1 e5#2 e5#3          | the other 2                                    |
| `references/auth-security/`                         | Pod certificates                                                           | e6#1 e6#2 e6#3          | the other 7                                    |
| `references/api-admission/`                         | mutating admission policies GA                                             | e7#1 e7#2 e7#3          | the other 8                                    |
| `references/kubectl-cli/`                           | kuberc, KYAML                                                              | e8#1 e8#2 e8#3          | command metadata in HTTP headers               |
| `references/observability/`                         | `/statusz`, `/flagz` (beta since v1.36)                                    | e9#1 e9#2 e9#3          | the other 5                                    |
| `references/node-kubelet/`                          | CrashLoopBackOff max, imageMaximumGCAge, drop-in config dir                | e10#1 e10#2 e10#3       | the other 9                                    |
| `references/removals/`                              | gitRepo driver off, `externalIPs` deprecated, kube-proxy `ipvs` deprecated | e13#1 e13#2 e13#3 e13#4 | the other 4                                    |
| SKILL.md working style 2 (say the stage and gate)   | gate off by default → caution                                              | e2#2 e6#3 e9#2          | not tested for on-by-default gates             |
| SKILL.md working style 3 (cluster version check)    | —                                                                          | —                       | no eval names a cluster older than the feature |
| `how-to-update.md` step 1 (window from cutoffs)     | Haiku 4.5 → Feb 2025 → v1.33+                                              | e11#1                   | non-Claude model lookup                        |
| `how-to-update.md` step 2 (`k8s-features.py table`) | script run with the window                                                 | e11#2 e11#3 e12#2       | blog-gaps and inconsistent-kep.yaml triage     |
| `how-to-update.md` step 3 (write-up format)         | restored KYAML section: Status, example, Docs                              | e12#1 e12#4             | a brand-new release (no fixture yet)           |
| `how-to-update.md` step 4 (SKILL.md date and lists) | Updated date, feature list line                                            | e12#3                   | Covers line                                    |
| `scripts/k8s-features.py` subcommands               | table, kep, blog, docs                                                     | e11#2 e12#2             | releases, --format json, --include-alpha       |

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
| **all** | **58**     | **48**  | **4** | **6** |               |               |

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

## Planned: full per-feature coverage

`scripts/k8s-features.py table --format json` lists every feature the skill covers. The next pass
generates one eval per row (prompt: a task that needs the feature; assertion: the field, kind, flag,
or endpoint that exists only in that feature) so the coverage map above has no "the other N" cells.
Run it on Haiku 4.5 with and without the skill; the without-skill column is the model's baseline.
