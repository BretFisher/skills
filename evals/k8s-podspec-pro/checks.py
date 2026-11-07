#!/usr/bin/env python3
"""checks.py: deterministic grader for the k8s-podspec-pro evals.

Grades every assertion a program can decide from the produced manifest, review, and answer, and leaves
`passed: null` plus the excerpts a model grader needs on the rest.
See AGENTS.md, "Deterministic checks before model judgment", and docs/eval-walkthrough.md.

Usage:
  checks.py --write [--force] <run-dir>...   write grading.json (program verdicts; null for the model)
  checks.py --finalize <run-dir>...          recompute summary, strip excerpts; exit 1 if a null remains
  checks.py --batch [--budget=60000] <run-dir>...
                                             one grader prompt per group of runs that still have nulls
  checks.py --kinds                          markdown table of program/split/model per eval (coverage.md)
  <run-dir> = evals/k8s-podspec-pro/runs/<iteration>/eval-N-<name>/<config>/run-M

Files are read from outputs/ first, then from the work repo. YAML is parsed with yq (brew install yq).
`--scanners` is accepted and ignored so `make eval-check` works for every skill.
"""
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EVALS = json.load(open(f"{HERE}/evals.json"))["evals"]
FIXTURES = f"{HERE}/fixtures"
OUTPUT = {0: "deployment.yaml", 2: "cleanup-cronjob.yaml", 3: "node-exporter.yaml", 4: "deploy/controller.yaml"}
HANDBACK = ["## Defaults applied", "## Questions", "## Placeholders"]
REPORT = ["## Meets the floor", "## Missing or wrong", "## Suggested"]


def read(p):
    if not p or not os.path.isfile(p):
        return ""
    with open(p, errors="ignore") as f:
        return f.read()


def find(d, rel):
    """The file at rel from outputs/ first, then the work repo; else the shortest basename match."""
    for base in (f"{d}/outputs", f"{d}/work"):
        if os.path.isfile(f"{base}/{rel}"):
            return f"{base}/{rel}"
    for base in (f"{d}/outputs", f"{d}/work"):
        hits = sorted((h for h in glob.glob(f"{base}/**/{os.path.basename(rel)}", recursive=True) if "/.git/" not in h), key=len)
        if hits:
            return hits[0]
    return None


def parse(text):
    if not text.strip():
        return []
    out = subprocess.run(["yq", "-o=json", "-I=0", "ea", "[.]", "-"], input=text, capture_output=True, text=True)
    if out.returncode:
        return []
    return [doc for doc in json.loads(out.stdout or "[]") if isinstance(doc, dict)]


def g(d, *keys):
    for k in keys:
        d = d.get(k) if isinstance(d, dict) else None
    return d


def pod_spec(doc):
    kind, spec = doc.get("kind"), doc.get("spec") or {}
    if kind == "Pod":
        return spec
    if kind == "CronJob":
        return g(spec, "jobTemplate", "spec", "template", "spec") or {}
    return g(spec, "template", "spec") or {}


class Run:
    def __init__(self, d):
        self.dir = d
        self.eval = int(re.search(r"eval-(\d+)", d).group(1))
        self.spec = next(e for e in EVALS if e["id"] == self.eval)
        self.answer = read(f"{d}/outputs/answer.md")
        self.review = read(find(d, "review.md"))
        self.yaml_path = find(d, OUTPUT[self.eval]) if self.eval in OUTPUT else None
        self.yaml = read(self.yaml_path)
        self.docs = parse(self.yaml)
        workload = [x for x in self.docs if x.get("kind") in ("Deployment", "CronJob", "DaemonSet", "StatefulSet", "Job", "Pod")]
        self.doc = workload[0] if workload else {}
        self.ps = pod_spec(self.doc) if self.doc else {}
        self.cs = self.ps.get("containers") or []
        self.c = self.cs[0] if self.cs else {}
        self.grading = json.load(open(f"{d}/grading.json")) if os.path.exists(f"{d}/grading.json") else None

    def text(self):
        return self.answer + "\n" + self.yaml


def ok(cond, ev):
    return (bool(cond), ev)


# ---- shared floor checks ----

def seccomp_nonroot(r):
    sc = r.ps.get("securityContext") or {}
    return ok(g(sc, "seccompProfile", "type") == "RuntimeDefault" and sc.get("runAsNonRoot") is True,
              f"seccomp={g(sc, 'seccompProfile', 'type')} runAsNonRoot={sc.get('runAsNonRoot')}")


def no_escalation(r):
    vals = [g(c, "securityContext", "allowPrivilegeEscalation") for c in r.cs]
    return ok(vals and all(v is False for v in vals), f"allowPrivilegeEscalation={vals}")


