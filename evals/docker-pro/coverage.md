# Eval coverage

Which assertion in `evals.json` proves each part of the skill, and what kind of check decides it.
`eN#k` = eval N, assertion k (1-based, order in `evals.json`). `checks.py` decides every assertion a
regex over the produced Dockerfile, `.dockerignore`, bake file, compose file, or answer can decide, and
leaves `passed: null` with excerpts for the model grader. Kinds: **program** (decided by `checks.py`),
**split** (the program decides the mechanical half and can fail the assertion outright; the residual
goes to the model), **model** (judgment only).

## Coverage map

| Skill part                                    | Assertions                   | Gap                                                                   |
| --------------------------------------------- | ---------------------------- | --------------------------------------------------------------------- |
| Dockerfile layout 1 (frontend directive)      | e0#1 e1#1 e2#1               | —                                                                     |
| Dockerfile layout 2 (global version ARGs)     | e0#2 e1#3                    | —                                                                     |
| Dockerfile layout 3 (FROM stages named, `AS`) | e0#2 e1#3                    | stage order (all FROMs at the top) is not checked                     |
| Dockerfile layout 4 (ENV near the top)        | —                            | not tested                                                            |
| Dockerfile layout 5 (BuildKit features)       | e1#4 (cache mount)           | secret mounts, bind mounts, `COPY --link`, heredocs, `ADD --checksum` |
| Base images: hardened by default              | e0#3 e1#2                    | DHI login path                                                        |
| Go example (`-dev` build, static final)       | e1#2 e1#6 e1#7               | —                                                                     |
| Pin every external image by digest            | e0#4 e1#5 e2#6               | `COPY --from=<image>` pins                                            |
| Always create a `.dockerignore`               | e0#5 e1#8 e2#7               | —                                                                     |
| Always add a bake file                        | e0#6 e1#8                    | not checked in the modernize eval                                     |
| Compose: ask on first-time setup              | e0#7                         | —                                                                     |
| Compose: `compose.yaml`, no `version:`        | e2#2 e2#3                    | —                                                                     |
| Compose: `develop.watch` over bind mounts     | e2#4 e2#5                    | `rebuild` and `sync+restart` actions                                  |
| Working style 2 (drop legacy patterns)        | e2#6 (`node:18`)             | —                                                                     |
| Working style 3 (no invented tags)            | e0#4 e1#5 (placeholder rule) | the rest of the rule is not tested                                    |
| Working style 4 / When you finish (the why)   | e0#9 e2#8                    | build and run commands                                                |
| Exec-form `ENTRYPOINT`/`CMD`                  | e0#8 e1#6                    | —                                                                     |

## Assertion kinds

Output of `checks.py --kinds`; regenerate when `evals.json` or `checks.py` changes.

| Eval    | Assertions | program | split | model | split indices | model indices |
| ------- | ---------- | ------- | ----- | ----- | ------------- | ------------- |
| e0      | 9          | 7       | 1     | 1     | #7            | #9            |
| e1      | 8          | 8       | 0     | 0     | —             | —             |
| e2      | 8          | 7       | 0     | 1     | —             | #8            |
| **all** | **25**     | **22**  | **1** | **2** |               |               |

## Results

One run per arm. Executors: `eval-executor-sonnet-5-5-high` (iteration 2), `eval-executor-opus-5-5-medium`
(iteration 3), `eval-executor-haiku-5-5-high` (iteration 4). Grader: `eval-grader-sonnet-5-high`.

| Iteration | Model      | With skill | Without skill |
| --------- | ---------- | ---------- | ------------- |
| 2         | Sonnet 5.5 | 25/25      | 14/25         |
| 3         | Opus 5.5   | 25/25      | 18/25         |
| 4         | Haiku 5.5  | 24/25      | 17/25         |

Iteration 4 note: the Go example in SKILL.md copied the binary from the empty `build` stage
(`COPY --from=build`); it was fixed to `FROM build AS compile` / `COPY --from=compile` while iteration 4
ran. Only e1 with-skill read the fixed version (its Dockerfile uses `compile`). The other runs used the
old example; no assertion checks the stage the binary comes from.

The one with-skill failure (iteration 4, e0#9): the answer described what `.dockerignore` excludes but
not why.

### Per assertion (with / without)

| Assertion | Sonnet 5.5 | Opus 5.5 | Haiku 5.5 |
| --------- | ---------- | -------- | --------- |
| e0#1      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |
| e0#2      | ✓ / ✗      | ✓ / ✓    | ✓ / ✓     |
| e0#3      | ✓ / ✗      | ✓ / ✗    | ✓ / ✗     |
| e0#4      | ✓ / ✗      | ✓ / ✓    | ✓ / ✓     |
| e0#5      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |
| e0#6      | ✓ / ✗      | ✓ / ✗    | ✓ / ✗     |
| e0#7      | ✓ / ✗      | ✓ / ✗    | ✓ / ✗     |
| e0#8      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |
| e0#9      | ✓ / ✗      | ✓ / ✗    | ✗ / ✗     |
| e1#1      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |
| e1#2      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |
| e1#3      | ✓ / ✗      | ✓ / ✗    | ✓ / ✗     |
| e1#4      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |
| e1#5      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |
| e1#6      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |
| e1#7      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |
| e1#8      | ✓ / ✗      | ✓ / ✗    | ✓ / ✗     |
| e2#1      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |
| e2#2      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |
| e2#3      | ✓ / ✗      | ✓ / ✗    | ✓ / ✓     |
| e2#4      | ✓ / ✓      | ✓ / ✓    | ✓ / ✗     |
| e2#5      | ✓ / ✓      | ✓ / ✓    | ✓ / ✗     |
| e2#6      | ✓ / ✗      | ✓ / ✓    | ✓ / ✓     |
| e2#7      | ✓ / ✓      | ✓ / ✓    | ✓ / ✓     |
| e2#8      | ✓ / ✗      | ✓ / ✓    | ✓ / ✓     |

## Non-discriminating assertions

Passed without the skill on all three models: e0#1 e0#5 e0#8 e1#1 e1#2 e1#4 e1#5 e1#6 e1#7 e2#1 e2#2
e2#7. These are the syntax line, `.dockerignore`, exec form, distroless final stage, Go cache mounts,
CGO off, and dropping `version:`. The models already know them. Keep the assertions as regression
anchors, and consider removing the matching SKILL.md lines to save tokens on every call. The skill's
measured value is the hardened base (e0#3), the bake file (e0#6, e1#8), asking about compose (e0#7), the
named-stage layout (e1#3), and the reasons in the hand-back (e0#9).
