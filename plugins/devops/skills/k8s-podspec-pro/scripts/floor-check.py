#!/usr/bin/env python3
"""floor-check.py: check every pod template in Kubernetes manifests against the pod spec floor.

Why: the floor is fifteen fields across three nesting levels and seven workload kinds. A program finds
a missing field the same way every time; reading YAML by eye does not.

Usage:
  floor-check.py <file>...          plain manifests (multi-document YAML is fine)
  helm template <chart> | floor-check.py -
  kustomize build <dir> | floor-check.py -

Output: one line per finding, "<file> <Kind>/<name> [<container>]: <rule-id>: <message>", then a
summary line "floor-check: clean" or "floor-check: N finding(s)". Lines marked "note:" are exceptions
the script applied (for example hostUsers skipped on a hostNetwork pod); they are not findings.

Rule ids: image-tag, readiness-probe, memory-limit, cpu-request, cpu-limit, allow-privilege-escalation,
privileged, seccomp, run-as-non-root, host-users, sa-token, service-links, grace-period, apparmor.
The script does not check values only the app knows (ports, probe paths, resource numbers).

Exit codes: 0 clean, 1 findings, 2 bad arguments or unparsable YAML, 3 yq absent (brew install yq).
"""
import json
import shutil
import subprocess
import sys

WORKLOADS = {"Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "ReplicationController", "Job"}
BATCH = {"Job", "CronJob"}


def load(path):
    src = sys.stdin.read() if path == "-" else None
    args = ["yq", "-o=json", "-I=0", "ea", "[.]"] + ([] if path == "-" else [path])
    out = subprocess.run(args, input=src, capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"floor-check: cannot parse {path}: {out.stderr.strip()}")
    return [d for d in json.loads(out.stdout or "[]") if isinstance(d, dict)]


def expand(doc):
    """Yield (kind, name, podSpec) for a manifest, following List items."""
    kind = doc.get("kind")
    if kind == "List":
        for item in doc.get("items") or []:
            yield from expand(item)
        return
    spec = doc.get("spec") or {}
    name = (doc.get("metadata") or {}).get("name", "?")
    if kind == "Pod":
        yield kind, name, spec
    elif kind == "CronJob":
        yield kind, name, (((spec.get("jobTemplate") or {}).get("spec") or {}).get("template") or {}).get("spec") or {}
    elif kind in WORKLOADS:
        yield kind, name, (spec.get("template") or {}).get("spec") or {}


def g(d, *keys):
    for k in keys:
        d = (d or {}).get(k)
    return d


def check(kind, ps):
    """Return (findings, notes); a finding is (container or '', rule, message)."""
    f, notes = [], []
    psc = ps.get("securityContext") or {}
    containers = ps.get("containers") or []
    every = lambda key, want: containers and all(g(c, "securityContext", key) == want for c in containers)

    if g(psc, "seccompProfile", "type") != "RuntimeDefault" and not all(
            g(c, "securityContext", "seccompProfile", "type") in ("RuntimeDefault", "Localhost") for c in containers):
        f.append(("", "seccomp", "set securityContext.seccompProfile.type: RuntimeDefault on the pod"))
    if psc.get("runAsNonRoot") is not True and not every("runAsNonRoot", True):
        f.append(("", "run-as-non-root", "set securityContext.runAsNonRoot: true on the pod"))
    if g(psc, "appArmorProfile", "type") == "Unconfined":
        f.append(("", "apparmor", "remove appArmorProfile type Unconfined; leave it unset or RuntimeDefault"))

    host = [k for k in ("hostNetwork", "hostPID", "hostIPC") if ps.get(k) is True]
    if host:
        notes.append(f"hostUsers skipped: the pod sets {', '.join(host)}, which needs the host user namespace")
    elif ps.get("hostUsers") is not False:
        f.append(("", "host-users", "set hostUsers: false (needs Kubernetes 1.33+, Linux 6.3+, containerd 2.0+ or CRI-O 1.25+)"))

    if ps.get("automountServiceAccountToken") is not False:
        sa = ps.get("serviceAccountName") or ps.get("serviceAccount")
        if ps.get("automountServiceAccountToken") is True and sa and sa != "default":
            notes.append(f"token mounted on purpose for ServiceAccount {sa}")
        else:
            f.append(("", "sa-token", "set automountServiceAccountToken: false unless the app calls the Kubernetes API"))
    if ps.get("enableServiceLinks") is not False:
        f.append(("", "service-links", "set enableServiceLinks: false (find Services by DNS name)"))
    if (ps.get("terminationGracePeriodSeconds") or 30) <= 30:
        f.append(("", "grace-period", "set terminationGracePeriodSeconds above the 30s default (pod.yaml uses 600)"))

    for c in containers:
        n = c.get("name", "?")
        image = c.get("image", "")
        last = image.rsplit("/", 1)[-1]
        if "@sha256:" not in image and (":" not in last or last.split(":", 1)[1] in ("latest", "stable")):
            f.append((n, "image-tag", f"pin {image or 'the image'} to an immutable tag or digest"))
        if kind not in BATCH and not c.get("readinessProbe"):
            f.append((n, "readiness-probe", "add a readinessProbe (exec when the app has no port)"))
        lim = g(c, "resources", "limits") or {}
        req = g(c, "resources", "requests") or {}
        if not lim.get("memory") or str(lim.get("memory")) != str(req.get("memory", lim.get("memory"))):
            f.append((n, "memory-limit", "set resources.limits.memory equal to requests.memory"))
        if not req.get("cpu"):
            f.append((n, "cpu-request", "set resources.requests.cpu"))
        if lim.get("cpu"):
            f.append((n, "cpu-limit", "remove limits.cpu unless the pod needs Guaranteed QoS (then limit = request)"))
        if g(c, "securityContext", "allowPrivilegeEscalation") is not False:
            f.append((n, "allow-privilege-escalation", "set securityContext.allowPrivilegeEscalation: false"))
        if g(c, "securityContext", "privileged") is True:
            f.append((n, "privileged", "set securityContext.privileged: false"))
    return f, notes


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if args else 2)
    if not shutil.which("yq"):
        print("floor-check: absent yq (brew install yq)")
        sys.exit(3)
    total = templates = 0
    for path in args:
        for doc in load(path):
            for kind, name, ps in expand(doc):
                templates += 1
                findings, notes = check(kind, ps)
                for container, rule, msg in findings:
                    where = f" [{container}]" if container else ""
                    print(f"{path} {kind}/{name}{where}: {rule}: {msg}")
                for note in notes:
                    print(f"{path} {kind}/{name}: note: {note}")
                total += len(findings)
    if not templates:
        print("floor-check: no pod templates found")
        sys.exit(2)
    print("floor-check: clean" if not total else f"floor-check: {total} finding(s)")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
