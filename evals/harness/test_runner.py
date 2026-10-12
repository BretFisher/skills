"""Offline tests for run preparation and residual grade validation."""

import concurrent.futures
import json
from pathlib import Path
import tempfile
import unittest

from harness.grading import parse_verdicts, validate_grading
from harness.runner import fixture_map, model_ref, opencode_config, safe_relative, tree_hash, write_json


class RunnerTests(unittest.TestCase):
    def test_model_variant_is_explicit(self):
        self.assertEqual(model_ref("openai/example#high"), {
            "providerID": "openai", "id": "example", "variant": "high"})

    def test_model_alias_is_rejected(self):
        with self.assertRaises(ValueError):
            model_ref("sonnet")

    def test_fixture_escape_is_rejected(self):
        for path in ("../answer.md", "/answer.md", ".git/config"):
            with self.assertRaises(ValueError):
                safe_relative(path)

    def test_repo_fixture_keeps_internal_path(self):
        source = "evals/docker-pro/fixtures/node-express/src/server.js"
        self.assertEqual(fixture_map({"files": [source], "prompt": "containerize"}, "docker-pro"),
                         {source: "src/server.js"})

    def test_explicit_fixture_destination(self):
        source = "evals/github-actions-workflow-pro/fixtures/good-ci.yml"
        spec = {"files": [source], "prompt": "edit", "fixture_map": {source: ".github/workflows/ci.yml"}}
        self.assertEqual(fixture_map(spec, "github-actions-workflow-pro"), spec["fixture_map"])

    def test_wrapper_uses_declared_dependency_fixtures(self):
        source = "evals/github-actions-workflow-pro/fixtures/insecure-ci.yml"
        self.assertEqual(fixture_map({"files": [source], "prompt": "/gha-audit"}, "gha-audit"),
                         {source: ".github/workflows/insecure-ci.yml"})
        with self.assertRaises(ValueError):
            fixture_map({"files": [source], "prompt": "lint"}, "super-linting")

    def test_wrapper_dependency_only_installed_with_skill(self):
        for mode in ("with_skill", "without_skill"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                home = Path(directory)
                config = opencode_config(home, home / "work", "gha-audit", mode)
                allowed = {p["resource"] for p in config["permissions"] if p["action"] == "skill" and p["effect"] == "allow"}
                expected = {"gha-audit", "github-actions-workflow-pro"} if mode == "with_skill" else set()
                self.assertEqual(allowed, expected)
                for name in expected:
                    self.assertTrue((home / "config/opencode/skills" / name / "SKILL.md").is_file())

    def test_parallel_metadata_writes_are_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metadata.json"
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda n: write_json(path, {"n": n}), range(32)))
            self.assertIn(json.loads(path.read_text())["n"], range(32))
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_bytecode_does_not_change_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "runner.py").write_text("source")
            before = tree_hash(root)
            (root / "__pycache__").mkdir()
            (root / "__pycache__/runner.pyc").write_text("volatile")
            self.assertEqual(tree_hash(root), before)

    def test_pending_grades_are_not_final(self):
        value = {"expectations": [{"text": "a", "passed": None, "evidence": "pending"}]}
        with self.assertRaises(ValueError):
            validate_grading(value)
        self.assertEqual(validate_grading(value, allow_pending=True)["pending_model"], 1)

    def test_assertion_order_is_checked(self):
        value = {"expectations": [{"text": "a", "passed": True, "evidence": "quote"}]}
        with self.assertRaises(ValueError):
            validate_grading(value, ["different"])

    def test_grader_duplicate_verdict_is_rejected(self):
        answer = json.dumps([{"key": "a", "passed": True, "evidence": "quote"}] * 2)
        with self.assertRaises(ValueError):
            parse_verdicts(answer, {"a", "b"})

    def test_grader_cannot_return_string_boolean(self):
        answer = json.dumps([{"key": "a", "passed": "true", "evidence": "quote"}])
        with self.assertRaises(ValueError):
            parse_verdicts(answer, {"a"})

    def test_grader_valid_json(self):
        answer = '```json\n[{"key":"a","passed":true,"evidence":"quote"}]\n```'
        self.assertTrue(parse_verdicts(answer, {"a"})["a"]["passed"])


if __name__ == "__main__":
    unittest.main()
