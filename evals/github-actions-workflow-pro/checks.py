#!/usr/bin/env python3
"""checks.py — deterministic grader for the github-actions-workflow-pro evals.

Grades every assertion a program can decide (YAML keys, regexes, byte equality with the
fixture, scanner exit codes) and leaves the rest to the model grader. See AGENTS.md,
"Deterministic checks before model judgment".

Usage:
  checks.py --write   [--scanners] <run-dir>...  write grading.json: program verdicts filled in,
                                                 `passed: null` on the assertions left for the model
  checks.py --compare [--scanners] <run-dir>...  grade, then compare with the verdicts already in
                                                 grading.json (agreement report; nothing written)
  checks.py --finalize <run-dir>...              recompute summary after the model filled the nulls;
                                                 exit 1 if any null remains
  checks.py --batch [--budget=60000] <run-dir>... group runs that still have nulls under an excerpt-byte
                                                 budget and write one grader prompt per group to
                                                 <iteration>/grader-batches/batch-N.md
  checks.py --kinds                              markdown table of program/split/model per eval (coverage.md)

Each null entry carries `context`: the excerpts (answer sections, transcript sections, the produced
YAML, the new SHAs) the model needs to judge it, so the grader can work from grading.json alone.
--finalize removes them.
  <run-dir> = evals/<skill>/runs/<iteration>/eval-N-<name>/<config>/run-M

Without --scanners the scanner assertion is left null. Needs yq (brew install yq) and, for
--scanners, actionlint, zizmor, poutine, pinact, and gh auth (scan.sh sets the token).
Kinds per assertion: program (decided here), split (program decides the mechanical half; the
residual goes to the model), model (judgment only).
"""
import json, re, subprocess, sys, os, glob, shutil, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SKILL = os.path.basename(HERE)
FIX = f"{HERE}/fixtures"
SCAN = f"{REPO}/skills/{SKILL}/scripts/scan.sh"
EVALS = json.load(open(f"{HERE}/evals.json"))["evals"]
SHA = re.compile(r"uses:\s*(\S+)@([0-9a-f]{40})\s*(#.*)?$")
YAML_BLOCK = re.compile(r"```ya?ml\n(.*?)```", re.S)
RUN_SCANNERS = "--scanners" in sys.argv


def yload(text):
    p = subprocess.run(["yq", "-o=json", "."], input=text, capture_output=True, text=True)
    if p.returncode:
        return None
    try:
        return json.loads(p.stdout)
    except json.JSONDecodeError:
        return None


def read(p):
    return open(p).read() if os.path.exists(p) else ""


class Run:
    def __init__(self, d):
        self.dir = d
        self.eval = int(re.search(r"eval-(\d+)", d).group(1))
        self.answer = read(f"{d}/outputs/answer.md")
        self.transcript = read(f"{d}/transcript.md")
        self.grading = json.load(open(f"{d}/grading.json")) if os.path.exists(f"{d}/grading.json") else None
        self.texts = next(e["expectations"] for e in EVALS if e["id"] == self.eval)
        self.wf = {}  # name -> (text, parsed)
        files = [f for f in glob.glob(f"{d}/outputs/**/*.y*ml", recursive=True) if not re.search(r"dependabot|before\.", f)]
        if not files and os.path.isdir(f"{d}/work/.git"):
            dirty = subprocess.run(["git", "status", "--porcelain"], cwd=f"{d}/work", capture_output=True, text=True).stdout
            files = [f for f in glob.glob(f"{d}/work/.github/workflows/*.y*ml") if os.path.basename(f) in dirty or "??" in dirty]
        files = [f for f in files if not f.endswith(".lock.yml")]
        for f in files:
            t = read(f)
            if "\njobs:" in t or t.startswith("jobs:"):
                self.wf[os.path.basename(f)] = (t, yload(t))
        if not self.wf:  # fenced blocks in the answer
            for i, m in enumerate(YAML_BLOCK.findall(self.answer)):
                if "\njobs:" in m:
                    self.wf[f"block-{i}.yml"] = (m, yload(m))
        self.all_text = "\n".join(t for t, _ in self.wf.values())

    def one(self):
        """The single primary workflow (build/edit evals)."""
        for n, v in self.wf.items():
            return n, v[0], v[1]
        return None, "", None

    def section(self, pat):
        """Body of the first `## heading` matching pat (case-insensitive)."""
        parts = re.split(r"^(#{1,3} .*)$", self.answer, flags=re.M)
        for i in range(1, len(parts) - 1, 2):
            if re.search(pat, parts[i].lstrip("# ").strip(), re.I):
                return parts[i + 1]
        return ""


# ---- helpers on parsed YAML ---------------------------------------------------
def jobs(wf):
    return (wf or {}).get("jobs") or {}


def steps(job):
    return job.get("steps") or []


def step_uses(step, name):
    return name in str(step.get("uses", ""))


def perms_ok(wf, top_empty_required=False):
    """permissions: {} (or read-only) at top, no write-all anywhere, every job has permissions."""
    top = wf.get("permissions", "MISSING")
    if top == "MISSING":
        return False, "no top-level permissions key"
    if top == "write-all" or any(j.get("permissions") == "write-all" for j in jobs(wf).values()):
        return False, "write-all present"
    if top_empty_required and top != {}:
        return False, f"top-level permissions is {top!r}, not {{}}"
    if isinstance(top, dict) and any(v == "write" for v in top.values()):
        return False, f"top-level write grant {top}"
    missing = [n for n, j in jobs(wf).items() if "permissions" not in j and "uses" not in j]
    if missing and top != {}:
        pass  # inherited read-only is tolerable
    if missing and top == {}:
        return False, f"jobs without permissions under top-level {{}}: {missing}"
    return True, f"top={top}; jobs={ {n: j.get('permissions') for n, j in jobs(wf).items()} }"


def cancel_in_progress(wf):
    c = wf.get("concurrency")
    return isinstance(c, dict) and c.get("cancel-in-progress") is True


def setup_node_cache(wf):
    for j in jobs(wf).values():
        for s in steps(j):
            if step_uses(s, "actions/setup-node") and str((s.get("with") or {}).get("cache", "")).lower() == "npm":
                return True
    return False


def all_timeouts(wf):
    return all("timeout-minutes" in j or "uses" in j for j in jobs(wf).values()) and bool(jobs(wf))


FRIENDLY = re.compile(r"^[A-Z][A-Za-z0-9]*( [A-Za-z0-9()/&+.-]+)*$")


def excludes_pr(cond):
    """An if: that keeps a job off pull_request events."""
    return bool(re.search(r"!= *'pull_request'|event_name *== *'push'|refs/heads/|refs/tags/|startsWith\(github\.ref", cond))


