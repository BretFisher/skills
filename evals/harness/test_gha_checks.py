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


class RerunProgramTests(unittest.TestCase):
    """checks.py --rerun-program fills null program verdicts in place and keeps everything else."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.run = Path(temp.name) / "iteration-1/eval-8-ci/with_skill/run-1"
        self.run.mkdir(parents=True)
        self.texts = next(e["expectations"] for e in checks.EVALS if e["id"] == 8)

    def write(self, overrides):
        """Eval 8 grades: every entry a program pass unless overridden by index."""
        entries = [overrides.get(i, {"text": t, "passed": True, "evidence": "program (program): ok", "graded_by": "program"})
                   for i, t in enumerate(self.texts, 1)]
        for i, e in overrides.items():
            e.setdefault("text", self.texts[i - 1])
        (self.run / "grading.json").write_text(json.dumps({"expectations": entries, "claims": ["kept"]}))

    def read(self):
        return json.loads((self.run / "grading.json").read_text())

    def scanners(self, verdict):
        return mock.patch.object(checks, "scanners", lambda run, actionlint_allow=None: verdict)

    def test_missing_docker_workflow_is_split_not_program(self):
        kinds = {i: k for i, k, _ in checks.checks_for(checks.Run(str(self.run)))}
        self.assertEqual(kinds[9], "split")
        self.write({9: {"passed": None, "evidence": "model: no docker workflow written; model", "kind": "program"}})
        self.assertEqual(checks.rerun_program(str(self.run)), [])
        self.assertEqual(self.read()["expectations"][8]["kind"], "split")

    def test_model_verdicts_are_kept(self):
        model = {"passed": False, "evidence": "model quote", "graded_by": "model"}
        self.write({4: dict(model), 8: {"passed": None, "evidence": "model: skipped", "kind": "program", "context": []}})
        with self.scanners((True, "clean")):
            self.assertEqual(checks.rerun_program(str(self.run)), [])
        doc = self.read()
        self.assertEqual({k: doc["expectations"][3][k] for k in model}, model)
        self.assertEqual(doc["expectations"][7], {"text": self.texts[7], "passed": True,
                                                  "evidence": "program (program): clean", "graded_by": "program"})
        self.assertEqual(doc["claims"], ["kept"])
        self.assertNotIn("residual", doc)
        self.assertEqual(doc["summary"]["pending_model"], 0)

    def test_legacy_entries_get_kinds_and_scanner_rerun(self):
        self.write({4: {"passed": None, "evidence": "model: judgment only"},
                      8: {"passed": None, "evidence": "model: skipped (--scanners not given)"}})
        with self.scanners((True, "clean")):
            self.assertEqual(checks.rerun_program(str(self.run)), [])
        doc = self.read()
        self.assertEqual(doc["expectations"][3]["kind"], "model")
        self.assertIs(doc["expectations"][7]["passed"], True)
        self.assertEqual(doc["residual"]["indices"], [4])

    def test_still_null_is_reported_and_kept(self):
        self.write({8: {"passed": None, "evidence": "model: skipped", "kind": "program"}})
        with self.scanners((None, "skipped (not installed: poutine)")):
            self.assertEqual(checks.rerun_program(str(self.run)), [(8, "skipped (not installed: poutine)")])
        self.assertIsNone(self.read()["expectations"][7]["passed"])

    def test_batch_stops_before_writing_prompts(self):
        self.write({8: {"passed": None, "evidence": "model: skipped", "kind": "program"}})
        with self.scanners((None, "skipped (not installed: poutine)")), self.assertRaises(SystemExit) as stop:
            checks.batch_mode([str(self.run)])
        self.assertEqual(stop.exception.code, 1)
        self.assertFalse((self.run.parents[2] / "grader-batches").exists())


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

    def fake_checker(self, verdict, rerun=True):
        """A checker that sets the first entry; it advertises --rerun-program unless rerun is False."""
        self.checker.write_text(
            ("# --rerun-program\n" if rerun else "") +
            "import json, sys\n"
            "p = sys.argv[-1] + '/grading.json'\n"
            "v = json.load(open(p))\n"
            f"v['expectations'][0].update(passed={verdict!r}, evidence='rerun')\n"
            "json.dump(v, open(p, 'w'))\n"
            f"sys.exit(0 if {verdict!r} is not None else 1)\n")

    def test_complete_grades_skip_the_checker(self):
        self.fake_checker(False)
        path = self.write({"text": "a", "passed": True, "evidence": "program"})
        self.assertIs(grading.regrade_program(path, "skill")["expectations"][0]["passed"], True)

    def test_checker_without_rerun_leaves_kindless_nulls_for_model(self):
        self.fake_checker(True, rerun=False)
        path = self.write({"text": "a", "passed": None, "evidence": "model"})
        self.assertIsNone(grading.regrade_program(path, "skill")["expectations"][0]["passed"])

    def test_checker_without_rerun_stops_on_program_null(self):
        self.fake_checker(True, rerun=False)
        path = self.write({"text": "a", "passed": None, "evidence": "skipped", "kind": "program"})
        with self.assertRaisesRegex(ValueError, r"cannot rerun"):
            grading.regrade_program(path, "skill")

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
