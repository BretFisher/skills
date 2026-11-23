"""Makefile delegation regressions for the local linting grader."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest


spec = importlib.util.spec_from_file_location(
    "super_linting_checks", Path(__file__).resolve().parents[1] / "super-linting/checks.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


class LintRecipeTests(unittest.TestCase):
    def recipe(self, makefile):
        files = {"Makefile": makefile, "scripts/lint.sh": "tflint --recursive\nshellcheck scripts/*.sh\n"}
        return checks.Run.lint_recipe(SimpleNamespace(file=lambda name: files.get(name, "")))

    def test_called_helper_is_part_of_lint_recipe(self):
        recipe = self.recipe("lint:\n\tbash scripts/lint.sh\n")
        self.assertIn("tflint", recipe)
        self.assertIn("shellcheck", recipe)

    def test_uncalled_helper_does_not_count(self):
        self.assertNotIn("tflint", self.recipe("lint:\n\techo no checks\n"))

    def test_helper_from_dependency_counts(self):
        self.assertIn("shellcheck", self.recipe("lint: lint-infra\n\n lint-infra:\n\tbash scripts/lint.sh\n".replace(" lint-infra:", "lint-infra:")))

    def test_external_helper_is_not_read(self):
        self.assertNotIn("tflint", self.recipe("lint:\n\tbash ../scripts/lint.sh\n"))


class AnswerCheckTests(unittest.TestCase):
    def run_(self, calls="", answer=""):
        return SimpleNamespace(calls=calls, answer=answer)

    def test_reference_read_after_cd_counts(self):
        self.assertTrue(checks.e0_5(self.run_("shell: cd skill/super-linting/references && cat linter-commands.md"))[0])

    def test_read_tool_counts(self):
        self.assertTrue(checks.e0_5(self.run_("read: /tmp/skill/super-linting/references/linter-commands.md"))[0])

    def test_name_only_mentions_do_not_count(self):
        for calls in ("shell: ls references/linter-commands.md", "shell: echo linter-commands.md"):
            self.assertFalse(checks.e0_5(self.run_(calls))[0], calls)

    def test_fetch_of_super_linter_fails(self):
        calls = "read: references/linter-commands.md\nshell: curl https://raw.githubusercontent.com/super-linter/super-linter/main/README.md"
        self.assertFalse(checks.e0_5(self.run_(calls))[0])

    def test_hook_question_wrapped_over_lines_counts(self):
        answer = "Do you also want a git pre-commit hook that blocks a commit when a linter fails,\nor is `make lint` enough?"
        self.assertTrue(checks.e0_8(self.run_(answer=answer))[0])

    def test_hook_statement_is_not_a_question(self):
        answer = "I did not add a git hook. Do you want me to commit?"
        self.assertFalse(checks.e0_8(self.run_(answer=answer))[0])


if __name__ == "__main__":
    unittest.main()