def trusted_refs(wf):
    """Two-job shape: push:true only in a job with packages: write and an if that excludes PRs;
    push: false job holds no packages: write; push values are literals."""
    pushers, builders, problems = [], [], []
    for jn, j in jobs(wf).items():
        for s in steps(j):
            if step_uses(s, "docker/build-push-action"):
                push = (s.get("with") or {}).get("push")
                perms = j.get("permissions") or {}
                if isinstance(push, str) and "${{" in push:
                    problems.append(f"{jn}: push is an expression ({push})")
                elif push is True:
                    pushers.append(jn)
                    cond = str(j.get("if", "")) + str(s.get("if", ""))
                    if not excludes_pr(cond):
                        problems.append(f"{jn}: push true with no if excluding pull_request ({cond!r})")
                else:
                    builders.append(jn)
                    if perms.get("packages") == "write":
                        problems.append(f"{jn}: push false job holds packages: write")
    if not pushers:
        problems.append("no job pushes")
    if not builders:
        problems.append("no push: false build job")
    return not problems, f"pushers={pushers} builders={builders} " + "; ".join(problems)


def uses_lines(text):
    return {m.group(1): (m.group(2), (m.group(3) or "").strip()) for m in (SHA.search(l) for l in text.splitlines()) if m}


def scanners(run, actionlint_allow=None):
    """Run actionlint, zizmor (regular), poutine, pinact -check on the run's YAML in a scratch repo.

    actionlint_allow: regex of actionlint messages that are the linter's stale schema rather than a
    workflow error (the parallel-step keys it does not know yet). Reports that all match are dropped;
    anything else still fails, so the allowance cannot hide a real finding."""
    if not run.wf:
        return True, "no YAML produced (vacuous)"
    if not RUN_SCANNERS:
        return None, "skipped (--scanners not given)"
    tmp = tempfile.mkdtemp(prefix="gha-check-")
    wfdir = f"{tmp}/.github/workflows"
    os.makedirs(wfdir)
    for n, (t, _) in run.wf.items():
        open(f"{wfdir}/{n}", "w").write(t)
    subprocess.run(["git", "init", "-q"], cwd=tmp)
    subprocess.run(["git", "add", "-A"], cwd=tmp)
    subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "x"], cwd=tmp)
    findings = []
    p = subprocess.run(["actionlint"] + glob.glob(f"{wfdir}/*"), cwd=tmp, capture_output=True, text=True)
    if p.returncode:
        reports = [l for l in p.stdout.splitlines() if re.match(r".*:\d+:\d+: ", l)]
        if actionlint_allow:
            reports = [l for l in reports if not re.search(actionlint_allow, l)]
        if reports:
            findings.append("actionlint: " + reports[0].strip())
    # explicit file list: zizmor's online cache has mis-attributed findings when handed a directory (seen 2026-09-09)
    p = subprocess.run([SCAN, "zizmor", "--no-progress", "--collect=all", "--format", "json", *sorted(os.path.relpath(f, tmp) for f in glob.glob(f"{wfdir}/*"))], cwd=tmp, capture_output=True, text=True)
    try:
        z = json.loads(p.stdout or "[]")
    except json.JSONDecodeError:
        z = []
    for f in z:
        if f.get("ident") == "dangerous-triggers" and re.search(r"collaborator|private repo", run.answer, re.I):
            continue
        findings.append(f"zizmor: {f.get('ident')}")
    p = subprocess.run(["poutine", "analyze_local", ".", "--format", "json", "--quiet", "--disable-version-check"], cwd=tmp, capture_output=True, text=True)
    try:
        po = json.loads(p.stdout or "{}").get("findings", [])
    except json.JSONDecodeError:
        po = []
    for f in po:
        rid = f.get("rule_id")
        if rid == "default_permissions_on_risky_events" and "permissions: {}" in run.all_text:
            continue
        findings.append(f"poutine: {rid}")
    p = subprocess.run([SCAN, "pinact", "run", "-check", "-verify-comment", "-min-age", "7", "-verify-min-age"], cwd=tmp, capture_output=True, text=True)
    if p.returncode:
        findings.append("pinact: " + (p.stderr or p.stdout).strip().splitlines()[-1][:120])
    shutil.rmtree(tmp)
    return not findings, "clean" if not findings else "; ".join(findings)


def raw_provenance(run, new):
    """Program verdict from raw-transcript.jsonl (the subagent's own tool log). Order decides: a SHA that a tool
    produced (pinact output, a `cat`/`git diff` of the pinned file) appears in a tool RESULT before the model ever
    puts it in a tool INPUT (writing outputs/, sed). A SHA whose first appearance is in an input was typed from
    memory or from an unlogged source. A SHA-returning lookup (git/refs, /commits/, /releases, git ls-remote)
    fails outright. Returns (passed, evidence) or None when there is no raw log."""
    path = f"{run.dir}/raw-transcript.jsonl"
    if not os.path.exists(path):
        return None
    seen_in_result, typed, lookups = set(), set(), []
    for line in open(path):
        try: o = json.loads(line)
        except Exception: continue
        msg = o.get("message") or {}
        content = msg.get("content")
        if not isinstance(content, list): continue
        for b in content:
            t = b.get("type")
            if t == "tool_use":
                inp = json.dumps(b.get("input") or {})
                for sha in new:
                    if sha in inp and sha not in seen_in_result: typed.add(sha)
                if b.get("name") == "Bash":
                    cmd = (b.get("input") or {}).get("command", "")
                    if re.search(r"gh api \S*(git/refs|/commits/|/releases)(?!/latest)|git ls-remote|curl \S*api\.github\.com/repos/\S*(commits|git/refs|releases)(?!/latest)", cmd) and "gh-aw" not in cmd:
                        lookups.append(cmd.strip()[:100])
            elif t == "tool_result":
                c = b.get("content"); text = c if isinstance(c, str) else "".join(x.get("text", "") for x in c if isinstance(x, dict))
                for sha in new:
                    if sha in text: seen_in_result.add(sha)
    if lookups:
        return False, f"raw log: SHA-returning lookup: {lookups[:2]}"
    if typed:
        return False, f"raw log: SHA(s) first appear in a tool input, never produced by a tool first: {sorted(typed)[:3]}"
    return True, f"raw log: every new SHA ({len(new)}) was produced by a tool result before any tool input used it; no lookup command"


def transcript_provenance(run, fixture_texts=()):
    """Split check. Vacuous pass when no new SHA was written. Deterministic FAIL on a SHA-returning
    lookup or a missing `pinact run`. Otherwise None: only the model can confirm provenance, because
    a SHA copied from another file is visible only in the transcript's prose (seen once, e6 iteration-11)."""
    bad = re.findall(r"(gh api \S*(?:git/refs|/commits/|/releases)\S*|git ls-remote\S*)", run.transcript)
    bad = [b for b in bad if "gh-aw/releases" not in b]  # e9 reads the gh-aw release tag, not a SHA
    known = set()
    for t in fixture_texts:
        known |= {v[0] for v in uses_lines(t).values()}
    new = {v[0] for v in uses_lines(run.all_text).values()} - known
    if not new:
        return True, "no new SHA written (vacuous)"
    raw = raw_provenance(run, new)
    if raw is not None:
        return raw
    if bad:
        return False, f"SHA-returning lookup in transcript: {bad[:3]}"
    if not re.search(r"pinact run(?! -check)", run.transcript):
        return False, f"{len(new)} new SHA(s) but no `pinact run` (non -check) in transcript"
    return None, f"{len(new)} new SHA(s), `pinact run` present, no lookup; model confirms none was copied by hand"


