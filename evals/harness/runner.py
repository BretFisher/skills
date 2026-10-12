"""Run isolated skill tasks and residual graders through native CLI adapters.

Use make eval-run / eval-grade. No dependencies outside the Python standard
library and the selected CLI. Native evidence and failure state are retained.
"""

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

from .evidence import EvidenceError, load_run
from .setup import prepare_updater, source_plan, validate_adapter


ROOT = Path(__file__).resolve().parents[2]
DEPENDENCIES = {"gha-audit": ("github-actions-workflow-pro",)}
TEMP = Path(os.environ.get("TMPDIR", tempfile.gettempdir())) / "opencode"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, suffix=".tmp", delete=False) as file:
        file.write(json.dumps(value, indent=2) + "\n")
        temporary = Path(file.name)
    temporary.replace(path)


def command(args, cwd, env=None, timeout=60):
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        # Native stderr is saved by the caller for model execution. Do not echo
        # provider errors here: they can contain credential-bearing URLs.
        raise RuntimeError(f"{Path(args[0]).name} {args[1]} exited {result.returncode}")
    return result.stdout


def safe_relative(value):
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] == ".git":
        raise ValueError(f"Unsafe fixture destination: {value}")
    return path


def fixture_map(spec, skill):
    validate_adapter(spec, skill)
    explicit = spec.get("fixture_map", {})
    mapping = {}
    files = spec.get("files", [])
    for source in files:
        roots = [ROOT / "evals" / name / "fixtures" for name in (skill, *DEPENDENCIES.get(skill, ()))]
        resolved = (ROOT / source).resolve()
        fixture_root = next((root for root in roots if resolved.is_relative_to(root)), None)
        if fixture_root is None or not resolved.is_file():
            raise ValueError(f"Missing or unsafe fixture: {source}")
        if source in explicit:
            destination = explicit[source]
        else:
            relative = resolved.relative_to(fixture_root)
            if len(relative.parts) > 1:
                destination = str(Path(*relative.parts[1:]))
            elif skill in ("github-actions-workflow-pro", "gha-audit") and relative.suffix in (".yml", ".yaml"):
                # Use the filename explicitly named in the task for a single workflow.
                workflows = [f for f in files if f.endswith((".yml", ".yaml")) and "dependabot" not in f]
                filename = "ci.yml" if len(workflows) == 1 and "ci.yml" in spec["prompt"] else relative.name
                destination = f".github/workflows/{filename}"
                if "dependabot" in relative.name:
                    destination = ".github/dependabot.yml"
            else:
                destination = str(relative)
        destination = str(safe_relative(destination))
        if destination in mapping.values():
            raise ValueError(f"Fixture destination collision: {destination}")
        mapping[source] = destination
    if set(explicit) - set(files):
        raise ValueError("fixture_map contains a source absent from files")
    return mapping


def tree_hash(directory):
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            digest.update(str(path.relative_to(directory)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def clean_environment(home):
    # Keep authentication in the native data store, not in the eval artifacts.
    env = {k: v for k, v in os.environ.items() if not k.startswith(("OPENCODE_", "CLAUDE_CODE_")) and k != "CLAUDECODE"}
    data = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / "config"),
               XDG_DATA_HOME=data, XDG_CACHE_HOME=str(home / "cache"),
               XDG_STATE_HOME=str(home / "state"))
    return env


def model_ref(value):
    base, _, variant = value.partition("#")
    provider, sep, model = base.partition("/")
    if not sep or not provider or not model:
        raise ValueError("OpenCode requires provider/model#variant")
    ref = {"providerID": provider, "id": model}
    if variant:
        ref["variant"] = variant
    return ref


def oc_api(work, env, method, path, data=None):
    args = ["opencode", "api", "--standalone", method, path]
    if data is not None:
        args.extend(["--data", json.dumps(data)])
    return json.loads(command(args, work, env, timeout=120))


