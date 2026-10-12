#!/usr/bin/env python3
"""checks.py: deterministic grader for the gha-audit evals.

Grades every assertion a program can decide from the work repo, the report (outputs/answer.md), the proposed
files in outputs/, and the tool calls in the raw log. See AGENTS.md, "Deterministic checks before model
judgment", and docs/eval-walkthrough.md.

Usage:
  checks.py --write [--force] <run-dir>...   write grading.json (program verdicts; null for the model)
  checks.py --finalize <run-dir>...          recompute summary, strip excerpts; exit 1 if a null remains
  checks.py --batch [--budget=60000] <run-dir>...
  checks.py --kinds                          markdown table of program/split/model per eval (coverage.md)
  <run-dir> = evals/gha-audit/runs/<iteration>/eval-N-<name>/<config>/run-M

`--scanners` is accepted and ignored so `make eval-check` works for every skill.
"""
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from harness.evidence import tool_calls
EVALS = json.load(open(f"{HERE}/evals.json"))["evals"]


def read(p):
    return open(p, errors="ignore").read() if os.path.isfile(p) else ""


class Run:
    def __init__(self, d):
        self.dir = d
        self.eval = int(re.search(r"eval-(\d+)", d).group(1))
        self.spec = next(e for e in EVALS if e["id"] == self.eval)
        self.answer = read(f"{d}/outputs/answer.md")
        self.calls = tool_calls(f"{d}/raw-transcript.jsonl")
        self.outputs = [os.path.basename(p) for p in glob.glob(f"{d}/outputs/**/*.y*ml", recursive=True)]
        self.grading = json.load(open(f"{d}/grading.json")) if os.path.exists(f"{d}/grading.json") else None

    def section(self, heading):
        m = re.search(rf"^## {re.escape(heading)}\b.*?(?=^## |\Z)", self.answer, re.M | re.S)
        return m.group(0) if m else ""


def ok(cond, ev):
    return (bool(cond), ev)


def untouched(r):
    out = subprocess.run(["git", "status", "--porcelain", ".github/workflows"], cwd=f"{r.dir}/work", capture_output=True, text=True).stdout.strip()
    return ok(not out, "clean" if not out else f"changed: {out.splitlines()[:3]}")


def headings(*hs):
    def f(r):
        miss = [h for h in hs if not re.search(rf"^## {re.escape(h)}\b", r.answer, re.M)]
        return ok(not miss, "all headings" if not miss else f"missing {miss}")
    return f


def e0_3(r):
    miss = [n for n in ("insecure-ci.yml", "slow-ci.yml", "deploy-static-keys.yml") if n not in r.answer]
    return ok(not miss, "all named" if not miss else f"missing {miss}")


def e0_4(r):
    al, zz = re.search(r"\bactionlint\b", r.calls), re.search(r"\bzizmor\b|scan\.sh|validate\.sh", r.calls)
    return ok(al and zz or re.search(r"validate\.sh", r.calls), f"actionlint={bool(al)} zizmor={bool(zz)}")


def e1_3(r):
    in_out = "slow-ci.yml" in r.outputs
    in_diff = "slow-ci.yml" in r.section("Proposed diff")
    return ok(not in_out and not in_diff, f"slow-ci.yml in outputs={in_out} in proposed diff={in_diff}")


CHECKS = {
    (0, 1): untouched, (0, 2): headings("Hard findings", "Speed", "Proposed diff"), (0, 3): e0_3, (0, 4): e0_4,
    (1, 1): untouched, (1, 2): headings("Hard findings", "Proposed diff"), (1, 3): e1_3,
}
SPLIT = set()


def context(run):
    return [{"source": "answer", "text": run.answer[:12000]}]


def kind(eid, idx):
    if (eid, idx) in SPLIT:
        return "split"
    return "program" if (eid, idx) in CHECKS else "model"


def grade(run):
    exps = []
    for i, text in enumerate(run.spec["expectations"], 1):
        fn = CHECKS.get((run.eval, i))
        passed, ev = fn(run) if fn else (None, "model: judgment only")
        k = kind(run.eval, i)
        e = {"text": text, "passed": passed, "graded_by": "program" if passed is not None else "model", "evidence": f"{'program' if passed is not None else 'model'} ({k}): {ev}"}
        if passed is None:
            e["context"] = context(run)
        exps.append(e)
    return exps


