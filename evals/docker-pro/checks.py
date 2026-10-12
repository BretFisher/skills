#!/usr/bin/env python3
"""checks.py: deterministic grader for the docker-pro evals.

Grades every assertion a program can decide from the produced Dockerfile, .dockerignore, docker-bake.hcl,
compose file, and answer, and leaves `passed: null` plus the excerpts a model grader needs on the rest.
See AGENTS.md, "Deterministic checks before model judgment", and docs/eval-walkthrough.md.

Usage:
  checks.py --write [--force] <run-dir>...   write grading.json (program verdicts; null for the model)
  checks.py --finalize <run-dir>...          recompute summary, strip excerpts; exit 1 if a null remains
  checks.py --batch [--budget=60000] <run-dir>...
                                             one grader prompt per group of runs that still have nulls
  checks.py --kinds                          markdown table of program/split/model per eval (coverage.md)
  <run-dir> = evals/docker-pro/runs/<iteration>/eval-N-<name>/<config>/run-M

Files are read from outputs/ first, then from the work repo, so an executor that edited in place is graded too.
`--scanners` is accepted and ignored so `make eval-check` works for every skill.
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EVALS = json.load(open(f"{HERE}/evals.json"))["evals"]
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}\b")
PLACEHOLDER = re.compile(r"@sha256:(<|\$\{|PIN|TODO|REPLACE|x{4})", re.I)


def read(p):
    return open(p, errors="ignore").read() if os.path.isfile(p) else ""


def find(d, names):
    """First file matching any glob in names, from outputs/ then the work repo."""
    for base in (f"{d}/outputs", f"{d}/work"):
        for n in names:
            hits = sorted(glob.glob(f"{base}/**/{n}", recursive=True), key=len)
            hits = [h for h in hits if "/node_modules/" not in h and "/.git/" not in h]
            if hits:
                return hits[0]
    return None


class Run:
    def __init__(self, d):
        self.dir = d
        self.eval = int(re.search(r"eval-(\d+)", d).group(1))
        self.spec = next(e for e in EVALS if e["id"] == self.eval)
        self.answer = read(f"{d}/outputs/answer.md")
        self.dockerfile = read(find(d, ["Dockerfile"]) or "")
        self.dockerignore = read(find(d, [".dockerignore"]) or "")
        self.bake = read(find(d, ["docker-bake.hcl"]) or "")
        self.compose_path = find(d, ["compose.yaml", "compose.yml", "docker-compose.yaml", "docker-compose.yml"])
        self.compose = read(self.compose_path or "")
        self.compose_in_outputs = [os.path.basename(p) for p in glob.glob(f"{d}/outputs/**/*compose*.y*ml", recursive=True)]
        self.grading = json.load(open(f"{d}/grading.json")) if os.path.exists(f"{d}/grading.json") else None

    def froms(self):
        """(image, stage-name) for every FROM line."""
        out = []
        for m in re.finditer(r"^\s*FROM\s+(?:--platform=\S+\s+)?(\S+)(?:\s+AS\s+(\S+))?", self.dockerfile, re.M | re.I):
            out.append((m.group(1), m.group(2)))
        return out

    def stages(self):
        return {s.lower() for _, s in self.froms() if s}

    def external(self):
        return [img for img, _ in self.froms() if img.lower() not in self.stages() and img.lower() != "scratch"]

    def final_stage(self):
        """Text of the last FROM to the end of the Dockerfile."""
        parts = re.split(r"(?=^\s*FROM\s)", self.dockerfile, flags=re.M | re.I)
        return parts[-1] if parts else ""


def ok(cond, ev):
    return (bool(cond), ev)


def syntax_first(r):
    first = r.dockerfile.splitlines()[0].strip() if r.dockerfile.strip() else ""
    return ok(first == "# syntax=docker/dockerfile:1", f"first line: {first[:60]!r}")


def args_and_names(r):
    head = re.split(r"^\s*FROM\s", r.dockerfile, maxsplit=1, flags=re.M | re.I)[0]
    arg = bool(re.search(r"^\s*ARG\s+\w+", head, re.M))
    unnamed = [img for img, s in r.froms() if not s and img.lower() not in r.stages()]
    return ok(arg and r.froms() and not unnamed, f"global ARG={arg} external FROM without AS={unnamed}")


def resolved_image(r, img):
    """Expand ${VAR} in an image reference from the Dockerfile's ARG defaults."""
    defaults = dict(re.findall(r"^\s*ARG\s+(\w+)=(\S+)", r.dockerfile, re.M))
    return re.sub(r"\$\{?(\w+)\}?", lambda m: defaults.get(m.group(1), m.group(0)), img)


def digests(r):
    ext = r.external()
    if not ext:
        return (False, "no external FROM")
    bad = [i for i in ext if not DIGEST.search(resolved_image(r, i)) and not PLACEHOLDER.search(resolved_image(r, i))]
    placeholders = [i for i in ext if PLACEHOLDER.search(resolved_image(r, i))]
    if bad:
        return (False, f"no digest: {bad}")
    if placeholders and not re.search(r"regctl|imagetools", r.answer):
        return (False, f"placeholder without a resolve command: {placeholders}")
    return (True, f"{len(ext)} external FROM pinned ({len(placeholders)} placeholder)")