def resources(r):
    bad = []
    for c in r.cs:
        lim, req = g(c, "resources", "limits") or {}, g(c, "resources", "requests") or {}
        if not lim.get("memory") or str(lim.get("memory")) != str(req.get("memory")) or not req.get("cpu") or lim.get("cpu"):
            bad.append((c.get("name"), lim, req))
    return ok(r.cs and not bad, f"bad={bad}" if bad else f"{len(r.cs)} container(s) ok")


def grace(r):
    v = r.ps.get("terminationGracePeriodSeconds")
    return ok(isinstance(v, int) and v > 30, f"terminationGracePeriodSeconds={v}")


def pod_false(*keys):
    def check(r):
        vals = {k: r.ps.get(k) for k in keys}
        return ok(r.ps and all(v is False for v in vals.values()), str(vals))
    return check


def headings(names, source):
    def check(r):
        text = getattr(r, source)
        pos = [text.find(f"\n{h}\n") if f"\n{h}\n" in text else (0 if text.startswith(f"{h}\n") else -1) for h in names]
        return ok(all(p >= 0 for p in pos) and pos == sorted(pos), f"positions={dict(zip(names, pos))}")
    return check


def not_guaranteed(source):
    def check(r):
        text = getattr(r, source)() if callable(getattr(r, source)) else getattr(r, source)
        g_ = re.search(r"\bGuaranteed\b", text)
        b_ = re.search(r"\bBurstable\b", text)
        return ok(not g_ or b_, f"Guaranteed={bool(g_)} Burstable={bool(b_)}")
    return check


def probe(path, port):
    def check(r):
        hg = g(r.c, "readinessProbe", "httpGet") or {}
        p = hg.get("port")
        named = {x.get("name"): x.get("containerPort") for x in r.c.get("ports") or [] if x.get("name")}
        port_ok = str(p) == str(port) or named.get(p) == port
        return ok(hg.get("path") == path and port_ok, f"readinessProbe.httpGet={hg}")
    return check


# ---- e0 ----

def e0_1(r):
    return ok(r.doc.get("kind") == "Deployment" and g(r.doc, "spec", "replicas") == 3 and r.c.get("image") == "registry.acme.io/payments/api:v1.4.2",
              f"kind={r.doc.get('kind')} replicas={g(r.doc, 'spec', 'replicas')} image={r.c.get('image')}")


def e0_3(r):
    return ok(any(p.get("containerPort") == 9090 for p in r.c.get("ports") or []), f"ports={r.c.get('ports')}")


def e0_5(r):
    uids = [g(r.ps, "securityContext", "runAsUser")] + [g(c, "securityContext", "runAsUser") for c in r.cs]
    uids = [u for u in uids if u is not None]
    return ok(r.ps and all(u == 65532 for u in uids), f"runAsUser values={uids}")


def e0_11(r):
    lines = r.yaml.splitlines()
    hit = any("memory:" in l and any("TODO" in x for x in lines[max(0, i - 2):i + 3]) for i, l in enumerate(lines))
    return ok(hit, "TODO near memory" if hit else f"{r.yaml.count('TODO')} TODO(s), none near memory:")


def commented(keys):
    def check(r):
        lines = r.yaml.splitlines()
        missing = []
        for k in keys:
            idx = [i for i, l in enumerate(lines) if re.match(rf"\s*{k}:", l)]
            if not idx or not any("#" in lines[i] or (i and lines[i - 1].strip().startswith("#")) for i in idx):
                missing.append(k)
        return ok(not missing, f"uncommented={missing}" if missing else "all commented")
    return check


# ---- e1 ----

def has(*pats):
    def check(r):
        hit = all(re.search(p, r.review, re.I) for p in pats)
        return ok(hit, f"patterns {pats} {'all found' if hit else 'missing'}")
    return check


def e1_7(r):
    nonroot = re.search(r"runAsNonRoot", r.review)
    gotcha = re.search(r"non-?numeric|numeric (UID|USER|user)|USER node|CreateContainerConfigError", r.review, re.I)
    return ok(nonroot and gotcha, f"runAsNonRoot={bool(nonroot)} named-USER warning={gotcha.group(0) if gotcha else None}")


def e1_12(r):
    bad = re.search(r"livenessProbe:\s*\n(?:[ \t]+[^\n]*\n){0,6}?[ \t]+path:\s*[\"']?/healthz", r.review)
    return ok(not bad, "livenessProbe on /healthz" if bad else "no livenessProbe on /healthz")


