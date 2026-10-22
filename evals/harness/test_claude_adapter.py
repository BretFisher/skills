"""Claude Code adapter command line, run by make eval-test."""

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

from . import runner


class Captured(Exception):
    pass


class ClaudeCommandTests(unittest.TestCase):
    def test_prompt_follows_double_dash(self):
        """--mcp-config takes several values, so without `--` it swallows the prompt as a config path."""
        def capture(argv, *rest):
            raise Captured(argv)
        args = SimpleNamespace(model="claude-sonnet-5-5", effort="high", timeout=1)
        with mock.patch.object(runner, "run_process", capture):
            with self.assertRaises(Captured) as caught:
                runner.claude_execute("the task", Path("."), Path("."), Path("."), args, {})
        argv = caught.exception.args[0]
        self.assertEqual(argv[-2:], ["--", "the task"])


if __name__ == "__main__":
    unittest.main()