def dependabot_ok(run):
    t = read(f"{run.dir}/outputs/dependabot.yml") or run.answer
    return bool(re.search(r"package-ecosystem:\s*\"?github-actions", t) and re.search(r"interval:\s*\"?daily", t) and re.search(r"default-days:\s*7", t)), "github-actions/daily/cooldown 7 " + ("found" if "default-days" in t else "missing")


def on_equal(run, fixture):
    _, t, wf = run.one()
    fx = yload(read(fixture))
    return (wf or {}).get("on") == fx.get("on"), f"on={json.dumps((wf or {}).get('on'))} fixture={json.dumps(fx.get('on'))}"


def headings(run):
    return [h.strip("# ").strip() for h in re.findall(r"^#{1,3} .*$", run.answer, re.M)]


def has_heading(run, text):
    """A `##`/`###` heading whose text is exactly `text` (case-insensitive, trailing punctuation ignored)."""
    return any(h.lower().rstrip(":.") == text.lower() for h in headings(run))


def tools_line(run, names):
    sec = run.section(r"^tools\b") or run.section(r"tool") or run.answer
    missing = [n for n in names if not re.search(re.escape(n), sec, re.I)]
    states = bool(re.search(r"\b(ran|absent|skipped)\b", sec, re.I))
    return not missing and states, f"missing={missing} states={states}"


