# Security reference

The full rule set behind the security lines of the SKILL.md checklist, each with the reason it exists and the scanner that detects a violation (actionlint, zizmor, poutine, gasa). Rules marked as detected are validated by running the tool, in the build path's Validate step and in an audit; your own reading is for the rules no tool covers. Read this when granting permissions, adding or pinning a third-party action, adding a secret or cloud credential, meeting `pull_request_target`, checking Dependabot, or writing the security section of an audit. GitHub Actions is a high-value supply-chain target: a workflow runs arbitrary code with a token, so these are defaults, not add-ons.

## Permissions: least-privilege

- Start every workflow with `permissions: {}` at the top level, then grant per job. The token starts with nothing, and each job's block documents exactly what it can touch, so a compromised step inherits only that job's grants. Default token permissions vary by org and repo setting; the empty block makes the workflow independent of them. Detected by zizmor `excessive-permissions`, gasa `workflows/workflow-permissions` and `write-all-permissions`.
- `actions/checkout` needs `contents: read`, even under `permissions: {}`. A job that only calls an API and never checks out can stay at zero grants.
- `actions/checkout` sets `persist-credentials: false` unless a later step in that job pushes or pulls with the token. By default it writes the token into `.git/config`, where any later step, cached artifact, or uploaded workspace can read it. Detected by zizmor `artipacked`, so leaving it out costs a validate-and-fix cycle every time.
- Look up each action's README for the permissions it needs before granting. When the README is silent and you are still unsure, ask the user about that specific grant rather than widening it. An unexplained `write` grant is how `write-all` creeps back in.
- When you meet `permissions: write-all` (or a broad top-level `write`), enumerate what each job actually does and replace it with per-job grants. The rewrite is the finding, so show the before and after.

## Third-party actions: pinned

- Pin every action outside the user's or org's scope to a full commit SHA with the version as a trailing comment: `uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`. Tags move; a SHA is immutable. The comment keeps the version readable for humans and lets Dependabot update the pin. Detected by zizmor `unpinned-uses` (missing SHA) and `ref-version-mismatch` (comment wrong or missing), gasa `workflows/action-version-pinning`, poutine `unpinnable_action`, and pinact `-check -verify-comment`.
- Choose a release that is at least 7 days old. Compromised releases are usually caught and yanked within days; the wait lets the ecosystem catch a bad one before this repo adopts it. pinact enforces this: `-update -min-age 7` skips releases inside the window, `-verify-min-age` flags existing pins that are inside it.
- `pinact` does the pinning; write the `uses:` line with the major you intend (`actions/checkout@v7`) and let the tool resolve it:

```bash
export GITHUB_TOKEN=$(gh auth token)          # unauthenticated API calls rate-limit fast
pinact run -update -min-age 7 <file>          # new or edited workflow: newest release at least 7 days old, SHA + comment
pinact run <file>                             # keep the version as written, just pin it (a specific older tag the user chose)
pinact run -check -verify-comment -min-age 7 -verify-min-age   # audit: report unpinned, wrong comments, too-fresh pins; edits nothing
```

`pinact run` without `-update` pins whatever the tag points at today, which can be a release from this week, so the `-update -min-age 7` form is the default for anything new. `pinact run -update` also crosses majors (v3 to v4) when the newest qualifying release is a new major; drop `-update` when the user wants to stay on the major they have.

- Keep the comment after a SHA pin to the version alone: `# v7.0.1`, nothing after it. Dependabot rewrites that comment when it bumps the SHA only when the comment is exactly the old version; with any other text on it (`# v7.0.1 # zizmor: ignore[artipacked]`, `# v7.0.1 # needed for release`) it bumps the SHA and leaves the comment as it was, on purpose, so the comment goes stale on the first update and zizmor `ref-version-mismatch` and pinact `-verify-comment` fire on every bump after that. When you meet extra text on a `uses:` line, recommend removing it: a note moves to a `#` line above the step, and a `# zizmor: ignore[...]` moves into `.github/zizmor.yml`, which zizmor reads from the repo root and which keeps the reason next to the exception (`rules.<audit>.ignore` takes `file.yml`, `file.yml:line`, or `file.yml:line:col`):

```yaml
# zizmor configuration: https://docs.zizmor.sh/configuration/
# Ignores live here, not as inline comments on SHA-pinned `uses:` lines,
# so Dependabot can keep rewriting the version comment.
rules:
  artipacked:
    # release.yml checkout must persist credentials: the release job pushes the tag.
    ignore:
      - release.yml
  unpinned-uses:
    # lint.yml calls our reusable super-linter workflow by @main; see the Hard finding.
    ignore:
      - lint.yml
```

No scanner flags the extra text itself; the damage shows up one Dependabot PR later, so this one is yours to check.