def opencode_config(home, work, skill, mode, skill_source=None):
    config_dir = home / "config/opencode"
    config_dir.mkdir(parents=True)
    permissions = [
        {"action": "*", "resource": "*", "effect": "deny"},
        *[{"action": action, "resource": "*", "effect": "allow"}
          for action in ("read", "glob", "grep", "edit", "shell", "webfetch", "websearch")],
        {"action": "external_directory", "resource": "*", "effect": "deny"},
        {"action": "external_directory", "resource": str(home / "config/opencode/skills") + "/**", "effect": "allow"},
        {"action": "read", "resource": str(ROOT) + "/**", "effect": "deny"},
        {"action": "edit", "resource": str(ROOT) + "/**", "effect": "deny"},
        {"action": "shell", "resource": "*git push*", "effect": "deny"},
        {"action": "shell", "resource": "*brew install*", "effect": "deny"},
        {"action": "shell", "resource": "*npm install -g*", "effect": "deny"},
    ]
    if mode == "with_skill":
        for name in (skill, *DEPENDENCIES.get(skill, ())):
            destination = config_dir / "skills" / name
            shutil.copytree(skill_source if name == skill and skill_source else ROOT / "skills" / name, destination)
            permissions.append({"action": "skill", "resource": name, "effect": "allow"})
    config = {"$schema": "https://opencode.ai/config.json", "permissions": permissions,
              "formatter": False, "snapshots": False, "warming": False}
    write_json(config_dir / "opencode.json", config)
    return config


def run_process(args, work, env, run, timeout):
    started = time.monotonic()
    with (run / "cli-output.jsonl").open("w") as stdout, (run / "cli-stderr.log").open("w") as stderr:
        process = subprocess.Popen(args, cwd=work, env=env, stdout=stdout, stderr=stderr)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            raise RuntimeError(f"Executor exceeded {timeout}s; its own CLI process was stopped")
    elapsed = time.monotonic() - started
    if code:
        raise RuntimeError(f"Executor exited {code}; see cli-stderr.log")
    return elapsed


def opencode_execute(prompt, work, home, run, args, config):
    env = clean_environment(home)
    # CLI-created sessions are durable. Create first to retain their ID even on failure.
    ref = model_ref(args.model)
    registered = oc_api(work, env, "get", f"/api/skill?location[directory]={work}")
    write_json(run / "skill-catalog.json", registered)
    write_json(run / "effective-config.json", config)
    # config discovery is checked independently of the runner's generated document.
    sources = oc_api(work, env, "get", f"/api/config?location[directory]={work}")
    write_json(run / "config-sources.json", sources)
    for source in sources:
        path = source.get("path")
        if path and not Path(path).is_relative_to(home):
            raise RuntimeError("Unexpected ambient OpenCode configuration; isolation refused")
    session = oc_api(work, env, "post", "/api/session", {
        "location": {"directory": str(work)}, "model": ref, "title": "skill eval",
    })["data"]["id"]
    write_json(run / "session.json", {"id": session})
    started = time.monotonic()
    try:
        elapsed = run_process(["opencode", "run", "--standalone", "--format", "json",
                               "--session", session, "--model", args.model, "--auto", prompt],
                              work, env, run, args.timeout)
    finally:
        export = oc_api(work, env, "get", f"/api/experimental/session/{session}/export?sanitize=false")
        write_json(run / "session-export.json", export)
        write_json(run / "timing.json", {"total_duration_seconds": time.monotonic() - started})
    messages = export["data"]["messages"]
    assistants = [m for m in messages if m.get("type") == "assistant"]
    if not assistants or any(m.get("error") for m in assistants):
        raise RuntimeError("Session has no successful assistant output")
    observed = [m["model"] for m in assistants]
    if any(m != ref for m in observed):
        raise RuntimeError(f"Model mismatch: requested {ref}, observed {observed}")
    usage = {"input": 0, "output": 0, "reasoning": 0, "cache_read": 0, "cache_write": 0}
    for message in assistants:
        tokens = message.get("tokens")
        if tokens is None:
            raise RuntimeError("Missing usage in assistant message")
        for key in ("input", "output", "reasoning"):
            usage[key] += tokens[key]
        usage["cache_read"] += tokens["cache"]["read"]
        usage["cache_write"] += tokens["cache"]["write"]
    # Provider token components remain authoritative. Reasoning is a subset of
    # output on some providers; do not add it again to this compatibility total.
    timing = {"total_duration_seconds": elapsed, "duration_ms": round(elapsed * 1000),
              "total_tokens": usage["input"] + usage["output"] + usage["cache_read"] + usage["cache_write"],
              "usage": usage, "token_accounting": "input + output + cache.read + cache.write; reasoning not added",
              "model": args.model, "harness": "opencode", "observed_models": observed}
    write_json(run / "timing.json", timing)
    return "\n\n".join(c["text"] for m in assistants for c in m.get("content", []) if c.get("type") == "text")


