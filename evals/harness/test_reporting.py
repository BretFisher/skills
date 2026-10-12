"""Reporting regressions against the unchanged installed viewer."""

import json
from pathlib import Path
import tempfile
import unittest

from harness.reporting import (benchmark, load_iteration, markdown, safe_html,
                              upstream_viewer, view_runs, viewer_benchmark)
from harness.runner import ROOT, tree_hash, write_json


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.iteration = Path(self.temp.name)
        self.paths = {}
        for config, passed in (("with_skill", True), ("without_skill", False)):
            path = self.iteration / "eval-7-nested-files" / config / "run-1"
            (path / "outputs/.github/workflows").mkdir(parents=True)
            (path / "outputs/.github/workflows/ci.yml").write_text("name: CI\n")
            (path / "outputs/Dockerfile").write_text("FROM scratch\n")
            (path / "outputs/.dockerignore").write_text(".git\n")
            write_json(path.parent.parent / "eval_metadata.json", {
                "eval_id": 7, "prompt": "Write the files", "eval_name": "nested-files", "assertions": ["a"]})
            write_json(path / "grading.json", {"expectations": [{"text": "a", "passed": passed, "evidence": "quote"}],
                       "summary": {"passed": int(passed), "failed": int(not passed), "total": 1, "pass_rate": int(passed)}})
            write_json(path / "timing.json", {"total_tokens": 100 if passed else 200, "total_duration_seconds": 2})
            self.paths[config] = path

    def report(self):
        return benchmark(self.iteration, "example")

    def test_primary_is_first_and_delta_is_positive(self):
        value, _ = self.report()
        self.assertEqual(list(value["run_summary"]), ["with_skill", "without_skill", "delta"])
        self.assertEqual(value["run_summary"]["delta"]["pass_rate"], "+1.00")
        self.assertEqual(value["run_summary"]["delta"]["tokens"], "-100")
        self.assertEqual(value["metadata"]["runs_per_configuration"], 1)

    def test_missing_tokens_are_unknown_not_output_characters(self):
        path = self.paths["with_skill"]
        write_json(path / "timing.json", {"total_duration_seconds": 2})
        grading = json.loads((path / "grading.json").read_text())
        grading["execution_metrics"] = {"output_chars": 9999}
        write_json(path / "grading.json", grading)
        value, _ = self.report()
        self.assertIsNone(value["run_summary"]["with_skill"]["tokens"]["mean"])
        self.assertNotIn("tokens", viewer_benchmark(value)["run_summary"]["with_skill"])
        self.assertIn("unknown", markdown(value))
        self.assertEqual(value["run_summary"]["delta"]["tokens"], "—")

    def test_pending_grade_cannot_be_published(self):
        path = self.paths["with_skill"] / "grading.json"
        value = json.loads(path.read_text())
        value["expectations"][0]["passed"] = None
        write_json(path, value)
        with self.assertRaises(ValueError):
            self.report()

    def test_incorrect_summary_is_rejected(self):
        path = self.paths["with_skill"] / "grading.json"
        value = json.loads(path.read_text())
        value["summary"]["total"] = 10
        write_json(path, value)
        with self.assertRaises(ValueError):
            self.report()

    def test_missing_pair_is_rejected(self):
        # Retain the directory to also test the missing grading-file diagnostic.
        (self.paths["without_skill"] / "grading.json").unlink()
        with self.assertRaises(ValueError):
            self.report()

    def test_missing_repeat_is_rejected(self):
        write_json(self.iteration / "manifest.json", {"eval_ids": [7], "repeats": 2,
                   "fingerprint": "x", "model": "openai/example#high", "harness": "opencode"})
        with self.assertRaises(ValueError):
            self.report()

    def test_mixed_model_comparison_is_rejected(self):
        for config, path in self.paths.items():
            write_json(path / "timing.json", {"total_tokens": 100, "total_duration_seconds": 2,
                       "model": config, "harness": "opencode"})
        with self.assertRaises(ValueError):
            self.report()

    def test_model_mismatch_is_rejected_for_runner_artifacts(self):
        write_json(self.iteration / "manifest.json", {"eval_ids": [7], "repeats": 1, "fingerprint": "x",
                   "model": "openai/example#high", "harness": "opencode"})
        for config, path in self.paths.items():
            write_json(path / "run.json", {"status": "complete", "fingerprint": "x", "configuration": config,
                       "requested_model": "openai/example#high"})
        with self.assertRaises(ValueError):
            self.report()

    def test_nonfinite_measurement_is_rejected(self):
        (self.paths["with_skill"] / "timing.json").write_text('{"total_tokens":NaN}')
        with self.assertRaises(ValueError):
            self.report()

    def test_failed_executor_cannot_be_reported(self):
        write_json(self.paths["with_skill"] / "run.json", {"status": "failed"})
        with self.assertRaises(ValueError):
            self.report()

    def test_nested_outputs_and_dotfiles_are_preserved(self):
        upstream = upstream_viewer(ROOT / ".agents/skills/skill-creator")
        _, records = self.report()
        runs = view_runs(self.iteration, records, upstream)
        self.assertEqual(runs[0]["prompt"], "Write the files")
        files = {f["name"]: f for f in runs[0]["outputs"]}
        self.assertIn(".github/workflows/ci.yml", files)
        self.assertEqual(files["Dockerfile"]["type"], "text")
        self.assertEqual(files[".dockerignore"]["type"], "text")

    def test_duplicate_basenames_do_not_collide(self):
        path = self.paths["with_skill"] / "outputs/other"
        path.mkdir()
        (path / "ci.yml").write_text("name: other\n")
        upstream = upstream_viewer(ROOT / ".agents/skills/skill-creator")
        _, records = self.report()
        names = [f["name"] for f in view_runs(self.iteration, records, upstream)[0]["outputs"]]
        self.assertIn("other/ci.yml", names)
        self.assertIn(".github/workflows/ci.yml", names)

    def test_upstream_is_not_modified_and_script_payload_is_safe(self):
        source = ROOT / ".agents/skills/skill-creator"
        before = tree_hash(source)
        upstream = upstream_viewer(source)
        (self.paths["with_skill"] / "outputs/answer.md").write_text('</script><script>alert("x")</script>')
        value, records = self.report()
        html = safe_html(upstream, view_runs(self.iteration, records, upstream), "test", {}, value)
        self.assertNotIn('</script><script>alert', html)
        marker = "const EMBEDDED_DATA = "
        embedded, _ = json.JSONDecoder().raw_decode(html[html.index(marker) + len(marker):])
        outputs = embedded["runs"][0]["outputs"]
        self.assertEqual(next(f["content"] for f in outputs if f["name"] == "answer.md"), '</script><script>alert("x")</script>')
        self.assertIn("benchmark", embedded)
        self.assertEqual(tree_hash(source), before)

    def test_symlink_outputs_are_rejected(self):
        path = self.paths["with_skill"] / "outputs/link.md"
        path.symlink_to(self.paths["with_skill"] / "grading.json")
        upstream = upstream_viewer(ROOT / ".agents/skills/skill-creator")
        _, records = self.report()
        with self.assertRaises(ValueError):
            view_runs(self.iteration, records, upstream)


if __name__ == "__main__":
    unittest.main()
