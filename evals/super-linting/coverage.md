# Eval coverage

## OpenCode validation

Iteration `5-opencode-sol` ran all three tasks on OpenCode v2.0.26 with
`openai/gpt-6.1-sol#low`, one pair per task. All six runs completed, final grading
was deterministic, and report validation passed. With skill: 16/17 assertions
(94.1%); without skill: 1/17 (5.9%). One skill failure remains: e0's answer omitted
the required hook question. No skill changes were made for this run.

The e1 checker initially missed TFLint and ShellCheck because `make lint` invoked
`bash scripts/lint.sh`. It now follows literal repository-local shell helpers;
four regression tests cover called, uncalled, dependency, and external-path cases.
Original grades are retained as `grading-before-helper-check-fix.json`.
One repeat is preliminary, and OpenCode's lack of automatic `CLAUDE.md` loading
limits comparison with the earlier Claude Code runs.

Which assertion in `evals.json` proves each part of the skill, and what kind of check decides it.
`eN#k` = eval N, assertion k (1-based, order in `evals.json`). `checks.py` decides every assertion: it
reads the agent guide, `Makefile`, and `README.md` in the work repo (outputs/ first), the answer, and
the commands in the raw log (heredocs and quoted strings stripped, so a command written into a file does
not count as executed). Kinds: **program**, **split**, **model**, as in the other skills.

## Coverage map

| Skill part                                   | Assertions          | Gap                                                    |
| -------------------------------------------- | ------------------- | ------------------------------------------------------ |
| Enforcement default: no git hook             | e0#6 e1#5           | —                                                      |
| Enforcement: offer the hook as a question    | e0#8                | not checked in e1 or e2                                |
| Step 1: decide scope (only the asked types)  | e1#3 e2#3           | —                                                      |
| Step 2: get linters from super-linter        | e0#5                | the offline fallback path is accepted but never forced |
| Step 3: primary + optional linters           | e0#2 e1#2 e1#4 e2#2 | —                                                      |
| Step 4: check installed, propose installs    | e0#7                | the case where every linter is already installed       |
| Step 5: `## Linting` contract in agent guide | e0#1 e1#1 e2#1      | —                                                      |
| Step 5: edit the existing guide, no second   | e2#1 e2#4           | —                                                      |
| Step 6: `make lint` target                   | e0#3 e1#3           | —                                                      |
| Step 6: document `make lint` in README       | e0#4                | —                                                      |
| Step 7: summary                              | —                   | content of the summary is not checked                  |
| `references/linter-commands.md`              | e0#7 (install cmds) | run commands per language                              |

## Assertion kinds

Output of `checks.py --kinds`; regenerate when `evals.json` or `checks.py` changes.

| Eval    | Assertions | program | split | model | split indices | model indices |
| ------- | ---------- | ------- | ----- | ----- | ------------- | ------------- |
| e0      | 8          | 8       | 0     | 0     | —             | —             |
| e1      | 5          | 5       | 0     | 0     | —             | —             |
| e2      | 4          | 4       | 0     | 0     | —             | —             |
| **all** | **17**     | **17**  | **0** | **0** |               |               |

## Results

One run per arm. Executors: `eval-executor-sonnet-5-5-high` (iteration 2), `eval-executor-opus-5-5-medium`
(iteration 3), `eval-executor-haiku-5-5-high` (iteration 4). No model grader: every assertion is program.

| Iteration | Model      | With skill | Without skill |
| --------- | ---------- | ---------- | ------------- |
| 2         | Sonnet 5.5 | 17/17      | 6/17          |
| 3         | Opus 5.5   | 17/17      | 6/17          |
| 4         | Haiku 5.5  | 17/17      | 7/17          |

### Per assertion (with / without)

| Assertion | Sonnet 5.5 | Opus 5.5 | Haiku 5.5 |
| --------- | ---------- | -------- | --------- |
| e0#1      | ✓ / ✗      | ✓ / ✗    | ✓ / ✗     |
| e0#2      | ✓ / ✗      | ✓ / ✗    | ✓ / ✗     |
| e0#3      | ✓ / ✗      | ✓ / ✗    | ✓ / ✗     |
| e0#4      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |
| e0#5      | ✓ / ✗      | ✓ / ✗    | ✓ / ✗     |
| e0#6      | ✓ / ✗      | ✓ / ✗    | ✓ / ✗     |
| e0#7      | ✓ / ✗      | ✓ / ✗    | ✓ / ✗     |
| e0#8      | ✓ / ✗      | ✓ / ✗    | ✓ / ✗     |
| e1#1      | ✓ / ✗      | ✓ / ✗    | ✓ / ✗     |
| e1#2      | ✓ / ✗      | ✓ / ✗    | ✓ / ✗     |
| e1#3      | ✓ / ✓      | ✓ / ✗    | ✓ / ✓     |
| e1#4      | ✓ / ✗      | ✓ / ✓    | ✓ / ✓     |
| e1#5      | ✓ / ✗      | ✓ / ✗    | ✓ / ✗     |
| e2#1      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |
| e2#2      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |
| e2#3      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |
| e2#4      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |

## Non-discriminating assertions

Passed without the skill on all three models: e0#4 and all of e2. In e2 the user names the file
(`CLAUDE.md`) and the language, so every model adds a ruff section to the existing file without help.
e2 measures nothing the skill adds; a stronger version would leave the file unnamed in a repo that has
both `AGENTS.md` and `CLAUDE.md`. Without the skill, the models add a `.pre-commit-config.yaml` or a git
hook and skip the super-linter lookup and the hook question; those are the skill's measured value.