def e1_14(r):
    orig = read(f"{FIXTURES}/web-app/deployment.yaml")
    now = read(f"{r.dir}/work/deployment.yaml")
    return ok(orig and now == orig, "unchanged" if now == orig else "work/deployment.yaml changed")


# ---- e2 ----

def e2_1(r):
    s = r.doc.get("spec") or {}
    return ok(r.doc.get("kind") == "CronJob" and s.get("schedule") == "0 2 * * *" and s.get("timeZone") in ("Etc/UTC", "UTC"),
              f"kind={r.doc.get('kind')} schedule={s.get('schedule')} timeZone={s.get('timeZone')}")


def e2_2(r):
    return ok(r.c.get("image") == "acme/cleanup-tool:2025.05.21-a1b2c3d", f"image={r.c.get('image')}")


def e2_3(r):
    return ok(g(r.doc, "spec", "concurrencyPolicy") == "Forbid", f"concurrencyPolicy={g(r.doc, 'spec', 'concurrencyPolicy')}")


def e2_4(r):
    v = g(r.doc, "spec", "jobTemplate", "spec", "activeDeadlineSeconds")
    return ok(isinstance(v, int) and v >= 1200, f"activeDeadlineSeconds={v}")


def e2_5(r):
    return ok(r.c and not r.c.get("ports") and not r.c.get("readinessProbe"), f"ports={r.c.get('ports')} readinessProbe={bool(r.c.get('readinessProbe'))}")


def e2_11(r):
    off = r.ps.get("automountServiceAccountToken") is False
    creds = re.search(r"IRSA|Pod Identity|workload identity|IAM role|serviceAccountName|secretRef|secretKeyRef", r.text())
    return ok(off and creds, f"automount={r.ps.get('automountServiceAccountToken')} credentials={creds.group(0) if creds else None}")


# ---- e3 ----

def e3_1(r):
    return ok(r.doc.get("kind") == "DaemonSet" and r.c.get("image") == "quay.io/prometheus/node-exporter:v1.9.1" and r.ps.get("hostNetwork") is True and r.ps.get("hostPID") is True,
              f"kind={r.doc.get('kind')} image={r.c.get('image')} hostNetwork={r.ps.get('hostNetwork')} hostPID={r.ps.get('hostPID')}")


def e3_2(r):
    return ok(r.ps and r.ps.get("hostUsers") is not False, f"hostUsers={r.ps.get('hostUsers')}")


def e3_3(r):
    for line in r.text().splitlines():
        if "hostUsers" in line and re.search(r"host ?(network|PID)|hostNetwork|hostPID|host (user )?namespace", line, re.I):
            return (True, line.strip()[:160])
    return (None, "no single line ties hostUsers to the host namespaces; model judges")


def e3_4(r):
    host = {v.get("name"): g(v, "hostPath", "path") for v in r.ps.get("volumes") or [] if v.get("hostPath")}
    mounts = {m.get("name"): m for c in r.cs for m in c.get("volumeMounts") or []}
    status = {p: g(mounts, n, "readOnly") for n, p in host.items() if p in ("/proc", "/sys")}
    return ok(set(status) == {"/proc", "/sys"} and all(v is True for v in status.values()), f"hostPath readOnly={status}")


def e3_5(r):
    rp = r.c.get("readinessProbe") or {}
    port = g(rp, "httpGet", "port") or g(rp, "tcpSocket", "port")
    named = {x.get("name"): x.get("containerPort") for x in r.c.get("ports") or [] if x.get("name")}
    return ok(rp and (str(port) == "9100" or named.get(port) == 9100), f"readinessProbe port={port}")


def floor_trio(r):
    a, ea = seccomp_nonroot(r)
    b, eb = no_escalation(r)
    return ok(a and b, f"{ea}; {eb}")


# ---- e4 ----

def e4_1(r):
    orig = read(f"{FIXTURES}/config-watcher/deploy/controller.yaml")
    changed = read(f"{r.dir}/work/deploy/controller.yaml") != orig
    return ok(changed and r.ps.get("serviceAccountName") == "config-watcher" and r.c.get("image") == "ghcr.io/acme/config-watcher:0.8.3",
              f"changed={changed} sa={r.ps.get('serviceAccountName')} image={r.c.get('image')}")


def e4_2(r):
    return ok(r.ps and r.ps.get("automountServiceAccountToken") is not False, f"automountServiceAccountToken={r.ps.get('automountServiceAccountToken')}")


def e4_3(r):
    for line in r.text().splitlines():
        if re.search(r"automountServiceAccountToken|token", line) and re.search(r"Kubernetes API|the API|API server|calls the API|watches", line):
            return (True, line.strip()[:160])
    return (None, "no line ties the token to API access; model judges")