def summary(exps):
    n = len(exps)
    p = sum(1 for e in exps if e["passed"] is True)
    nulls = sum(1 for e in exps if e["passed"] is None)
    return {"total": n, "passed": p, "failed": n - p - nulls, "null": nulls, "pass_rate": round(p / n, 3) if n else 0}


def write(run, force):
    if run.grading and not force:
        print(f"skip (exists): {run.dir}")
        return
    exps = grade(run)
    nulls = [i for i, e in enumerate(exps) if e["passed"] is None]
    g = {"eval_id": run.eval, "eval_name": run.spec["name"], "expectations": exps, "summary": summary(exps)}
    if nulls:
        g["residual"] = {"null_indices": nulls, "prompt": run.spec["prompt"]}
    json.dump(g, open(f"{run.dir}/grading.json", "w"), indent=2)
    print(f"{run.dir}: {g['summary']}")


def finalize(run):
    g = run.grading
    if not g:
        sys.exit(f"no grading.json in {run.dir}")
    for e in g["expectations"]:
        e.pop("context", None)
    g.pop("residual", None)
    g["summary"] = summary(g["expectations"])
    json.dump(g, open(f"{run.dir}/grading.json", "w"), indent=2)
    print(f"{run.dir}: {g['summary']}")
    return g["summary"]["null"]


def batch(runs, budget):
    groups, cur, size = [], [], 0
    for run in runs:
        g = run.grading
        if not g or not any(e["passed"] is None for e in g["expectations"]):
            continue
        n = sum(len(c["text"]) for e in g["expectations"] if e["passed"] is None for c in e.get("context", []))
        if cur and size + n > budget:
            groups.append(cur)
            cur, size = [], 0
        cur.append(run.dir)
        size += n
    if cur:
        groups.append(cur)
    if not groups:
        print("no residual nulls")
        return
    it = os.path.dirname(os.path.dirname(os.path.dirname(groups[0][0])))
    os.makedirs(f"{it}/grader-batches", exist_ok=True)
    for i, grp in enumerate(groups, 1):
        lines = ["Grade these runs. For each file below:", ""]
        for d in grp:
            lines.append(f"- `{d}/grading.json`")
        lines += ["", "Its `residual` object lists the null indices and the task prompt. Each null entry has a `context` array of",
                  "excerpts (the report). Judge each from the excerpts: set `passed`,",
                  "replace `evidence` with quoted evidence, set `graded_by` to \"model\". Open a source file only if an excerpt",
                  "is insufficient, and say so in `evidence`. Leave every other entry untouched, recompute `summary`, write the",
                  "file back. No `timing` object, no `claims`; `eval_feedback` only if an assertion looked weak."]
        open(f"{it}/grader-batches/batch-{i}.md", "w").write("\n".join(lines) + "\n")
        print(f"batch-{i}.md: {len(grp)} runs")


def kinds():
    print("| Eval | Assertions | program | split | model | split indices | model indices |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    tot = [0, 0, 0, 0]
    for e in EVALS:
        ks = [kind(e["id"], i) for i in range(1, len(e["expectations"]) + 1)]
        sp = " ".join(f"#{i}" for i, k in enumerate(ks, 1) if k == "split") or "—"
        mo = " ".join(f"#{i}" for i, k in enumerate(ks, 1) if k == "model") or "—"
        row = [len(ks), ks.count("program"), ks.count("split"), ks.count("model")]
        tot = [a + b for a, b in zip(tot, row)]
        print(f"| e{e['id']} | {row[0]} | {row[1]} | {row[2]} | {row[3]} | {sp} | {mo} |")
    print(f"| **all** | **{tot[0]}** | **{tot[1]}** | **{tot[2]}** | **{tot[3]}** | | |")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    if "--kinds" in flags:
        return kinds()
    runs = [Run(d) for d in args if os.path.isdir(d)]
    if "--write" in flags:
        for r in runs:
            write(r, "--force" in flags)
    elif "--finalize" in flags:
        left = sum(finalize(r) for r in runs)
        if left:
            sys.exit(f"{left} assertion(s) still null")
    elif "--batch" in flags:
        budget = next((int(f.split("=")[1]) for f in flags if f.startswith("--budget=")), 60000)
        batch(runs, budget)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
