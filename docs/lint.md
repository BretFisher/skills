# Lint

`make lint` runs every linter as one Dagger check in the module `.dagger/modules/lint`.
Dagger Cloud Checks run the same checks on each push and pull request, so a pass on your machine is a pass in CI.
You need Docker and the Dagger CLI (`brew install dagger/tap/dagger`).

```bash
make lint
```

```bash
make lint CHECK=prettier
```

The linter rules stay in `.github/linters/` (and `.shellcheckrc` at the root), so editors and native tools read the same files.

## The checks

| Check             | Tool and source                                 | What it reads                                                        |
| ----------------- | ----------------------------------------------- | -------------------------------------------------------------------- |
| `markdownlint`    | markdownlint-cli (npm)                          | All Markdown, with `.github/linters/.markdown-lint.yml`              |
| `prettier`        | prettier (npm)                                  | Markdown, JSON, and `.github` YAML; `make fmt` fixes the findings    |
| `yamllint`        | yamllint (pip)                                  | `.github/`, `plugins/`, and the eval fixtures                        |
| `shellcheck`      | `koalaman/shellcheck-alpine` image              | Every `*.sh` outside the fixtures; each script must be executable    |
| `python`          | `python:3.14-alpine` image                      | Byte-compiles every script, then runs the eval harness unit tests    |
| `plugins`         | `scripts/check-plugins.py` and check-jsonschema | Manifests, marketplaces, and plugin READMEs agree                    |
| `actionlint`      | `rhysd/actionlint` image                        | Repo workflows (when there are any) and the well-formed fixture ones |
| `merge-conflicts` | grep                                            | No conflict markers in any file                                      |
| `codespell`       | codespell (pip)                                 | Every file, with `.github/linters/.codespellrc`                      |
| `gitleaks`        | `ghcr.io/gitleaks/gitleaks` image               | Secrets in the working tree                                          |
| `trivy`           | `aquasec/trivy` image                           | Vulnerabilities, misconfigurations, and secrets                      |
| `checkov`         | `bridgecrew/checkov` image                      | Infrastructure-as-code rules                                         |

These are the linters that super-linter ran on this repo, plus the ones `make lint` already ran.
Super-linter also ran three more: `ENV` (no `.env` files remain), `JSON` (prettier already parses every JSON file), and `PRE_COMMIT` (this repo has no pre-commit config).
Super-linter's `BASH_EXEC` rule is now part of the `shellcheck` check.

This repo has no GitHub Actions workflows, so it does not run the tools that only read workflows: zizmor, poutine, and pinact.
actionlint stays, because the github-actions-workflow-pro evals need well-formed workflow fixtures.
If you add a workflow again, add those three checks back.

## Why it is fast

Each check starts from a pinned tool image or installs one pinned tool version, and only then adds the repo files.
Dagger caches every step by its inputs, so the tool layers stay cached and a file change reruns only the lint command.
`dagger.lock` records the digest of each image, so a tag cannot change under you.
`.git`, ignored files, and eval runs stay out of the source, so a new commit does not change the cache key of a check whose files did not change.

Measured on a Mac with a warm cache: all 15 checks in 10.5 seconds (before zizmor, poutine, and pinact were removed).
Super-linter took 2 minutes for each run when it worked.

## Add or change a linter

1. Change the tool version constant or the check function in `.dagger/modules/lint/src/lint/__init__.py`.
   A check is an `async` method with `@function` and then `@check`, and it returns `None`; a nonzero exit code fails it.
2. Update `.dagger/modules/lint/sdk/entrypoint/types.dang` for a new, removed, or renamed check, or for a changed docstring or argument.
   Each check is one `.withFunction(...)` block with `.withCheck`.
   This step is necessary because `dagger generate` fails with Dagger v1.0.0-beta.28 and python-sdk v1.6.0 or v1.8.0 (`a type pattern is the non-null type its arm binds`, from Dagger's `sdk-helpers`).
   When an upgrade fixes `dagger generate`, run it once and delete this step.
3. Run `dagger check -l --module lint` to see the check, then `make lint CHECK=<name>`.
4. If Dagger Cloud Checks select checks by name, turn on the new check there too.

Use plain path names in the `skip-path` list of `.github/linters/.checkov.yaml`, never regex characters such as `+`, `*`, `?`, `[`, or `]`.
Checkov 3.4 joins the characters of that list into one regex when it loads Terraform modules.
A quantifier then raises `re.error` in a forked worker, and checkov waits for that worker forever.
The skip path `evals/[^/]+/fixtures` caused this, and it stopped every super-linter run from 2026-09-25 until each one timed out after 6 hours.

## Dagger Cloud Checks

Cloud Checks replace the GitHub Actions workflow.
They run on Dagger Cloud engines, report each result to GitHub, and use the `dagger.lock` committed with the repo.
They must run only the `lint` module's checks: the `install-tests` checks need several minutes and the network, and the `python-sdk` `stale` check fails until `dagger generate` works.
For that, `dagger.toml` sets `check.skip = ["*"]` on `install-tests` and `python-sdk`, so `dagger check` with no filter selects only the 12 lint checks.
That skip also applies to `dagger check --module install-tests`, and env overlays and user-level config cannot change it, so `make test-install` calls those checks in script mode instead ([install-tests.md](install-tests.md)).

Set them up once, from the repo root, after the branch is pushed:

```bash
dagger cloud checks on
```

```bash
dagger workspace activity
```

`dagger cloud checks list` shows each run's checks and results for the current branch.
