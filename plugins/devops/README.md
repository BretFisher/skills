# Bret Fisher DevOps Skills

Opinionated DevOps and platform engineering skills from Bret Fisher, a Cloud Native Ambassador and Docker Captain. They help an agent write and review Dockerfiles and Compose files, GitHub Actions workflows, and Kubernetes pod specs, learn Kubernetes features newer than its training data, and set up local linting. Each skill is tested with evals that compare the agent with and without the skill.

This folder is the `bretfisher-devops` plugin from the [bretfisher/skills](https://github.com/BretFisher/skills) marketplace.
The repository also has the `bretfisher-utils` plugin.

## Skills

| Skill                                                                        | What it does                                                |
| ---------------------------------------------------------------------------- | ----------------------------------------------------------- |
| [`docker-pro`](skills/docker-pro/SKILL.md)                                   | Modern Dockerfiles, Compose, and Bake with BuildKit         |
| [`gha-audit`](skills/gha-audit/SKILL.md)                                     | Audit this repo's workflows and propose a fix diff          |
| [`github-actions-workflow-pro`](skills/github-actions-workflow-pro/SKILL.md) | Create, harden, and speed up GitHub Actions workflows       |
| [`k8s-catch-up`](skills/k8s-catch-up/SKILL.md)                               | Kubernetes v1.35 to v1.37 features newer than training data |
| [`k8s-podspec-pro`](skills/k8s-podspec-pro/SKILL.md)                         | Hardened pod spec recommendations for Kubernetes workloads  |
| [`super-linting`](skills/super-linting/SKILL.md)                             | Pick linters per file type and wire up make lint            |

## Install

In Claude Code:

```text
/plugin marketplace add bretfisher/skills
/plugin install bretfisher-devops@bretfisher
```

In any agent, with [`npx skills`](https://github.com/vercel-labs/skills):

```bash
npx skills add bretfisher/skills -g
```

The [repository README](https://github.com/BretFisher/skills#install) has the install steps for Claude Desktop, Codex, Cursor, GitHub Copilot, Pi, and other agents.

## License

MIT. See [LICENSE](https://github.com/BretFisher/skills/blob/main/LICENSE).
