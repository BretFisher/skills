# Roadmap

Open work for this repo, in rough priority order. Done items move to the changelog in each PR, not here.

## Milestone: run the scanners from containers instead of installing them

**Why.** The `github-actions-workflow-pro` audit and validate steps run five scanners (`actionlint`, `zizmor`, `poutine`, `pinact`, `gasa`). Today the skill checks whether each is installed and, if not, asks the user whether to install it with Homebrew. Some users would rather not put five binaries on their machine to audit one repo; four of the five ship an official container image, so the skill can offer "run it in a container with the repo bind-mounted read-only" as the second answer to that question.

**Verified images (2026-08-25):**

| Tool       | Image                                                                                    | Example                                                                                                                                       |
| ---------- | ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| actionlint | `rhysd/actionlint:latest` (Docker Hub, official; docs/usage.md "Docker")                 | `docker run --rm -v "$PWD:/repo:ro" --workdir /repo rhysd/actionlint:latest -color`                                                           |
| zizmor     | `ghcr.io/zizmorcore/zizmor:latest` (official; docs/installation.md "Docker")             | `docker run --rm -v "$PWD:/src:ro" -e GH_TOKEN ghcr.io/zizmorcore/zizmor:latest --collect=all /src`                                           |
| poutine    | `ghcr.io/boostsecurityio/poutine:latest` (official; README)                              | `docker run --rm -v "$PWD:/repo:ro" ghcr.io/boostsecurityio/poutine:latest analyze_local /repo --format json --quiet --disable-version-check` |
| gasa       | `ghcr.io/bretfisher/gasa:latest` (official; README; pin `:vX.Y.Z`)                       | `docker run --rm -e GITHUB_TOKEN ghcr.io/bretfisher/gasa:latest run owner/repo --format json` (API-only, no mount needed)                     |
| pinact     | **none** (Homebrew core, aqua, mise, GitHub Releases binaries; Go, single static binary) | would need our image (below) or a generic Go/Alpine image plus the release tarball                                                            |

Pin image tags (or digests, per `docker-pro`) once the option lands; `latest` is only for the table above.

**Alternative: one image for the whole skill.** Instead of five `docker run` shapes, build a tiny image of our own (Alpine or a distroless base plus the five static binaries from their GitHub Releases, digest-pinned, with `gh` left on the host for auth) published to `ghcr.io/bretfisher/gha-tools`. One `docker run --rm -v "$PWD:/repo:ro" -e GH_TOKEN ghcr.io/bretfisher/gha-tools <tool> ...` covers every scanner, pinact included, and the image is where version pinning of the tools themselves lives. Cost: a release workflow and Dependabot/Renovate for the five upstreams; benefit: one thing to install, identical versions in CI (`make lint`) and on laptops.

**Scope.**

1. `references/audit.md` gate and `SKILL.md` Validate: when a scanner is missing, the question becomes "install with Homebrew, run from a container, or skip and report absent?" Prefer the container when Docker is running and the user has not said otherwise.
2. Extend `scripts/scan.sh` (exists since 2026-08-26; today it only sets the token inside its own process and exec's the local binary) to pick local binary or container per tool (per-tool images, or the single image above), bind-mount the repo read-only, and print the same output either way, so `audit.md` keeps calling one command per tool. Token handling stays inside the wrapper: `docker run -e GH_TOKEN …` with the variable _name only_ forwards the value from the wrapper's environment without putting it on the command line (verified: a `set -x` trace shows `-e GH_TOKEN`, the container sees the value), so the agent never sees the token in either mode. gasa in a container has no `gh` login to fall back on, so the wrapper pipes the token to `gasa run --token-stdin` there.
3. `make lint-actions` uses the same wrapper so `make lint` works on a machine with only Docker.
4. Eval: an audit run on a machine with no scanners installed but Docker present must still produce the full Tools section with versions.

**Not in scope.** Building our own images; running `gh` itself in a container (it stays local for auth).

## Milestone: action inventory with pin drift

**Why.** No scanner or update bot measures the gap between what a workflow pins and where the action's repo actually is. Dependabot and Renovate chase the latest tag; pinact resolves a ref to a SHA and checks the comment; zizmor's `archived-uses` catches only the formally archived case. The real-repo audits (2026-08-25) hit the gap twice: `docker-build-workflow`'s only tag was 264 commits and three years behind `main`, so `pinact --branch-to-tag` "fixed" a caller onto dead code with a clean exit, and `super-linter-workflow` has no tags at all. A latest tag that trails the default branch by months is a signal in its own right: a dying action, an owner who stopped releasing, or a repo where something is wrong, and a pin to it inherits whatever that is.

**Scope.**

1. `scripts/action-inventory.py` (stdlib + `gh`, like `run-stats.py`): for every `uses:` across the workflows in scope, one row: action, ref as written, resolved SHA, version comment, latest release tag, date of the pinned commit, date of the latest default-branch commit, and the deltas (commits and days) pinned→latest tag and latest tag→default branch. JSON and `--markdown`. Cache API calls per action; the same action appears in many files.
2. `references/audit.md` step 3 runs it and the report gains an **Actions** section: the table, plus a finding per action whose pinned version trails the latest release (with the release date) and per action whose latest tag trails the default branch by a long stretch (state the numbers; no fixed threshold, the reader judges against what the caller depends on). Interim rule, already in `security.md: pinned`: check `compare/<tag>...<default>` by hand before `--branch-to-tag`.
3. Evals: a fixture repo whose `uses:` lines include a current pin, a pin two releases behind, and a same-owner ref whose only tag is far behind; assertions on the table rows and on the two findings. Needs the live-repo eval harness noted in `evals/coverage.md`.

## Milestone: description trigger optimization

Run the skill-creator description loop (`scripts/run_loop.py`, 20 queries with near-miss negatives: Dockerfile questions, local lint setup, GitLab CI, Jenkins) on `github-actions-workflow-pro` once its content is stable. Never run yet.

## Milestone: finish the references split

`references/yaml-style.md` and `references/docker.md` for the two SKILL.md sections still inline, following the same branch test: inline what every task needs, disclose what only some reach.

## Small items

- This repo's `call-super-linter.yaml`: `filter-regex-exclude: ^\.agents/` never matches (super-linter tests the absolute `/github/workspace/` path); 5 of 5 recent runs are red. Fix: `(^|/)\.agents/`.
- `bretfisher/super-linter-workflow` has no tags, so callers can only pin a branch SHA that Dependabot cannot bump; tag releases there.
- A CLI eval runner (`claude -p` per eval, with and without the skill) would replace hand-spawned subagents; scope before building.
