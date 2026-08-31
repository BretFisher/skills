---
name: github-actions-workflow-pro
description: Create, edit, audit, and speed up GitHub Actions workflows using Bret Fisher's opinionated DevOps rules. Use it when the user asks to create a workflow or CI/CD pipeline, edit or add a job to an existing `.github/workflows/*` file (even a one-line change), review or harden a workflow for security, speed up slow CI, publish a container image from CI, automate releases, or mentions GHA, action pinning, or findings from gasa, zizmor, poutine, pinact, or actionlint, even if they don't say "GitHub Actions".
---

# GitHub Actions Workflow Rules

Apply these defaults proactively to every workflow you touch, unless the repository has a clear conflicting convention or the user asks for a different tradeoff. The rules exist because a workflow runs arbitrary code with a token: security is built in from the first line, and speed is what keeps a workflow maintained.

## Working Style

1. Inspect existing workflow files before editing so new changes match the repository's naming, trigger, and secret conventions.
2. Prefer the smallest correct change, and fix insecure or wasteful patterns in the code you are already touching.
3. Facts are yours to find (an action's SHA, its required permissions, whether a tool supports OIDC). Decisions are the user's (adding a manual trigger, choosing a registry, creating an environment): put each one to them and wait.
4. Use placeholders for secret names, environment names, package names, and cloud roles the repo does not reveal, and list every placeholder when you hand back.

## Building a workflow

- Ask only about decisions the repo cannot answer: deploy target, registry, whether a needed secret already exists. Everything else you infer from the repo: the runtime version comes from its version file (`.nvmrc`, `.python-version`, `go.mod`) or `engines`, the lint and test commands from its scripts.
- Use conventional filenames: `ci.yml`, `docker.yml`, `release.yml`, `deploy.yml`; `call-*.yaml` and `reusable-*.yaml` for reusable workflows.
- Write each third-party `uses:` with the major you intend (`actions/checkout@v7`), then run `scripts/scan.sh pinact run -update -min-age 7 <file>` to pin it to the newest release at least 7 days old (see **pinned** below).
- For a Docker build workflow, or a lint workflow in a repo with no linter of its own, offer a reusable workflow before writing a bespoke one and ask whether the user already has one: Bret's are <https://github.com/BretFisher/docker-build-workflow> and <https://github.com/BretFisher/super-linter-workflow>. A repo that already defines `npm run lint` or equivalent runs that.

## Auditing an existing workflow

When the user hands you workflows to review, harden, secure, or speed up, or asks what is wrong with their CI, read [audit.md](references/audit.md) and follow it. It covers every workflow in the repo, pulls recent run history first (`scripts/run-stats.py`: failures, and workflows and jobs ranked by duration), then the linters (`actionlint`, `zizmor`, `gasa`), sorts findings into correctness, hard, speed, and opinion, opens with a Do-first list, and asks how the user wants the report delivered.

## Checklist

Every workflow you create or edit meets these. The linked reference carries the full rule and its reason; read it when a line needs more than the summary.

- `permissions: {}` at the top level, then **least-privilege** grants per job. `actions/checkout` still needs `contents: read`, and sets `persist-credentials: false` unless a later step pushes with the token. → [security.md](references/security.md)
- Every third-party `uses:` is **pinned** to a full commit SHA with a `# vX.Y.Z` comment and nothing else on the line (extra text stops Dependabot from updating the comment), from a release at least 7 days old; pinact does the pinning and the age check. Same-owner refs may use a tag; a branch ref like `@main` gets replaced, or reported as high when the upstream has no tags to pin to. → [security.md](references/security.md)
- Cloud credentials come from OIDC (`id-token: write`), third-party secrets live in a repository environment the job names, and `${{ github.event.* }}` values reach `run:` only through `env:`. → [security.md](references/security.md)
- `pull_request` for PR triggers. `pull_request_target` appears only where external PRs cannot reach it: a repo whose pull request access is Collaborators only, or a private repo with the untrusted checkout isolated in its own zero-grant job; never in a public repo that accepts outside PRs. → [security.md](references/security.md)
- If `.github/dependabot.yml` exists, it has a `github-actions` entry with a daily schedule and a 7-day cooldown; recommend the snippet when it is missing. → [security.md](references/security.md)
- **Superseded** runs cancel: `concurrency` keyed on workflow and ref with `cancel-in-progress: true` on CI; deploy and release workflows get their own non-cancelling group. → [speed.md](references/speed.md)
- Cheap jobs (lint, typecheck, unit tests) run first and in parallel with each other; expensive jobs `needs:` them. → [speed.md](references/speed.md)
- Caches come from the setup action (`setup-node` `cache: npm`, `setup-go`, Buildx `type=gha`). `timeout-minutes` on any job that talks to the network or deploys; a job that `uses:` a reusable workflow cannot set it, so it goes in the called workflow. → [speed.md](references/speed.md)
- New CI workflows ship without path filters; add one later only when it is obviously correct and the workflow is not a required check. Security, release, and deploy workflows stay unfiltered. → [speed.md](references/speed.md)
- Manual and remote triggers (`workflow_dispatch`, `repository_dispatch`) are added only after the user says yes.

## Maintainable YAML

- Friendly `name:` values with capitals and spaces: workflow 1–3 words, job up to 5, step up to 10. Two test jobs need names that tell them apart. Match the style of the repo's other workflows.
- Triggers stay explicit: CI on `pull_request` and `push` to the default branch; releases on tags, releases, or manual dispatch (after asking). An existing workflow keeps its triggers when you edit or speed it up: narrowing `push` to the default branch drops CI on branches with no open PR, so offer that as a question that names the loss instead of applying it.
- Multi-line Bash steps start with `set -euo pipefail`; prefer several clear lines over one dense one.
- Comments mark security boundaries, non-obvious triggers, and deployment gates. YAML keys explain themselves.
- Reusable workflows earn their indirection when several workflows or repositories share stable behavior. One workflow stays inline.

## Container images

Publish images on **trusted refs** only (default branch, tags, releases), from two jobs: a build job that runs on `pull_request` with `contents: read` and `push: false`, and a publish job that runs on `push` to the default branch or a tag and is the only job with `packages: write`. A permission cannot depend on the event, so one job with `push: ${{ github.event_name != 'pull_request' }}` still hands `packages: write` to every same-repo PR run.

- `docker/setup-buildx-action`, then `docker/metadata-action` for tags and labels, then `docker/build-push-action`. On a PR, `metadata-action` yields `pr-N`, not a semver tag, which is what you want.
- `ghcr.io` unless the repo names another registry.
- `cache-from: type=gha` and `cache-to: type=gha,mode=max`. `provenance: true` and `sbom: true` when publishing.
- A deploy job that follows a build consumes the image by the digest the build job output (`build-push-action` `outputs.digest`, passed through job outputs), not by a tag: a tag can be re-pushed between build and deploy, a digest cannot, so the artifact that was scanned and tested is the artifact that ships.

## Validate

Run `actionlint`, `scripts/scan.sh zizmor` (the wrapper sets the token from your `gh` login inside its own process, so it never appears in a command, trace, or transcript; zizmor runs offline without it), `poutine analyze_local . --quiet --disable-version-check`, and `scripts/scan.sh pinact run -check -verify-comment -min-age 7 -verify-min-age` on every file you edited; fix what they report and run again until all four are clean. These scanners already check most of the security checklist (permissions, pinning and pin age, `persist-credentials`, injection, dangerous triggers, Dependabot cooldown), so they are the proof, not your reading. `gasa` audits a pushed repository through the API, so it belongs to the audit path, not to a local edit. Check `command -v` first; for a missing tool, ask whether to install it (`brew install actionlint shellcheck zizmor poutine pinact`) or skip it, and wait for the answer. Hand back only when the validators are clean or reported absent by name.

## Done when

- [ ] `actionlint`, `zizmor`, `poutine`, and `pinact -check` clean on every edited file, or reported absent by name; the two reports allowed to remain are a branch ref pinact cannot pin (listed as open with the upstream fix: tag a release) and zizmor `dangerous-triggers` on a `pull_request_target` kept for a stated reason
- [ ] Every job has a `permissions:` block and the workflow starts with `permissions: {}`
- [ ] Every third-party `uses:` is a full SHA with a version comment
- [ ] Every placeholder is listed for the user to confirm
- [ ] The hand-back states the reason for each opinionated default you applied, in one line each: why it applies here, not what it does
