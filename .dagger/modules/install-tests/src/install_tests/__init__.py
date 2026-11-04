"""Install this repo's skills into each agent harness, in a fresh Ubuntu container.

Each check installs a harness at its latest release, installs the skills the
way the README tells users to, and asks the harness which skills it loaded.
Upgrade checks start from what users have today (`old_ref`, default
`origin/main`) and update to the working tree, uncommitted changes included.

Inside the container, git rewrites every github.com/BretFisher/skills URL to a
local bare repo, so the real install commands run and nothing is pushed.
Harnesses that need a login before they install or list skills are left out.
"""

from __future__ import annotations

import datetime
import json
import re

from dagger import check, function, object_type
from dagger_clients.core import Container, Directory, Workspace, core

MARKETPLACE = "bretfisher"
REPO = "bretfisher/skills"

REPO_SETUP = r"""
git config --global --add safe.directory '*'
git config --global user.name eval
git config --global user.email eval@example.invalid
git config --global commit.gpgsign false
git config --global core.hooksPath /dev/null
git config --global protocol.file.allow always
git config --global init.defaultBranch main
for owner in BretFisher bretfisher; do
  for prefix in https://github.com/ git@github.com: ssh://git@github.com/; do
    for suffix in "" .git; do
      git config --global --add url.file:///srv/skills.git.insteadOf "$prefix$owner/skills$suffix"
    done
  done
done
cd /srv/src
git rev-parse --verify "$OLD_REF^{commit}" > /srv/old-ref
git add -A
git commit -q --allow-empty --no-verify -m "working tree under test"
git rev-parse HEAD > /srv/new-ref
git clone -q --bare --no-local /srv/src /srv/skills.git
cat > /usr/local/bin/set-main <<'EOF'
#!/bin/sh
# set-main old|new: point the served repo's default branch at that commit
git -C /srv/skills.git update-ref refs/heads/main "$(cat /srv/$1-ref)"
git -C /srv/skills.git symbolic-ref HEAD refs/heads/main
EOF
chmod +x /usr/local/bin/set-main
set-main new
"""

NPX_ADD = f"skills add {REPO} -a opencode -y --skill '*' >/dev/null 2>&1\n"
LOCK_NAMES = "python3 -c 'import json; print(\" \".join(json.load(open(\"skills-lock.json\"))[\"skills\"]))'\n"

INSTALLERS = {
    "claude": "curl -fsSL https://claude.ai/install.sh | bash",
    "codex": "npm install -g @openai/codex",
    "copilot": "npm install -g @github/copilot",
    "opencode": "curl -fsSL https://opencode.ai/install | bash",
    "pi": "npm install -g @earendil-works/pi-coding-agent",
    "npx-skills": "npm install -g skills",
}


def _diff(label: str, want: set[str], got: set[str]) -> str:
    if want == got:
        return ""
    parts = []
    if want - got:
        parts.append("missing " + ", ".join(sorted(want - got)))
    if got - want:
        parts.append("extra " + ", ".join(sorted(got - want)))
    return f"{label}: " + "; ".join(parts)


def _require(problems: list[str], notes: list[str]) -> None:
    """Print the notes to the check's log, then fail with every problem found."""
    for note in notes:
        print(note)
    problems = [p for p in problems if p]
    if problems:
        raise ValueError("\n".join(problems))


