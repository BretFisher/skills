#!/usr/bin/env python3
"""k8s-features.py: list the beta and stable Kubernetes features of recent releases.

Maintainer tool for the k8s-catch-up skill. The reading agent never runs it: it reads SKILL.md and the
linked feature files. Joins three public sources into one compact table so an updater never reads a
360 KB changelog:

  kubernetes/enhancements  keps/*/*/kep.yaml     stage, alpha/beta/stable milestones, feature-gate names
  kubernetes/website       feature-gates/*.md    the gate's default value in each version range
  kubernetes/website       blog release posts    what actually shipped (kep.k8s.io/NNNN links), release date

Both repos are cloned once as shallow, blobless, sparse checkouts (about 100 MB total) into
--cache-dir and refreshed on later runs. Needs git and Python 3.9+; no third-party packages.

Usage:
  k8s-features.py releases                       every minor release the blog knows, with its date
  k8s-features.py table [--since YYYY-MM | --releases v1.36,v1.37 | --last N] [--format md|json]
                                                 one row per (release, KEP) that reached beta or stable
  k8s-features.py kep NNNN [--max-words 600]     the Summary and Motivation sections of a KEP README
  k8s-features.py blog v1.36 [--section "OCI"]   headings of a release blog post, or one section's text
  k8s-features.py docs "image volume" [--body]   docs pages whose path or title (or body) matches
  k8s-features.py verify [--strict]              check every feature file's Status line against the release
                                                 posts, the gate pages, and kep.yaml, and SKILL.md's links
                                                 (no dead links, no unlinked file); --strict exits 1 on any note
  k8s-features.py index [--write]                regenerate the Categories section of SKILL.md from the feature
                                                 files under references/<category>/, so the index cannot drift
  k8s-features.py check                          exit 1 when a minor release newer than SKILL.md's Covers
                                                 line exists: the freshness gate

Default window for `table` is the last 12 months. `--include-alpha` adds alpha rows; the skill
leaves them out because an alpha API can change or vanish before anyone should build on it.
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys
import textwrap

REPOS = {
    "enhancements": ("https://github.com/kubernetes/enhancements.git", ["keps"]),
    "website": (
        "https://github.com/kubernetes/website.git",
        [
            "content/en/blog/_posts",
            "content/en/docs/concepts",
            "content/en/docs/tasks",
            "content/en/docs/reference",
            "content/en/docs/tutorials",
            "content/en/examples",
        ],
    ),
}
DEFAULT_CACHE = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "k8s-catch-up")
GATES = "content/en/docs/reference/command-line-tools-reference/feature-gates"
POSTS = "content/en/blog/_posts"
RANK = {"alpha": 0, "beta": 1, "stable": 2}
# every way a release post has linked a KEP so far
KEP_LINK = re.compile(r"(?:kep\.k8s\.io/|enhancements/issues/|kubernetes\.dev/resources/keps/|KEP\s*#)(\d+)")


def sh(args, cwd=None):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout


def sync(cache, offline=False):
    """Clone or refresh both repos. Sparse + blobless keeps the download to the paths we read."""
    for name, (url, paths) in REPOS.items():
        d = os.path.join(cache, name)
        if not os.path.isdir(os.path.join(d, ".git")):
            if offline:
                sys.exit(f"{d} missing and --offline set")
            os.makedirs(cache, exist_ok=True)
            print(f"cloning {url} (sparse) into {d}", file=sys.stderr)
            sh(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse", url, d])
            sh(["git", "sparse-checkout", "set", *paths], cwd=d)
        elif not offline:
            print(f"refreshing {name}", file=sys.stderr)
            sh(["git", "sparse-checkout", "set", *paths], cwd=d)
            sh(["git", "fetch", "-q", "--depth", "1", "origin"], cwd=d)
            sh(["git", "reset", "-q", "--hard", "FETCH_HEAD"], cwd=d)
    return {n: os.path.join(cache, n) for n in REPOS}


# ---- tiny YAML readers (the fields are flat; PyYAML is not always installed) ----------------
def scalar(text, key):
    m = re.search(r"^%s:\s*\"?([^\"\n#]*?)\"?\s*(#.*)?$" % re.escape(key), text, re.M)
    return m.group(1).strip() if m else ""


def block(text, key):
    m = re.search(r"^%s:\s*\n((?:[ \t]+.*\n?)+)" % re.escape(key), text, re.M)
    return m.group(1) if m else ""


def vnorm(v):
    m = re.match(r"\s*\"?v?(1\.\d+)", v or "")
    return "v" + m.group(1) if m else ""


def vkey(v):
    m = re.match(r"v?1\.(\d+)", v or "")
    return int(m.group(1)) if m else -1


def read(p):
    with open(p, errors="ignore") as f:
        return f.read()


# ---- sources ----------------------------------------------------------------------------------
def load_keps(enh):
    keps = []
    for p in glob.glob(os.path.join(enh, "keps", "sig-*", "*", "kep.yaml")):
        t = read(p)
        ms = textwrap.dedent(block(t, "milestone"))
        gates = re.findall(r"^\s*-\s*name:\s*\"?([A-Za-z0-9]+)\"?", block(t, "feature-gates"), re.M)
        keps.append(
            {
                "kep": scalar(t, "kep-number") or os.path.basename(os.path.dirname(p)).split("-")[0],
                "title": scalar(t, "title"),
                "sig": scalar(t, "owning-sig"),
                "status": scalar(t, "status"),
                "stage": scalar(t, "stage"),
                "latest": vnorm(scalar(t, "latest-milestone")),
                "alpha": vnorm(scalar(ms, "alpha")),
                "beta": vnorm(scalar(ms, "beta")),
                "stable": vnorm(scalar(ms, "stable")),
                "gates": gates,
                "path": os.path.relpath(p, enh),
            }
        )
    return keps


def load_gates(web):
    """gate name -> list of {stage, default, from, to}"""
    out = {}
    for p in glob.glob(os.path.join(web, GATES, "*.md")):
        t = read(p)
        stages = []
        for m in re.finditer(r"- stage:\s*(\w+)\n((?:\s+\w+:.*\n?)+)", t):
            body = textwrap.dedent(m.group(2))
            stages.append(
                {
                    "stage": m.group(1),
                    "default": scalar(body, "defaultValue"),
                    "from": vkey(scalar(body, "fromVersion")),
                    "to": vkey(scalar(body, "toVersion")),
                }
            )
        out[os.path.basename(p)[:-3]] = stages
    return out


def gate_at(stages, version):
    v = vkey(version)
    for s in stages:
        if s["from"] <= v and (s["to"] < 0 or v <= s["to"]):
            return s
    return None


def load_blogs(web):
    """version -> {date, path, text, keps:set, toc:[(level, heading)]}"""
    out = {}
    for p in glob.glob(os.path.join(web, POSTS, "**", "*kubernetes-v1-*-release*", "index.md"), recursive=True) + glob.glob(
        os.path.join(web, POSTS, "**", "*kubernetes-v1-*-release*.md"), recursive=True
    ):
        m = re.search(r"kubernetes-v1-(\d+)-release", p)
        if not m:
            continue
        t = read(p)
        date = scalar(t, "date")[:10]
        if not re.match(r"\d{4}-\d{2}-\d{2}", date):
            continue
        out["v1." + m.group(1)] = {
            "date": date,
            "path": os.path.relpath(p, web),
            "text": t,
            "keps": set(KEP_LINK.findall(t)),
            "toc": [(len(h), s.strip()) for h, s in re.findall(r"^(#{2,3}) (.*)$", t, re.M)],
        }
    return out


def heading_for(blog_text, kep):
    """The nearest ### heading above the first mention of the KEP number."""
    m = re.search(r"(?:kep\.k8s\.io/|enhancements/issues/|kubernetes\.dev/resources/keps/|KEP\s*#)%s\b" % kep, blog_text)
    if not m:
        return ""
    i = m.start()
    heads = list(re.finditer(r"^### (.*?)(?:\s*\{#.*\})?$", blog_text[:i], re.M))
    return heads[-1].group(1).strip() if heads else ""