def claude_execute(prompt, work, home, run, args, config):
    # Safe mode removes ambient skills/instructions while retaining native auth.
    # Task-quality evals read the explicitly supplied skill snapshot as a file.
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    tools = "" if config.get("grader") else "Read,Write,Edit,Bash,Glob,Grep,WebFetch,WebSearch"
    elapsed = run_process([
        "claude", "--safe-mode", "-p", "--output-format", "stream-json", "--verbose",
        "--model", args.model, "--effort", args.effort, "--permission-mode", "dontAsk",
        "--tools", tools,
        *(["--allowedTools", tools] if tools else []),
        "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', prompt,
    ], work, env, run, args.timeout)
    shutil.copyfile(run / "cli-output.jsonl", run / "raw-transcript.jsonl")
    records = [json.loads(line) for line in (run / "raw-transcript.jsonl").read_text().splitlines() if line.strip()]
    results = [r for r in records if r.get("type") == "result"]
    if not results or results[-1].get("is_error"):
        raise RuntimeError("Claude run has no successful result")
    assistants = [r["message"] for r in records if r.get("type") == "assistant"]
    observed = sorted({m["model"] for m in assistants})
    if not observed or any(m != args.model for m in observed):
        raise RuntimeError(f"Use a full Claude model ID; observed model mismatch: {observed}")
    usage = results[-1].get("usage")
    if not usage or any(k not in usage for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")):
        raise RuntimeError("Missing Claude usage")
    write_json(run / "timing.json", {
        "total_duration_seconds": elapsed, "duration_ms": round(elapsed * 1000),
        "total_tokens": sum(usage[k] for k in (
            "input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")),
        "usage": usage, "harness": "claude", "model": args.model,
        "effort": args.effort, "observed_models": observed,
    })
    write_json(run / "effective-config.json", {"safe_mode": True, "effort": args.effort})
    return results[-1].get("result", "")


ADAPTERS = {"opencode": opencode_execute, "claude": claude_execute}


def prepare_work(work, mapping, setup=None):
    work.mkdir()
    command(["git", "init", "-q"], work)
    command(["git", "config", "--local", "include.path", str(ROOT / "evals/eval.gitconfig")], work)
    for source, destination in mapping.items():
        target = work / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / source, target)
    if setup:
        setup(work)
    command(["git", "add", "--all"], work)
    command(["git", "-c", "core.hooksPath=/dev/null", "commit", "--no-gpg-sign", "-q", "--allow-empty", "-m", "eval: pristine fixtures"], work)
    (work / ".git/info/exclude").write_text(".eval-outputs/\n")
    return command(["git", "rev-parse", "HEAD"], work).strip()


def collect_outputs(work, run, final_text):
    destination = run / "outputs"
    supplied = work / ".eval-outputs"
    destination.mkdir()
    if supplied.exists():
        if any(path.is_symlink() for path in supplied.rglob("*")):
            raise RuntimeError("Executor output contains a symlink; collection refused")
        shutil.copytree(supplied, destination, dirs_exist_ok=True)
    if not (destination / "answer.md").exists():
        (destination / "answer.md").write_text(final_text + "\n")
    changed = command(["git", "diff", "--name-only", "HEAD", "-z"], work).split("\0")
    changed += command(["git", "ls-files", "--others", "--exclude-standard", "-z"], work).split("\0")
    for name in filter(None, changed):
        path = work / safe_relative(name)
        if path.is_file() and not path.is_symlink():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copyfile(path, target)
    shutil.copytree(work, run / "work", ignore=shutil.ignore_patterns(".eval-outputs"))


