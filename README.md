# Bret's DevOps and *Ops Skills

A bunch of skills for daily work in DevOps, found in ./skills/

Installable via `npx skills add https://github.com/bretfisher/skills --skill <skill-name>`

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
