"""Recover collection after an evidence-reader failure, without model execution."""

import argparse
import hashlib
import json
from pathlib import Path

from .evidence import load_run
from .runner import ROOT, collect_outputs, command, model_ref, transcript, write_json


def recover(run):
    state = json.loads((run / "run.json").read_text())
    if state.get("status") != "failed" or state.get("error") != "Incomplete tool evidence; deterministic grading refused":
        raise ValueError(f"Run is not a recoverable evidence-collection failure: {run}")
    if state.get("harness") != "opencode":
        raise ValueError("Only OpenCode evidence collection recovery is supported")
    if (run / "work").exists() or (run / "outputs").exists():
        raise ValueError("Existing collected files are retained; recovery will not overwrite them")
    evidence = load_run(run).require_complete()
    export = json.loads((run / "session-export.json").read_text())["data"]
    assistants = [m for m in export["messages"] if m.get("type") == "assistant"]
    expected = model_ref(state["requested_model"])
    if not assistants or assistants[-1].get("finish") != "stop" or any(m.get("error") or m["model"] != expected for m in assistants):
        raise ValueError("Native session is unfinished, failed, or used a different model")
    timing = json.loads((run / "timing.json").read_text())
    if not timing.get("total_tokens") or timing.get("model") != state["requested_model"]:
        raise ValueError("Missing verified usage from completed model execution")
    work = Path(state["workspace"])
    if command(["git", "rev-parse", "HEAD"], work).strip() != state["fixture_commit"]:
        raise ValueError("Retained fixture HEAD changed; recovery refused")
    last_time = assistants[-1]["time"]["completed"] / 1000
    for file in work.rglob("*"):
        if file.is_file() and ".git" not in file.relative_to(work).parts and file.stat().st_mtime > last_time + 0.001:
            raise ValueError(f"Retained task file changed after session completion: {file}")
    metadata = json.loads((run / "eval_metadata.json").read_text())
    final = "\n\n".join(c["text"] for m in assistants for c in m.get("content", []) if c.get("type") == "text")
    write_json(run / "recovery.json", {"original_state": state,
               "native_sha256": hashlib.sha256((run / "session-export.json").read_bytes()).hexdigest(),
               "reader_sha256": hashlib.sha256((ROOT / "evals/harness/evidence.py").read_bytes()).hexdigest(),
               "model_calls": 0})
    transcript(run, metadata, evidence)
    collect_outputs(work, run, final)
    state = {**state, "status": "complete", "recovered_collection": True}
    state.pop("error", None)
    write_json(run / "run.json", state)
    print(f"Recovered collection without a model call: {run}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    recover(args.run.resolve())


if __name__ == "__main__":
    main()
