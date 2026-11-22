# Bret Fisher Utilities

Small developer utilities for coding agents from Bret Fisher. The screencapture-mac skill lets the agent take a screenshot of a native macOS app, a window, or a screen region, and then read the image, so it can see what you see after a build or a code change.

This folder is the `bretfisher-utils` plugin from the [bretfisher/skills](https://github.com/BretFisher/skills) marketplace.
The repository also has the `bretfisher-devops` plugin.

## Skills

| Skill                                                    | What it does                                           |
| -------------------------------------------------------- | ------------------------------------------------------ |
| [`screencapture-mac`](skills/screencapture-mac/SKILL.md) | Screenshot native macOS apps so the agent can see them |

## Install

In Claude Code:

```text
/plugin marketplace add bretfisher/skills
/plugin install bretfisher-utils@bretfisher
```

In any agent, with [`npx skills`](https://github.com/vercel-labs/skills):

```bash
npx skills add bretfisher/skills -g
```

The [repository README](https://github.com/BretFisher/skills#install) has the install steps for Claude Desktop, Codex, Cursor, GitHub Copilot, Pi, and other agents.

## License

MIT. See [LICENSE](https://github.com/BretFisher/skills/blob/main/LICENSE).
