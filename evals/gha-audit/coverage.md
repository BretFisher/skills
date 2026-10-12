# Eval coverage

## OpenCode validation

Iteration `5-opencode-sol` ran both tasks on OpenCode v2.0.26 with
`openai/gpt-6.1-sol#low`, one pair per task. All four runs completed, deterministic
grading finished, and report validation passed. With skill: 7/7 assertions (100%);
without skill: 5/7 (71.4%). The runner installs the wrapper and its required
`github-actions-workflow-pro` dependency only in the with-skill configuration,
records the dependency hash, and uses the shared GitHub Actions fixtures in both
configurations. No skill changes were made. One repeat is a preliminary result.

`gha-audit` is a user-invoked wrapper: it runs the audit path of `github-actions-workflow-pro`. These
evals test only what the wrapper adds; the audit rules are covered in
`evals/github-actions-workflow-pro/coverage.md`. `eN#k` = eval N, assertion k (1-based). `checks.py`
decides every assertion from `git status` in the work repo, the report headings, and the raw log.

## Coverage map

| Skill part                                         | Assertions | Gap                                           |
| -------------------------------------------------- | ---------- | --------------------------------------------- |
| Leave workflow files untouched                     | e0#1 e1#1  | the "apply the fixes" follow-up is not tested |
| Produce the report in the audit template           | e0#2 e1#2  | —                                             |
| No argument: every file under `.github/workflows/` | e0#3       | —                                             |
| Argument: audit only the named file                | e1#3       | —                                             |
| Run the audit path (scanners)                      | e0#4       | non-discriminating, see below                 |

## Assertion kinds

| Eval    | Assertions | program | split | model |
| ------- | ---------- | ------- | ----- | ----- |
| e0      | 4          | 4       | 0     | 0     |
| e1      | 3          | 3       | 0     | 0     |
| **all** | **7**      | **7**   | **0** | **0** |

## Results

One run per arm. Executors: `eval-executor-sonnet-5-5-high` (iteration 1), `eval-executor-opus-5-5-medium`
(iteration 2), `eval-executor-haiku-5-5-high` (iteration 3). No model grader: every assertion is program.
Without the skill, the executor gets the same `/gha-audit …` text as a plain prompt.

| Iteration | Model      | With skill | Without skill |
| --------- | ---------- | ---------- | ------------- |
| 1         | Sonnet 5.5 | 7/7        | 5/7           |
| 2         | Opus 5.5   | 7/7        | 3/7           |
| 3         | Haiku 5.5  | 7/7        | 5/7           |

### Per assertion (with / without)

| Assertion | Sonnet 5.5 | Opus 5.5 | Haiku 5.5 |
| --------- | ---------- | -------- | --------- |
| e0#1      | ✓ / ✓      | ✓ / ✗    | ✓ / ✓     |
| e0#2      | ✓ / ✗      | ✓ / ✗    | ✓ / ✗     |
| e0#3      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |
| e0#4      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |
| e1#1      | ✓ / ✓      | ✓ / ✗    | ✓ / ✓     |
| e1#2      | ✓ / ✗      | ✓ / ✗    | ✓ / ✗     |
| e1#3      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |

## Non-discriminating assertions

e0#3, e0#4, and e1#3 passed without the skill on all three models. e0#4 cannot discriminate as written:
the executor prompt lists `actionlint` and `zizmor` as available tools, so every baseline runs them.
The skill's measured value is the report template (e0#2, e1#2) and, on Opus, keeping the workflow files
untouched (e0#1, e1#1): Opus without the skill edited the files in place.

## Open item from these runs

On Opus, `pinact --update` moved `actions/checkout` and `actions/setup-node` from v4 to v7 (a major
version jump). Both reports named the jump and gave the command to stay on v4. The rule to keep the
current major version belongs in `github-actions-workflow-pro` (pinning reference), not in this wrapper.