# ---- per-eval check tables ------------------------------------------------------
# Each entry: (1-based index, kind, function(run) -> (passed|None, evidence))
def checks_for(run):
    e = run.eval
    n, text, wf = run.one()
    wf = wf or {}
    T = lambda: transcript_provenance(run, [read(f) for f in glob.glob(f"{FIX}/*.yml")])
    TK = "program" if run.dir and os.path.exists(f"{run.dir}/raw-transcript.jsonl") else "split"  # raw tool log makes provenance decidable
    S = lambda: scanners(run)

    if e == 0:
        return [
            (1, "program", lambda: (bool(re.search(r"run:\s*npm ci\s*$", text, re.M)) and bool(re.search(r"run:\s*npm test\s*$", text, re.M)), "npm ci / npm test as run lines")),
            (2, "program", lambda: perms_ok(wf)),
            (3, "program", lambda: (cancel_in_progress(wf), "concurrency.cancel-in-progress")),
            (4, "program", lambda: (setup_node_cache(wf), "setup-node cache: npm")),
            (5, "program", lambda: (all_timeouts(wf) and bool(wf.get("name")) and all(j.get("name") for j in jobs(wf).values()) and all(s.get("name") for j in jobs(wf).values() for s in steps(j) if s.get("uses")), f"wf name={wf.get('name')!r} jobs named={[bool(j.get('name')) for j in jobs(wf).values()]} unnamed uses steps={sum(1 for j in jobs(wf).values() for s in steps(j) if s.get('uses') and not s.get('name'))} timeouts={all_timeouts(wf)}")),
            (6, "program", S),
            (7, "model", None),
            (8, "model", None),
            (9, TK, T),
        ]
    if e == 1:
        on = wf.get("on") or {}
        push = on.get("push") or {} if isinstance(on, dict) else {}
        return [
            (1, "program", lambda: ("pull_request" in on and "main" in json.dumps(push.get("branches")) and bool(push.get("tags")), f"on={json.dumps(on)}")),
            (2, "program", lambda: trusted_refs(wf)),
            (3, "program", lambda: (any((j.get("permissions") or {}).get("packages") == "write" for j in jobs(wf).values()) and "write-all" not in text, "packages: write on a job, no write-all")),
            (4, "program", lambda: (all(k in text for k in ("cache-from: type=gha", "provenance: true", "sbom: true")), "gha cache + provenance + sbom")),
            (5, "program", S),
            (6, "model", None),
            (7, "program", lambda: (n == "docker.yml" and "github.repository" in text, f"file={n}")),
            (8, TK, T),
        ]
    if e == 2:
        prt = any("pull_request_target" in json.dumps((w or {}).get("on")) for _, w in run.wf.values())  # parsed on:, so a comment does not count
        def digest():
            out = bool(re.search(r"outputs\.digest", run.all_text))
            used = bool(re.search(r"@\$\{\{[^}]*digest", run.all_text, re.I)) or bool(re.search(r"needs\.[\w-]+\.outputs\.[\w-]*digest", run.all_text, re.I))
            return out and used, f"outputs.digest={out} consumed via needs={used}"
        def oidc():
            y = "configure-aws-credentials" in run.all_text and "role-to-assume" in run.all_text and "id-token: write" in run.all_text
            return y or bool(re.search(r"OIDC", run.answer)), f"yaml={y}"
        def pr_no_creds():
            probs = []
            for jn, j in jobs(wf).items():
                pr_runs = not excludes_pr(str(j.get("if", "")))
                p = j.get("permissions") or {}
                if pr_runs and (p.get("packages") == "write" or p.get("id-token") == "write"):
                    probs.append(f"{jn} runs on PR with {p}")
            ok, ev = trusted_refs(wf)
            return ok and not probs, ev + " " + "; ".join(probs)
        return [
            (1, "split", lambda: (True, "no pull_request_target in output") if not prt else (None, "pull_request_target kept; model judges the constraint")),
            (2, "program", lambda: perms_ok(wf)),
            (3, "program", lambda: ("docker/build-push-action" in run.all_text and not re.search(r"run:.*docker (build|push)", run.all_text), "build-push-action present, no shell docker build/push")),
            (4, "program", oidc),
            (5, "program", lambda: (bool(wf.get("concurrency") or any("concurrency" in j for j in jobs(wf).values())) and all_timeouts(wf) and bool(re.search(r"cache(-from)?:", run.all_text)), f"concurrency={bool(wf.get('concurrency') or any('concurrency' in j for j in jobs(wf).values()))} timeouts={all_timeouts(wf)}")),
            (6, "program", S),
            (7, "model", None),
            (8, "model", None),
            (9, "program", pr_no_creds),
            (10, "program", digest),
            (11, TK, T),
        ]
    if e == 3:
        fx = read(f"{FIX}/insecure-ci.yml")
        def major_jump():
            out = uses_lines(text)
            jumped = [a for a, (s, c) in out.items() if a in ("actions/checkout", "actions/setup-node") and not re.search(r"# v4\.", c)]
            if not jumped:
                return True, "stayed on v4"
            names = all(re.search(re.escape(a), run.answer) for a in jumped)
            ok_cmd = bool(re.search(r"pinact run(?! -update)[^\n]*-i ['\"]?actions/[a-z-]+['\"]?", run.answer)) and not re.search(r"-i ['\"]?actions/[a-z-]+@v\d", run.answer)
            return names and ok_cmd, f"jumped {jumped}; named={names}; keep-major command without -update and without @vN in -i: {ok_cmd}"
        def artifact_comment():
            m = re.search(r"uses: actions/upload-artifact@[0-9a-f]{40}\s*# v[\d.]+\s*$", text, re.M)
            return bool(m) and bool(re.search(r"upload-artifact", run.answer)), f"clean comment line={bool(m)} reported={('upload-artifact' in run.answer)}"
        return [
            (1, "program", lambda: ("pull_request_target" not in json.dumps(wf.get("on")) and "pull_request_target" in run.answer, f"trigger removed={'pull_request_target' not in json.dumps(wf.get('on'))} reported={'pull_request_target' in run.answer}")),
            (2, "program", lambda: (not any("pull_request.title" in str(s.get("run", "")) for j in jobs(wf).values() for s in steps(j)) and bool(re.search(r"injection", run.answer, re.I)), "title not in any run:, report says injection")),
            (3, "program", lambda: perms_ok(wf, top_empty_required=True)),
            (4, "program", lambda: (all(a in uses_lines(text) and uses_lines(text)[a][1].startswith("# v") for a in ("actions/checkout", "actions/setup-node")), f"pinned={list(uses_lines(text))}")),
            (5, "program", lambda: (has_heading(run, "Hard findings") and has_heading(run, "Opinions"), f"headings={headings(run)}")),
            (6, "program", lambda: tools_line(run, ["actionlint", "shellcheck", "zizmor", "poutine", "pinact", "gasa", "run-stats"]) if has_heading(run, "Tools") else (False, "no `## Tools` heading")),
            (7, "program", S),
            (8, "split", lambda: (None, f"events in output on:={sorted((wf.get('on') or {}).keys()) if isinstance(wf.get('on'), dict) else wf.get('on')} (fixture: pull_request_target, push); PR-comment shape and the gh-pr-comment-on-push line: model")),
            (9, "program", major_jump),
            (10, "program", artifact_comment),
            (11, TK, T),
        ]
    if e == 4:
        fx = read(f"{FIX}/slow-ci.yml")
        fxu = uses_lines(fx)
        def matrix():
            for j in jobs(wf).values():
                os_ = ((j.get("strategy") or {}).get("matrix") or {}).get("os")
                if os_:
                    alias = sum(1 for o in os_ if o in ("ubuntu-latest", "ubuntu-24.04"))
                    if alias == 1 and "ubuntu-22.04" in os_:
                        return True, f"os={os_}"
                    return (None, f"os={os_}; model judges the coverage question") if alias == 1 else (False, f"os={os_}")
            return None, "no matrix found; model"
        def pins():
            out = uses_lines(run.all_text)
            same = all(a in out and out[a] == v for a, v in fxu.items())
            return same and "write" not in json.dumps(wf.get("permissions")), f"fixture pins kept={same}"
        return [
            (1, "program", lambda: (cancel_in_progress(wf), "cancel-in-progress")),
            (2, "program", lambda: (setup_node_cache(wf), "cache: npm")),
            (3, "split", matrix),
            (4, "split", lambda: (True, "fetch-depth: 0 gone") if "fetch-depth: 0" not in text else (None, "fetch-depth kept; model")),
            (5, "split", lambda: (True, "test job has no needs: lint") if not any("lint" in json.dumps(j.get("needs")) for jn, j in jobs(wf).items() if "test" in jn) else (None, "test job still needs lint; model judges the justification")),
            (6, "program", lambda: (all_timeouts(wf), "timeout on every job")),
            (7, "program", lambda: ("docker/build-push-action" in run.all_text and "type=gha" in run.all_text or "build-push-action" in run.answer, "buildx recommended or applied")),
            (8, "program", pins),
            (9, "model", None),
            (10, "program", S),
            (11, "split", lambda: (True, "on: identical") if on_equal(run, f"{FIX}/slow-ci.yml")[0] else (None, "on: changed; model judges the coverage question " + on_equal(run, f"{FIX}/slow-ci.yml")[1])),
            (12, TK, T),
        ]
    if e == 5:
        fxt = read(f"{FIX}/good-ci-tagged.yml")
        fx = yload(fxt)
        def test_unchanged():
            """test job equal to the fixture once the upload-artifact step's uses: is normalized."""
            import copy
            got = copy.deepcopy(jobs(wf).get("test")); want = copy.deepcopy(fx["jobs"]["test"])
            for job in (got, want):
                for st in steps(job or {}):
                    if step_uses(st, "actions/upload-artifact"):
                        st["uses"] = "actions/upload-artifact@<pin>"
            return got == want and wf.get("on") == fx.get("on") and wf.get("permissions") == fx.get("permissions") and wf.get("concurrency") == fx.get("concurrency"), "test/on/permissions/concurrency equal to fixture apart from the upload-artifact pin"
        def artifact_pinned():
            u = uses_lines(text).get("actions/upload-artifact")
            return bool(u and u[1].startswith("# v")), f"upload-artifact line: {u}"
        lint = jobs(wf).get("lint") or next((j for jn, j in jobs(wf).items() if "lint" in jn), {})
        lu = uses_lines("\n".join(json.dumps(s) for s in steps(lint)))
        def lint_uses():
            """lint job's checkout and setup-node lines equal the fixture test job's (same SHA, same comment)."""
            fx_lines = {l.strip() for l in fxt.splitlines() if "uses:" in l}
            got = []
            for st in steps(lint):
                if step_uses(st, "actions/checkout") or step_uses(st, "actions/setup-node"):
                    line = next((l.strip() for l in text.splitlines() if st.get("uses", "") in l), st.get("uses", ""))
                    got.append(line)
            return len(got) == 2 and all(g in fx_lines for g in got), f"lint uses lines={got}"
        def runs():
            r = [s.get("run") for s in steps(lint) if s.get("run")]
            return r == ["npm ci", "npm run lint"] or (len(r) == 2 and r[0].strip() == "npm ci" and r[1].strip() == "npm run lint"), f"runs={r}"
        return [
            (1, "program", lambda: (lint.get("permissions") == {"contents": "read"}, f"lint perms={lint.get('permissions')}")),
            (2, "program", lint_uses),
            (3, "program", lambda: (any(step_uses(s, "checkout") and (s.get("with") or {}).get("persist-credentials") is False for s in steps(lint)) and any(step_uses(s, "setup-node") and (s.get("with") or {}).get("cache") == "npm" for s in steps(lint)), "persist-credentials false + cache npm in lint")),
            (4, "program", lambda: ("timeout-minutes" in lint and bool(FRIENDLY.match(str(lint.get("name", "")))), f"name={lint.get('name')!r} timeout={'timeout-minutes' in lint}")),
            (5, "split", lambda: (True, "no needs") if "needs" not in lint else (None, "needs present; model")),
            (6, "program", test_unchanged),
            (7, "program", lambda: on_equal(run, f"{FIX}/good-ci-tagged.yml")),
            (8, "program", S),
            (9, "program", runs),
            (10, "program", artifact_pinned),
            (11, TK, T),
        ]
    if e == 6:
        def do_first():
            sec = run.section(r"do.first")
            items = re.findall(r"^\s*(?:\d+[.)]|[-*])\s+\S", sec, re.M)
            return 1 <= len(items) <= 5, f"{len(items)} items"
        def cites():
            c = re.findall(r"`?(zizmor|poutine|actionlint|gasa|pinact)[:`\s]+`?([a-z][a-z0-9_/-]{3,})", run.answer)
            return (True if len(c) >= 3 else None), f"{len(c)} tool:rule citations"
        def sections():
            need = ["Correctness", "Hard findings", "Speed", "Opinions"]
            miss = [k for k in need if not has_heading(run, k)]
            return not miss, f"missing headings={miss}"
        def tools():
            sec = run.section(r"tool") or run.answer
            ok = bool(re.search(r"run-stats[^\n]*skipped", sec, re.I)) and bool(re.search(r"gasa[^\n]*skipped", sec, re.I)) and bool(re.search(r"remote", sec, re.I))
            return ok, "run-stats/gasa skipped with remote reason" if ok else "missing skipped/remote"
        def speed():
            sec = run.section(r"speed")
            names = [f for f in ("insecure-ci", "slow-ci", "deploy") if f in sec]
            return len(names) == 3 and "cancel-in-progress" in sec, f"named={names} cancel={'cancel-in-progress' in sec}"
        def unmodified():
            p = subprocess.run(["git", "status", "--porcelain"], cwd=f"{run.dir}/work", capture_output=True, text=True)
            return p.stdout.strip() == "", f"git status: {p.stdout.strip()!r}"
        def pins():
            probs = []
            for f in ("deploy-static-keys.yml", "slow-ci.yml"):
                fxu = uses_lines(read(f"{FIX}/{f}"))
                out = uses_lines(run.wf.get(f, ("", None))[0])
                for a, v in fxu.items():
                    if a in out and out[a] != v:
                        if out[a][1] < v[1]:  # downgrade comment string compare is rough but v4 < v7
                            probs.append(f"{f}: {a} {v[1]} -> {out[a][1]} (downgrade)")
                        elif not re.search(re.escape(a) + r".{0,200}(major|newer|bump|moved)", run.answer, re.S | re.I):
                            probs.append(f"{f}: {a} {v[1]} -> {out[a][1]} without a stated reason")
            return not probs, "; ".join(probs) or "pinned lines kept"
        return [
            (1, "program", do_first),
            (2, "split", cites),
            (3, "program", sections),
            (4, "program", tools),
            (5, "model", None),
            (6, "program", speed),
            (7, "program", unmodified),
            (8, "program", S),
            (9, "program", pins),
            (10, "model", None),
            (11, "model", None),
            (12, TK, T),
        ]
    if e == 7:
        job = next(iter(jobs(wf).values()), {})
        deploy = next((j for j in jobs(wf).values() if any("configure-aws" in str(s.get("uses")) for s in steps(j))), job)
        def order():
            st = steps(deploy)
            idx = lambda pred: next((i for i, s in enumerate(st) if pred(s)), None)
            aws = idx(lambda s: step_uses(s, "configure-aws-credentials"))
            build = max([i for i, s in enumerate(st) if re.search(r"npm (ci|run build)", str(s.get("run", "")))] or [-1])
            if aws is None:
                return False, "no configure-aws-credentials step"
            if build == -1:
                other = [j for j in jobs(wf).values() if j is not deploy and any("npm" in str(s.get("run", "")) for s in steps(j))]
                return bool(other) and all((j.get("permissions") or {}).get("id-token") != "write" for j in other), "build in a separate job without id-token"
            return aws > build, f"aws step {aws} after build step {build}"
        def pipefail():
            bad = [s.get("run") for j in jobs(wf).values() for s in steps(j) if "\n" in str(s.get("run", "")).strip() and not str(s.get("run")).lstrip().startswith("set -euo pipefail")]
            return not bad, f"{len(bad)} multi-line run blocks without set -euo pipefail"
        def hard_perms():
            hard = run.section(r"^hard findings")
            if not hard:
                return False, "no `## Hard findings` heading"
            return (None, "Hard section mentions permissions; model judges the reason") if "permissions" in hard else (False, "Hard section does not mention permissions")
        return [
            (1, "program", lambda: ("AWS_ACCESS_KEY_ID" not in text and "configure-aws-credentials" in text and "role-to-assume" in text and "id-token: write" in text, "OIDC shape")),
            (2, "program", lambda: ((deploy.get("concurrency") or wf.get("concurrency") or {}).get("cancel-in-progress") is False or "cancel-in-progress: false" in text, "cancel-in-progress: false")),
            (3, "model", None),
            (4, "program", lambda: ("environment" in deploy and all("secrets." not in json.dumps(j) for jn, j in jobs(wf).items() if j is not deploy), f"environment={deploy.get('environment')}")),
            (5, "program", pipefail),
            (6, "program", lambda: (any(step_uses(s, "checkout") and (s.get("with") or {}).get("persist-credentials") is False for s in steps(deploy)) and "timeout-minutes" in deploy, "persist-credentials false + timeout")),
            (7, "program", lambda: dependabot_ok(run)),
            (8, "model", None),
            (9, "program", S),
            (10, "program", order),
            (11, "program", lambda: (wf.get("permissions") == {} and (deploy.get("permissions") or {}).get("contents") == "read" and (deploy.get("permissions") or {}).get("id-token") == "write", f"top={wf.get('permissions')} deploy={deploy.get('permissions')}")),
            (12, "split", hard_perms),
            (13, TK, T),
        ]
    if e == 8:
        ci = next(((t, w) for nme, (t, w) in run.wf.items() if "setup-node" in t), ("", {}))
        dk = next(((t, w) for nme, (t, w) in run.wf.items() if "build-push-action" in t), ("", {}))
        def parallel():
            j = jobs(ci[1])
            l = next((v for k, v in j.items() if "lint" in k), None)
            t = next((v for k, v in j.items() if "test" in k), None)
            return bool(l and t) and "needs" not in l and "needs" not in t and "super-linter" not in run.answer, f"lint={bool(l)} test={bool(t)} super-linter mentioned={'super-linter' in run.answer}"
        def no_triggers():
            for _, w in run.wf.values():
                on = json.dumps((w or {}).get("on"))
                if re.search(r"workflow_dispatch|repository_dispatch|paths", on):
                    return False, on
            return True, "no dispatch or path filters"
        return [
            (1, "program", lambda: ("node-version-file: .nvmrc" in ci[0], "node-version-file")),
            (2, "program", parallel),
            (3, "program", lambda: ("docker-build-workflow" in run.answer, "names docker-build-workflow")),
            (4, "model", None),
            (5, "model", None),
            (6, "program", no_triggers),
            (7, "model", None),
            (8, "program", S),
            (9, "program", lambda: trusted_refs(dk[1]) if dk[1] else (None, "no docker workflow written; model")),
            (10, TK, T),
        ]
    if e == 9:
        lockfx = read(f"{FIX}/link-checker.lock.yml")
        def pair():
            sec = run.section(r"agentic")
            return bool(sec) and "link-checker.lock.yml" in sec and "link-checker.md" in sec, f"agentic section={bool(sec)}"
        def lock_untouched():
            out = read(f"{run.dir}/outputs/link-checker.lock.yml")
            diffed = bool(re.search(r"^\+\+\+ .*link-checker\.lock\.yml", run.answer, re.M))
            return (not out or out == lockfx) and not diffed and "gh aw compile" in run.answer, f"lock output differs={bool(out and out != lockfx)} diff hunk={diffed} compile={'gh aw compile' in run.answer}"
        def stale():
            return "v0.79.0" in run.answer and bool(re.search(r"v0\.(8\d|9\d)\.\d+|\b20\d\d-\d\d-\d\d\b", run.answer)), "reads v0.79.0 and names a newer tag or a date"
        return [
            (1, "program", pair),
            (2, "program", lock_untouched),
            (3, "program", stale),
            (4, "program", lambda: ("gh aw update-actions" in run.answer and "gh aw compile" in run.answer, "both gh aw commands named")),
            (5, "model", None),
            (6, "model", None),
            (7, "program", lambda: ("good-ci.yml" in run.answer.replace(run.section(r"agentic") or "@@", "", 1) if run.section(r"agentic") else "good-ci.yml" in run.answer, "good-ci outside the agentic section")),
            (8, "program", S),
            (9, TK, T),
        ]
    if e == 10:
        j = jobs(wf)
        one_job = next(iter(j.values()), {}) if j else {}
        sts = steps(one_job)
        def concurrent_builds():
            names = ("build:frontend", "build:backend", "build:docs")
            par = [st for st in sts if "parallel" in st]
            in_par = " ".join(json.dumps(st["parallel"]) for st in par)
            if all(nme in in_par for nme in names):
                return True, "all three builds inside a parallel: block"
            bg = [st for st in sts if st.get("background") and any(nme in json.dumps(st) for nme in names)]
            waited = any("wait" in st for st in sts)
            return len(bg) == 3 and waited, f"parallel blocks={len(par)} background builds={len(bg)} wait step={waited}"
        def server_background():
            srv = next((st for st in sts if "start:api" in json.dumps(st)), None)
            shell_bg = bool(re.search(r"start:api\s*&\s*$", run.all_text, re.M))
            return bool(srv and srv.get("background") and srv.get("id")) and not shell_bg, \
                f"server step={bool(srv)} background={bool(srv and srv.get('background'))} id={(srv or {}).get('id')} shell &={shell_bg}"
        def cancels():
            srv = next((st for st in sts if "start:api" in json.dumps(st)), None)
            sid = (srv or {}).get("id")
            return bool(sid) and any(st.get("cancel") == sid for st in sts), f"server id={sid} cancel targets={[st.get('cancel') for st in sts if 'cancel' in st]}"
        def no_sleep():  # split: the sleep is mechanical, the readiness check is judgment
            if re.search(r"sleep\s+30", run.all_text):
                return False, "sleep 30 still in the produced YAML"
            return None, "sleep 30 gone; model judges the readiness check that replaced it"
        def one_job_kept():
            return len(j) == 1 and "matrix" not in run.all_text, f"jobs={list(j)} matrix={'matrix' in run.all_text}"
        def actionlint_note():
            return bool(re.search(r"actionlint", run.answer, re.I)) and bool(re.search(r"unexpected key|does not know|stale schema|schema|not yet support", run.answer, re.I)), \
                "answer names actionlint and its unknown-key/schema lag"
        def recent():  # split: naming the feature as new is mechanical, "does not claim steps cannot parallelize" is judgment
            m = re.search(r"\b2026\b|new(ly)?|recent(ly)?|just (shipped|added|landed)", run.answer, re.I)
            if not m:
                return False, "answer never marks the keys as a recent feature"
            return None, f"answer marks the feature as new ({m.group(0)!r}); model judges the rest"
        return [
            (1, "program", concurrent_builds),
            (2, "program", server_background),
            (3, "program", cancels),
            (4, "split", no_sleep),
            (5, "program", one_job_kept),
            (6, "program", actionlint_note),
            (7, "split", recent),
            (8, "program", lambda: scanners(run, actionlint_allow=r'unexpected key "(background|wait|wait-all|cancel|parallel)"|step must run script with "run" section')),
            (9, "program", lambda: (bool(uses_lines(run.all_text)) and all(v[0] in read(f"{FIX}/serial-build-job.yml") and v[1].startswith("#") for v in uses_lines(run.all_text).values()), f"uses={uses_lines(run.all_text)}")),
        ]
    if e == 11:
        STEPS = ["Run Integration Suite", "Build And Push Image", "Install Dependencies", "Set up job", "Upload Coverage"]
        def names_steps():
            missing = [nme for nme in STEPS if nme.lower() not in run.answer.lower()]
            both_installs = len(re.findall(r"install dependencies", run.answer, re.I)) >= 2
            return not missing and both_installs, f"missing={missing} install mentioned twice={both_installs}"
        def asks_threshold():  # split: a duration question is mechanical, whether it offers a real alternative cut is judgment
            qs = [q for q in re.findall(r"[^.!?\n]*\?", run.answer) if re.search(r"minute|\bmins?\b|second|threshold|cut\b", q, re.I)]
            if not qs:
                return False, "no question about a duration threshold"
            return None, f"threshold question(s) asked: {qs[:3]}"
        def runner_step():  # split: naming it runner time is mechanical, "no YAML fix proposed" is judgment
            near = " ".join(re.findall(r"[^\n]*set up job[^\n]*", run.answer, re.I))
            if not re.search(r"runner|queue|startup|start-up|image|not a (YAML|yaml) step|no YAML fix", near, re.I):
                return False, f"Set up job not explained as runner time: {near[:200]!r}"
            return None, f"Set up job called runner time: {near[:200]!r}"
        def npm_cache():
            return "cache: npm" in run.answer, "setup-node cache: npm named"
        def buildx():
            return bool(re.search(r"setup-buildx", run.answer)) and "type=gha" in run.answer, "buildx + type=gha named"
        def triggers_kept():
            added = [nme for nme, (t, w) in run.wf.items() if "paths-ignore" in t or "paths:" in t]
            return not added or bool(re.search(r"\?", run.answer)), f"yaml with path filters={added}"
        return [
            (1, "program", names_steps),
            (2, "split", asks_threshold),
            (3, "split", runner_step),
            (4, "program", npm_cache),
            (5, "program", buildx),
            (6, "model", None),
            (7, "model", None),
            (8, "program", triggers_kept),
            (9, "program", S),
            (10, "program", lambda: (all(v[0] in read(f"{FIX}/long-tail-ci.yml") and v[1].startswith("#") for v in uses_lines(run.all_text).values()), f"uses={uses_lines(run.all_text)}")),
        ]
    return []


