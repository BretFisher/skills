---
name: super-linting
description: Set up local development linting by picking the right linters for each file type a project uses, then recording them as required pre-commit checks in AGENTS.md / CLAUDE.md and a `make lint` target. Uses the linters the super-linter project runs for each language, with local install and run commands for every one. Use this skill whenever the user wants to add, choose, configure, or standardize linters for local development; asks "what linter should I use for X"; wants the agent to lint files before committing; sets up AGENTS.md/CLAUDE.md linting rules; or mentions super-linter, linting setup, pre-commit linting, or keeping linters up to date. This is for LOCAL developer/agent linting, not for authoring CI workflows.
license: MIT
---

# Super-Linting: local linters for every file type

Pick one linter for each file type the project uses, and make those linters a required step before every
commit: a `## Linting` section in the project's agent guide, plus a `make lint` target a human can run.
The goal is a fast local loop that catches problems while code is written. CI workflows belong to the
`github-actions-workflow-pro` skill.

## Enforcement: the agent guide by default, a git hook only on request

"Lint before every commit" and "make them run before any commit" are met by the `## Linting` section and
`make lint`: that section is what makes every agent session lint before it commits. Add a git hook
(`.githooks/`, `core.hooksPath`, or a `.pre-commit-config.yaml`) only when the user names a git hook or a
pre-commit hook, because a hook changes how every commit works for every person on the repo. In all other
cases, finish the agent guide and `make lint`, then ask the hook question in step 6.

The linter choices come from the super-linter project's list of linters per language. This skill ships that
list with local install and run commands, and each reference file gives the date it was last checked.
Read the references for every linter choice, because they are the complete source for this skill.

## Workflow

### 1. Scope the file types

- Work in progress (files in `git status`, files the user is about to create): cover only those file types.
- A fresh setup for a repo: scan the tree and cover every file type in it.

Map files to languages with the table in [linter-commands.md](references/linter-commands.md). A file type
that table sends elsewhere is in [more-linters.md](references/more-linters.md); read that file only then.

### 2. Choose one primary linter per language

Use the `Primary` linter from the references (Python → `ruff`, Shell → `shellcheck`, Dockerfile →
`hadolint`, YAML → `yamllint`, Terraform → `tflint`). Name the other super-linter tools for that language
as optional extras and install none of them by default, because a wall of linters is the fastest way to get
linting abandoned. Name a formatter separately, because formatting and linting are different jobs.
Security scanners (Checkov, Trivy, zizmor) are extras for infrastructure-heavy repos.

### 3. Check what is installed, then ask before installing

Check each linter with `command -v <tool>`. For each missing one, show the install command from the
references; on macOS prefer Homebrew. Ask the user to confirm before you install anything, because
installs change their machine.

### 4. Write the linting contract into the agent guide

Edit `AGENTS.md` or `CLAUDE.md`, whichever exists (when one is a symlink, edit the real file). When
neither exists, ask whether to create `AGENTS.md`. Add or update this section, with one row per file type
the project uses:

```markdown
## Linting

Before committing, lint every file type you changed and fix what the linter reports, so problems are
caught locally. Commit only after the relevant linters pass. Run `make lint` to check everything at once.

| File type      | Linter     | Run                  |
| -------------- | ---------- | -------------------- |
| Python (`.py`) | ruff       | `ruff check <files>` |
| Shell (`.sh`)  | shellcheck | `shellcheck <files>` |

Optional extra linters for this project: <list, or "none">.
```

### 5. Add `make lint` and document it

Add a `lint` target to the `Makefile` (create one when there is none) that runs each primary linter across
the repo, and mention `make lint` in `README.md`. Match the existing Makefile and README style.

```makefile
.PHONY: lint
lint: ## Run all project linters
	ruff check .
	shellcheck $$(git ls-files '*.sh')
```

### 6. Summarize, then offer a git hook

Report the file types found, the linters chosen (primary and optional) and why, what is installed and what
still needs an install, and the files you edited. Then ask:

> "Linting is now in your agent guide and `make lint`. Do you also want a git pre-commit hook that blocks a commit when a linter fails, or is the agent guide and `make lint` enough?"

Add `.githooks/` and a `make hooks` target (or a `.pre-commit-config.yaml`) only when the user says yes,
because a hook changes how every commit works and the user did not ask for one.

## Done when

- [ ] The agent guide has a `## Linting` section that says to lint before committing, one row per file type in scope
- [ ] The `Makefile` `lint` target runs each primary linter, and `README.md` mentions `make lint`
- [ ] No installer ran without the user's yes, and each missing linter has its install command in the answer
- [ ] No git hook exists unless the user named one, and the answer ends with the hook question
