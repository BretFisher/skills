# Roadmap

Open work for this repo, in rough priority order. Done items move to the changelog in each PR, not here.

## Milestone: run the scanners from containers instead of installing them

**Why.** The `github-actions-workflow-pro` audit and validate steps run four scanners (`actionlint`, `zizmor`, `poutine`, `gasa`). Today the skill checks whether each is installed and, if not, asks the user whether to install it with Homebrew. Some users would rather not put four binaries on their machine to audit one repo; every one of these tools ships an official container image, so the skill can offer "run it in a container with the repo bind-mounted read-only" as the second answer to that question.

**Verified images (2026-08-25):**

| Tool | Image | Example |
| --- | --- | --- |
| actionlint | `rhysd/actionlint:latest` (Docker Hub, official; docs/usage.md "Docker") | `docker run --rm -v "$PWD:/repo:ro" --workdir /repo rhysd/actionlint:latest -color` |
| zizmor | `ghcr.io/zizmorcore/zizmor:latest` (official; docs/installation.md "Docker") | `docker run --rm -v "$PWD:/src:ro" -e GH_TOKEN ghcr.io/zizmorcore/zizmor:latest --collect=all /src` |
| poutine | `ghcr.io/boostsecurityio/poutine:latest` (official; README) | `docker run --rm -v "$PWD:/repo:ro" ghcr.io/boostsecurityio/poutine:latest analyze_local /repo --format json --quiet --disable-version-check` |
| gasa | `ghcr.io/bretfisher/gasa:latest` (official; README; pin `:vX.Y.Z`) | `docker run --rm -e GITHUB_TOKEN ghcr.io/bretfisher/gasa:latest run owner/repo --format json` (API-only, no mount needed) |

Pin image tags (or digests, per `docker-pro`) once the option lands; `latest` is only for the table above.

**Scope.**

1. `references/audit.md` gate and `SKILL.md` Validate: when a scanner is missing, the question becomes "install with Homebrew, run from its container image, or skip and report absent?" Prefer the container when Docker is running and the user has not said otherwise.
2. A `scripts/scan.sh` wrapper that picks local binary or container per tool, bind-mounts the repo read-only, passes `GH_TOKEN`/`GITHUB_TOKEN` through only to zizmor and gasa, and prints the same JSON either way, so `audit.md` calls one command per tool regardless of how it runs.
3. `make lint-actions` uses the same wrapper so `make lint` works on a machine with only Docker.
4. Eval: an audit run on a machine with no scanners installed but Docker present must still produce the full Tools section with versions.

**Not in scope.** Building our own images; running `gh` itself in a container (it stays local for auth).

## Milestone: eval coverage for every checklist and done-when line

Map each SKILL.md checklist line, done-when item, and audit.md done-when item to at least one assertion in `evals/evals.json`, skipping rules a scanner already owns (those need no agent assertion; `make lint` and the Validate step prove them). Add fixtures and evals for the gaps: OIDC over static keys, deploy concurrency group, Dependabot snippet offer, `set -euo pipefail`, decisions-only interview, `node-version-file`, reusable-workflow offer, placeholder listing, audit Do-first and delivery-format question, run-stats skipped-with-reason.

## Milestone: description trigger optimization

Run the skill-creator description loop (`scripts/run_loop.py`, 20 queries with near-miss negatives: Dockerfile questions, local lint setup, GitLab CI, Jenkins) on `github-actions-workflow-pro` once its content is stable. Never run yet.

## Milestone: finish the references split

`references/yaml-style.md` and `references/docker.md` for the two SKILL.md sections still inline, following the same branch test: inline what every task needs, disclose what only some reach.

## Small items

- `wait-what` is missing from the README skill table.
- This repo's `call-super-linter.yaml`: `filter-regex-exclude: ^\.agents/` never matches (super-linter tests the absolute `/github/workspace/` path); 5 of 5 recent runs are red. Fix: `(^|/)\.agents/`.
- `bretfisher/super-linter-workflow` has no tags, so callers can only pin a branch SHA that Dependabot cannot bump; tag releases there.
- A CLI eval runner (`claude -p` per eval, with and without the skill) would replace hand-spawned subagents; scope before building.