def grade(run):
    """Yield (idx, kind, passed|None, evidence) for every assertion of the run's eval."""
    for idx, kind, fn in checks_for(run):
        if fn is None:
            yield idx, kind, None, "model: judgment only"
            continue
        try:
            res, ev = fn()
        except Exception as ex:  # a check bug must not stop the run
            res, ev = None, f"CHECK ERROR {type(ex).__name__}: {ex}"
        yield idx, kind, res, ev


# ---- excerpts for the model grader --------------------------------------------------
# The residual grader judges from these instead of opening files: a grader call's cost scales with
# the number of tool-call turns (each resends the whole context), not with file size. Specs per
# (eval, assertion): ("answer", heading-regex | None=whole file), ("transcript", regex | None),
# ("yaml", None) = every workflow the run produced, ("head", n) = first n lines of answer.md,
# ("shas", None) = the new SHAs in uses: lines. A regex that matches no heading falls back to the
# whole file. Unlisted residuals get the whole answer.md.
REASONS = [("answer", r"why|reason|default|change|explain|rationale")]
ASKS = [("answer", r"question|assum|default|ask|deferred"), ("transcript", r"question|deferred|assum|default")]
PLACEHOLDERS = [("answer", r"placeholder|confirm|assum")]
PROVENANCE = [("shas", None), ("transcript", r"command|shell|pin|sha|question|deferred")]
EXCERPTS = {
    (0, 7): REASONS, (0, 8): ASKS,
    (1, 6): REASONS, (1, 8): PROVENANCE,
    (2, 1): [("yaml", None), ("answer", r"pull_request_target|trigger|security|hard")], (2, 7): REASONS, (2, 8): PLACEHOLDERS, (2, 11): PROVENANCE,
    (3, 8): [("yaml", None), ("answer", r"correctness|comment|remov|hard")], (3, 11): PROVENANCE,
    (4, 3): [("answer", r"matrix|runner|coverage|question|speed")], (4, 4): [("answer", r"fetch|history|speed|question")],
    (4, 5): [("answer", r"needs|parallel|lint|speed|question")], (4, 9): [("answer", r"speed|why|reason|change")],
    (4, 11): [("answer", r"trigger|on:|coverage|question|assum")], (4, 12): PROVENANCE,
    (5, 5): [("answer", r"needs|parallel|chain|why")], (5, 11): PROVENANCE,
    (6, 2): [("answer", r"correctness|hard|speed|opinion")], (6, 5): [("head", 25), ("answer", r"deliver|format|question|default")],
    (6, 10): [("answer", None)], (6, 11): [("answer", r"correctness|hard|proposed"), ("yaml", None)], (6, 12): PROVENANCE,
    (7, 3): [("answer", r"concurrency|cancel|speed|why|reason")], (7, 8): PLACEHOLDERS, (7, 12): [("answer", r"hard|finding")], (7, 13): PROVENANCE,
    (8, 4): [("answer", r"docker-build-workflow|reusable|question|default|ask|assum")], (8, 5): ASKS, (8, 7): REASONS, (8, 10): PROVENANCE,
    (9, 5): [("answer", r"agentic|dependabot|hard|lock")], (9, 6): [("answer", r"agentic|hard")], (9, 9): PROVENANCE,
    (10, 4): [("yaml", None), ("answer", r"sleep|ready|readiness|health|why")], (10, 7): [("answer", r"parallel|background|new|2026|why")],
    (11, 2): ASKS, (11, 3): [("answer", r"set up job|runner|speed")],
    (11, 6): [("answer", r"integration|speed|log|shard")], (11, 7): [("answer", r"do first|speed|order|first")],
}
EXCERPT_CAP = 30000


