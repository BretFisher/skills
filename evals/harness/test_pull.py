"""eval-pull decisions and file manifests, without SSH."""

import os
from pathlib import Path
import shutil
import tempfile
import unittest

from harness.pull import decide, default_suffix, list_iterations, local_name, main, tree_manifest


class PullTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.run = self.repo / "evals/demo-skill/runs/iteration-3"
        (self.run / "eval-0-task/with_skill/run-1/outputs").mkdir(parents=True)
        (self.repo / "evals/harness").mkdir()
        (self.run / "manifest.json").write_text("{}\n")
        (self.run / "eval-0-task/with_skill/run-1/outputs/answer.md").write_text("done\n")
        os.symlink("answer.md", self.run / "eval-0-task/with_skill/run-1/outputs/link.md")

    def entry(self):
        return list_iterations(str(self.repo))[0]

    def test_manifest_matches_a_copy_and_records_links(self):
        copy = Path(self.temp.name) / "copy"
        shutil.copytree(self.run, copy, symlinks=True)
        files = tree_manifest(copy)[0]
        self.assertEqual(files, self.entry()["files"])
        self.assertEqual(files["eval-0-task/with_skill/run-1/outputs/link.md"], "link:answer.md")

    def test_one_changed_byte_is_a_conflict(self):
        dest = Path(self.temp.name) / "copy"
        shutil.copytree(self.run, dest, symlinks=True)
        entry = self.entry()
        self.assertEqual(decide(entry, dest, entry["newest"] + 7200, 3600), "present")
        (dest / "manifest.json").write_text("{ }\n")
        self.assertEqual(decide(entry, dest, entry["newest"] + 7200, 3600), "conflict")

    def test_missing_copy_is_copied_and_recent_run_is_skipped(self):
        entry = self.entry()
        dest = Path(self.temp.name) / "absent"
        self.assertEqual(decide(entry, dest, entry["newest"] + 7200, 3600), "copy")
        self.assertEqual(decide(entry, dest, entry["newest"] + 60, 3600), "recent")

    def test_filters_and_names(self):
        self.assertEqual(list_iterations(str(self.repo), skill="other"), [])
        self.assertEqual(list_iterations(str(self.repo), iteration="iteration-9"), [])
        self.assertEqual(local_name("iteration-27", "lab-1"), "iteration-27-lab-1")
        self.assertEqual(default_suffix("me@box.example"), "box.example")

    def test_listing_refuses_a_directory_that_is_not_this_repo(self):
        with self.assertRaises(SystemExit):
            list_iterations(self.temp.name)

    def test_unsafe_arguments_are_refused_before_ssh(self):
        for argv in (["--host=-oProxyCommand=x", "--remote-repo", "skills"],
                     ["--host", "box", "--remote-repo", "../skills"],
                     ["--host", "box", "--remote-repo", "skills; rm -rf ~"],
                     ["--host", "box", "--remote-repo", "skills", "--iteration", "../iteration-1"]):
            with self.subTest(argv=argv), self.assertRaises(SystemExit):
                main(argv)


if __name__ == "__main__":
    unittest.main()