@object_type
class InstallTests:
    source: Directory
    old_ref: str

    @classmethod
    def create(cls, ws: Workspace, old_ref: str = "origin/main") -> InstallTests:
        return cls(
            source=ws.directory(
                "/",
                exclude=[
                    ".claude/worktrees",
                    "evals/*/runs",
                    "evals/_dashboard",
                    "**/node_modules",
                    "**/.venv",
                    "**/__pycache__",
                ],
            ),
            old_ref=old_ref,
        )

    @function
    def base(self) -> Container:
        """Ubuntu 26.04 with git, Node, and the repo served at its GitHub URLs."""
        return (
            core()
            .container()
            .from_("ubuntu:26.04")
            .with_env_variable("DEBIAN_FRONTEND", "noninteractive")
            .with_exec(["sh", "-c", "apt-get update -qq && apt-get install -y -qq "
                        "git curl ca-certificates nodejs npm python3 >/dev/null"])
            .with_env_variable("PATH", "/root/.local/bin:/root/.opencode/bin:"
                               "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin")
            .with_directory("/srv/src", self.source)
            .with_env_variable("OLD_REF", self.old_ref)
            .with_exec(["bash", "-euo", "pipefail", "-c", REPO_SETUP])
        )

    @function
    def harness(self, name: str) -> Container:
        """The base container with one harness installed at its latest release."""
        # Installs are cached per day; the date makes "latest" mean today's latest.
        return (
            self.base()
            .with_env_variable("LATEST_AS_OF", datetime.date.today().isoformat())
            .with_exec(["bash", "-euo", "pipefail", "-c", INSTALLERS[name] + " >/dev/null 2>&1"])
            .with_workdir("/work")
        )

    async def _expected(self) -> dict[str, set[str]]:
        """Plugin name to skill names, from the working tree's marketplace file."""
        marketplace = json.loads(await self.source.file(".claude-plugin/marketplace.json").contents())
        plugins = {}
        for plugin in marketplace["plugins"]:
            if "skills" in plugin:
                names = {path.rstrip("/").rsplit("/", 1)[-1] for path in plugin["skills"]}
            else:
                root = plugin["source"].removeprefix("./").rstrip("/")
                skills = self.source.directory(f"{root}/skills" if root else "skills")
                names = {entry.rstrip("/") for entry in await skills.entries()}
            plugins[plugin["name"]] = names
        return plugins

    async def _run(self, container: Container, script: str) -> str:
        return await container.with_exec(["bash", "-euo", "pipefail", "-c", script]).stdout()

    # Claude Code ---------------------------------------------------------

    @staticmethod
    def _claude_skills(details: str) -> set[str]:
        match = re.search(r"Skills \((\d+)\)\s*(.*)", details)
        return {s.strip() for s in match.group(2).split(",") if s.strip()} if match else set()

    @function
    @check
    async def claude_install(self) -> None:
        """Claude Code: each marketplace plugin installs exactly its own skills."""
        expected = await self._expected()
        script = f"claude plugin marketplace add {REPO} >/dev/null\n" + "".join(
            f"claude plugin install {p}@{MARKETPLACE} >/dev/null\n"
            f"echo '### {p}'; claude plugin details {p}@{MARKETPLACE}\n"
            for p in expected
        )
        out = await self._run(self.harness("claude"), script)
        sections = dict(re.findall(r"### (\S+)\n(.*?)(?=### |\Z)", out, re.S))
        _require([_diff(p, want, self._claude_skills(sections.get(p, "")))
                         for p, want in expected.items()], [])

    @function
    @check
    async def claude_upgrade(self) -> None:
        """Claude Code: an install from old_ref updates, then the README's install lines restore every skill."""
        expected = await self._expected()
        script = f"""
set-main old
claude plugin marketplace add {REPO} >/dev/null
old=$(python3 -c 'import json,sys; print(" ".join(p["name"] for p in json.load(sys.stdin)["plugins"]))' \
  < <(git -C /srv/src show "$(cat /srv/old-ref):.claude-plugin/marketplace.json"))
for p in $old; do claude plugin install $p@{MARKETPLACE} >/dev/null; done
echo "### old $old"
set-main new
claude plugin marketplace update {MARKETPLACE} >/dev/null
for p in $old; do claude plugin update $p@{MARKETPLACE} >/dev/null 2>&1 || echo "### update-failed $p"; done
echo "### after-update"; claude plugin list --json | python3 -c 'import json,sys; print(" ".join(p["id"] for p in json.load(sys.stdin)))'
""" + "".join(
            f"claude plugin install {p}@{MARKETPLACE} >/dev/null\n"
            f"echo '### {p}'; claude plugin details {p}@{MARKETPLACE}\n"
            for p in expected
        ) + "echo '### final'; claude plugin list --json | python3 -c " \
            "'import json,sys; print(\" \".join(p[\"id\"] for p in json.load(sys.stdin)))'\n"
        out = await self._run(self.harness("claude"), script)
        old = re.search(r"### old (.*)", out).group(1).split()
        after = re.search(r"### after-update\n(.*)", out).group(1).split()
        final = set(re.search(r"### final\n(.*)", out).group(1).split())
        sections = dict(re.findall(r"### (\S+)\n(.*?)(?=### |\Z)", out, re.S))
        notes = [f"- installed from old_ref: {', '.join(old)}",
                 f"- installed after `claude plugin update`: {', '.join(after) or 'nothing'}"]
        notes += [f"- `claude plugin update {p}` failed" for p in re.findall(r"### update-failed (\S+)", out)]
        problems = [_diff(p, want, self._claude_skills(sections.get(p, ""))) for p, want in expected.items()]
        stale = {i for i in final if i.split("@")[0] not in expected}
        if stale:
            problems.append("old plugins still installed beside the new ones: " + ", ".join(sorted(stale)))
        _require(problems, notes)

    # Codex ---------------------------------------------------------------

    @function
    @check
    async def codex_install(self) -> None:
        """Codex: each plugin read from our marketplace gets only its own skills."""
        expected = await self._expected()
        script = f"codex plugin marketplace add {REPO} >/dev/null 2>&1\n" + "".join(
            f"codex plugin add {p}@{MARKETPLACE} >/dev/null 2>&1\n" for p in expected
        ) + f"cd /root/.codex/plugins/cache/{MARKETPLACE} && find . -name SKILL.md | sort\n"
        out = await self._run(self.harness("codex"), script)
        problems, notes = [], []
        for p, want in expected.items():
            paths = [line for line in out.splitlines() if line.startswith(f"./{p}/")]
            got = {m.group(1) for line in paths if (m := re.match(rf"\./{p}/[^/]+/skills/([^/]+)/SKILL\.md$", line))}
            problems.append(_diff(p, want, got))
            other = [line for line in paths if not re.match(rf"\./{p}/[^/]+/skills/[^/]+/SKILL\.md$", line)]
            if other:
                notes.append(f"- {p} also copied {', '.join(other)}")
        _require(problems, notes)

    # GitHub Copilot CLI --------------------------------------------------

    @function
    @check
    async def copilot_install(self) -> None:
        """Copilot CLI: each marketplace plugin loads exactly its own skills."""
        expected = await self._expected()
        script = f"copilot plugin marketplace add {REPO} >/dev/null\n" + "".join(
            f"copilot plugin install {p}@{MARKETPLACE} >/dev/null\n"
            f"echo '### {p}'; copilot skill list\n"
            for p in expected
        )
        out = await self._run(self.harness("copilot"), script)
        sections = dict(re.findall(r"### (\S+)\n(.*?)(?=### |\Z)", out, re.S))
        # Copilot prefixes a skill with "plugin:" only when two installed plugins share its name.
        # Unprefixed skills are credited to the plugin whose install added them.
        got: dict[str, set[str]] = {p: set() for p in expected}
        seen: set[str] = set()
        for p in expected:
            listing = sections.get(p, "").split("Plugin skills:", 1)[-1].split("\n\n", 1)[0]
            entries = re.findall(r"^  (?:([a-z0-9-]+):)?([a-z0-9-]+) - ", listing, re.M)
            for plugin, skill in entries:
                if plugin:
                    got.setdefault(plugin, set()).add(skill)
                elif skill not in seen:
                    got[p].add(skill)
            seen |= {skill for _, skill in entries}
        _require([_diff(p, want, got.get(p, set())) for p, want in expected.items()], [])

    # npx skills and OpenCode ---------------------------------------------

    @function
    @check
    async def npx_skills_install(self) -> None:
        """npx skills: installing every skill gets all of them, and OpenCode loads each one."""
        expected = set().union(*(await self._expected()).values())
        script = "git init -q\n" + NPX_ADD + "echo '### lock'; " + LOCK_NAMES + \
            "echo '### opencode'; opencode debug skill | python3 -c " \
            "'import json,sys; print(\" \".join(s[\"name\"] for s in json.load(sys.stdin) " \
            "if s[\"location\"].startswith(\"/work/\")))'\n"
        container = self.harness("npx-skills").with_exec(["bash", "-c", INSTALLERS["opencode"] + " >/dev/null 2>&1"])
        out = await self._run(container, script)
        lock = set(re.search(r"### lock\n(.*)", out).group(1).split())
        loaded = set(re.search(r"### opencode\n(.*)", out).group(1).split())
        _require([_diff("skills-lock.json", expected, lock),
                         _diff("opencode debug skill", expected, loaded)], [])

    @function
    @check
    async def npx_skills_upgrade(self) -> None:
        """npx skills: every skill installed from old_ref updates to the working tree's set."""
        expected = set().union(*(await self._expected()).values())
        script = "git init -q\nset-main old\n" + NPX_ADD + "echo '### old'; " + LOCK_NAMES + \
            "set-main new\nskills update -y >/dev/null 2>&1\n" + \
            "echo '### lock'; " + LOCK_NAMES + "echo '### dirs'; ls .agents/skills | tr '\\n' ' '; echo\n" + \
            "echo '### stale'; python3 -c 'import json,os; print(\" \".join(n for n,s in " \
            "json.load(open(\"skills-lock.json\"))[\"skills\"].items() " \
            "if not os.path.isfile(\"/srv/src/\"+s[\"skillPath\"])))'\n"
        out = await self._run(self.harness("npx-skills"), script)
        old = set(re.search(r"### old\n(.*)", out).group(1).split())
        lock = set(re.search(r"### lock\n(.*)", out).group(1).split())
        dirs = set(re.search(r"### dirs\n(.*)", out).group(1).split())
        stale = set(re.search(r"### stale\n(.*)", out).group(1).split())
        notes = [f"- installed from old_ref: {', '.join(sorted(old))}"]
        problems = [_diff("skills-lock.json after update", expected, lock),
                    _diff(".agents/skills after update", expected, dirs)]
        if stale:
            problems.append("skills-lock.json paths missing from the working tree: " + ", ".join(sorted(stale)))
        _require(problems, notes)

    # Pi ------------------------------------------------------------------

    @function
    @check
    async def pi_install(self) -> None:
        """Pi: `pi install git:github.com/BretFisher/skills` loads every skill."""
        expected = set().union(*(await self._expected()).values())
        script = "pi install git:github.com/BretFisher/skills >/dev/null 2>&1\n" \
            "echo '{\"type\":\"get_commands\",\"id\":\"1\"}' | timeout 60 pi --mode rpc --no-session | head -n 1\n"
        out = await self._run(self.harness("pi"), script)
        commands = json.loads(out)["data"]["commands"]
        got = {c["name"].removeprefix("skill:") for c in commands
               if c.get("source") == "skill" and "BretFisher/skills" in c["sourceInfo"].get("source", "")}
        _require([_diff("pi skills", expected, got)], [])
