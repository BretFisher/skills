#!/usr/bin/env python3
"""checks.py: deterministic grader for the k8s-catch-up evals.

Grades every assertion a regex over the produced YAML, answer, transcript, or work repo can decide,
and leaves `passed: null` plus the excerpts a model grader needs on the rest. See AGENTS.md,
"Deterministic checks before model judgment", and docs/eval-walkthrough.md.

Usage:
  checks.py --write [--force] <run-dir>...   write grading.json (program verdicts; null for the model)
  checks.py --finalize <run-dir>...          recompute summary, strip excerpts; exit 1 if a null remains
  checks.py --batch [--budget=60000] <run-dir>...
                                             group runs that still have nulls and write one grader
                                             prompt per group to <iteration>/grader-batches/batch-N.md
  checks.py --kinds                          markdown table of program/split/model per eval (coverage.md)
  <run-dir> = evals/k8s-catch-up/runs/<iteration>/eval-N-<name>/<config>/run-M

`--scanners` is accepted and ignored so `make eval-check` works for every skill.
Kinds: program (decided here), split (a mechanical half here, the rest to the model), model (judgment).
"""
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
EVALS = json.load(open(f"{HERE}/evals.json"))["evals"]
YAML_BLOCK = re.compile(r"```ya?ml\n(.*?)```", re.S)


def read(p):
    return open(p, errors="ignore").read() if os.path.exists(p) else ""


class Run:
    def __init__(self, d):
        self.dir = d
        self.eval = int(re.search(r"eval-(\d+)", d).group(1))
        self.spec = next(e for e in EVALS if e["id"] == self.eval)
        self.answer = read(f"{d}/outputs/answer.md") or "\n".join(read(f) for f in glob.glob(f"{d}/outputs/*.md"))
        self.transcript = read(f"{d}/transcript.md") + read(f"{d}/raw-transcript.jsonl")
        self.work = f"{d}/work"
        files = [f for f in glob.glob(f"{d}/outputs/**/*.y*ml", recursive=True)]
        self.yaml = "\n---\n".join(read(f) for f in files)
        if not self.yaml.strip():
            self.yaml = "\n---\n".join(YAML_BLOCK.findall(self.answer))
        self.all = self.answer + "\n" + self.yaml
        self.grading = json.load(open(f"{d}/grading.json")) if os.path.exists(f"{d}/grading.json") else None

    def has(self, pat, where=None, flags=re.M):
        return re.search(pat, where if where is not None else self.all, flags) is not None

    def work_file(self, rel):
        return read(f"{self.work}/{rel}")

    def work_dirty(self, sub=""):
        if not os.path.isdir(f"{self.work}/.git"):
            return None
        out = subprocess.run(["git", "status", "--porcelain", "--", sub or "."], cwd=self.work, capture_output=True, text=True).stdout
        return out.strip()


def ok(cond, ev):
    return (bool(cond), ev)


# ---- the checks: (eval id, 1-based assertion index) -> function(Run) -> (passed|None, evidence) --------
def e0_1(r):
    return ok(r.has(r"restartPolicyRules") and r.has(r"exitCodes") and r.has(r"\b42\b", r.yaml) and r.has(r"action:\s*Restart"), "restartPolicyRules/exitCodes/42/Restart in YAML")


def e0_2(r):
    return ok(r.has(r"^\s*image:\s*\n\s+reference:\s*registry\.example\.com/models/llama:v3", r.yaml) or r.has(r"image:\s*\{[^}]*reference:\s*registry\.example\.com/models/llama:v3", r.yaml), "image volume source with reference")


def e0_3(r):
    return ok(r.has(r"fileKeyRef") and r.has(r"volumeName:") and r.has(r"\bpath:") and r.has(r"\bkey:"), "fileKeyRef with volumeName/path/key")


def e1_1(r):
    up = re.search(r"scaleUp:(?:\n[ \t]+.*)+", r.yaml)
    down = re.search(r"scaleDown:(?:\n[ \t]+.*)+", r.yaml)
    return ok(up and re.search(r"tolerance:\s*0?\.05\b", up.group(0)) and down and re.search(r"tolerance:\s*0?\.15\b", down.group(0)), "behavior.scaleUp.tolerance 0.05, scaleDown.tolerance 0.15")


