# Install tests

`make test-install` checks that the skills install correctly in each agent harness before a change to the repo layout is pushed.
It runs `dagger check --module install-tests` locally.
It never runs in GitHub Actions or Dagger Cloud.
You need Docker and the Dagger CLI (`brew install dagger/tap/dagger`).

## What runs

The module is at `.dagger/modules/install-tests/`, and each check is a function in its `__init__.py`.
Every check starts from Ubuntu 26.04 and installs one harness at that day's latest release.
It then installs the skills with the same commands the README gives users and asks the harness which skills it loaded.

| Check                | Harness                | What must hold                                                                                             |
| -------------------- | ---------------------- | ---------------------------------------------------------------------------------------------------------- |
| `claude-install`     | Claude Code            | Each marketplace plugin installs exactly its own skills (`claude plugin details`).                         |
| `claude-upgrade`     | Claude Code            | An install from `origin/main` updates, and the README's install lines leave every skill and no old plugin. |
| `codex-install`      | Codex                  | Each plugin's `skills/` holds only its own skills.                                                         |
| `copilot-install`    | GitHub Copilot CLI     | Each marketplace plugin loads exactly its own skills (`copilot skill list`).                               |
| `npx-skills-install` | `npx skills`, OpenCode | Installing every skill records all of them, and `opencode debug skill` loads each one.                     |
| `npx-skills-upgrade` | `npx skills`           | Skills installed from `origin/main` update to exactly the working tree's set.                              |
| `pi-install`         | Pi                     | `pi install git:github.com/BretFisher/skills` loads every skill (`pi --mode rpc`, `get_commands`).         |

The expected skills come from the working tree's `.claude-plugin/marketplace.json`.
A plugin entry with a `skills` list expects those skills; an entry without one expects every folder in `<source>/skills/`.

## How the repo is served

The working tree, uncommitted changes included, is committed inside the container on top of `HEAD` and cloned to a bare repo.
Git's `url.<base>.insteadOf` then points every `github.com/BretFisher/skills` URL at that bare repo.
That way `claude plugin marketplace add bretfisher/skills` and the other real commands run unchanged, and nothing is pushed.
Upgrade checks point the bare repo's `main` at `origin/main` first, install, then move `main` to the working tree and update.
After you push, `origin/main` equals the working tree and the upgrade checks only confirm an update with no changes.

## Harnesses left out

These need a login before they install or list skills, so they are not tested:

- **Amp** starts a browser login on `amp skill list`.
- **Cursor CLI** (`cursor-agent plugin`) needs `CURSOR_API_KEY` or `agent login`.
- **`gh skill`** reads the repo through the GitHub API, which needs a token.

The desktop apps (Claude desktop, the Cursor editor) and the macOS behavior of `screencapture-mac` cannot run in a Linux container.

## Running one check

```bash
dagger check --module install-tests --check=codex-install
```

Add `-i` to open a shell in the container when a command fails.
After editing `__init__.py`, run `dagger generate -y` once so Dagger reloads the module's function list.
