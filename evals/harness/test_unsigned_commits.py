"""Eval commits ignore synthetic global signing and hook settings."""

import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from harness.runner import prepare_work


spec = importlib.util.spec_from_file_location(
    "gha_checks", Path(__file__).resolve().parents[1] / "github-actions-workflow-pro/checks.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


class UnsignedCommitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        hooks = self.root / "hooks"
        hooks.mkdir()
        hook = hooks / "pre-commit"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o700)
        config = self.root / "global.gitconfig"
        config.write_text(f"[commit]\n gpgsign = true\n[gpg]\n program = /usr/bin/false\n"
                          f"[core]\n hooksPath = {hooks}\n[user]\n name = owner\n email = owner@example.invalid\n")
        self.environment = patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1"})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def assert_unsigned(self, work):
        raw = subprocess.check_output(["git", "cat-file", "commit", "HEAD"], cwd=work, text=True)
        self.assertNotIn("gpgsig", raw)
        self.assertIn("skill-eval <skill-eval@example.invalid>", raw)

    def test_fixture_commit_needs_no_signer_or_hooks(self):
        work = self.root / "work"
        self.assertEqual(len(prepare_work(work, {})), 40)
        self.assert_unsigned(work)

    def test_scanner_commit_needs_no_signer_or_hooks(self):
        work = self.root / "scratch"
        work.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=work, check=True)
        (work / "fixture.txt").write_text("fixture\n")
        subprocess.run(["git", "add", "--all"], cwd=work, check=True)
        checks.commit_scratch(work)
        self.assert_unsigned(work)

    def test_workflow_proposal_in_hidden_directory_is_read(self):
        run = self.root / "eval-13-proposal/with_skill/run-1"
        output = run / "outputs/.github/workflows"
        output.mkdir(parents=True)
        (output / "deploy.yml").write_text("name: Deploy\non: push\njobs:\n  deploy:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n")
        self.assertIn("deploy.yml", checks.Run(str(run)).wf)

    def test_missing_required_proposal_fails_preservation_checks(self):
        run = self.root / "eval-13-no-proposal/without_skill/run-1"
        (run / "outputs").mkdir(parents=True)
        (run / "outputs/answer.md").write_text("The existing permissions and deployment settings stay unchanged.\n")
        verdicts = {i: fn() for i, _, fn in checks.checks_for(checks.Run(str(run))) if 7 <= i <= 11}
        for index in range(7, 12):
            self.assertIs(verdicts[index][0], False)


if __name__ == "__main__":
    unittest.main()
