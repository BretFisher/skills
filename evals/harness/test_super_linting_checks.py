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


if __name__ == "__main__":
    unittest.main()
