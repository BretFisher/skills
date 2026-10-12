"""Kubernetes updater preparation uses disposable skill and source copies."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from harness.setup import prepare_updater, source_plan, validate_adapter


class SetupTests(unittest.TestCase):
    def test_unknown_procedure_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_adapter({"id": 12, "setup": "run arbitrary commands"}, "k8s-catch-up")
        with self.assertRaises(ValueError):
            validate_adapter({"id": 12, "setup_adapter": "k8s-restore-kyaml"}, "docker-pro")

    def test_missing_sources_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            source_plan(Path(directory))

    def test_damaged_skill_and_isolated_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / "source-cache"
            for name in ("website", "enhancements"):
                repo = cache / name
                (repo / ".git").mkdir(parents=True)
                (repo / "source.md").write_text("local source\n")
                (repo / "alias.md").symlink_to("source.md")
                (repo / ".git/config").write_text("not copied\n")
            home = root / "home"
            work = home / "work"
            work.mkdir(parents=True)
            with patch("harness.setup.subprocess.check_output", return_value="a" * 40 + "\n"):
                plan = source_plan(cache)
                skill = prepare_updater(work, home, plan)
                self.assertFalse((skill / "references/kubectl-cli/kyaml-output-format.md").exists())
                self.assertNotIn("kyaml-output-format.md", (skill / "SKILL.md").read_text())
                for name in plan["repositories"]:
                    copied = home / "cache/k8s-catch-up" / name
                    self.assertEqual((copied / "source.md").read_text(), "local source\n")
                    self.assertEqual((copied / "alias.md").read_text(), "local source\n")
                    self.assertFalse((copied / "alias.md").is_symlink())
                    self.assertFalse((copied / ".git/config").exists())
                    self.assertEqual((cache / name / ".git/config").read_text(), "not copied\n")
                (cache / "website/source.md").write_text("changed\n")
                self.assertNotEqual(source_plan(cache), plan)


if __name__ == "__main__":
    unittest.main()
