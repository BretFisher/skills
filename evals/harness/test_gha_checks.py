"""github-actions-workflow-pro checker and residual-grading regressions, run by make eval-test."""

import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from . import grading


spec = importlib.util.spec_from_file_location(
    "gha_checks", Path(__file__).resolve().parents[1] / "github-actions-workflow-pro/checks.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)

RUN = SimpleNamespace(wf={"ci.yml": ("on: push\n", {})}, answer="", all_text="")


class ScannerDefaultTests(unittest.TestCase):
    def test_scanners_run_unless_opted_out(self):
        self.assertTrue(checks.RUN_SCANNERS)

    def test_opt_out_leaves_null(self):
        with mock.patch.object(checks, "RUN_SCANNERS", False):
            self.assertEqual(checks.scanners(RUN), (None, "skipped (--no-scanners given)"))

    def test_missing_tool_is_named(self):
        with mock.patch.object(checks.shutil, "which", lambda t: None if t == "poutine" else f"/bin/{t}"):
            self.assertEqual(checks.scanners(RUN), (None, "skipped (not installed: poutine)"))

    def test_no_yaml_is_vacuous(self):
        self.assertTrue(checks.scanners(SimpleNamespace(wf={}))[0])


class RegradeProgramTests(unittest.TestCase):
    """make eval-grade reruns the checker for a null program verdict instead of asking the model."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.run = self.root / "run-1"
        self.run.mkdir()
        self.checker = self.root / "evals/skill/checks.py"
        self.checker.parent.mkdir(parents=True)
        patcher = mock.patch.object(grading, "ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, *entries):
        path = self.run / "grading.json"
        path.write_text(json.dumps({"expectations": list(entries)}))
        return path

    def fake_checker(self, verdict):
        self.checker.write_text(
            "import json, sys\n"
            "p = sys.argv[-1] + '/grading.json'\n"
            "v = json.load(open(p))\n"
            f"v['expectations'][0].update(passed={verdict!r}, evidence='rerun')\n"
            "json.dump(v, open(p, 'w'))\n")

    def test_judgment_null_is_left_for_model(self):
        path = self.write({"text": "a", "passed": None, "evidence": "model", "kind": "model"})
        self.assertIsNone(grading.regrade_program(path, "skill")["expectations"][0]["passed"])

    def test_program_null_is_rerun(self):
        self.fake_checker(True)
        path = self.write({"text": "a", "passed": None, "evidence": "skipped", "kind": "program"})
        self.assertIs(grading.regrade_program(path, "skill")["expectations"][0]["passed"], True)

    def test_program_null_that_stays_null_stops(self):
        self.fake_checker(None)
        path = self.write({"text": "a", "passed": None, "evidence": "skipped", "kind": "program"})
        with self.assertRaisesRegex(ValueError, r"still null"):
            grading.regrade_program(path, "skill")


if __name__ == "__main__":
    unittest.main()
