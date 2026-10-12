"""Evidence contract regression tests. Run through make eval-test."""

import unittest

from harness.evidence import EvidenceError, claude_events, opencode_events, provenance


SHA = "a" * 40


def call(call_id, command):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": call_id, "name": "Bash", "input": {"command": command}}
    ]}}


def result(call_id, output):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": call_id, "content": output}
    ]}}


def oc_tool(call_id, name, start, end, inp, output):
    return {"type": "tool", "id": call_id, "name": name,
            "time": {"created": start, "ran": start, "completed": end},
            "state": {"status": "completed", "input": inp,
                      "content": [{"type": "text", "text": output}]}}


class EvidenceTests(unittest.TestCase):
    def test_unsupported_log_cannot_pass(self):
        with self.assertRaises(EvidenceError):
            claude_events([{"type": "tool", "state": {}}])

    def test_empty_log_cannot_pass(self):
        with self.assertRaises(EvidenceError):
            claude_events([])

    def test_truncated_call_cannot_pass(self):
        with self.assertRaises(EvidenceError):
            provenance(claude_events([call("1", "pinact run")]), {SHA})

    def test_mismatched_result(self):
        with self.assertRaises(EvidenceError):
            claude_events([result("unknown", SHA)])

    def test_missing_sha_cannot_pass(self):
        self.assertFalse(provenance(claude_events([call("1", "true"), result("1", "")]), {SHA})[0])

    def test_valid_source(self):
        evidence = claude_events([call("1", "pinact run"), result("1", SHA),
                                  call("2", f"write {SHA}"), result("2", "ok")])
        self.assertTrue(provenance(evidence, {SHA})[0])

    def test_input_first(self):
        self.assertFalse(provenance(claude_events([call("1", SHA), result("1", SHA)]), {SHA})[0])

    def test_forbidden_lookup(self):
        evidence = claude_events([call("1", "gh api repos/a/b/commits/main"), result("1", SHA)])
        self.assertFalse(provenance(evidence, {SHA})[0])

    def test_opencode_parallel_calls_use_time_not_block_order(self):
        evidence = opencode_events({"messages": [{"type": "assistant", "content": [
            oc_tool("1", "shell", 1, 4, {"command": "pinact run"}, SHA),
            oc_tool("2", "shell", 2, 3, {"command": SHA}, "ok"),
        ]}]})
        self.assertFalse(provenance(evidence, {SHA})[0])

    def test_opencode_valid_source(self):
        evidence = opencode_events({"messages": [{"type": "assistant", "content": [
            oc_tool("1", "shell", 1, 2, {"command": "pinact run"}, SHA),
            oc_tool("2", "read", 3, 4, {"path": "ci.yml"}, SHA),
        ]}]})
        self.assertTrue(provenance(evidence, {SHA})[0])
        self.assertIn("read: ci.yml", evidence.calls())

    def test_opaque_code_mode_cannot_pass(self):
        evidence = opencode_events({"messages": [{"type": "assistant", "content": [
            oc_tool("1", "execute", 1, 2, {"code": "tools.shell()"}, SHA),
        ]}]})
        with self.assertRaises(EvidenceError):
            provenance(evidence, {SHA})

    def test_equal_timestamp_is_inconclusive(self):
        evidence = opencode_events({"messages": [{"type": "assistant", "content": [
            oc_tool("1", "shell", 1, 2, {}, SHA),
            oc_tool("2", "shell", 2, 3, {}, ""),
        ]}]})
        with self.assertRaises(EvidenceError):
            evidence.require_complete()

    def test_simultaneous_results_are_complete(self):
        evidence = opencode_events({"messages": [{"type": "assistant", "content": [
            oc_tool("1", "read", 1, 4, {"path": "a"}, SHA),
            oc_tool("2", "read", 2, 4, {"path": "b"}, SHA),
            oc_tool("3", "shell", 5, 6, {"command": SHA}, "ok"),
        ]}]})
        evidence.require_complete()
        self.assertTrue(provenance(evidence, {SHA})[0])


if __name__ == "__main__":
    unittest.main()
