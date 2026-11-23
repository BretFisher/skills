"""Lint this repo: one Dagger check per linter.

`make lint` runs every check here on your machine, and Dagger Cloud Checks run
the same functions on each push and pull request, so local and CI results match.

Each check starts from a pinned tool image (dagger.lock records its digest) or
installs one pinned tool version, and only then adds the repo files. The tool
layer therefore stays cached, and a file change reruns only the lint command.
Linter rules live in .github/linters/, so editors and native tools read the
same files.
"""

from __future__ import annotations

from dagger import check, function, object_type
from dagger_clients.core import Container, Directory, Workspace, core

# Pinned tool versions. Change a version here, then run `make lint` to test it.
MARKDOWNLINT_CLI = "0.50.0"
PRETTIER = "3.10.1"
YAMLLINT = "1.38.0"
CODESPELL = "2.4.3"
CHECK_JSONSCHEMA = "0.39.0"

NODE_IMAGE = "node:24-alpine"
PYTHON_IMAGE = "python:3.14-alpine"
SHELLCHECK_IMAGE = "koalaman/shellcheck-alpine:v0.11.0"
ACTIONLINT_IMAGE = "rhysd/actionlint:1.7.12"
GITLEAKS_IMAGE = "ghcr.io/gitleaks/gitleaks:v8.30.1"
TRIVY_IMAGE = "aquasec/trivy:0.76.2"
CHECKOV_IMAGE = "bridgecrew/checkov:3.4.5"

# Paths no linter reads: vendored upstream code and files Dagger generates.
VENDORED = [".agents", ".dagger/modules/*/sdk", ".dagger/modules/*/clients"]
# Eval fixtures are deliberately broken inputs that the evals ask an agent to fix.
FIXTURES = "evals/*/fixtures"

# The repo's own workflows, when it has any. Today there are none: Dagger Cloud Checks run the
# linters, so only actionlint stays, for the workflow fixtures the evals read.
WORKFLOWS = "$(find .github/workflows -name '*.y*ml' 2>/dev/null)"
GOOD_FIXTURE_WORKFLOWS = (
    "evals/github-actions-workflow-pro/fixtures/good-ci.yml "
    "evals/github-actions-workflow-pro/fixtures/good-ci-tagged.yml "
    "evals/github-actions-workflow-pro/fixtures/slow-ci.yml"
)
PRETTIER_FILES = (
    "'**/*.md' '**/*.json' '.github/**/*.y*ml' '!.agents/**' '!.dagger/modules/*/sdk/**' "
    "'!.dagger/modules/*/clients/**' '!CLAUDE.md'"
)