def e1_3(r):
    want = [r"apiVersion:\s*autoscaling/v2$", r"kind:\s*Deployment", r"name:\s*api\b", r"minReplicas:\s*2\b", r"maxReplicas:\s*30\b", r"averageUtilization:\s*70\b"]
    miss = [w for w in want if not r.has(w, r.yaml)]
    return ok(not miss, "missing: " + ", ".join(miss) if miss else "shape complete")


def e2_1(r):
    return ok(r.has(r"4671|GenericWorkload|kind:\s*(Workload|PodGroup)\b|Workload API|PodGroup"), "names the native gang-scheduling API")


def e2_2(r):
    return (None, "GenericWorkload named; model judges the off-by-default statement") if r.has(r"GenericWorkload") else (False, "GenericWorkload gate not named")


def e2_3(r):
    return (None, "group manifest present; model judges Pod reference") if r.has(r"kind:\s*(Workload|PodGroup)\b", r.yaml) else (False, "no Workload/PodGroup manifest")


def e3_1(r):
    return ok(r.has(r"firstAvailable") and r.has(r"gpu-large\.example\.com") and r.has(r"gpu-small\.example\.com") and r.has(r"count:\s*2\b", r.yaml), "firstAvailable with both device classes and count 2")


def e3_2(r):
    return ok(r.has(r"apiVersion:\s*resource\.k8s\.io/v1\s*$", r.yaml) and not r.has(r"resource\.k8s\.io/v1(alpha|beta)", r.yaml), "resource.k8s.io/v1 only")


def e3_3(r):
    return ok(r.has(r"resourceClaims:") and r.has(r"resourceClaimTemplateName:") and r.has(r"claims:", r.yaml), "resourceClaims + template name + containers claims")


def e4_1(r):
    return ok(r.has(r"kind:\s*VolumeGroupSnapshot\s*$", r.yaml) and r.has(r"apiVersion:\s*groupsnapshot\.storage\.k8s\.io/v1(beta\d*)?\s*$", r.yaml) and not r.has(r"groupsnapshot\.storage\.k8s\.io/v1alpha", r.yaml), "VolumeGroupSnapshot in groupsnapshot.storage.k8s.io, not v1alpha1")


def e4_2(r):
    return ok(r.has(r"app:\s*pg\b", r.yaml) and r.has(r"volumeGroupSnapshotClassName:\s*csi-group", r.yaml), "selector app=pg and class csi-group")


def e5_1(r):
    return ok(r.has(r"trafficDistribution:\s*PreferSameNode", r.yaml), "trafficDistribution: PreferSameNode")


def e5_2(r):
    bad = [p for p in (r"internalTrafficPolicy:\s*Local", r"topology-mode", r"PreferClose") if r.has(p, r.yaml)]
    return ok(not bad, "old mechanisms in YAML: " + ", ".join(bad) if bad else "no old mechanism in YAML")


def e6_1(r):
    return ok(r.has(r"podCertificate:") and r.has(r"signerName:\s*kubernetes\.io/kube-apiserver-client-pod", r.yaml), "podCertificate source with the built-in signer")


def e6_2(r):
    return ok(r.has(r"keyType:", r.yaml) and (r.has(r"credentialBundlePath:", r.yaml) or (r.has(r"certificateChainPath:", r.yaml) and r.has(r"keyPath:", r.yaml))), "keyType and output path fields")


def e7_1(r):
    kinds = r.has(r"kind:\s*MutatingAdmissionPolicy\s*$", r.yaml) and r.has(r"kind:\s*MutatingAdmissionPolicyBinding\s*$", r.yaml)
    return ok(kinds and r.has(r"apiVersion:\s*admissionregistration\.k8s\.io/v1\s*$", r.yaml) and not r.has(r"admissionregistration\.k8s\.io/v1(alpha|beta)", r.yaml), "both kinds in admissionregistration.k8s.io/v1")


def e7_2(r):
    return ok(r.has(r"deployments", r.yaml) and r.has(r"CREATE", r.yaml) and r.has(r"team", r.yaml) and r.has(r"platform", r.yaml), "matches deployments CREATE and sets team label")


def e7_3(r):
    if r.has(r"MutatingWebhookConfiguration", r.yaml):
        return (False, "falls back to a webhook")
    return (None, "no webhook; model judges the namespace scoping") if r.has(r"platform", r.yaml) else (False, "binding never names the platform namespace")


def e8_1(r):
    return ok(r.has(r"kubectl\.config\.k8s\.io/v1beta1") and r.has(r"kind:\s*Preference"), "kuberc Preference v1beta1")