def transcript(run, spec, evidence):
    write_json(run / "evidence.json", {"schema_version": 1, "source": evidence.source,
                                      "complete": evidence.complete, "events": evidence.events})
    rows = [f"# Captured executor evidence\n\n## Eval Prompt\n\n{spec['prompt']}\n\n## Tool calls\n"]
    for item in evidence.events:
        if item["type"] == "tool_input":
            rows.append(f"### {item['name']} ({item['call_id']})\n\n```json\n{json.dumps(item['input'], indent=2)}\n```\n")
        else:
            rows.append(f"Result ({item['call_id']}), error={item['error']}, {len(item['output'])} captured characters.\n")
    (run / "transcript.md").write_text("\n".join(rows))


def execute_one(spec, mode, number, iteration, args, fingerprint):
    slug = spec.get("name", f"task-{spec['id']}")
    slug = re.sub(r"[^a-z0-9-]", "-", slug.lower())
    eval_dir = iteration / f"eval-{spec['id']}-{slug}"
    run = eval_dir / mode / f"run-{number}"
    if run.exists():
        if args.resume and (run / "run.json").exists():
            prior = json.loads((run / "run.json").read_text())
            if prior.get("status") == "complete" and prior.get("fingerprint") == fingerprint:
                print(f"skip complete: {run.relative_to(ROOT)}", flush=True)
                return
        raise RuntimeError(f"Existing run retained: {run}; select a new iteration")
    run.mkdir(parents=True)
    mapping = fixture_map(spec, args.skill)
    metadata = {"eval_id": spec["id"], "eval_name": slug, "prompt": spec["prompt"],
                "assertions": spec.get("expectations", spec.get("assertions", [])), "fixture_map": mapping}
    write_json(eval_dir / "eval_metadata.json", metadata)
    write_json(run / "eval_metadata.json", metadata)
    (eval_dir / "prompt.md").write_text(spec["prompt"] + "\n")
    state = {"schema_version": 1, "status": "running", "fingerprint": fingerprint,
             "harness": args.harness, "requested_model": args.model, "configuration": mode}
    write_json(run / "run.json", state)
    TEMP.mkdir(parents=True, exist_ok=True)
    home = Path(tempfile.mkdtemp(prefix="skill-eval-", dir=TEMP))
    work = home / "work"
    # Preserve failed workspaces for diagnosis. Their paths are recorded, not reused.
    state["workspace"] = str(work)
    try:
        skill_source = work / "skills/k8s-catch-up" if spec.get("setup_adapter") else None
        setup = (lambda directory: prepare_updater(directory, home, args.source_plan)) if skill_source else None
        state["fixture_commit"] = prepare_work(work, mapping, setup)
        write_json(run / "run.json", state)
        config = opencode_config(home, work, args.skill, mode, skill_source) if args.harness == "opencode" else {}
        skill_line = ""
        if mode == "with_skill":
            if args.harness == "opencode":
                skill_line = f"Load the {args.skill} skill first and follow it."
            else:
                snapshot = home / "skill" / args.skill
                shutil.copytree(skill_source or ROOT / "skills" / args.skill, snapshot)
                skill_line = f"Read {snapshot}/SKILL.md first and follow it."
        prompt = (
            "Execute this user task in the current repository. The user is unavailable; "
            "state necessary defaults. Install nothing. Keep credentials private. "
            "Keep the initial fixture commit unchanged. "
            "Save your final user-facing answer to .eval-outputs/answer.md. "
            "Save proposed files there using their repository-relative paths. "
            "Apply edits in the repository when the task requests edits.\n\n"
            f"{skill_line}\n\nTask:\n{spec['prompt']}\n"
        )
        if skill_source:
            prompt += ("\nThe local Kubernetes sources are in " + str(home / "cache/k8s-catch-up") +
                       ". Run the source helper with --offline --cache-dir pointing there, before its subcommand. "
                       "Use those copies only; do not fetch or refresh source repositories.\n")
        (run / "executor-prompt.md").write_text(prompt)
        final = ADAPTERS[args.harness](prompt, work, home, run, args, config)
        evidence = load_run(run).require_complete()
        transcript(run, spec, evidence)
        current_head = command(["git", "rev-parse", "HEAD"], work).strip()
        if current_head != state["fixture_commit"]:
            raise RuntimeError("Executor changed HEAD; pristine fixture commit contract violated")
        collect_outputs(work, run, final)
        state["status"] = "complete"
    except Exception as exc:
        state.update(status="failed", error=str(exc))
        raise
    finally:
        write_json(run / "run.json", state)
    print(f"complete: {run.relative_to(ROOT)}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", required=True)
    parser.add_argument("--iteration", required=True, help="Iteration suffix, for example 24-opencode-sol")
    parser.add_argument("--harness", choices=ADAPTERS, default="opencode")
    parser.add_argument("--model", required=True, help="Full model ID; OpenCode accepts provider/model#variant")
    parser.add_argument("--effort", choices=("low", "medium", "high", "xhigh", "max"), default="high", help="Claude only")
    parser.add_argument("--evals", help="Comma-separated eval IDs; default: all")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--resume", action="store_true", help="Skip only matching completed runs; retain failed runs")
    parser.add_argument("--prepare-only", action="store_true", help="Validate the plan without model calls")
    parser.add_argument("--source-cache", type=Path, default=Path.home() / ".cache/k8s-catch-up",
                        help="Existing local Kubernetes source checkouts for updater tasks")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.skill) or not re.fullmatch(r"[A-Za-z0-9-]+", args.iteration):
        parser.error("Use safe skill and iteration names")
    if min(args.repeat, args.jobs, args.timeout) < 1:
        parser.error("repeat, jobs, and timeout must be positive")
    if args.harness == "opencode":
        model_ref(args.model)
    definitions = ROOT / "evals" / args.skill / "evals.json"
    specs = json.loads(definitions.read_text())["evals"]
    requested = {int(i) for i in args.evals.split(",")} if args.evals else {s["id"] for s in specs}
    if requested - {s["id"] for s in specs}:
        parser.error("Unknown eval ID")
    specs = [s for s in specs if s["id"] in requested]
    mappings = {str(s["id"]): fixture_map(s, args.skill) for s in specs}
    args.source_plan = source_plan(args.source_cache) if any(s.get("setup_adapter") for s in specs) else None
    version = command([args.harness, "--version"], ROOT).strip() if not args.prepare_only else "not queried"
    skill_hash = tree_hash(ROOT / "skills" / args.skill)
    plan = {"schema_version": 1, "harness": args.harness, "harness_version": version,
            "model": args.model, "effort": args.effort if args.harness == "claude" else None,
             "skill": args.skill, "skill_sha256": skill_hash, "eval_ids": sorted(requested),
             "dependency_hashes": {name: tree_hash(ROOT / "skills" / name) for name in DEPENDENCIES.get(args.skill, ())},
             "source_plan": args.source_plan,
            "repeats": args.repeat, "fixtures": mappings,
            "definitions_sha256": hashlib.sha256(definitions.read_bytes()).hexdigest(),
            "runner_sha256": tree_hash(Path(__file__).parent),
            "fixture_hashes": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for s in specs for f in s.get("files", [])}}
    fingerprint = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    if args.prepare_only:
        print(json.dumps(plan, indent=2))
        return
    iteration = ROOT / "evals" / args.skill / "runs" / f"iteration-{args.iteration}"
    manifest = iteration / "manifest.json"
    if manifest.exists() and json.loads(manifest.read_text()).get("fingerprint") != fingerprint:
        parser.error("Iteration metadata differs; select a new iteration")
    write_json(manifest, {**plan, "fingerprint": fingerprint})
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        tasks = [pool.submit(execute_one, spec, mode, n, iteration, args, fingerprint)
                 for spec in specs for n in range(1, args.repeat + 1)
                 for mode in ("with_skill", "without_skill")]
        for task in concurrent.futures.as_completed(tasks):
            try:
                task.result()
            except Exception as exc:
                failures.append(str(exc))
    if failures:
        raise SystemExit("\n".join(failures))


if __name__ == "__main__":
    main()
