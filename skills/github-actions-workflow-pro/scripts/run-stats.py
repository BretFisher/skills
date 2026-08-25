#!/usr/bin/env python3
"""run-stats.py — recent GitHub Actions run history for every workflow in a repo:
failures, per-workflow and per-job durations over the last N completed runs,
consistency between runs, ranked longest first.

Why a script: the audit needs the same dozen `gh run list` / `gh run view` calls
for every workflow, and the ranking math is easy to get subtly wrong by hand.

Requires: gh (authenticated). Python 3.9+, stdlib only.

Usage:
  run-stats.py [--runs N] [--repo owner/repo] [--branch main] [--markdown]

  --runs N          completed runs to inspect per workflow (default 3)
  --repo owner/repo repo to inspect (default: the one the current directory belongs to)
  --branch NAME     only runs on this branch (default: all branches)
  --markdown        print ranked tables instead of JSON

Output (JSON, stdout):
  {"repo": "...", "runs_per_workflow": 3,
   "workflows": [ {name, path, runs:[{id,url,conclusion,event,branch,title,started,duration_s}],
                   mean_s, min_s, max_s, spread_ratio, failures, latest_failing} ... ],   # longest mean first
   "jobs":      [ {workflow, job, n, mean_s, max_s, failures} ... ],                      # longest mean first
   "failures":  [ {workflow, run_id, url, title, started, still_failing} ... ]}
  spread_ratio = max_s / min_s; above ~1.5 the workflow's time is inconsistent, so
  investigate the slow run (cache miss? flaky test? queue wait?) before optimizing.

Exit codes: 0 ok, 2 bad arguments, 4 gh api failure, 5 gh missing or not authenticated
"""
import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone


def die(code, msg):
    print(f"run-stats: {msg}", file=sys.stderr)
    sys.exit(code)


def gh(*args, raw=False):
    try:
        out = subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout
    except subprocess.CalledProcessError as e:
        die(4, f"gh {' '.join(args[:3])}... failed: {e.stderr.strip()}")
    if raw:
        return out.strip()
    return json.loads(out) if out.strip() else []


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def seconds(a, b):
    a, b = ts(a), ts(b)
    return round((b - a).total_seconds()) if a and b else None


def main():
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("--repo", default=None)
    p.add_argument("--branch", default=None)
    p.add_argument("--markdown", action="store_true")
    a = p.parse_args()
    if a.runs < 1:
        die(2, "--runs must be at least 1")
    if not shutil.which("gh"):
        die(5, "gh CLI not found; install it and run 'gh auth login'")
    if subprocess.run(["gh", "auth", "status"], capture_output=True).returncode != 0:
        die(5, "gh is not authenticated; run 'gh auth login'")

    repo_flag = ["-R", a.repo] if a.repo else []
    repo_name = a.repo or gh("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner", raw=True)

    workflows = [w for w in gh("workflow", "list", *repo_flag, "--json", "name,id,path,state", "--limit", "100")
                 if w["path"].startswith(".github/workflows/")]

    result = {"repo": repo_name, "runs_per_workflow": a.runs, "workflows": [], "jobs": [], "failures": []}
    job_acc = {}  # (workflow, job) -> list of (duration, conclusion)

    for w in workflows:
        args = ["run", "list", *repo_flag, "--workflow", str(w["id"]), "--status", "completed",
                "--limit", str(a.runs), "--json", "databaseId,conclusion,startedAt,updatedAt,event,headBranch,url,displayTitle"]
        if a.branch:
            args += ["--branch", a.branch]
        runs = gh(*args)
        entry = {"name": w["name"], "path": w["path"], "runs": [], "failures": 0, "latest_failing": False}
        durations = []
        for i, r in enumerate(runs):
            d = seconds(r["startedAt"], r["updatedAt"])
            entry["runs"].append({"id": r["databaseId"], "url": r["url"], "conclusion": r["conclusion"],
                                  "event": r["event"], "branch": r["headBranch"], "title": r["displayTitle"],
                                  "started": r["startedAt"], "duration_s": d})
            if d is not None:
                durations.append(d)
            if r["conclusion"] in ("failure", "timed_out", "startup_failure"):
                entry["failures"] += 1
                if i == 0:
                    entry["latest_failing"] = True
                result["failures"].append({"workflow": w["name"], "run_id": r["databaseId"], "url": r["url"],
                                           "title": r["displayTitle"], "started": r["startedAt"],
                                           "conclusion": r["conclusion"], "still_failing": False})
            for j in gh("run", "view", *repo_flag, str(r["databaseId"]), "--json", "jobs",
                        "--jq", "[.jobs[] | {name, conclusion, startedAt, completedAt}]"):
                jd = seconds(j.get("startedAt"), j.get("completedAt"))
                if jd is not None:
                    job_acc.setdefault((w["name"], j["name"]), []).append((jd, j.get("conclusion")))
        if durations:
            entry.update(mean_s=round(sum(durations) / len(durations)), min_s=min(durations), max_s=max(durations),
                         spread_ratio=round(max(durations) / max(min(durations), 1), 2))
        else:
            entry.update(mean_s=None, min_s=None, max_s=None, spread_ratio=None)
        result["workflows"].append(entry)
        for f in result["failures"]:
            if f["workflow"] == w["name"]:
                f["still_failing"] = entry["latest_failing"]

    result["workflows"].sort(key=lambda e: e["mean_s"] or -1, reverse=True)
    for (wf, job), vals in job_acc.items():
        ds = [d for d, _ in vals]
        result["jobs"].append({"workflow": wf, "job": job, "n": len(ds), "mean_s": round(sum(ds) / len(ds)),
                               "max_s": max(ds), "failures": sum(1 for _, c in vals if c == "failure")})
    result["jobs"].sort(key=lambda j: j["mean_s"], reverse=True)

    if not a.markdown:
        print(json.dumps(result, indent=2))
        return

    def mmss(s):
        return "-" if s is None else f"{s // 60}m{s % 60:02d}s"

    print(f"# Run history: {repo_name} (last {a.runs} completed runs per workflow)\n")
    print("## Workflows, longest mean first\n")
    print("| Workflow | Mean | Min | Max | Spread | Fails/runs | Latest |")
    print("|---|---|---|---|---|---|---|")
    for e in result["workflows"]:
        latest = "FAILING" if e["latest_failing"] else ("ok" if e["runs"] else "no runs")
        spread = "-" if e["spread_ratio"] is None else f"{e['spread_ratio']}x"
        print(f"| {e['name']} (`{e['path'].split('/')[-1]}`) | {mmss(e['mean_s'])} | {mmss(e['min_s'])} | "
              f"{mmss(e['max_s'])} | {spread} | {e['failures']}/{len(e['runs'])} | {latest} |")
    print("\n## Jobs, longest mean first\n")
    print("| Workflow | Job | Mean | Max | Runs | Fails |")
    print("|---|---|---|---|---|---|")
    for j in result["jobs"]:
        print(f"| {j['workflow']} | {j['job']} | {mmss(j['mean_s'])} | {mmss(j['max_s'])} | {j['n']} | {j['failures']} |")
    if result["failures"]:
        print("\n## Recent failures\n")
        for f in result["failures"]:
            flag = " (still failing on latest run)" if f["still_failing"] else ""
            print(f"- {f['workflow']}: run {f['run_id']} \"{f['title']}\" {f['started'][:10]} {f['conclusion']}{flag} — {f['url']}")


if __name__ == "__main__":
    main()