def e8_2(r):
    return ok(r.has(r"\bgpw\b") and r.has(r"get.{0,40}pods.{0,40}wide", flags=re.S) and r.has(r"output:\s*kyaml|(-o|--output)[=\s]+kyaml"), "alias gpw and a kyaml output default")


def e8_3(r):
    return ok(r.has(r"(-o|--output)[=\s]+kyaml|output:\s*kyaml"), "kyaml used as an output-flag value")


def e9_1(r):
    return ok(r.has(r"/statusz") and r.has(r"/flagz"), "both endpoints named")


def e9_2(r):
    return (None, "gates named; model judges the stage statement") if r.has(r"ComponentStatusz") and r.has(r"ComponentFlagz") else (False, "feature gates not named")


def e9_3(r):
    """Every curl line uses https and carries credentials."""
    curls = [l for l in r.all.splitlines() if re.search(r"\bcurl\b", l) and "http" in l]
    if not curls:
        return (False, "no curl command")
    bad = [l for l in curls if not re.search(r"--cert|--key|Authorization: ?Bearer|\$TOKEN|--cacert.*--cert|-H ['\"]Authorization", l)]
    return ok(not bad and all("https://" in l for l in curls), f"{len(curls)} curl lines, {len(bad)} without credentials")


def e9_4(r):
    return ok(r.has(r"system:monitoring|nonResourceURLs"), "RBAC named")


def e10_1(r):
    return ok(r.has(r"crashLoopBackOff:(?:\n[ \t]+.*)*\n[ \t]+maxContainerRestartPeriod:\s*\"?30s", r.yaml), "crashLoopBackOff.maxContainerRestartPeriod 30s")


def e10_2(r):
    return ok(r.has(r"imageMaximumGCAge:\s*\"?(168h|7d|10080m|604800s)", r.yaml), "imageMaximumGCAge = 7 days")


def e10_3(r):
    return ok(r.has(r"--config-dir") and r.has(r"kind:\s*KubeletConfiguration", r.yaml) and r.has(r"kubelet\.config\.k8s\.io/v1beta1", r.yaml), "--config-dir with a KubeletConfiguration fragment")


def e11_1(r):
    return ok(r.has(r"Haiku") and r.has(r"Feb(ruary)?\s*2025") and r.has(r"v?1\.33"), "Haiku cutoff Feb 2025, window from v1.33")


def e11_2(r):
    return ok(r.has(r"k8s-features\.py.*table", r.transcript) and r.has(r"--since 2025-01|--since 2025-0[12]|v1\.33", r.transcript), "script run with a v1.33 window")


def e11_3(r):
    dirty = r.work_dirty("skills/k8s-catch-up")
    if dirty:
        return (False, "skill files modified: " + dirty[:200])
    return ok(r.has(r"DRA") and len(re.findall(r"\b(4816|4815|5004|5055|5075|5007|5234|4817|6072|5304|5729|5018|4381)\b", r.answer)) >= 3, "DRA rows listed, skill untouched")


def e12_2(r):
    return ok(r.has(r"how-to-update\.md", r.transcript) and r.has(r"k8s-features\.py", r.transcript), "procedure read and script run")


def e13_1(r):
    return ok(r.has(r"gitRepo") and r.has(r"GitRepoVolumeDriver|disabled|removed") and r.has(r"initContainers:", r.yaml) and r.has(r"git\s+clone|alpine/git|bitnami/git|[\"']?clone[\"']?\s*$", r.yaml) and r.has(r"emptyDir", r.yaml), "gitRepo removal named; init-container clone into emptyDir")


def e13_2(r):
    return ok(r.has(r"externalIPs") and r.has(r"deprecat", flags=re.I | re.M) and r.has(r"v?1\.36") and r.has(r"LoadBalancer|Gateway|Ingress|MetalLB|ExternalName", flags=re.I | re.M), "externalIPs deprecated in v1.36 with a replacement")


def e13_3(r):
    return ok(r.has(r"ipvs") and r.has(r"deprecat", flags=re.I | re.M) and r.has(r"mode:\s*(nftables|iptables)", r.yaml), "ipvs deprecated; config moved to nftables or iptables")