def sections_matching(text, pat):
    """Every `#`-heading section whose heading matches pat, as (heading, body) pairs."""
    parts = re.split(r"^(#{1,3} .*)$", text, flags=re.M)
    out = []
    for i in range(1, len(parts) - 1, 2):
        h = parts[i].lstrip("# ").strip()
        if pat is None or re.search(pat, h, re.I):
            out.append((h, parts[i + 1].strip()))
    return out


def clip(t):
    return t if len(t) <= EXCERPT_CAP else t[:EXCERPT_CAP] + f"\n[... clipped at {EXCERPT_CAP} chars; open the file if you need the rest]"


def excerpts_for(run, idx):
    specs = EXCERPTS.get((run.eval, idx), [("answer", None)])
    out = []
    for kind, arg in specs:
        if kind == "answer":
            secs = sections_matching(run.answer, arg) if arg else []
            if secs and sum(len(b) for _, b in secs) >= 600:
                for h, body in secs:
                    out.append({"source": f"outputs/answer.md § {h}", "text": clip(body)})
            else:  # no matching heading, or only stubs: hand over the whole answer
                out.append({"source": "outputs/answer.md (whole file)", "text": clip(run.answer)})
        elif kind == "transcript":
            secs = sections_matching(run.transcript, arg) if arg else []
            if secs:
                for h, body in secs:
                    out.append({"source": f"transcript.md § {h}", "text": clip(body)})
            else:
                out.append({"source": "transcript.md (whole file)", "text": clip(run.transcript)})
        elif kind == "yaml":
            for n, (t, _) in run.wf.items():
                out.append({"source": f"outputs/{n}", "text": clip(t)})
        elif kind == "head":
            out.append({"source": f"outputs/answer.md (first {arg} lines)", "text": "\n".join(run.answer.splitlines()[:arg])})
        elif kind == "shas":
            known = set()
            for f in glob.glob(f"{FIX}/*.yml"):
                known |= {v[0] for v in uses_lines(read(f)).values()}
            new = {a: v[0] for a, v in uses_lines(run.all_text).items() if v[0] not in known}
            out.append({"source": "new SHAs in uses: lines (not in any fixture)", "text": json.dumps(new, indent=1) if new else "none"})
    # de-duplicate identical sources
    seen, dedup = set(), []
    for e in out:
        if e["source"] not in seen:
            seen.add(e["source"]); dedup.append(e)
    return dedup