# ---- commands -----------------------------------------------------------------------------------
def pick_releases(blogs, args):
    versions = sorted(blogs, key=vkey)
    if args.releases:
        return [vnorm(v) for v in args.releases.split(",")]
    if args.last:
        return versions[-args.last :]
    since = args.since or (dt.date.today() - dt.timedelta(days=365)).strftime("%Y-%m")
    return [v for v in versions if blogs[v]["date"][:7] >= since]


def cmd_releases(repos, args):
    blogs = load_blogs(repos["website"])
    for v in sorted(blogs, key=vkey):
        print(f"{v}\t{blogs[v]['date']}\t{blogs[v]['path']}")


def cmd_table(repos, args):
    keps, gates, blogs = load_keps(repos["enhancements"]), load_gates(repos["website"]), load_blogs(repos["website"])
    releases = pick_releases(blogs, args)
    stages = ("beta", "stable") + (("alpha",) if args.include_alpha else ())
    rows = []
    for v in releases:
        blog = blogs.get(v)
        for k in keps:
            reached = [s for s in stages if k.get(s) == v]
            if not reached:
                continue
            stage = "stable" if "stable" in reached else reached[0]
            gate_info = []
            for g in k["gates"]:
                if g not in gates:
                    continue  # env vars (KUBECTL_*), placeholders (NA, None), or gates with no docs page yet
                s = gate_at(gates[g], v)
                gate_info.append({"gate": g, "default": (s or {}).get("default", "?"), "stage": (s or {}).get("stage", "?")})
            rows.append(
                {
                    "release": v,
                    "release_date": blog["date"] if blog else "",
                    "stage": stage,
                    "kep": k["kep"],
                    "title": k["title"],
                    "sig": k["sig"].replace("sig-", ""),
                    "alpha": k["alpha"],
                    "beta": k["beta"],
                    "stable": k["stable"],
                    "gates": gate_info,
                    "in_blog": bool(blog and k["kep"] in blog["keps"]),
                    "blog_heading": heading_for(blog["text"], k["kep"]) if blog else "",
                    "kep_status": k["status"],
                    "kep_stage": k["stage"],
                    "kep_path": k["path"],
                }
            )
    rows.sort(key=lambda r: (vkey(r["release"]), r["stage"] != "stable", r["sig"], int(r["kep"] or 0)))
    if args.format == "json":
        json.dump(rows, sys.stdout, indent=1)
        print()
        return
    labels = [f"{v} ({blogs[v]['date']})" if v in blogs else v for v in releases]
    print(f"Releases: {', '.join(labels)}")
    print("in_blog = the release announcement links this KEP, so it shipped as planned; a row without it")
    print("may have slipped: confirm against the changelog before writing it up. default = the feature")
    print("gate's default in that release, from the docs' feature-gate pages. A row whose kep.yaml `stage:` is")
    print("still alpha (or below the row's stage) is flagged in the in_blog column: the milestone block is a")
    print("plan, not a record, and such a row is often a feature that has not shipped.\n")
    print("| release | stage | KEP | title | SIG | beta | GA | gates (default in release) | in_blog | blog heading |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        g = ", ".join(f"{x['gate']} ({'on' if x['default'] == 'true' else 'off' if x['default'] == 'false' else '?'})" for x in r["gates"]) or "-"
        print(
            f"| {r['release']} | {r['stage']} | [{r['kep']}](https://kep.k8s.io/{r['kep']}) | {r['title']} | {r['sig']} | "
            f"{r['beta'] or '-'} | {r['stable'] or '-'} | {g} | {'yes' if r['in_blog'] else 'NO'}"
            f"{' (kep.yaml stage: ' + r['kep_stage'] + ')' if RANK.get(r['kep_stage'], 9) < RANK[r['stage']] else ''} | {r['blog_heading'] or '-'} |"
        )
    print(f"\n{len(rows)} rows")
    by_kep = {k["kep"]: k for k in keps}
    print("\nBlog gaps: KEPs the release post links that the table does not list for that release.")
    print("Most are alpha (skip) or kep.yaml milestones that lag the post; a beta/stable heading here is a")
    print("feature to add by hand, with the post as the source of its stage.\n")
    print("| release | KEP | title | kep.yaml stage | kep.yaml beta | kep.yaml GA | blog heading |")
    print("|---|---|---|---|---|---|---|")
    have = {(r["release"], r["kep"]) for r in rows}
    for v in releases:
        blog = blogs.get(v)
        if not blog:
            continue
        for kep in sorted(blog["keps"], key=int):
            if (v, kep) in have:
                continue
            k = by_kep.get(kep, {})
            print(f"| {v} | [{kep}](https://kep.k8s.io/{kep}) | {k.get('title', '?')} | {k.get('stage', '?')} | {k.get('beta') or '-'} | {k.get('stable') or '-'} | {heading_for(blog['text'], kep) or '-'} |")
    odd = [k for k in keps if k["latest"] in releases and k["stage"] in ("beta", "stable") and k.get(k["stage"]) != k["latest"] and (k["latest"], k["kep"]) not in have]
    if odd:
        print("\nInconsistent kep.yaml: latest-milestone is in the window and stage is beta or stable, but the")
        print("milestone block names another version. The KEP may have slipped or the file may be stale; check")
        print("the release post and the changelog before you include or exclude it.\n")
        print("| latest-milestone | stage | KEP | title | SIG | milestone.beta | milestone.stable |")
        print("|---|---|---|---|---|---|---|")
        for k in sorted(odd, key=lambda k: (vkey(k["latest"]), k["sig"])):
            print(f"| {k['latest']} | {k['stage']} | [{k['kep']}](https://kep.k8s.io/{k['kep']}) | {k['title']} | {k['sig'].replace('sig-', '')} | {k['beta'] or '-'} | {k['stable'] or '-'} |")


def cmd_kep(repos, args):
    paths = glob.glob(os.path.join(repos["enhancements"], "keps", "sig-*", f"{args.number}-*", "README.md"))
    if not paths:
        sys.exit(f"no KEP README for {args.number}")
    t = read(paths[0])
    want = ("Summary", "Motivation", "Goals", "User Stories")
    out = []
    for m in re.finditer(r"^(#{1,4}) (.*)$", t, re.M):
        title = m.group(2).strip()
        if any(title.startswith(w) for w in want):
            end = re.search(r"^#{1,4} ", t[m.end() :], re.M)
            body = t[m.end() : m.end() + end.start()] if end else t[m.end() :]
            body = re.sub(r"<!--.*?-->", "", body, flags=re.S).strip()
            out.append(f"## {title}\n{body}")
    words = " ".join(out).split()
    print(f"# KEP {args.number} ({os.path.relpath(paths[0], repos['enhancements'])})\n")
    print(" ".join(words[: args.max_words]) + (" ..." if len(words) > args.max_words else ""))


def cmd_blog(repos, args):
    blogs = load_blogs(repos["website"])
    b = blogs.get(vnorm(args.version))
    if not b:
        sys.exit(f"no release post for {args.version}; known: {', '.join(sorted(blogs, key=vkey))}")
    if not args.section:
        print(f"{args.version} released {b['date']} ({b['path']})")
        for level, h in b["toc"]:
            print(("  " * (level - 2)) + "- " + re.sub(r"\s*\{#.*\}$", "", h))
        return
    parts = re.split(r"^(#{2,3} .*)$", b["text"], flags=re.M)
    for i in range(1, len(parts) - 1, 2):
        if re.search(args.section, parts[i], re.I):
            print(parts[i].strip() + "\n" + parts[i + 1].strip() + "\n")


def cmd_docs(repos, args):
    root = os.path.join(repos["website"], "content", "en", "docs")
    pat = re.compile(args.query, re.I)
    hits = []
    for p in glob.glob(os.path.join(root, "**", "*.md"), recursive=True):
        rel = os.path.relpath(p, root)
        text = read(p)
        title = scalar(text[:600], "title")
        if pat.search(rel) or pat.search(title) or (args.body and pat.search(text)):
            hits.append((rel, title))
    for rel, title in sorted(hits)[: args.limit]:
        url = "https://kubernetes.io/docs/" + re.sub(r"(/_index|/index)?\.md$", "/", rel)
        print(f"{title}\t{url}\t{os.path.join(root, rel)}")
    if not hits:
        print("no docs page matched; try a shorter query or grep the clone directly", file=sys.stderr)


# ---- the skill's own files ------------------------------------------------------------------------
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(SKILL_DIR, "references")
# category directory -> (title, one-line scope) in the order SKILL.md lists them
CATEGORIES = [
    ("pods", "Pods and containers", "Pod spec fields for lifecycle, resources, volumes, and security"),
    ("workloads-autoscaling", "Workload controllers and autoscaling", "Deployment, StatefulSet, Job, and HPA fields"),
    ("scheduling", "Scheduling", "kube-scheduler behavior and the workload-level APIs"),
    ("dra", "Dynamic Resource Allocation", "ResourceClaim, DeviceClass, and ResourceSlice fields; use `resource.k8s.io/v1`"),
    ("storage", "Storage", "Volumes, CSI, snapshots, and PVC behavior"),
    ("networking", "Networking", "Service fields and validation changes"),
    ("auth-security", "Authentication, authorization, and security", "Identity for Pods and nodes, impersonation, kubelet authorization"),
    ("api-admission", "API server, admission, and API machinery", "In-process admission, storage migration, encodings, control-plane upgrades"),
    ("kubectl-cli", "kubectl and the CLI", "Output formats and the kuberc preferences file"),
    ("observability", "Metrics, logs, and component status", "What the kubelet and control plane expose over HTTP"),
    ("node-kubelet", "Node and kubelet operations", "KubeletConfiguration fields, CPU and memory managers, cgroups"),
    ("removals", "Removals and deprecations", "Things to stop emitting; check every manifest against this list"),
]


def feature_files():
    return sorted(glob.glob(os.path.join(REFS, "*", "*.md")))


def feature(path):
    """One feature file as {heading, status, where, kep, gates, beta, ga, default, verified, ...}."""
    t = read(path)
    h = re.search(r"^# (.*)$", t, re.M)
    st = re.search(r"\*\*Status:\*\*(.*?)(?=\n\*\*Where|\n\n)", t, re.S)
    wh = re.search(r"\*\*Where:\*\*(.*?)(?=\n\n)", t, re.S)
    kep = re.search(r"kep\.k8s\.io/(\d+)", t)
    status = " ".join(st.group(1).split()) if st else ""
    return {
        "path": path,
        "rel": os.path.relpath(path, SKILL_DIR),
        "category": os.path.basename(os.path.dirname(path)),
        "heading": h.group(1).strip() if h else os.path.basename(path)[:-3],
        "status": status,
        "where": " ".join(wh.group(1).split()) if wh else "",
        "kep": kep.group(1) if kep else "",
        "gates": re.findall(r"`([A-Z][A-Za-z0-9]+)`", status),
        "beta": (re.search(r"[Bb]eta (?:in|since) (v1\.\d+)", status) or [None, ""])[1],
        # a GA claim, unless the text attributes it to a source the file then rejects ("kep.yaml says GA in v1.36")
        "ga": next((m.group(1) for m in re.finditer(r"GA (?:in|since) (v1\.\d+)", status) if not re.search(r"(says|claims|targets|lists)\s*(GA )?$", status[max(0, m.start() - 24) : m.start()])), ""),
        # one clear "(on|off) by default" phrase; two or more (a history, or a source conflict) is left unjudged
        "default": (lambda m: m[0] if len(m) == 1 else "")(re.findall(r"\b(on|off) by default", status)),
        "verified": (re.search(r"<!-- verified: (.*?) -->", t) or [None, ""])[1],
        "has_docs": "Docs:" in t,
    }


def index_text(feats):
    """The Categories section of SKILL.md, derived from the feature files: GA first (newest release
    first), then beta, then the rest; every feature is one link."""
    lines = ["## Categories", "", "Each line links every feature file in that category; a file is about 300 tokens. Open the ones", "that match the task.", ""]
    for d, title, scope in CATEGORIES:
        fs = [f for f in feats if f["category"] == d]
        if not fs:
            continue
        fs.sort(key=lambda f: (0 if f["ga"] else 1 if f["beta"] else 2, -vkey(f["ga"] or f["beta"]), f["heading"]))
        links = "; ".join(f"[{f['heading']}]({f['rel']})" for f in fs)
        lines.append(f"**{title}** ({scope}): {links}.")
        lines.append("")
    return "\n".join(lines)


def cmd_index(args):
    feats = [feature(p) for p in feature_files()]
    skill_path = os.path.join(SKILL_DIR, "SKILL.md")
    skill = read(skill_path)
    a, b = skill.index("## Categories"), skill.index("## Updating this skill")
    new = index_text(feats) + "\n"
    norm = lambda x: re.sub(r"\s+", " ", x)
    if norm(skill[a:b]) == norm(new):
        print(f"SKILL.md index up to date ({len(feats)} features)")
        return
    if args.write:
        open(skill_path, "w").write(skill[:a] + new + skill[b:])
        print(f"SKILL.md index rewritten ({len(feats)} features in {len({f['category'] for f in feats})} categories)")
    else:
        print("SKILL.md index differs from the feature files; run with --write")
        sys.exit(1)


def cmd_verify(repos, args):
    """Cross-check each feature file's Status claims against the sources a program can read, then
    check that SKILL.md links every feature file and nothing else."""
    keps = {k["kep"]: k for k in load_keps(repos["enhancements"])}
    gates, blogs = load_gates(repos["website"]), load_blogs(repos["website"])
    feats = [feature(p) for p in feature_files()]
    problems, rows = 0, []
    for f in feats:
        notes = []
        if not f["status"] or not f["where"] or not f["has_docs"]:
            notes.append("missing Status, Where, or Docs")
        if f["category"] not in {c[0] for c in CATEGORIES}:
            notes.append(f"directory {f['category']} is not a known category")
        k = keps.get(f["kep"])
        ev = "-"
        if f["ga"]:
            v = f["ga"]
            blog_ok = bool(blogs.get(v) and f["kep"] in blogs[v]["keps"])
            gate_ok = any(any(s["stage"] == "stable" and s["from"] == vkey(v) for s in gates.get(g, [])) for g in f["gates"])
            if blog_ok:
                ev = "post"
            elif gate_ok:
                ev = "gate page"
            elif f["verified"]:
                ev = "maintainer: " + f["verified"][:40]
            elif k and k["stable"] == v:
                ev = "kep.yaml only"
                notes.append(f"GA {v}: kep.yaml is the only source")
            else:
                ev = "none"
                notes.append(f"GA {v}: no source supports it")
        if f["beta"] and f["default"] and f["gates"]:
            g = f["gates"][0]
            # the claimed default must hold at the beta version or at some later version the gate page covers
            stages_ = [st for st in gates.get(g, []) if st["from"] >= vkey(f["beta"]) or st["to"] < 0 or st["to"] >= vkey(f["beta"])]
            held = {"on" if st["default"] == "true" else "off" for st in stages_ if st["default"] in ("true", "false")}
            if g in gates and held and f["default"] not in held:
                notes.append(f"gate {g} is never {f['default']} by default from {f['beta']} on (page says {', '.join(sorted(held))})")
        if "Unconfirmed" in f["status"]:
            notes.append("Unconfirmed feature is still shipped")
        problems += bool(notes)
        rows.append((f["rel"].replace("references/", ""), f["kep"] or "-", f["beta"] or "-", f["ga"] or "-", ev, "; ".join(notes) or "ok"))
    print("| file | KEP | beta | GA | GA evidence | notes |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        print("| " + " | ".join(r) + " |")
    print(f"\n{len(rows)} feature files, {problems} with notes")
    # SKILL.md links: every link resolves to a file, every feature file is linked
    skill = read(os.path.join(SKILL_DIR, "SKILL.md"))
    linked = set(re.findall(r"\]\((references/[a-z-]+/[a-z0-9-]+\.md)\)", skill))
    files = {f["rel"] for f in feats}
    dead = sorted(linked - files)
    orphan = sorted(files - linked)
    print(f"SKILL.md links: {len(linked & files)} of {len(files)} feature files linked; {len(dead)} dead links; {len(orphan)} unlinked files")
    for d in dead:
        print(f"- dead link: {d}")
    for o in orphan:
        print(f"- not linked from SKILL.md: {o}  (run `index --write`)")
    problems += len(dead) + len(orphan)
    if args.strict and problems:
        sys.exit(1)


def cmd_check(repos, args):
    blogs = load_blogs(repos["website"])
    latest = max(blogs, key=vkey)
    skill = read(os.path.join(SKILL_DIR, "SKILL.md"))
    covers = re.search(r"\*\*Covers:\*\*(.*)$", skill, re.M)
    covered = sorted(set(re.findall(r"v1\.\d+", covers.group(1) if covers else "")), key=vkey)
    top = covered[-1] if covered else "none"
    print(f"newest release: {latest} ({blogs[latest]['date']}); SKILL.md covers up to {top}")
    if vkey(latest) > vkey(top):
        print(f"UPDATE NEEDED: {latest} is not covered. Run the procedure in references/how-to-update.md.")
        sys.exit(1)
    print("up to date")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache-dir", default=DEFAULT_CACHE, help=f"where the two sparse clones live (default {DEFAULT_CACHE})")
    ap.add_argument("--offline", action="store_true", help="use the clones as they are; no fetch")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("releases", help="minor releases the blog knows, with dates")
    t = sub.add_parser("table", help="beta/stable KEP rows for a release window")
    t.add_argument("--since", help="YYYY-MM; releases dated on or after this month (default: 12 months ago)")
    t.add_argument("--releases", help="comma list, e.g. v1.36,v1.37")
    t.add_argument("--last", type=int, help="the N most recent releases")
    t.add_argument("--include-alpha", action="store_true")
    t.add_argument("--format", choices=("md", "json"), default="md")
    k = sub.add_parser("kep", help="Summary/Motivation of one KEP README")
    k.add_argument("number")
    k.add_argument("--max-words", type=int, default=600)
    b = sub.add_parser("blog", help="release post table of contents, or one section")
    b.add_argument("version")
    b.add_argument("--section", help="regex matched against ## and ### headings")
    d = sub.add_parser("docs", help="find docs pages in the local clone")
    d.add_argument("query")
    d.add_argument("--limit", type=int, default=15)
    d.add_argument("--body", action="store_true", help="also match page bodies (slower, wider)")
    v = sub.add_parser("verify", help="check every feature file's Status line against the sources, and SKILL.md's links")
    v.add_argument("--strict", action="store_true", help="exit 1 when any file has a note or a link is wrong")
    ix = sub.add_parser("index", help="regenerate the Categories section of SKILL.md from the feature files")
    ix.add_argument("--write", action="store_true")
    sub.add_parser("check", help="exit 1 when a release newer than SKILL.md's Covers line exists")
    args = ap.parse_args()
    if args.cmd == "index":
        return cmd_index(args)
    repos = sync(args.cache_dir, args.offline)
    {"releases": cmd_releases, "table": cmd_table, "kep": cmd_kep, "blog": cmd_blog, "docs": cmd_docs, "verify": cmd_verify, "check": cmd_check}[args.cmd](repos, args)


if __name__ == "__main__":
    main()
