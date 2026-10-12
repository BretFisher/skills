"""Validated benchmarks and compatible input for the read-only upstream viewer.

Use make eval-benchmark / eval-view. Reports preserve native artifacts and use
unknown values, not output characters, when historical usage is unavailable.
"""

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import statistics
import types
import webbrowser

from .evidence import load_run
from .grading import validate_grading
from .runner import ROOT, model_ref, write_json


CONFIGS = {"with_skill", "without_skill", "new_skill", "old_skill"}


def read_json(path):
    def invalid(value):
        raise ValueError(f"Non-finite JSON number in {path}: {value}")
    return json.loads(path.read_text(), parse_constant=invalid)


def measurement(value, name):
    if value is None:
        return None
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(f"Invalid {name}: {value}")
    return value


def native_models_and_tokens(path, harness):
    if harness == "opencode":
        export = read_json(path / "session-export.json")
        assistants = [m for m in export["data"]["messages"] if m.get("type") == "assistant"]
        models = [m["model"] for m in assistants]
        components = [v for m in assistants for v in (m["tokens"]["input"], m["tokens"]["output"],
                      m["tokens"]["cache"]["read"], m["tokens"]["cache"]["write"])]
    elif harness == "claude":
        records = [json.loads(line) for line in (path / "raw-transcript.jsonl").read_text().splitlines() if line.strip()]
        models = sorted({r["message"]["model"] for r in records if r.get("type") == "assistant"})
        results = [r for r in records if r.get("type") == "result"]
        if not results or results[-1].get("is_error"):
            raise ValueError("Native Claude transcript has no successful result")
        usage = results[-1]["usage"]
        components = [usage[k] for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")]
    else:
        raise ValueError(f"Unsupported runner harness: {harness}")
    if not models or any(measurement(value, "native token component") is None for value in components):
        raise ValueError("Missing native models or usage components")
    return models, sum(components)


def discover_runs(iteration, primary, baseline):
    if primary == baseline or primary not in CONFIGS or baseline not in CONFIGS:
        raise ValueError("Select distinct, supported primary and baseline configurations")
    found = []
    for directory in sorted(iteration.glob("eval-*")):
        if not directory.is_dir():
            continue
        for config in (primary, baseline):
            parent = directory / config
            children = sorted(parent.glob("run-*")) if parent.exists() else []
            # The first iterations also used a flat configuration directory.
            if not children and parent.is_dir():
                children = [parent]
            for path in children:
                if not path.is_dir() or path.is_symlink():
                    raise ValueError(f"Invalid run directory: {path}")
                if (path / "outputs").is_symlink():
                    raise ValueError(f"Symlink output directory: {path}")
                if not (path / "grading.json").exists():
                    raise ValueError(f"Missing grading.json: {path}")
                match = re.fullmatch(r"run-([1-9]\d*)", path.name)
                number = int(match[1]) if match else 1
                if path != parent and match is None:
                    raise ValueError(f"Invalid repeat directory: {path}")
                found.append((directory, config, number, path))
    if not found:
        raise ValueError(f"No runs found in {iteration}")
    return found


def run_metadata(directory, path):
    for source in (path / "eval_metadata.json", directory / "eval_metadata.json"):
        if source.exists():
            return read_json(source)
    prompt = directory / "prompt.md"
    if prompt.exists():
        match = re.match(r"eval-(\d+)-?(.*)", directory.name)
        return {"eval_id": int(match[1]), "eval_name": match[2], "prompt": prompt.read_text()}
    raise ValueError(f"Missing task metadata: {path}")


def load_iteration(iteration, primary="with_skill", baseline="without_skill"):
    manifest_path = iteration / "manifest.json"
    manifest = read_json(manifest_path) if manifest_path.exists() else {}
    records, identities, keys = [], set(), set()
    for directory, config, number, path in discover_runs(iteration, primary, baseline):
        metadata = run_metadata(directory, path)
        eval_id = metadata["eval_id"]
        if type(eval_id) is not int or eval_id < 0 or not metadata.get("prompt"):
            raise ValueError(f"Invalid eval metadata: {path}")
        key = (eval_id, config, number)
        if key in keys:
            raise ValueError(f"Duplicate run: {key}")
        keys.add(key)
        grading = read_json(path / "grading.json")
        expected = metadata.get("assertions") or None
        summary = validate_grading(grading, expected)
        recorded = grading.get("summary", {})
        if any(recorded.get(k) != summary[k] for k in ("passed", "failed", "total")) or not math.isclose(
            recorded.get("pass_rate", -1), summary["pass_rate"], abs_tol=0.0005,
        ):
            raise ValueError(f"Grading summary differs from verdicts: {path}")
        timing_path = path / "timing.json"
        timing = read_json(timing_path) if timing_path.exists() else {}
        tokens = measurement(timing.get("total_tokens"), "total_tokens")
        seconds = measurement(timing.get("total_duration_seconds"), "total_duration_seconds")
        if seconds is None and timing.get("duration_ms") is not None:
            seconds = measurement(timing["duration_ms"], "duration_ms") / 1000
        state_path = path / "run.json"
        state = read_json(state_path) if state_path.exists() else {}
        if state and state.get("status") != "complete":
            raise ValueError(f"Executor is not complete: {path}")
        if manifest:
            if not state or state.get("fingerprint") != manifest["fingerprint"]:
                raise ValueError(f"Run does not match the iteration fingerprint: {path}")
            if state.get("configuration") != config or state.get("requested_model") != manifest["model"]:
                raise ValueError(f"Run selection differs from manifest: {path}")
            if timing.get("model") != manifest["model"] or timing.get("harness") != manifest["harness"]:
                raise ValueError(f"Timing model/harness differs from manifest: {path}")
            if tokens is None or seconds is None or seconds <= 0:
                raise ValueError(f"Missing executor usage or duration: {path}")
            load_run(path).require_complete()
            if not (path / "outputs/answer.md").is_file():
                raise ValueError(f"Missing user-facing answer: {path}")
            observed = timing.get("observed_models", [])
            expected_model = model_ref(manifest["model"]) if manifest["harness"] == "opencode" else manifest["model"]
            if not observed or any(model != expected_model for model in observed):
                raise ValueError(f"Observed model differs from requested model: {path}")
            native_models, native_tokens = native_models_and_tokens(path, manifest["harness"])
            if native_models != observed or native_tokens != tokens:
                raise ValueError(f"Recorded usage/model differs from native evidence: {path}")
        identity = (timing.get("harness"), timing.get("model"), timing.get("effort"))
        if identity[1]:
            identities.add(identity)
        records.append({"directory": path, "metadata": metadata, "grading": grading,
                        "timing": timing, "eval_id": eval_id, "configuration": config,
                        "run_number": number, "result": {**summary, "tokens": tokens, "time_seconds": seconds}})
    if len(identities) > 1:
        raise ValueError(f"Mixed harness/model/effort identities in one comparison: {identities}")
    ids = {r["eval_id"] for r in records}
    repeats = manifest.get("repeats", max(r["run_number"] for r in records))
    expected_ids = set(manifest.get("eval_ids", ids))
    expected_keys = {(i, c, n) for i in expected_ids for c in (primary, baseline) for n in range(1, repeats + 1)}
    if keys != expected_keys:
        raise ValueError(f"Incomplete comparison: missing={sorted(expected_keys - keys)}, extra={sorted(keys - expected_keys)}")
    for eval_id in ids:
        related = [r for r in records if r["eval_id"] == eval_id]
        contract = related[0]["grading"]["expectations"]
        for record in related[1:]:
            if [e["text"] for e in record["grading"]["expectations"]] != [e["text"] for e in contract] or record["metadata"]["prompt"] != related[0]["metadata"]["prompt"]:
                raise ValueError(f"Paired runs have different prompts or assertions: eval {eval_id}")
    records.sort(key=lambda r: (r["eval_id"], r["configuration"] != primary, r["run_number"]))
    return manifest, records


def stats(values):
    missing = sum(value is None for value in values)
    measured = [value for value in values if value is not None]
    # Partial averages can hide expensive missing runs. Label the whole metric
    # unknown until every run has a measurement; retain coverage counts.
    if missing or not measured:
        return {"mean": None, "stddev": None, "min": None, "max": None,
                "samples": len(measured), "missing": missing}
    return {"mean": statistics.mean(measured), "stddev": statistics.stdev(measured) if len(measured) > 1 else 0,
            "min": min(measured), "max": max(measured), "samples": len(measured), "missing": 0}


def benchmark(iteration, skill, primary="with_skill", baseline="without_skill"):
    manifest, records = load_iteration(iteration, primary, baseline)
    summary = {config: {metric: stats([r["result"][metric] for r in records if r["configuration"] == config])
                        for metric in ("pass_rate", "time_seconds", "tokens")}
               for config in (primary, baseline)}
    summary["delta"] = {}
    for metric, digits in (("pass_rate", 2), ("time_seconds", 1), ("tokens", 0)):
        a, b = summary[primary][metric]["mean"], summary[baseline][metric]["mean"]
        summary["delta"][metric] = f"{a - b:+.{digits}f}" if a is not None and b is not None else "—"
    timing = records[0]["timing"]
    notes = ["Delta is primary minus baseline. Token totals are recorded component sums, not billing estimates."]
    if not manifest:
        notes.append("Historical iteration: no runner manifest; harness/version and task coverage may be unrecorded.")
    for config in (primary, baseline):
        for metric in ("time_seconds", "tokens"):
            if summary[config][metric]["missing"]:
                notes.append(f"{config}: {metric} is unknown for {summary[config][metric]['missing']} run(s); no character-count fallback or partial average.")
    meta = {"skill_name": skill, "executor_model": manifest.get("model", timing.get("model") or "unknown"),
            "harness": manifest.get("harness", timing.get("harness") or "unknown"),
            "harness_version": manifest.get("harness_version", "unknown"),
            "effort": manifest.get("effort", timing.get("effort")), "skill_sha256": manifest.get("skill_sha256"),
            "evals_run": sorted({r["eval_id"] for r in records}),
            "runs_per_configuration": manifest.get("repeats", max(r["run_number"] for r in records)),
            "primary": primary, "baseline": baseline,
            "timestamp": datetime.now(timezone.utc).isoformat()}
    value = {"schema_version": 1, "metadata": meta, "run_summary": summary, "notes": notes,
             "runs": [{"eval_id": r["eval_id"], "eval_name": r["metadata"].get("eval_name"),
                       "configuration": r["configuration"], "run_number": r["run_number"],
                       "result": r["result"], "expectations": r["grading"]["expectations"],
                       "grader": {"model": r["timing"].get("grader_model"),
                                  "harness": r["timing"].get("grader_harness"),
                                  "tokens": r["timing"].get("grader_tokens"),
                                  "time_seconds": r["timing"].get("grader_duration_seconds"),
                                  "allocation": r["timing"].get("grader_allocation")},
                       "notes": []} for r in records]}
    return value, records


def markdown(value):
    meta, summaries = value["metadata"], value["run_summary"]
    primary, baseline = meta["primary"], meta["baseline"]
    rows = [f"# Skill Benchmark: {meta['skill_name']}", "",
            f"**Harness:** {meta['harness']} ({meta['harness_version']})",
            f"**Model:** {meta['executor_model']}" + (f"; effort {meta['effort']}" if meta.get("effort") else ""),
            f"**Evals:** {', '.join(map(str, meta['evals_run']))}; {meta['runs_per_configuration']} repeat(s) per configuration",
            "", f"| Metric | {primary} | {baseline} | Delta |", "| --- | --- | --- | --- |"]
    for metric, label, scale, digits, unit in (("pass_rate", "Pass rate", 100, 1, "%"),
                                               ("time_seconds", "Executor time", 1, 1, "s"),
                                               ("tokens", "Executor tokens", 1, 0, "")):
        def fmt(stat):
            if stat["mean"] is None:
                return "unknown"
            return f"{stat['mean'] * scale:.{digits}f}{unit} ± {stat['stddev'] * scale:.{digits}f}{unit}"
        rows.append(f"| {label} | {fmt(summaries[primary][metric])} | {fmt(summaries[baseline][metric])} | {summaries['delta'][metric]} |")
    rows += ["", "## Notes", "", *[f"- {note}" for note in value["notes"]]]
    return "\n".join(rows) + "\n"


def upstream_viewer(skill_creator):
    path = skill_creator / "eval-viewer/generate_review.py"
    module = types.ModuleType("upstream_eval_viewer")
    module.__file__ = str(path)
    # Execute the installed renderer without importing through a loader that can
    # write bytecode into the read-only installation. Its main() never runs.
    exec(compile(path.read_text(), str(path), "exec"), module.__dict__)
    if not callable(getattr(module, "embed_file", None)) or not callable(getattr(module, "generate_html", None)):
        raise ValueError("Installed skill-creator does not expose the supported viewer interface")
    return module


def view_runs(iteration, records, upstream):
    runs = []
    text_names = {"Dockerfile", "Makefile", ".dockerignore", ".gitignore", ".nvmrc"}
    for record in records:
        path = record["directory"]
        root = path / "outputs"
        outputs = []
        if not root.is_dir() or root.is_symlink():
            raise ValueError(f"Missing or unsafe output directory: {root}")
        for file in sorted(root.rglob("*")):
            if file.is_symlink():
                raise ValueError(f"Symlink output: {file}")
            if not file.is_file():
                continue
            relative = file.relative_to(root)
            if len(relative.parts) == 1 and file.name in upstream.METADATA_FILES:
                continue
            if file.name in text_names or file.suffix in (".hcl", ".conf", ".ini", ".env"):
                embedded = {"type": "text", "content": file.read_text(errors="replace")}
            else:
                embedded = upstream.embed_file(file)
            embedded["name"] = str(relative)
            outputs.append(embedded)
        runs.append({"id": str(path.relative_to(iteration)).replace("/", "-"),
                     "eval_id": record["eval_id"], "prompt": record["metadata"]["prompt"],
                     "outputs": outputs, "grading": record["grading"]})
    return runs


def viewer_benchmark(value):
    compatible = json.loads(json.dumps(value))
    # The upstream renderer calls toFixed() on means. An absent statistic is its
    # supported unknown representation; canonical benchmark.json keeps nulls.
    for config, metrics in compatible["run_summary"].items():
        if config != "delta":
            for metric in list(metrics):
                if metrics[metric]["mean"] is None:
                    del metrics[metric]
    return compatible


def safe_html(upstream, runs, title, previous, value):
    html = upstream.generate_html(runs, title, previous, viewer_benchmark(value))
    marker = "const EMBEDDED_DATA = "
    start = html.index(marker) + len(marker)
    _, length = json.JSONDecoder().raw_decode(html[start:])
    payload = html[start:start + length].replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return html[:start] + payload + html[start + length:]


def write_report(iteration, value):
    write_json(iteration / "benchmark.json", value)
    (iteration / "benchmark.md").write_text(markdown(value))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("benchmark", "view"))
    parser.add_argument("iteration", type=Path)
    parser.add_argument("--skill-name", required=True)
    parser.add_argument("--primary", default="with_skill")
    parser.add_argument("--baseline", default="without_skill")
    parser.add_argument("--skill-creator", type=Path, default=ROOT / ".agents/skills/skill-creator")
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--open", action="store_true", help="Open the static review.html in the default browser")
    args = parser.parse_args()
    iteration = args.iteration.resolve()
    value, records = benchmark(iteration, args.skill_name, args.primary, args.baseline)
    write_report(iteration, value)
    print(f"Validated {len(records)} runs; wrote {iteration / 'benchmark.json'}")
    if args.action == "view":
        upstream = upstream_viewer(args.skill_creator.resolve())
        previous = {}
        if args.previous:
            _, old_records = load_iteration(args.previous, args.primary, args.baseline)
            feedback_path = args.previous / "feedback.json"
            feedback = read_json(feedback_path) if feedback_path.exists() else {}
            by_id = {r["run_id"]: r.get("feedback", "") for r in feedback.get("reviews", [])}
            previous = {r["id"]: {"outputs": r["outputs"], "feedback": by_id.get(r["id"], "")}
                        for r in view_runs(args.previous, old_records, upstream)}
        meta = value["metadata"]
        title = f"{args.skill_name} · {meta['harness']} · {meta['executor_model']}"
        path = iteration / "review.html"
        path.write_text(safe_html(upstream, view_runs(iteration, records, upstream), title, previous, value))
        print(f"Wrote {path}")
        if args.open:
            webbrowser.open(path.as_uri())


if __name__ == "__main__":
    main()