def write_mode(dirs):
    for d in dirs:
        run = Run(d)
        out = f"{d}/grading.json"
        if os.path.exists(out) and "--force" not in sys.argv:
            print(f"refusing to overwrite {out} (pass --force)"); continue
        exps = []
        for idx, kind, res, ev in grade(run):
            e = {"text": run.texts[idx - 1], "passed": res,
                 "evidence": (f"program ({kind}): {ev}" if res is not None else f"model: {ev}"),
                 "graded_by": "program" if res is not None else "model"}
            if res is None:
                e["context"] = excerpts_for(run, idx)
            exps.append(e)
        n = len(exps); decided = sum(1 for e in exps if e["passed"] is not None)
        nulls = [i + 1 for i, e in enumerate(exps) if e["passed"] is None]
        ctx_chars = sum(len(c["text"]) for e in exps for c in e.get("context", []))
        doc = {"expectations": exps,
               "summary": {"passed": sum(1 for e in exps if e["passed"] is True),
                           "failed": sum(1 for e in exps if e["passed"] is False), "total": n,
                           "pass_rate": None, "pending_model": n - decided}}
        if nulls:
            doc["residual"] = {"indices": nulls, "prompt": next(x["prompt"] for x in EVALS if x["id"] == run.eval),
                               "note": "Judge each null entry from its `context` excerpts. Open a source file only if an excerpt is "
                                       "insufficient, and say so in `evidence`. Set `passed`, replace `evidence` with quoted evidence, "
                                       "set `graded_by` to \"model\", leave every other entry untouched, then recompute `summary`."}
        json.dump(doc, open(out, "w"), indent=2)
        print(f"{d}: {decided}/{n} graded by program, {n - decided} left for the model ({ctx_chars} chars of excerpts)")