@object_type
class Lint:
    source: Directory

    @classmethod
    def create(cls, ws: Workspace) -> Lint:
        # gitignore=True drops eval runs, the dashboard, venvs, and caches.
        # .git stays out so a new commit does not change every check's cache key.
        return cls(
            source=ws.directory("/", gitignore=True, exclude=[".git", ".claude/worktrees", "**/node_modules"])
        )

    def _run(self, tools: Container, script: str) -> Container:
        """Add the repo after the tool layers, then run one shell script in it."""
        return (
            tools.with_directory("/src", self.source)
            .with_workdir("/src")
            .with_exec(["sh", "-euc", script])
        )

    def _node(self, *packages: str) -> Container:
        return (
            core().container().from_(NODE_IMAGE)
            .with_mounted_cache("/root/.npm", core().cache_volume("lint-npm"))
            .with_exec(["npm", "install", "-g", "--no-fund", "--no-audit", *packages])
        )

    def _python(self, *packages: str) -> Container:
        tools = (
            core().container().from_(PYTHON_IMAGE)
            .with_exec(["apk", "add", "--no-cache", "git", "bash", "yq-go"])
        )
        if packages:
            tools = tools.with_mounted_cache("/root/.cache/pip", core().cache_volume("lint-pip")).with_exec(
                ["pip", "install", "--root-user-action=ignore", *packages]
            )
        return tools

    # Markdown, JSON, and YAML -----------------------------------------------

    @function
    @check
    async def markdownlint(self) -> None:
        """markdownlint on all Markdown, with .github/linters/.markdown-lint.yml."""
        ignores = " ".join(f"--ignore '{p}/**'" for p in VENDORED)
        await self._run(
            self._node(f"markdownlint-cli@{MARKDOWNLINT_CLI}"),
            f"markdownlint -c .github/linters/.markdown-lint.yml '**/*.md' {ignores} --ignore CLAUDE.md",
        ).sync()

    @function
    @check
    async def prettier(self) -> None:
        """prettier --check on Markdown, JSON, and the .github YAML (`make fmt` fixes it)."""
        await self._run(self._node(f"prettier@{PRETTIER}"), f"prettier --check {PRETTIER_FILES}").sync()

    @function
    @check
    async def yamllint(self) -> None:
        """yamllint on .github, the skills, and the eval fixtures, with .github/linters/.yaml-lint.yml."""
        await self._run(
            self._python(f"yamllint=={YAMLLINT}"),
            f"yamllint -c .github/linters/.yaml-lint.yml .github/ plugins/ {FIXTURES}/",
        ).sync()

    # Shell and Python ----------------------------------------------------------

    @function
    @check
    async def shellcheck(self) -> None:
        """shellcheck on every shell script outside the fixtures; each script must be executable."""
        find = "find . -name '*.sh' -not -path './evals/*/fixtures/*' -not -path './.agents/*'"
        await self._run(
            core().container().from_(SHELLCHECK_IMAGE),
            f"files=$({find}); [ -z \"$files\" ] && exit 0\n"
            "shellcheck $files\n"
            "for f in $files; do [ -x \"$f\" ] || { echo \"not executable: $f\"; exit 1; }; done",
        ).sync()

    @function
    @check
    async def python(self) -> None:
        """Byte-compile every Python script, then run the eval harness unit tests."""
        await self._run(
            self._python(),
            "python3 -m compileall -q plugins/*/skills/*/scripts evals/harness scripts\n"
            "python3 -m unittest discover -s evals -p 'test_*.py'",
        ).sync()

    @function
    @check
    async def plugins(self) -> None:
        """Plugin manifests, marketplaces, and READMEs agree; plugin.json matches the Agent Plugins schema."""
        await self._run(
            self._python(f"check-jsonschema=={CHECK_JSONSCHEMA}"),
            "python3 scripts/check-plugins.py\n"
            "check-jsonschema --schemafile https://agent-plugins.org/schemas/1.0.0/plugin.schema.json plugins/*/plugin.json",
        ).sync()

    # GitHub Actions -----------------------------------------------------------

    @function
    @check
    async def actionlint(self) -> None:
        """actionlint on this repo's workflows and the well-formed eval fixture workflows."""
        await self._run(
            core().container().from_(ACTIONLINT_IMAGE).with_entrypoint([]),
            f"actionlint {WORKFLOWS} {GOOD_FIXTURE_WORKFLOWS}",
        ).sync()

    # Repo hygiene and security -----------------------------------------------

    @function
    @check
    async def merge_conflicts(self) -> None:
        """No git merge conflict markers in any file."""
        await self._run(
            core().container().from_(PYTHON_IMAGE),
            "if grep -rnI -E '^(<<<<<<<|>>>>>>>) ' --exclude-dir=.agents .; then exit 1; fi",
        ).sync()

    @function
    @check
    async def codespell(self) -> None:
        """codespell on every file, with .github/linters/.codespellrc."""
        await self._run(
            self._python(f"codespell=={CODESPELL}"), "codespell --config .github/linters/.codespellrc ."
        ).sync()

    @function
    @check
    async def gitleaks(self) -> None:
        """gitleaks secret scan on the working tree."""
        await self._run(
            core().container().from_(GITLEAKS_IMAGE).with_entrypoint([]),
            "gitleaks dir . --no-banner --redact",
        ).sync()

    @function
    @check
    async def trivy(self) -> None:
        """trivy fs: vulnerabilities, misconfigurations, and secrets, with .github/linters/trivy.yaml."""
        await self._run(
            core().container().from_(TRIVY_IMAGE).with_entrypoint([])
            .with_mounted_cache("/root/.cache/trivy", core().cache_volume("lint-trivy")),
            "trivy fs --quiet --config .github/linters/trivy.yaml .",
        ).sync()

    @function
    @check
    async def checkov(self) -> None:
        """checkov infrastructure-as-code rules, with .github/linters/.checkov.yaml."""
        await self._run(
            core().container().from_(CHECKOV_IMAGE).with_entrypoint([]),
            "checkov --config-file .github/linters/.checkov.yaml -d .",
        ).sync()
