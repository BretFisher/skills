# Bret's DevOps and \*Ops Skills

A bunch of skills for daily work in DevOps, grouped into plugins under `./plugins/<group>/skills/`.
The [`skills-devops`](skills-devops) and [`skills-utils`](skills-utils) symlinks at the repo root point to those folders.

## Install

Skills come in two plugins, so you can install only the group you want: `bretfisher-devops` and `bretfisher-utils`.

### Any agent, with `npx skills`

[`npx skills`](https://github.com/vercel-labs/skills) works with Claude Code, Codex, Cursor, OpenCode, Amp, and many other agents.
It asks which skills and which agents to install for. `gh skill install bretfisher/skills` also works.

Globally, for all your projects:

```bash
npx skills add bretfisher/skills -g
```

Per project, committed so your team gets the skills too (run it from the project root):

```bash
npx skills add bretfisher/skills
```

### As a plugin, per harness

A plugin install gets the whole group and updates with the marketplace.

**Claude Code:**

```text
/plugin marketplace add bretfisher/skills
/plugin install bretfisher-devops@bretfisher
/plugin install bretfisher-utils@bretfisher
```

To get every new commit automatically, open `/plugin`, go to **Marketplaces**, select `bretfisher`, and choose **Enable auto-update**.
If you installed the old `bretfisher-skills` plugin, run the `bretfisher-devops` install line once: updating the marketplace removes the old plugin.

**Codex:**

```bash
codex plugin marketplace add bretfisher/skills
codex plugin add bretfisher-devops@bretfisher
```

**GitHub Copilot CLI:**

```bash
copilot plugin marketplace add bretfisher/skills
copilot plugin install bretfisher-devops@bretfisher
```

**Cursor:** add `bretfisher/skills` as a plugin marketplace; it reads `.cursor-plugin/marketplace.json`.

**Pi:** `pi install git:github.com/BretFisher/skills` loads every skill.

## Skills

| Skill                                                                                       | Plugin              | Purpose                                                                                                                                                                                                                                    |
| ------------------------------------------------------------------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [`docker-pro`](plugins/devops/skills/docker-pro/SKILL.md)                                   | `bretfisher-devops` | Use it when you create or change a Dockerfile, `.dockerignore`, Bake file, or Compose file. It applies modern Docker and BuildKit features and security best practices from a Docker Captain.                                              |
| [`github-actions-workflow-pro`](plugins/devops/skills/github-actions-workflow-pro/SKILL.md) | `bretfisher-devops` | Use it when you create, edit, audit, or speed up a GitHub Actions workflow. It applies opinionated security and speed defaults.                                                                                                            |
| [`gha-audit`](plugins/devops/skills/gha-audit/SKILL.md)                                     | `bretfisher-devops` | Type `/gha-audit [file]` when you want a workflow audit now. It runs the audit path of [`github-actions-workflow-pro`](plugins/devops/skills/github-actions-workflow-pro/SKILL.md): scanners first, then a report and a proposed diff.     |
| [`k8s-catch-up`](plugins/devops/skills/k8s-catch-up/SKILL.md)                               | `bretfisher-devops` | Use it when you write Kubernetes manifests or Helm templates, run `kubectl`, or ask what a recent Kubernetes version can do. It teaches the agent the features that reached beta or GA after its training data ended (now v1.35 to v1.37). |
| [`super-linting`](plugins/devops/skills/super-linting/SKILL.md)                             | `bretfisher-devops` | Use it when you add, choose, or standardize linters for local development. It picks the right linter for each file type and adds them to a `make lint` target, so code is linted before each commit.                                       |
| [`screencapture-mac`](plugins/utils/skills/screencapture-mac/SKILL.md)                      | `bretfisher-utils`  | Use it when the agent must see a native macOS app or a desktop window. It captures the screen, a window, or a region. Web pages go to a browser automation tool.                                                                           |

## Does the skill help?

My goal is to prove that each skill helps and does not hurt.
In general, newer and larger models do better without a skill than older and smaller models.
But as of October 2026, each skill improved the result on every model tested.

To measure this, each eval prompt runs twice on the same model: once with the skill and once without.
The score is the share of checks that passed. The gain is the difference, in percentage points.

### [`github-actions-workflow-pro`](plugins/devops/skills/github-actions-workflow-pro/SKILL.md)

| Model       | Without skill | With skill | Gain |
| ----------- | ------------- | ---------- | ---- |
| Haiku 4.5   | 47%           | 81%        | +34  |
| Haiku 5.5   | 60%           | 98%        | +38  |
| Sonnet 5    | 59%           | 92%        | +33  |
| Sonnet 5.5  | 64%           | 95%        | +31  |
| Opus 5.5    | 62%           | 97%        | +35  |
| GPT-6.1 Sol | 53%           | 86%        | +33  |

Details: [`evals/github-actions-workflow-pro/coverage.md`](evals/github-actions-workflow-pro/coverage.md).

### [`k8s-catch-up`](plugins/devops/skills/k8s-catch-up/SKILL.md)

| Model       | Without skill | With skill | Gain |
| ----------- | ------------- | ---------- | ---- |
| Haiku 4.5   | 21%           | 100%       | +79  |
| Haiku 5.5   | 80%           | 100%       | +20  |
| Sonnet 5    | 74%           | 100%       | +26  |
| Sonnet 5.5  | 89%           | 96%        | +7   |
| Opus 5.5    | 91%           | 96%        | +5   |
| GPT-6.1 Sol | 90%           | 98%        | +8   |

Newer models know more, so the gain is smaller. Without the skill, a newer model still gets the stage of a feature (beta or GA, and in which version) and recent deprecations wrong.

Details: [`evals/k8s-catch-up/coverage.md`](evals/k8s-catch-up/coverage.md).

### [`docker-pro`](plugins/devops/skills/docker-pro/SKILL.md)

| Model       | Without skill | With skill | Gain |
| ----------- | ------------- | ---------- | ---- |
| Haiku 5.5   | 68%           | 96%        | +28  |
| Sonnet 5.5  | 56%           | 100%       | +44  |
| Opus 5.5    | 72%           | 100%       | +28  |
| GPT-6.1 Sol | 36%           | 100%       | +64  |

Details: [`evals/docker-pro/coverage.md`](evals/docker-pro/coverage.md).

### [`super-linting`](plugins/devops/skills/super-linting/SKILL.md)

| Model       | Without skill | With skill | Gain |
| ----------- | ------------- | ---------- | ---- |
| Haiku 5.5   | 41%           | 100%       | +59  |
| Sonnet 5.5  | 35%           | 100%       | +65  |
| Opus 5.5    | 35%           | 100%       | +65  |
| GPT-6.1 Sol | 6%            | 94%        | +88  |

Details: [`evals/super-linting/coverage.md`](evals/super-linting/coverage.md).

### [`gha-audit`](plugins/devops/skills/gha-audit/SKILL.md)

| Model       | Without skill | With skill | Gain |
| ----------- | ------------- | ---------- | ---- |
| Haiku 5.5   | 71%           | 100%       | +29  |
| Sonnet 5.5  | 71%           | 100%       | +29  |
| Opus 5.5    | 43%           | 100%       | +57  |
| GPT-6.1 Sol | 71%           | 100%       | +29  |

Details: [`evals/gha-audit/coverage.md`](evals/gha-audit/coverage.md).

[`screencapture-mac`](plugins/utils/skills/screencapture-mac/SKILL.md) has no evals yet.

## Makefile

`make help` lists everything, including the eval targets for agents. Tools are checked, never installed; a missing one prints its `brew install` formula.

| Target                                   | What it does                                                                          |
| ---------------------------------------- | ------------------------------------------------------------------------------------- |
| `make lint`                              | Pre-commit gate: the same linters CI runs, plus the scanners on this repo's workflows |
| `make fmt`                               | `prettier --write` on Markdown and JSON                                               |
| `make k8s-features [SINCE=… RELEASES=…]` | Print the Kubernetes features that reached beta or GA in a window                     |
| `make k8s-verify [STRICT=1]`             | Check every k8s-catch-up feature file against its upstream sources                    |
| `make k8s-check`                         | Exit 1 when a Kubernetes release newer than the skill exists                          |
| `make pin [FILES=…]`                     | Pin this repo's workflows with pinact                                                 |
| `make run-stats [RUNS=3] [REPO=…]`       | Rank a repo's workflows and jobs by duration over recent runs                         |

See [AGENTS.md](./AGENTS.md) for the repo conventions (also symlinked as `CLAUDE.md`). Open work is tracked in
[GitHub Issues](https://github.com/BretFisher/skills/issues), one label per skill.