def finalize_mode(dirs):
    rc = 0
    for d in dirs:
        g = json.load(open(f"{d}/grading.json"))
        nulls = [i + 1 for i, e in enumerate(g["expectations"]) if e.get("passed") is None]
        if nulls:
            print(f"{d}: still null: {nulls}"); rc = 1; continue
        p = sum(1 for e in g["expectations"] if e["passed"]); n = len(g["expectations"])
        g["summary"] = {"passed": p, "failed": n - p, "total": n, "pass_rate": round(p / n, 4)}
        g.pop("residual", None)
        for e in g["expectations"]:
            e.pop("context", None)  # excerpts served their purpose; keep grading.json lean
        json.dump(g, open(f"{d}/grading.json", "w"), indent=2)
        print(f"{d}: {p}/{n}")
    sys.exit(rc)


def compare_mode(dirs):
    tot = {"program": 0, "split": 0, "model": 0}
    decided = agree = 0
    disagreements, residual = [], {}
    for d in dirs:
        run = Run(d)
        if not run.grading:
            print(f"{d}: no grading.json to compare with"); continue
        label = re.search(r"([^/]+)/(eval-[^/]+)", run.dir)
        print(f"\n== {label.group(1)} / {label.group(2)}  ({len(run.wf)} workflow file(s): {list(run.wf)})")
        for idx, kind, res, ev in grade(run):
            tot[kind] += 1
            model = run.grading["expectations"][idx - 1]["passed"]
            if res is None:
                residual[label.group(2)] = residual.get(label.group(2), 0) + 1
                print(f"  #{idx:<2} {kind:<8} program=undecided model={model}  {ev[:110]}")
                continue
            decided += 1
            if res == model:
                agree += 1
            else:
                disagreements.append((label.group(2), idx, res, model, ev))
            print(f"  #{idx:<2} {kind:<8} {'ok ' if res == model else '!! '}program={res} model={model}  {ev[:110]}")
    print("\nresidual model judgments per eval:")
    for k, v in sorted(residual.items()):
        print(f"  {k}: {v}")
    n = sum(tot.values())
    print(f"\nassertions: {n}  program={tot['program']} split={tot['split']} model={tot['model']}")
    print(f"program-decided verdicts: {decided}; agree with model grader: {agree} ({100*agree//max(decided,1)}%)")
    for d in disagreements:
        print(f"  DISAGREE {d[0]} #{d[1]} program={d[2]} model={d[3]}  {d[4][:160]}")


BATCH_PROMPT = """You are a grader for skill evals. A program has already graded most assertions in each file below; you judge only the entries it left null, working from the excerpts it attached rather than reading files.

Process each grading.json independently, in order:
{files}

In each file, the `residual` object lists the null indices (1-based) and the task prompt. Each null entry in `expectations` has a `context` array of excerpts: the sections of the answer, transcript, or produced YAML that the assertion needs. For each null entry: judge from the excerpts, set `passed` to true or false, replace `evidence` with your quoted evidence, and set `graded_by` to "model". Open a source file (paths are relative to that run directory, the parent of its grading.json) only if an excerpt is insufficient, and say in `evidence` that you did. Leave every other entry untouched. Recompute `summary` (passed, failed, total, pass_rate; remove `pending_model`). Do not add a `timing` object. Do not add `claims`. Add `eval_feedback` only if an assertion looked weak. Write each file back to its own path before starting the next.

Grading standard: PASS needs clear evidence in the excerpts that the expectation is true; the burden of proof is on the expectation; no partial credit.

When done, reply with one line per file: its eval name, how many entries you judged, the final passed/total, and whether you opened any file beyond grading.json.
"""


def batch_mode(dirs):
    """Group runs that still have nulls under an excerpt-byte budget; write one grader prompt per group."""
    budget = int(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--budget=")), 60000))
    runs = []
    for d in dirs:
        g = json.load(open(f"{d}/grading.json"))
        if "residual" not in g:
            continue
        chars = sum(len(c["text"]) for e in g["expectations"] for c in e.get("context", []))
        runs.append((d, chars, len(g["residual"]["indices"])))
    if not runs:
        print("no run has null assertions; nothing to grade"); return
    runs.sort(key=lambda r: -r[1])  # largest first, then fill
    groups = []
    for r in runs:
        for grp in groups:
            if sum(x[1] for x in grp) + r[1] <= budget:
                grp.append(r); break
        else:
            groups.append([r])
    out_dir = os.path.commonpath([os.path.abspath(d) for d, _, _ in runs])
    while out_dir and not re.search(r"iteration-|grader-compare|verify", os.path.basename(out_dir)) and os.path.dirname(out_dir) != out_dir:
        out_dir = os.path.dirname(out_dir)
    bdir = f"{out_dir}/grader-batches"
    shutil.rmtree(bdir, ignore_errors=True); os.makedirs(bdir)
    for i, grp in enumerate(groups, 1):
        files = "\n".join(f"- {os.path.abspath(d)}/grading.json  ({n} null, {c} chars of excerpts)" for d, c, n in grp)
        open(f"{bdir}/batch-{i}.md", "w").write(BATCH_PROMPT.format(files=files))
        print(f"batch-{i}: {len(grp)} run(s), {sum(x[2] for x in grp)} null assertions, {sum(x[1] for x in grp)} chars -> {bdir}/batch-{i}.md")
    print(f"{len(runs)} run(s) need a grader; {len(groups)} grader call(s) at budget {budget} chars. Spawn one grader per file: 'Read <file> and follow it.'")


def kinds_mode():
    """Markdown table of assertion kinds per eval, for coverage.md."""
    print("| Eval | Assertions | program | split | model | split indices | model indices |")
    print("| ---- | ---------- | ------- | ----- | ----- | ------------- | ------------- |")
    tot = {"program": 0, "split": 0, "model": 0}
    for e in EVALS:
        class Stub:  # checks_for only needs .eval, .wf, .answer, .all_text, .dir for table construction
            eval = e["id"]; wf = {}; answer = ""; all_text = ""; transcript = ""; dir = ""; texts = e["expectations"]
            def one(self): return None, "", {}
            def section(self, pat): return ""
        rows = checks_for(Stub())
        c = {k: sum(1 for _, kind, _ in rows if kind == k) for k in tot}
        for k in tot: tot[k] += c[k]
        sp = " ".join(f"#{i}" for i, k, _ in rows if k == "split"); mo = " ".join(f"#{i}" for i, k, _ in rows if k == "model")
        print(f"| e{e['id']} | {len(rows)} | {c['program']} | {c['split']} | {c['model']} | {sp or '—'} | {mo or '—'} |")
    print(f"| **all** | **{sum(tot.values())}** | **{tot['program']}** | **{tot['split']}** | **{tot['model']}** | | |")


def main():
    if "-h" in sys.argv or "--help" in sys.argv or len(sys.argv) < 2:
        print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
    dirs = [a.rstrip("/") for a in sys.argv[1:] if not a.startswith("--")]
    if "--kinds" in sys.argv:
        kinds_mode(); return
    if "--batch" in sys.argv:
        batch_mode(dirs); return
    if "--write" in sys.argv:
        write_mode(dirs)
    elif "--finalize" in sys.argv:
        finalize_mode(dirs)
    else:
        compare_mode(dirs)


if __name__ == "__main__":
    main()
