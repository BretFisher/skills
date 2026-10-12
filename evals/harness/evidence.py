"""Read native transcripts without treating missing evidence as success.

Claude JSONL and OpenCode V2 session exports are retained unchanged. Adapters
produce ordered input/result events for checks that need tool provenance.
"""

import json
from dataclasses import dataclass
from pathlib import Path


class EvidenceError(ValueError):
    """Evidence cannot support a deterministic verdict."""


ALIASES = {"Bash": "shell", "Read": "read", "Write": "write", "Edit": "edit"}


@dataclass
class Evidence:
    source: str
    events: list
    complete: bool = True

    def require_complete(self):
        if not self.complete:
            raise EvidenceError("Incomplete tool evidence; deterministic grading refused")
        return self

    def calls(self):
        self.require_complete()
        return "\n".join(
            f"{e['name']}: " + " ".join(
                str(e["input"][k])
                for k in ("file_path", "command", "url", "pattern", "path", "id")
                if k in e["input"]
            )
            for e in self.events if e["type"] == "tool_input"
        )


def text_content(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    raise EvidenceError("Unsupported tool result content")


def event(kind, call_id, name, **fields):
    return {"type": kind, "call_id": call_id, "name": ALIASES.get(name, name), **fields}


def claude_events(records):
    events, pending, recognized = [], {}, False
    for record in records:
        if record.get("type") in ("assistant", "user", "system", "result"):
            recognized = True
        content = record.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            kind = block.get("type")
            if kind == "tool_use":
                call_id = block["id"]
                if call_id in pending:
                    raise EvidenceError("Duplicate tool-call ID")
                name = block["name"]
                pending[call_id] = name
                events.append(event("tool_input", call_id, name, input=block.get("input", {})))
            elif kind == "tool_result":
                call_id = block["tool_use_id"]
                if call_id not in pending:
                    raise EvidenceError("Tool result has no preceding input")
                name = pending.pop(call_id)
                events.append(event("tool_result", call_id, name,
                                    output=text_content(block.get("content", "")),
                                    error=bool(block.get("is_error", False))))
    if not recognized:
        raise EvidenceError("Unsupported or empty native transcript")
    return Evidence("claude", events, not pending)


def opencode_events(export):
    data = export.get("data", export)
    if not isinstance(data, dict) or not isinstance(data.get("messages"), list) or not data["messages"]:
        raise EvidenceError("Expected a nonempty OpenCode V2 session export")
    ordered, complete, ids = [], True, set()
    for message in data["messages"]:
        if message.get("type") != "assistant":
            continue
        if message.get("error"):
            complete = False
        for block in message.get("content", []):
            if block.get("type") != "tool":
                continue
            call_id, name = block["id"], block["name"]
            if call_id in ids:
                raise EvidenceError("Duplicate tool-call ID")
            ids.add(call_id)
            state, times = block["state"], block["time"]
            # Wrapper source is not a trace of the tools it executes.
            if name in ("execute", "code", "code_mode", "subagent"):
                complete = False
            started = times.get("ran", times.get("created"))
            finished = times.get("completed")
            if started is None or finished is None or finished < started:
                complete = False
                continue
            ordered.append((started, 0, event("tool_input", call_id, name, input=state.get("input", {}))))
            if state.get("status") not in ("completed", "error"):
                complete = False
                continue
            output = text_content(state.get("content", [])) if state.get("status") == "completed" else str(state.get("error", ""))
            ordered.append((finished, 1, event("tool_result", call_id, name, output=output,
                                              error=state.get("status") == "error")))
    # Two results (or two inputs) can share a millisecond without affecting
    # provenance. Only a cross-call input/result tie has ambiguous ordering.
    stamps = {}
    for timestamp, _, e in ordered:
        stamps.setdefault(timestamp, []).append(e)
    if any(len({e["call_id"] for e in events}) > 1 and
           {e["type"] for e in events} == {"tool_input", "tool_result"}
           for events in stamps.values()):
        complete = False
    ordered.sort(key=lambda item: (item[0], item[1]))
    return Evidence("opencode", [item[2] for item in ordered], complete)


def load(path):
    path = Path(path)
    if not path.exists():
        raise EvidenceError(f"Missing native evidence: {path}")
    try:
        raw = path.read_text()
        if path.suffix == ".json":
            return opencode_events(json.loads(raw))
        return claude_events([json.loads(line) for line in raw.splitlines() if line.strip()])
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"Malformed native evidence: {path}: {exc}") from exc


def load_run(directory):
    directory = Path(directory)
    native = directory / "session-export.json"
    return load(native if native.exists() else directory / "raw-transcript.jsonl")


def tool_calls(path):
    """Legacy checkers pass their Claude path; select the sibling V2 export."""
    path = Path(path)
    if not path.exists() and not (path.parent / "session-export.json").exists():
        if (path.parent / "run.json").exists():
            raise EvidenceError("Runner artifact has no native tool evidence")
        return ""  # Historical runs without tool logs retain their existing fallback.
    return load_run(path.parent).calls()


def provenance(evidence, shas):
    """Return a verdict only after every supplied SHA has a logged source."""
    import re

    evidence.require_complete()
    seen, typed, lookups, pending = set(), set(), [], {}
    for e in evidence.events:
        if e["type"] == "tool_input":
            encoded = json.dumps(e["input"])
            typed.update(sha for sha in shas if sha in encoded and sha not in seen)
            command = e["input"].get("command", "")
            if e["name"] == "shell" and re.search(
                r"gh api \S*(git/refs|/commits/|/releases)(?!/latest)|git ls-remote|curl \S*api\.github\.com/repos/\S*(commits|git/refs|releases)(?!/latest)",
                command,
            ) and "gh-aw" not in command:
                pending[e["call_id"]] = command
        elif e["type"] == "tool_result":
            command = pending.pop(e["call_id"], None)
            if command and any(sha in e["output"] for sha in shas):
                lookups.append(command)
            seen.update(sha for sha in shas if sha in e["output"])
    if lookups:
        return False, f"native log: SHA-returning lookup: {lookups[:2]}"
    if typed:
        return False, f"native log: SHA first appears in tool input: {sorted(typed)[:3]}"
    missing = set(shas) - seen
    if missing:
        return False, f"native log: no tool result produced SHA: {sorted(missing)[:3]}"
    return True, f"native log: all {len(shas)} new SHAs have a preceding tool result; no lookup"
