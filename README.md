# Bret's DevOps and *Ops Skills

A bunch of skills for daily work in DevOps, found in `./skills/`

Installable via `npx skills add https://github.com/bretfisher/skills` and mark the ones you want to install. Add `-g` to command to install them globally.

## Skills

| Name | Purpose |
| --- | --- |
| `docker-pro` | Light up all the best docker features and security best practices for dockerizing a repo. From a Docker Captain. |
| `github-actions-workflow-pro` | Keeping your workflows safe and linted by an expert who teaches GH Actions. |
| `super-linting` | Picks the right linter for every file type in a project and wires them into a `make lint` target plus an agent-guide contract so code is linted before every commit. Focused on local developer/agent linting, not CI. |

## Repo layout

| Path | What | Committed? |
| --- | --- | --- |
| `skills/<name>/SKILL.md` | The skill itself | ✅ yes |
| `skills/<name>/evals/evals.json` | Eval **definitions** (prompts + assertions) — the test contract | ✅ yes |
| `.evals/<name>/iteration-N/` | Eval **run artifacts** (transcripts, gradings, timings, benchmarks) | ❌ gitignored |

### Skill evals

Eval *definitions* live next to each skill (`skills/<name>/evals/evals.json`) and are committed —
they document what each skill is supposed to do and let anyone re-run the evals to catch regressions.

Eval *run artifacts* (the output of executing those evals) are written to `.evals/<name>/iteration-N/`
at the repo root, which is gitignored. They're regenerated on every run and machine-specific, so they
aren't source of truth. When running the skill-creator eval loop, point its workspace at
`.evals/<name>/` rather than the default `<name>-workspace/` sibling.

See [AGENTS.md](./AGENTS.md) for the full convention (also symlinked as `CLAUDE.md`).
