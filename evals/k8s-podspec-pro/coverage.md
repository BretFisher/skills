# Eval coverage

Which assertion in `evals.json` proves each part of the skill, and what kind of check decides it.
`eN#k` = eval N, assertion k (1-based, order in `evals.json`). `checks.py` parses the produced manifest
with `yq` and greps the review and answer; it leaves `passed: null` with excerpts for the model grader.
Kinds: **program** (decided by `checks.py`), **split** (the program passes the assertion when one line
proves it and leaves the rest to the model), **model** (judgment only).

## Coverage map

| Skill part                                                | Assertions                           | Gap                                               |
| --------------------------------------------------------- | ------------------------------------ | ------------------------------------------------- |
| Read pod.yaml; teaching comments on floor fields          | e0#12                                | comments are checked only in e0                   |
| Working style 1 (nesting by kind)                         | e2 (CronJob), e3 (DaemonSet)         | StatefulSet, Job, raw Pod                         |
| Working style 2 (facts from the repo)                     | e0#5 (Dockerfile UID), e1#3 e4#4     | `EXPOSE` without a port in the prompt             |
| Working style 3 (decisions → TODO placeholders)           | e0#11                                | the bundled question when the user is present     |
| Working style 4 (edit brings the template to floor)       | e4                                   | —                                                 |
| Floor: image tag                                          | e0#1 e1#2 e2#2 e3#1 e4#1             | digest pins                                       |
| Floor: containerPort; no port on batch                    | e0#3 e2#5                            | —                                                 |
| Floor: readinessProbe; none on batch                      | e0#2 e1#3 e2#5 e3#5 e4#4             | `exec` probe for a portless long-running app      |
| Floor: livenessProbe never checks a dependency            | e1#12                                | —                                                 |
| Floor: resources and the QoS class                        | e0#7 e0#13 e1#4 e1#13 e2#8 e3#8 e4#7 | Guaranteed on request                             |
| Floor: container securityContext                          | e0#6 e1#6 e2#7 e3#6 e4#5             | `privileged: false` is not asserted               |
| Floor: seccomp and runAsNonRoot                           | e0#4 e1#5 e2#6 e3#6 e4#5             | —                                                 |
| Floor: named `USER` gotcha                                | e1#7                                 | —                                                 |
| Floor: hostUsers and its host-namespace exception         | e0#9 e1#9 e2#10 e3#2 e3#3 e4#6       | node requirements in the hand-back                |
| Floor: automountServiceAccountToken and the API exception | e0#10 e1#10 e2#11 e3#7 e4#2 e4#3     | —                                                 |
| Floor: enableServiceLinks and the env var search          | e0#10 e1#11 e2#10 e3#7 e4#6          | —                                                 |
| Floor: terminationGracePeriodSeconds                      | e0#8 e1#8 e2#9 e4#8                  | —                                                 |
| Floor: appArmorProfile                                    | —                                    | not tested                                        |
| Review: three headings, file unchanged, the why           | e1#1 e1#14 e1#15                     | the script run is not checked from the transcript |
| Hand-back: three headings                                 | e0#14 e2#12 e3#9 e4#9                | the content of each section                       |
| Batch settings (workload-kinds.md)                        | e2#1 e2#3 e2#4                       | `ttlSecondsAfterFinished`, `backoffLimit`         |
| Helm and Kustomize (workload-kinds.md)                    | —                                    | not tested                                        |
| Validate: floor-check.py clean                            | indirectly, by the floor rows        | the run of the script is not checked              |

## Assertion kinds

Output of `checks.py --kinds`; regenerate when `evals.json` or `checks.py` changes.

| Eval    | Assertions | program | split | model | split indices | model indices |
| ------- | ---------- | ------- | ----- | ----- | ------------- | ------------- |
| e0      | 14         | 14      | 0     | 0     | —             | —             |
| e1      | 15         | 14      | 0     | 1     | —             | #15           |
| e2      | 12         | 12      | 0     | 0     | —             | —             |
| e3      | 9          | 8       | 1     | 0     | #3            | —             |
| e4      | 9          | 8       | 1     | 0     | #3            | —             |
| **all** | **59**     | **56**  | **2** | **1** |               |               |

## History

The first draft of this skill and e0 to e2 were written in the podspec repo on 2026-10-07 and never
committed. Its iteration 1 ran one pair per eval on Sonnet 5.5 (88% without the skill, 100% with it),
but its benchmark header said three runs, and its audit eval scored 12/12 in both arms. Regraded with
this `checks.py` (scratch copy, fixtures differ for e1), the old with-skill answer called the floor's QoS
class `Guaranteed`, which the draft skill taught, and its CronJob had a readinessProbe. Both are fixed in
this skill and covered by e0#13, e1#13, and e2#5.

## Results

Share of all assertions passed, one run per cell. Harness: the repo runner through the Claude Code CLI
(`make eval-run HARNESS=claude MODEL=claude-sonnet-5-5 EFFORT=high`, Claude Code 2.1.319). Residual
grader: `claude-sonnet-5-5` at high effort (`make eval-grade GRADER_HARNESS=claude`).

| Iteration | Model      | With skill  | Without skill | Executor tokens (with / without) |
| --------- | ---------- | ----------- | ------------- | -------------------------------- |
| 2         | Sonnet 5.5 | 58/59 (98%) | 34/59 (58%)   | 523k / 244k                      |

Per eval, with / without: e0 14/14 vs 8/14, e1 14/15 vs 10/15, e2 12/12 vs 8/12, e3 9/9 vs 3/9,
e4 9/9 vs 5/9. Without the skill, Sonnet 5.5 never set `hostUsers`, `enableServiceLinks`, or the memory
limit equal to the request, kept the CPU limit in e4, and missed the `REDIS_PORT` clash in e1; it did
warn about the named `USER node`, avoid a livenessProbe on `/healthz`, and keep the controller's token.

The one with-skill failure (e1#15): the review's last item, a note that the resource numbers are
placeholders, gives no reason. e1#15 also fails without the skill because that review has no
`## Missing or wrong` heading, so e1#1 and e1#15 both depend on the heading; reword e1#15 to "each
finding in the review" before the next model is added.

Iteration 1 (same model and harness) is a development run and is not a result: the runner's Claude
evidence reader crashed on a `permission_denied` record whose `message` is a string (fixed in
`evals/harness/evidence.py`, with a test), so e0 with-skill was never collected. Graded from its kept
workspace, that run scored 14/14; the other nine matched iteration 2 within one assertion. Before
iteration 2, SKILL.md step 1 also started to send Job, CronJob, and DaemonSet work to workload-kinds.md.

Next: Opus 5.5 (`claude-opus-5-5`, medium) and Haiku 5.5 (`claude-haiku-5-5`, high) full suites.