- Same-owner actions and reusable workflows may use a tag or a SHA. A branch ref such as `@main` is the one form to replace, whoever owns it: the branch moves on every push, so a compromise there runs here on the next event with no release step and no review in this repo in between. A reusable workflow multiplies that: every caller inherits the same moving target, so one bad push cascades into every downstream repo at once, each with its own permissions and secrets. Rate it high when the ref is a reusable workflow or a shared action; gasa says medium, the blast radius says otherwise. Detected by gasa `workflows/action-version-pinning` and zizmor `unpinned-uses`. When the repo has tags, `pinact run --branch-to-tag '^main$'` converts the branch to the latest stable tag's SHA. A clean pinact run proves the pin is immutable, not that it is current: check the distance first with `gh api repos/O/R/compare/<tag>...<default-branch> --jq .ahead_by`. A tag a handful of commits behind is the normal fix. A tag far behind (hundreds of commits, or older than the features the caller relies on; `docker-build-workflow`'s only tag was 264 commits and three years behind `main`) would pin the caller to code the owner no longer ships, so leave the ref as it is, report the branch ref as the finding with the distance, and give the user the two real options: the owner tags a current release, or the caller stays on the branch knowingly. No scanner or update bot measures this gap; Dependabot and Renovate chase the latest tag and never ask how far it trails the default branch.
- When the repo has no tags or releases, pinact reports "action can't be pinned" because there is nothing it can verify against. The fix is upstream: the owner tags a release (`gh release create v1.0.0 --generate-notes` in that repo), then `pinact run --branch-to-tag` pins every caller. Report the finding with the cascading reason and put that choice to the user. Hand-pinning the branch HEAD or adding an `ignore_actions` entry only quiets the tools: the pin fails `pinact -check` forever and Dependabot cannot bump it, and the ignore hides the finding from the one tool that tracks it.
- A repo can carry `.github/pinact.yaml` (`min_age`, `ignore_actions`, `rules`). Read it before reporting a pin: an `ignore_actions` entry means the owner recorded the decision, so quote its reason next to the finding. The finding stays in Hard, because the config changes who knows about the risk, not the risk.
- Dependabot keeps SHA pins current. If `.github/dependabot.yml` exists without a `github-actions` entry, or the entry lacks a daily schedule or a cooldown of at least 7 days, recommend the entry below (wrap it in `version: 2` / `updates:` when the file does not exist yet):

```yaml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "daily"
    cooldown:
      default-days: 7
    commit-message:
      prefix: "[actions] "
```

Without `cooldown`, Dependabot proposes the fresh SHA on release day and quietly undoes the 7-day rule. Detected by zizmor `dependabot-cooldown` (`--collect all`) and gasa `updates/update-tool-configuration`, `updates/update-tool-actions-cooldown`, `updates/update-tool-actions-pinning`.

## Credentials: OIDC over static secrets

- For cloud deploys and any tool that supports it, authenticate with GitHub OIDC federation: the job gets `id-token: write` and the cloud trusts the repo's identity. There is no long-lived key to leak, rotate, or find in a log. When a tool needs a secret and you are unsure whether it supports OIDC, offer to check its docs before adding the secret. No scanner judges the auth method; this one is yours to check.
- Scope each third-party secret to a GitHub repository environment and have the job declare `environment:`. The secret is then visible only to jobs that name that environment, and environment protection rules gate who can trigger them. Detected by zizmor `secrets-outside-env` (auditor persona): <https://docs.zizmor.sh/audits/#secrets-outside-env>.
- Pass secrets into the one step that uses them via `env:` and reference them as `$VAR` in `run:`. Print only derived, non-secret values (an image digest, a URL). Full `env` dumps and `set -x` in a step with secrets belong to debugging in a fork, not to a committed workflow. Partly detected: zizmor `unredacted-secrets` and `overprovisioned-secrets`, poutine `job_all_secrets`; a plain `echo $TOKEN` is yours to spot.

## Untrusted input: trusted context only

- Put any `${{ github.event.* }}` value (PR title, branch name, issue body, commit message) into `env:` and reference it as `"$VAR"` inside `run:`. Interpolating it directly into the script is shell injection by anyone who can open a PR. Detected by actionlint (script injection), zizmor `template-injection`, poutine `injection`.
- `pull_request` is the safe default for PRs: fork runs get a read-only token and no secrets.
- `pull_request_target` runs the base branch's YAML with a write token and secrets, so it exists for private repos where a fork PR genuinely needs trusted context (labeling, commenting). When it must be used, keep untrusted code out of the privileged job: check out `github.event.pull_request.head.sha` only in a separate job with zero grants, and gate the privileged job on a maintainer label. In a public repo, use `pull_request` and move the privileged work to a `workflow_run` follow-up. Detected by gasa `workflows/pull-request-target` (critical), zizmor `dangerous-triggers`, poutine `untrusted_checkout_exec`, `confused_deputy_auto_merge`, `default_permissions_on_risky_events`.
- Adding `workflow_dispatch` or `repository_dispatch` widens who can start a privileged run, so it is a decision for the user: ask before adding either. No scanner flags these triggers.