def exec_form(r):
    fin = r.final_stage()
    m = re.findall(r"^\s*(ENTRYPOINT|CMD)\s+(.*)$", fin, re.M)
    return ok(m and all(v.strip().startswith("[") for _, v in m), f"final stage {m[-1][0] if m else 'none'}: {m[-1][1][:50] if m else ''}")


def final_image(r):
    """The image the last stage is built on, following stage aliases (FROM runtime -> its FROM)."""
    f = r.froms()
    if not f:
        return ""
    alias = {s.lower(): img for img, s in f if s}
    img, seen = f[-1][0], set()
    while img.lower() in alias and img.lower() not in seen:
        seen.add(img.lower())
        img = alias[img.lower()]
    return resolved_image(r, img)


def e0_3(r):
    img = final_image(r)
    return ok(re.match(r"(cgr\.dev/chainguard/|dhi\.io/)", img), f"final FROM {img[:80]}")


def e0_5(r):
    lines = {l.strip().rstrip("/") for l in r.dockerignore.splitlines()}
    return ok(".git" in lines and "coverage" in lines, f".git={'.git' in lines} coverage={'coverage' in lines}")


def e0_6(r):
    return ok(re.search(r'target\s+"[^"]+"\s*\{', r.bake) and "dockerfile" in r.bake and "tags" in r.bake, f"bake file {len(r.bake)} chars")


def e0_7(r):
    if r.compose_in_outputs:
        return (False, f"created {r.compose_in_outputs}")
    asked = any(re.search(r"compose", l, re.I) and l.rstrip().endswith("?") for l in r.answer.splitlines())
    return (True, "no compose file; asks with a question") if asked else (None, "no compose file; model judges whether the answer offers one")


def e1_2(r):
    img = final_image(r)
    return ok(re.search(r"static|distroless", img), f"final FROM {img[:80]}")


def e1_4(r):
    # Join continued lines within one instruction. A cache on a different RUN
    # (or in a comment) cannot cache the Go command being graded.
    lines = "\n".join(line for line in r.dockerfile.splitlines() if not line.lstrip().startswith("#"))
    logical = re.sub(r"\\\s*\n", " ", lines)
    runs = re.findall(r"^\s*RUN\b[^\n]*", logical, re.M | re.I)
    hit = any(re.search(r"--mount=type=cache(?:,|\s)", run) and
              re.search(r"\bgo\s+(?:build\b|mod\s+download\b)", run) for run in runs)
    return ok(hit, "cache mount on go build/mod download" if hit else f"{len(runs)} RUN lines, none with a cache mount")


def e1_7(r):
    return ok(re.search(r"CGO_ENABLED=0", r.dockerfile), "CGO_ENABLED=0")


def e1_8(r):
    return ok(r.dockerignore.strip() and r.bake.strip(), f".dockerignore={bool(r.dockerignore.strip())} bake={bool(r.bake.strip())}")


def e2_2(r):
    return ok(r.compose and not re.search(r"^version\s*:", r.compose, re.M), f"compose={os.path.basename(r.compose_path or '')} version key={bool(re.search(r'^version', r.compose, re.M))}")


def e2_3(r):
    names = r.compose_in_outputs
    return ok("compose.yaml" in names and not any(n.startswith("docker-compose") for n in names), f"compose files in outputs={names}")


def e2_4(r):
    watch = re.search(r"develop:\s*\n\s+watch:[\s\S]*?action:\s*sync\b", r.compose)
    bind = re.search(r"\./src:/app/src", r.compose)
    return ok(watch and not bind, f"develop.watch sync={bool(watch)} bind mount kept={bool(bind)}")


def e2_5(r):
    hit = re.search(r"docker compose (?:watch(?=\s|$|`)|up\b[^\n]*?(?<!\S)--watch(?=\s|$|`))", r.answer)
    return ok(hit, f"run command: {hit.group(0) if hit else 'none'}")


def e2_6(r):
    old = [i for i in r.external() if re.match(r"node:18\b", resolved_image(r, i))]
    pinned = digests(r)
    return (False, f"still node:18: {old}") if old else pinned


def e2_7(r):
    return ok(r.dockerignore.strip(), f".dockerignore {len(r.dockerignore)} chars")


CHECKS = {
    (0, 1): syntax_first, (0, 2): args_and_names, (0, 3): e0_3, (0, 4): digests, (0, 5): e0_5, (0, 6): e0_6, (0, 7): e0_7, (0, 8): exec_form,
    (1, 1): syntax_first, (1, 2): e1_2, (1, 3): args_and_names, (1, 4): e1_4, (1, 5): digests, (1, 6): exec_form, (1, 7): e1_7, (1, 8): e1_8,
    (2, 1): syntax_first, (2, 2): e2_2, (2, 3): e2_3, (2, 4): e2_4, (2, 5): e2_5, (2, 6): e2_6, (2, 7): e2_7,
}
SPLIT = {(0, 7)}


def context(run):
    return [{"source": "answer", "text": run.answer[:12000]}, {"source": "Dockerfile", "text": run.dockerfile[:6000]},
            {"source": "compose", "text": run.compose[:3000]}]


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
                  "excerpts (answer, Dockerfile, compose file). Judge each from the excerpts: set `passed`,",
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
