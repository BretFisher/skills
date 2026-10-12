#!/usr/bin/env python3
"""checks.py: deterministic grader for the super-linting evals.

Grades every assertion a program can decide from the agent guide (AGENTS.md / CLAUDE.md), the Makefile, the
README, the answer, and the tool calls in the raw log, and leaves `passed: null` plus excerpts for the model
grader on the rest. See AGENTS.md, "Deterministic checks before model judgment", and docs/eval-walkthrough.md.

Usage:
  checks.py --write [--force] <run-dir>...   write grading.json (program verdicts; null for the model)
  checks.py --finalize <run-dir>...          recompute summary, strip excerpts; exit 1 if a null remains
  checks.py --batch [--budget=60000] <run-dir>...
                                             one grader prompt per group of runs that still have nulls
  checks.py --kinds                          markdown table of program/split/model per eval (coverage.md)
  <run-dir> = evals/super-linting/runs/<iteration>/eval-N-<name>/<config>/run-M

Repo files are read from outputs/ first (the executor copies every changed file there), then from the work repo.
`--scanners` is accepted and ignored so `make eval-check` works for every skill.
"""
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from harness.evidence import tool_calls
EVALS = json.load(open(f"{HERE}/evals.json"))["evals"]
INSTALL = {"ruff": "ruff", "shellcheck": "shellcheck", "hadolint": "hadolint", "yamllint": "yamllint", "tflint": "tflint"}


def read(p):
    return open(p, errors="ignore").read() if os.path.isfile(p) else ""


class Run:
    def __init__(self, d):
        self.dir = d
        self.eval = int(re.search(r"eval-(\d+)", d).group(1))
        self.spec = next(e for e in EVALS if e["id"] == self.eval)
        self.work = f"{d}/work"
        self.answer = read(f"{d}/outputs/answer.md")
        self.calls = tool_calls(f"{d}/raw-transcript.jsonl")
        self.grading = json.load(open(f"{d}/grading.json")) if os.path.exists(f"{d}/grading.json") else None

    def file(self, name):
        """outputs/ first (the executor's copy of every changed file), then the work repo."""
        return read(f"{self.dir}/outputs/{name}") or read(f"{self.work}/{name}")

    def exists(self, name):
        return os.path.exists(f"{self.work}/{name}") or os.path.exists(f"{self.dir}/outputs/{name}")

    def guide(self):
        """The ## Linting section of AGENTS.md or CLAUDE.md, and which file held it."""
        for name in ("AGENTS.md", "CLAUDE.md"):
            m = re.search(r"^## Linting\b.*?(?=^## |\Z)", self.file(name), re.M | re.S)
            if m:
                return m.group(0), name
        return "", None

    def lint_recipe(self):
        """The recipe text of the `lint` target plus the recipes of every target it depends on, recursively,
        so `lint: lint-sh lint-tf` counts the linters its prerequisites run."""
        mk = self.file("Makefile")
        targets = {}
        for m in re.finditer(r"^([A-Za-z0-9_.-]+)\s*:(?!=)([^\n#]*)(?:#.*)?\n((?:\t.*\n?|[ \t]*\n|(?:ifn?eq|ifn?def|else|endif)\b.*\n)*)", mk, re.M):
            targets[m.group(1)] = (m.group(2).split(), m.group(3))
        if "lint" not in targets:
            return None
        out, todo, seen = [], ["lint"], set()
        while todo:
            t = todo.pop()
            if t in seen or t not in targets:
                continue
            seen.add(t)
            out.append(targets[t][1])
            # Follow literal repository-local shell helpers invoked by a recipe;
            # an unrelated script elsewhere is not part of make lint.
            for helper in re.findall(r"(?m)^\s*@?(?:bash|sh)\s+([\w./-]+\.sh)\b", targets[t][1]):
                if not helper.startswith("/") and ".." not in helper.split("/"):
                    out.append(self.file(helper.removeprefix("./")))
            todo += targets[t][0]
        return "\n".join(out)


def ok(cond, ev):
    return (bool(cond), ev)


def linting_section(r):
    sec, name = r.guide()
    return ok(sec and re.search(r"commit", sec, re.I), f"## Linting in {name}" if name else "no ## Linting section")


def names_in_section(*tools):
    def f(r):
        sec, _ = r.guide()
        miss = [t for t in tools if not re.search(rf"\b{t}\b", sec, re.I)]
        return ok(sec and not miss, "all named" if sec and not miss else f"missing {miss}")
    return f


def make_runs(*tools):
    def f(r):
        rec = r.lint_recipe()
        if rec is None:
            return (False, "no lint: target")
        miss = [t for t in tools if not re.search(rf"\b{t}\b", rec, re.I)]
        return ok(not miss, "recipe runs all" if not miss else f"recipe missing {miss}")
    return f


def no_hooks(r):
    found = [p for p in (".githooks", ".pre-commit-config.yaml") if r.exists(p)]
    if re.search(r"git\s+config\b[^\n;&|]*\bcore\.hooksPath\s+\S", executed(r.calls)):
        found.append("core.hooksPath set")
    return ok(not found, "no hook" if not found else f"found {found}")