FLOOR_COMMENTS = ["allowPrivilegeEscalation", "runAsNonRoot", "hostUsers", "automountServiceAccountToken", "enableServiceLinks", "terminationGracePeriodSeconds"]
CHECKS = {
    (0, 1): e0_1, (0, 2): probe("/readyz", 9090), (0, 3): e0_3, (0, 4): seccomp_nonroot, (0, 5): e0_5, (0, 6): no_escalation,
    (0, 7): resources, (0, 8): grace, (0, 9): pod_false("hostUsers"), (0, 10): pod_false("automountServiceAccountToken", "enableServiceLinks"),
    (0, 11): e0_11, (0, 12): commented(FLOOR_COMMENTS), (0, 13): not_guaranteed("text"), (0, 14): headings(HANDBACK, "answer"),
    (1, 1): headings(REPORT, "review"), (1, 2): has(r"latest"), (1, 3): has(r"readinessProbe|readiness probe", r"/healthz"),
    (1, 4): has(r"memory", r"limit", r"request"), (1, 5): has(r"seccomp", r"RuntimeDefault"), (1, 6): has(r"allowPrivilegeEscalation"),
    (1, 7): e1_7, (1, 8): has(r"terminationGracePeriodSeconds"), (1, 9): has(r"hostUsers"), (1, 10): has(r"automountServiceAccountToken"),
    (1, 11): has(r"enableServiceLinks", r"REDIS_PORT"), (1, 12): e1_12, (1, 13): not_guaranteed("review"), (1, 14): e1_14,
    (2, 1): e2_1, (2, 2): e2_2, (2, 3): e2_3, (2, 4): e2_4, (2, 5): e2_5, (2, 6): seccomp_nonroot, (2, 7): no_escalation,
    (2, 8): resources, (2, 9): grace, (2, 10): pod_false("hostUsers", "enableServiceLinks"), (2, 11): e2_11, (2, 12): headings(HANDBACK, "answer"),
    (3, 1): e3_1, (3, 2): e3_2, (3, 3): e3_3, (3, 4): e3_4, (3, 5): e3_5, (3, 6): floor_trio,
    (3, 7): pod_false("automountServiceAccountToken", "enableServiceLinks"), (3, 8): resources, (3, 9): headings(HANDBACK, "answer"),
    (4, 1): e4_1, (4, 2): e4_2, (4, 3): e4_3, (4, 4): probe("/readyz", 8081), (4, 5): floor_trio,
    (4, 6): pod_false("hostUsers", "enableServiceLinks"), (4, 7): resources, (4, 8): grace, (4, 9): headings(HANDBACK, "answer"),
}
SPLIT = {(3, 3), (4, 3)}


def context(run):
    out = [{"source": "answer", "text": run.answer[:12000]}]
    if run.review:
        out.append({"source": "review.md", "text": run.review[:12000]})
    if run.yaml:
        out.append({"source": run.spec and OUTPUT.get(run.eval, "manifest"), "text": run.yaml[:6000]})
    return out


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
        by = "program" if passed is not None else "model"
        e = {"text": text, "passed": passed, "graded_by": by, "evidence": f"{by} ({k}): {ev}"}
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
    g_ = {"eval_id": run.eval, "eval_name": run.spec["name"], "expectations": exps, "summary": summary(exps)}
    if nulls:
        g_["residual"] = {"null_indices": nulls, "prompt": run.spec["prompt"]}
    json.dump(g_, open(f"{run.dir}/grading.json", "w"), indent=2)
    print(f"{run.dir}: {g_['summary']}")


def finalize(run):
    g_ = run.grading
    if not g_:
        sys.exit(f"no grading.json in {run.dir}")
    for e in g_["expectations"]:
        e.pop("context", None)
    g_.pop("residual", None)
    g_["summary"] = summary(g_["expectations"])
    json.dump(g_, open(f"{run.dir}/grading.json", "w"), indent=2)
    print(f"{run.dir}: {g_['summary']}")
    return g_["summary"]["null"]


def batch(runs, budget):
    groups, cur, size = [], [], 0
    for run in runs:
        g_ = run.grading
        if not g_ or not any(e["passed"] is None for e in g_["expectations"]):
            continue
        n = sum(len(c["text"]) for e in g_["expectations"] if e["passed"] is None for c in e.get("context", []))
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
        lines += [f"- `{d}/grading.json`" for d in grp]
        lines += ["", "Its `residual` object lists the null indices and the task prompt. Each null entry has a `context` array of",
                  "excerpts (answer, review.md, the manifest). Judge each from the excerpts: set `passed`,",
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
