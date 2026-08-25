# Security reference

The full rule set behind the security lines of the SKILL.md checklist, each with the reason it exists. Read this when granting permissions, adding or pinning a third-party action, adding a secret or cloud credential, meeting `pull_request_target`, checking Dependabot, or writing the security section of an audit. GitHub Actions is a high-value supply-chain target: a workflow runs arbitrary code with a token, so these are defaults, not add-ons.

## Permissions: least-privilege

- Start every workflow with `permissions: {}` at the top level, then grant per job. The token starts with nothing, and each job's block documents exactly what it can touch, so a compromised step inherits only that job's grants. Default token permissions vary by org and repo setting; the empty block makes the workflow independent of them.
- `actions/checkout` needs `contents: read`, even under `permissions: {}`. A job that only calls an API and never checks out can stay at zero grants.
- Look up each action's README for the permissions it needs before granting. When the README is silent and you are still unsure, ask the user about that specific grant rather than widening it. An unexplained `write` grant is how `write-all` creeps back in.
- When you meet `permissions: write-all` (or a broad top-level `write`), enumerate what each job actually does and replace it with per-job grants. The rewrite is the finding, so show the before and after.

## Third-party actions: pinned

- Pin every action outside the user's or org's scope to a full commit SHA with the version as a trailing comment: `uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`. Tags move; a SHA is immutable. The comment keeps the version readable for humans and lets Dependabot update the pin.
- Choose a release that is at least 7 days old. Compromised releases are usually caught and yanked within days; the wait lets the ecosystem catch a bad one before this repo adopts it.
- Run `scripts/pin-action.sh owner/repo` to do the lookup. It picks the newest release that passes the age rule, dereferences annotated tags, and prints the `uses:` value. Pass `@vX` to resolve a specific tag, `--line` for a paste-ready line, `--help` for the rest.
- Same-owner actions and reusable workflows may use a tag or a SHA. A branch ref such as `@main` is the one form to replace: it moves on every push to that repo, so a compromise there runs here on the next commit with no release step between (gasa reports this at medium).
- Dependabot keeps SHA pins current. If `.github/dependabot.yml` exists without a `github-actions` entry, or the entry lacks a daily schedule or a cooldown of at least 7 days, recommend:

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

  Without `cooldown`, Dependabot proposes the fresh SHA on release day and quietly undoes the 7-day rule.

## Credentials: OIDC over static secrets

- For cloud deploys and any tool that supports it, authenticate with GitHub OIDC federation: the job gets `id-token: write` and the cloud trusts the repo's identity. There is no long-lived key to leak, rotate, or find in a log. When a tool needs a secret and you are unsure whether it supports OIDC, offer to check its docs before adding the secret.
- Scope each third-party secret to a GitHub repository environment and have the job declare `environment:`. The secret is then visible only to jobs that name that environment, and environment protection rules gate who can trigger them. zizmor flags secrets used outside an environment: <https://docs.zizmor.sh/audits/#secrets-outside-env>.
- Pass secrets into the one step that uses them via `env:` and reference them as `$VAR` in `run:`. Print only derived, non-secret values (an image digest, a URL). Full `env` dumps and `set -x` in a step with secrets belong to debugging in a fork, not to a committed workflow.

## Untrusted input: trusted context only

- Put any `${{ github.event.* }}` value (PR title, branch name, issue body, commit message) into `env:` and reference it as `"$VAR"` inside `run:`. Interpolating it directly into the script is shell injection by anyone who can open a PR. zizmor's `template-injection` audit catches the direct form.
- `pull_request` is the safe default for PRs: fork runs get a read-only token and no secrets.
- `pull_request_target` runs the base branch's YAML with a write token and secrets, so it exists for private repos where a fork PR genuinely needs trusted context (labeling, commenting). When it must be used, keep untrusted code out of the privileged job: check out `github.event.pull_request.head.sha` only in a separate job with zero grants, and gate the privileged job on a maintainer label. In a public repo, use `pull_request` and move the privileged work to a `workflow_run` follow-up. gasa rates `pull_request_target` critical.
- Adding `workflow_dispatch` or `repository_dispatch` widens who can start a privileged run, so it is a decision for the user: ask before adding either.