def e0_4(r):
    return ok(re.search(r"make lint", r.file("README.md")), "README mentions make lint")


def e0_5(r):
    fetched = re.search(r"super-linter", r.calls)
    fallback = re.search(r"offline|fallback", r.answer, re.I)
    return ok(fetched or fallback, f"fetched={bool(fetched)} fallback stated={bool(fallback)}")


HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?^\s*\1\s*$", re.M | re.S)
QUOTED = re.compile(r"'[^']*'|\"(?:\\.|[^\"\\])*\"")


def executed(calls):
    """Bash command text with heredoc bodies and quoted strings removed, so an install line the executor
    wrote into a README or an answer does not count as a command it ran."""
    out = []
    for line in re.split(r"(?:^|\n)(?:Bash|shell): ", calls) if calls else []:
        out.append(QUOTED.sub("''", HEREDOC.sub("", line)))
    return "\n".join(out)


def e0_7(r):
    cmds = executed(r.calls)
    ran = [m.group(0) for m in re.finditer(r"(?:^|[;&|(]\s*|\n\s*)(?:sudo\s+)?(brew install|pipx install|pip3? install|npm (?:install|i) -g|go install)\b[^\n;&|]*", cmds)]
    missing = [t for t in ("ruff", "shellcheck", "hadolint", "yamllint") if not shutil.which(t)]
    unlisted = [t for t in missing if not re.search(rf"(brew|pipx|pip3?|npm|go)\s+(install|i)\b[^\n]*\b{t}\b", r.answer)]
    return ok(not ran and not unlisted, f"installers run={ran[:2]} missing on PATH={missing} without an install line={unlisted}")


def e0_8(r):
    asked = any(re.search(r"hook", l, re.I) and "?" in l for l in r.answer.splitlines())
    return ok(asked, "asks about a hook" if asked else "no question about a hook")


def e1_3(r):
    rec = r.lint_recipe()
    if rec is None:
        return (False, "no lint: target")
    want = [t for t in ("tflint", "shellcheck") if not re.search(rf"\b{t}\b", rec, re.I)]
    extra = [t for t in ("ruff", "pylint", "flake8", "markdownlint") if re.search(rf"\b{t}\b", rec, re.I)]
    return ok(not want and not extra, f"missing {want} extra {extra}")


def e1_4(r):
    named = re.search(r"\b(checkov|trivy)\b", r.answer, re.I)
    in_make = re.search(r"\b(checkov|trivy)\b", r.file("Makefile"), re.I)
    return ok(named and not in_make, f"named={bool(named)} in Makefile={bool(in_make)}")


def e2_1(r):
    orig = subprocess.run(["git", "show", "HEAD:CLAUDE.md"], cwd=r.work, capture_output=True, text=True).stdout if os.path.isdir(f"{r.work}/.git") else ""
    first = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"], cwd=r.work, capture_output=True, text=True).stdout.split() if orig is not None else []
    if first:
        orig = subprocess.run(["git", "show", f"{first[-1]}:CLAUDE.md"], cwd=r.work, capture_output=True, text=True).stdout
    now = r.file("CLAUDE.md")
    kept = all(l in now for l in orig.splitlines() if l.strip())
    sec = re.search(r"^## Linting\b.*?(?=^## |\Z)", now, re.M | re.S)
    return ok(kept and sec and re.search(r"commit", sec.group(0), re.I), f"original lines kept={kept} linting section={bool(sec)}")


def e2_2(r):
    sec, _ = r.guide()
    return ok(re.search(r"\bruff\b", r.answer, re.I) and re.search(r"\bruff\b", sec, re.I), "ruff in answer and section")


def e2_3(r):
    sec, _ = r.guide()
    other = [t for t in ("shellcheck", "yamllint", "hadolint", "markdownlint", "eslint") if re.search(rf"\b{t}\b", sec, re.I)]
    return ok(sec and not other, f"other linters {other}")


def e2_4(r):
    return ok(not r.exists("AGENTS.md"), "no AGENTS.md")


CHECKS = {
    (0, 1): linting_section, (0, 2): names_in_section("ruff", "shellcheck", "hadolint", "yamllint"),
    (0, 3): make_runs("ruff", "shellcheck", "hadolint", "yamllint"), (0, 4): e0_4, (0, 5): e0_5, (0, 6): no_hooks, (0, 7): e0_7, (0, 8): e0_8,
    (1, 1): linting_section, (1, 2): names_in_section("tflint", "shellcheck"), (1, 3): e1_3, (1, 4): e1_4, (1, 5): no_hooks,
    (2, 1): e2_1, (2, 2): e2_2, (2, 3): e2_3, (2, 4): e2_4,
}
SPLIT = set()


def context(run):
    sec, name = run.guide()
    return [{"source": "answer", "text": run.answer[:12000]}, {"source": f"{name} ## Linting", "text": sec[:4000]},
            {"source": "Makefile", "text": run.file("Makefile")[:3000]}]


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
                  "excerpts (answer, the ## Linting section, the Makefile). Judge each from the excerpts: set `passed`,",
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
