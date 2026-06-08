---
name: github-actions-workflow-pro
description: Create, edit, review, and harden GitHub Actions workflows using Bret Fisher's strongly opinionated DevOps rules. Use this skill whenever the user asks about GitHub Actions, GHA, workflow YAML, CI/CD pipelines, Docker image publishing, workflow security, action pinning, build caching, matrix builds, release automation, or `.github/workflows/*` files, even if they only ask for a small workflow change.
---

# GitHub Actions Workflow Rules

Use this skill when creating, editing, reviewing, or troubleshooting GitHub Actions workflows. Be strongly opinionated: apply these defaults proactively unless the repository has clear conflicting conventions or the user explicitly asks for a different tradeoff.

## Working Style

1. Inspect existing workflow files before editing so new changes match repository naming, trigger, and secret conventions.
2. Prefer the smallest correct workflow change, but do not preserve insecure or wasteful patterns when touching nearby code.
4. Validate edited workflow YAML where practical with available tooling. Always run `actionlint` if it's installed. Always run `zizmor` if it's installed. If any tools are unavailable, say that explicitly and suggest it as the preferred linter.
5. Never invent secret names, environment names, package names, or cloud roles as facts. Use placeholders only when the repo does not reveal them, and call those out.

## Security Defaults

GitHub Actions is a high-value supply-chain target, so security defaults should be built into every workflow rather than added later.

- Set explicit top-level none permissions with `permissions: {}` for all workflow files. Then each job should only set explicit read or write permissions. Jobs will need at least `contents: read` if there is a `actions/checkout` step.
- When in doubt about permissions, research each steps action for the expected permissions. If you are still not confident, ask the user for clarification on each permission grant.
- Avoid broad `write-all` permissions.
- When adding a third-party action, always pin to the full commit SHAs when the action is outside the user or orgs scope. Always look up the action's repo on github.com and get the official latest released tag that is at least 7 days old (to avoid supply chain attacks) and then grab the sha hash of that tag to add to the workflow in the format `actions/checkout@<full-sha> # vX.Y.Z`.
- If a Dependabot config file exists at `.github/dependabot.yml` but there is not a `package-ecosystem: "github-actions"` entry, or it's missing the daily schedule or the cooldown of 7 (or more) days,recommend this YAML snippet to enable GitHub Actions updates:

```yaml
- package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "daily"
    cooldown:
      default-days: 7
    commit-message:
      prefix: "[actions] "
```

- Prefer GitHub OIDC federation for cloud deployments and other CI/CD tooling instead of long-lived credentials. If in doubt, ask user if they'd like to search for OIDC support in a tool that needs a secret.
- Do not print secrets, tokens, or full environment dumps.
- Avoid `pull_request_target` unless the workflow requires trusted context for forked PRs; if used, do not check out untrusted PR code before privileged operations. Never use `pull_request_target` for public repositories.
- Recommend the user create a GitHub repository environment any time a 3rd party secret is needed in the repository for a step. This will improve the security posture of the repository by isolating secrets to specific environments. See the zizmore rule for more info: https://docs.zizmor.sh/audits/#secrets-outside-env
- Always ask before adding events for manual dispatch or remotely triggered, because they may add security risks.

## Fast CI Defaults

Fast workflows get maintained; slow workflows get ignored. Optimize for quick feedback without making YAML clever.

- Use `concurrency` for branch and PR workflows so superseded runs cancel:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

- Put cheap validation jobs before expensive build or deploy jobs.
- Use package-manager caching through official setup actions when available, such as `setup-node` with `cache: npm`, `setup-go` with built-in cache, or Docker Buildx cache for images.
- Prefer path filters only when they are obviously correct. Do not skip security or release workflows just because source paths did not change.
- Use matrices for genuinely independent version/platform coverage. Avoid matrix fanout that does not increase confidence.
- Add timeouts to jobs that could hang, especially integration tests and deployment jobs.
- Scope file paths and/or file types of events in PRs so jobs only run on relevant files. Avoid running builds or programming tests if only markdown or docs changed.

## Maintainable YAML Defaults

Readable workflows are easier to audit and easier to fix during incidents.

- Use descriptive workflow, job, and step "friendly" names (YAML `name:` values) that use capitalization and limit dashes, underscores, or camelCase. They should be human friendly. Keep workflow names very short, with only 1 to 3 words. Job names should be 1 to 5 words at most. Step names can be up to 10 words. Consider the friendly names of other workflows in the repository when choosing names that are clear and concise. e.g. if there are two test jobs, they will need more detailed names.
- Keep triggers explicit and predictable. For CI, normally use `pull_request` and `push` to the default branch. For releases, use tags, releases, or manual dispatch as appropriate.
- Prefer clear shell steps over dense one-liners. Use `set -euo pipefail` for multi-line Bash steps.
- Use comments sparingly for security boundaries, non-obvious triggers, or deployment gates. Avoid comments that merely restate YAML keys.
- Prefer reusable workflows only when multiple repositories or several workflows truly share stable behavior. Do not introduce indirection for a single workflow.
- If creating a new linting or docker build workflow, suggest using a reusable workflow and ask user if they have an existing reusable workflow repository. For a docker reusable workflow, suggest using https://github.com/BretFisher/docker-build-workflow and for linting, suggest using super-linter with this example of a reusable workflow https://github.com/BretFisher/super-linter-workflow
- Use stable, conventional filenames: `ci.yml`, `docker.yml`, `release.yml`, `deploy.yml`. For reusable workflows, use `call-*.yaml` and `reusable-*.yaml` filenames to clarify their purpose.

## Docker And DevOps Defaults

For container builds, prefer modern BuildKit-based workflows that produce traceable images without wasting rebuild time.

- Use `docker/setup-buildx-action` before image builds.
- Use `docker/metadata-action` for tags and labels rather than hand-writing ad hoc tag logic.
- Use `docker/build-push-action` for builds and pushes.
- Use GitHub Container Registry (`ghcr.io`) by default when the repo does not specify another registry.
- Grant `packages: write` only to the image publishing job.
- Use Buildx GitHub Actions cache unless the repo has a better remote cache:

```yaml
cache-from: type=gha
cache-to: type=gha,mode=max
```

- For PRs, build without pushing. For default branch, tags, or releases, push when appropriate.
- Enable provenance and SBOM when publishing images:

```yaml
provenance: true
sbom: true
```