def process_show(r):
    """The lookup path: only per-feature files under references/<category>/ were read, at most four."""
    if "with_skill" not in r.dir:
        return (True, "no skill in this run; vacuous")
    t = r.transcript
    reads = re.findall(r"references/([a-z-]+)/([a-z0-9-]+)\.md", t)
    other = re.findall(r"references/([a-z-]+)\.md", t)  # a whole-category file no longer exists; a read of one is a stale path
    if not reads:
        return (False, "no feature file read; " + (f"{len(other)} stale category-file reads" if other else "answered from memory"))
    distinct = {f"{c}/{f}" for c, f in reads}
    return ok(len(distinct) <= 4, f"{len(distinct)} feature file(s) read: {', '.join(sorted(distinct))[:120]}")


def e12_1(r):
    files = glob.glob(f"{r.work}/skills/k8s-catch-up/references/kubectl-cli/*.md")
    for f in files:
        t = read(f)
        if re.search(r"^# .*KYAML", t, re.M | re.I) or "-o kyaml" in t:
            st = re.search(r"\*\*Status:\*\*.*?(?:\n\n|\n\*\*Where)", t, re.S)
            st = st.group(0) if st else ""
            return ok("v1.35" in st and "v1.37" in st and re.search(r"-o[= ]kyaml|--output[= ]kyaml", t) and "Docs:" in t, f"{os.path.basename(f)}: Status has v1.35 and v1.37, example, Docs")
    return (False, "no KYAML feature file under references/kubectl-cli/")


def e12_3(r):
    s = r.work_file("skills/k8s-catch-up/SKILL.md")
    today = dt.date.today().isoformat()
    m = re.search(r"\*\*Updated:\*\*\s*(\d{4}-\d{2}-\d{2})", s)
    linked = re.search(r"\]\(references/kubectl-cli/[a-z0-9-]*kyaml[a-z0-9-]*\.md\)", s, re.I)
    return ok(m and m.group(1) == today and linked, f"Updated {m.group(1) if m else None} (today {today}); KYAML linked: {bool(linked)}")


def e12_4(r):
    src = f"{REPO}/skills/k8s-catch-up/references/kubectl-cli"
    miss = []
    for f in glob.glob(f"{src}/*.md"):
        if "kyaml" in os.path.basename(f):
            continue
        want = re.findall(r"^\*\*Status:\*\*.*$", read(f), re.M)
        got = r.work_file(f"skills/k8s-catch-up/references/kubectl-cli/{os.path.basename(f)}")
        miss += [w for w in want if w not in got]
    return ok(not miss, "unchanged Status lines" if not miss else "changed: " + miss[0][:80])


CHECKS = {
    (0, 1): e0_1, (0, 2): e0_2, (0, 3): e0_3,
    (1, 1): e1_1, (1, 3): e1_3,
    (2, 1): e2_1, (2, 2): e2_2, (2, 3): e2_3,
    (3, 1): e3_1, (3, 2): e3_2, (3, 3): e3_3,
    (4, 1): e4_1, (4, 2): e4_2,
    (5, 1): e5_1, (5, 2): e5_2,
    (6, 1): e6_1, (6, 2): e6_2,
    (7, 1): e7_1, (7, 2): e7_2, (7, 3): e7_3,
    (8, 1): e8_1, (8, 2): e8_2, (8, 3): e8_3,
    (9, 1): e9_1, (9, 2): e9_2, (9, 3): e9_3, (9, 4): e9_4,
    (10, 1): e10_1, (10, 2): e10_2, (10, 3): e10_3,
    (11, 1): e11_1, (11, 2): e11_2, (11, 3): e11_3,
    (12, 1): e12_1, (12, 2): e12_2, (12, 3): e12_3, (12, 4): e12_4,
    (13, 1): e13_1, (13, 2): e13_2, (13, 3): e13_3,
    (0, 5): process_show, (1, 4): process_show, (2, 4): process_show, (3, 4): process_show, (4, 4): process_show,
    (5, 4): process_show, (6, 4): process_show, (7, 4): process_show, (8, 4): process_show, (9, 5): process_show,
    (10, 4): process_show, (13, 5): process_show,
}
SPLIT = {(2, 2), (2, 3), (7, 3), (9, 2)}


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
            e["context"] = [{"source": "answer", "text": run.answer[:12000]}, {"source": "yaml", "text": run.yaml[:8000]}]
            if run.eval >= 11:
                e["context"].append({"source": "transcript", "text": run.transcript[:8000]})
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
                  "excerpts (answer, produced YAML, transcript for updater evals). Judge each from the excerpts: set `passed`,",
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
