"""Secret scan and export redaction, with fake values only."""

import collections
from pathlib import Path
import subprocess
import tempfile
import unittest

from harness.scrub import find_secrets, identity_leftovers, redact, scan_tree, selftest

FAKE_GH = b"ghp_" + b"Q7w8E9r0" * 4 + b"Tt11"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null"]


def rules(data):
    return sorted({rule for rule, _, _ in find_secrets(data)})


class SecretRuleTests(unittest.TestCase):
    def test_each_secret_kind_is_found(self):
        cases = {
            "github-token": FAKE_GH,
            "github-pat": b"github_pat_" + b"a1B2" * 20,
            "anthropic-key": b"sk-ant-api03-" + b"x" * 30,
            "aws-access-key": b"AKIA" + b"ABCDEFGHIJKLMNOP",
            # Built from parts so this file is not itself a finding when an export copies the harness.
            "private-key": b"-----BEGIN OPENSSH " + b"PRIVATE KEY-----",
            "auth-header": b'"Authorization": "Bear' + b'er abcdefghijklmnopqrstuvwx"',
            "url-credential": b"https://bot:s3cr3tvalue1@github.com/org/repo.git",
            "env-credential": b"MESSAGING_TOKEN=Zx9-" + b"q" * 20,
        }
        cases["env-credential (escaped JSON env dump)"] = b'"PATH=/bin\\nMESSAGING_TOKEN=Zx9-' + b"q" * 20 + b'\\nHOME=/x"'
        for rule, sample in cases.items():
            with self.subTest(rule=rule):
                self.assertIn(rule.split(" ")[0], rules(b"before " + sample + b" after"))

    def test_examples_and_commands_are_not_secrets(self):
        for sample in (b"GIT_AUTH_TOKEN=mytoken", b"MY_SECRET=./secret.txt", b"GH_TOKEN=$(gh auth token) zizmor .",
                       b"TOKEN=<redacted>", b"`unredacted-secrets` rule", b"actions/checkout@v4"):
            with self.subTest(sample=sample):
                self.assertEqual(rules(sample), [])


class ScanTreeTests(unittest.TestCase):
    def test_finds_a_token_in_a_file_and_in_a_git_commit(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            (run / "work").mkdir()
            (run / "transcript.md").write_bytes(b"token " + FAKE_GH + b"\n")
            subprocess.run(GIT + ["init", "-q"], cwd=run / "work", check=True)
            subprocess.run(GIT + ["commit", "-q", "--allow-empty", "-m", FAKE_GH.decode()], cwd=run / "work", check=True)
            findings, stats = scan_tree([run])
        self.assertEqual(stats["git repos"], 1)
        self.assertEqual({f["where"].rsplit("/", 1)[-1] for f in findings}, {"transcript.md", ".git [objects]"})
        self.assertNotIn(FAKE_GH.decode(), str(findings))

    def test_selftest_passes(self):
        selftest()


class RedactTests(unittest.TestCase):
    def test_identifiers_become_placeholders(self):
        data = (b'{"cwd":"/Users/alex/code/skills","email":"The user\'s email address is alex@corp.example.org.",'
                b'"organizationUuid":"0f5d6b8e-1111-2222-3333-444455556666"}\n'
                b"HOME=/Users/alex\\nUSER=alex\\nCLAUDE_CODE_USER_EMAIL=alex@corp.io\\nBAGGAGE=sentry-trace=abc\\n"
                b"/home/alexw/projects ~/.claude/projects/-Users-alex-code-skills/ build-host-7 alex@corp.io\n")
        counts = collections.Counter()
        out = redact(data, ["build-host-7"], counts)
        for gone in (b"alex@corp.io", b"/Users/alex/", b"/home/alexw", b"-Users-alex-", b"0f5d6b8e", b"USER=alex",
                     b"sentry-trace", b"build-host-7"):
            with self.subTest(gone=gone):
                self.assertNotIn(gone, out)
        self.assertIn(b"/Users/<user>/code/skills", out)
        self.assertIn(b'"organizationUuid":"<redacted>"', out)
        self.assertIn(b"alex@corp.example.org", out)  # example domains are not personal
        self.assertEqual(list(identity_leftovers(["build-host-7"])(out)), [])

    def test_public_and_generic_values_stay(self):
        data = (b"git@github.com:org/repo.git noreply@anthropic.com eval@example.invalid "
                b"41898282+github-actions[bot]@users.noreply.github.com /home/runner/work /home/linuxbrew/.linuxbrew/bin "
                b"/Users/Shared/x actions/setup-node@v4.0.2")
        self.assertEqual(redact(data, [], collections.Counter()), data)


if __name__ == "__main__":
    unittest.main()
