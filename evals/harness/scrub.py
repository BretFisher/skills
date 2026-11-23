"""Find secrets in eval run data, and export a scrubbed copy of the evals to share.

Run it through make:
  make eval-secrets  scans evals/*/runs in place, files and every object in nested git repos; read-only
  make eval-export   copies the eval definitions and runs, drops nested .git folders, replaces personal
                     identifiers with placeholders, scans the copy, and packs it as a tarball only when
                     the scan is clean

Both commands first run a positive control: they plant fake secrets and stop if the scanner misses one.
Findings print masked (first 4 and last 4 characters) with a short hash, so a full secret never prints.
"""

import argparse
import collections
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
EVALS = ROOT / "evals"

SECRET_RULES = {
    "github-token": rb"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,255}\b",
    "github-pat": rb"\bgithub_pat_[A-Za-z0-9_]{60,255}\b",
    "anthropic-key": rb"\bsk-ant-[A-Za-z0-9_-]{20,}",
    "openai-key": rb"\bsk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_-]{32,}",
    "aws-access-key": rb"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b",
    "slack-token": rb"\bxox[abprs]-[A-Za-z0-9-]{10,}",
    "google-api-key": rb"\bAIza[0-9A-Za-z_-]{35}\b",
    "npm-token": rb"\bnpm_[A-Za-z0-9]{36}\b",
    "private-key": rb"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----",
    "jwt": rb"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
    "auth-header": rb"(?i)authorization[\"']?\s*[:=]\s*[\"']?(?:bearer|token|basic)\s+[A-Za-z0-9_\-\.=+/]{16,}",
    "url-credential": rb"\bhttps?://[^/\s:@\"']+:[^/\s@\"']{8,}@[A-Za-z0-9.-]+",
    # An `env` dump prints NAME=value, in a JSON log after an escaped newline (\n). A name that says credential,
    # with a literal value of 16 or more characters, is a finding.
    # Shorter values are documentation examples (GIT_AUTH_TOKEN=mytoken); $VAR and <placeholder> are not values.
    "env-credential": rb"(?:(?<=\\[nt])|\b)[A-Z][A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|PASSWD|API_KEY|APIKEY|PRIVATE_KEY|ACCESS_KEY|CREDENTIAL)"
                      rb"[A-Z0-9_]*=(?![$<])[^\s\"'\\]{16,}",
}
SECRETS ={name: re.compile(rx) for name, rx in SECRET_RULES.items()}

# Identifiers that are not secrets but name a person, an account, or a machine.
GENERIC_HOMES = rb"runner|node|nonroot|linuxbrew|ubuntu|user|app|vscode|root|<user>"
SAFE_EMAIL = re.compile(rb"(?i)(?:^git@|noreply|no-reply|@(?:[\w-]+\.)*(?:example\.(?:com|org|net)|invalid|local|test|localhost)$)")
EMAIL = re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b")
IDENTITY_RULES = [
    ("home-path", re.compile(rb"/Users/(?!Shared\b|<user>)[^/\s\"'\\<>]+"), b"/Users/<user>"),
    ("home-path", re.compile(rb"/home/(?!(?:" + GENERIC_HOMES + rb")(?=[/\s\"'\\]|$))[^/\s\"'\\<>:]+"), b"/home/<user>"),
    ("home-path", re.compile(rb"-Users-(?!<user>)[A-Za-z0-9._]+-"), b"-Users-<user>-"),
    ("account-field", re.compile(rb"(\"(?:organizationUuid|accountUuid|organization_uuid|account_uuid|userEmail|emailAddress)\\?\"\s*:\s*\\?\")"
                                 rb"[^\"\\]+"), rb"\1<redacted>"),
    ("account-env", re.compile(rb"(?:(?<=\\[nt])|\b)((?:CLAUDE_CODE_[A-Z_]*(?:UUID|SESSION_ID|EMAIL)|BAGGAGE)=)(?!<)[^\s\"\\]+"), rb"\1<redacted>"),
    ("user-env", re.compile(rb"(?:(?<=\\[nt])|\b)((?:USER|LOGNAME)=)(?!<)[^\s\"\\]+"), rb"\1<user>"),
]


def mask(value):
    text = value.decode("utf-8", "replace")
    return text if len(text) <= 12 else f"{text[:4]}…{text[-4:]} (len {len(text)})"


def find_secrets(data):
    """Yield (rule, value, offset) for each secret pattern match in data."""
    for name, rx in SECRETS.items():
        for m in rx.finditer(data):
            yield name, m.group(0), m.start()


def git_objects(repo):
    """Return the content of every object in a git repo, dangling objects included."""
    out = subprocess.run(["git", "-c", "safe.directory=*", "-C", str(repo), "cat-file", "--batch-all-objects", "--batch"],
                         capture_output=True, check=False)
    return out.stdout


def scan_tree(roots, extra=None):
    """Scan files and nested git objects below roots; return (findings, stats)."""
    findings, stats = [], collections.Counter()

    def check(data, where):
        for rule, value, offset in find_secrets(data):
            findings.append({"rule": rule, "where": where, "line": data.count(b"\n", 0, offset) + 1,
                             "masked": mask(value), "id": hashlib.sha256(value).hexdigest()[:10]})
        if extra:
            for rule, value, offset in extra(data):
                findings.append({"rule": rule, "where": where, "line": data.count(b"\n", 0, offset) + 1,
                                 "masked": mask(value), "id": hashlib.sha256(value).hexdigest()[:10]})

    for root in roots:
        for top, dirs, names in os.walk(root):
            if ".git" in dirs:
                dirs.remove(".git")
                stats["git repos"] += 1
                check(git_objects(top), os.path.join(top, ".git") + " [objects]")
            for name in names:
                path = os.path.join(top, name)
                if os.path.islink(path):
                    check(os.readlink(path).encode(), path + " [link target]")
                elif os.path.isfile(path):
                    stats["files"] += 1
                    with open(path, "rb") as handle:
                        check(handle.read(), path)
    return findings, stats


def selftest():
    """Plant fake secrets in a file and in a git commit; stop if the scanner misses either."""
    fake = b"gho_" + b"A1b2C3d4" * 4 + b"Zz99"
    with tempfile.TemporaryDirectory() as temp:
        run = Path(temp) / "run"
        (run / "work").mkdir(parents=True)
        (run / "raw-transcript.jsonl").write_bytes(b'{"output":"' + fake + b'"}\n')
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@t.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null"]
        subprocess.run(git + ["init", "-q"], cwd=run / "work", check=True)
        subprocess.run(git + ["commit", "-q", "--allow-empty", "-m", "GH_TOKEN=" + fake.decode()], cwd=run / "work", check=True)
        findings, _ = scan_tree([run])
    places = {f["where"].rsplit("/", 1)[-1] for f in findings if f["rule"] == "github-token"}
    if places != {"raw-transcript.jsonl", ".git [objects]"}:
        raise SystemExit(f"secret scanner self-test failed: planted token found in {sorted(places)}; nothing exported")


def local_literals(redact_file):
    """Strings to replace that the repo must not name: this machine's host name and lines of the local redact file."""
    literals = set()
    for name in {socket.gethostname(), socket.gethostname().split(".")[0]}:
        if len(name) >= 4 and name.lower() not in {"localhost", "localhost.localdomain", "local"}:
            literals.add(name)
    if redact_file and Path(redact_file).is_file():
        for line in Path(redact_file).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                literals.add(line)
    return sorted(literals, key=len, reverse=True)


def redact(data, literals, counts):
    """Replace personal identifiers in data; count each rule that changed something."""
    def email(m):
        if SAFE_EMAIL.search(m.group(0)):
            return m.group(0)
        counts["email"] += 1
        return b"<email>"

    data = EMAIL.sub(email, data)
    for rule, rx, replacement in IDENTITY_RULES:
        data, n = rx.subn(replacement, data)
        counts[rule] += n
    for literal in literals:
        n = data.count(literal.encode())
        if n:
            data = data.replace(literal.encode(), b"<redacted>")
            counts["local-literal"] += n
    return data


def identity_leftovers(literals):
    """An extra scan rule for the export: any identifier that redaction should have replaced."""
    def check(data):
        for m in EMAIL.finditer(data):
            if not SAFE_EMAIL.search(m.group(0)):
                yield "leftover-email", m.group(0), m.start()
        for rule, rx, _ in IDENTITY_RULES:
            for m in rx.finditer(data):
                if b"<user>" not in m.group(0) and b"<redacted>" not in m.group(0):
                    yield "leftover-" + rule, m.group(0), m.start()
        for literal in literals:
            start = data.find(literal.encode())
            if start >= 0:
                yield "leftover-local-literal", literal.encode(), start
    return check


def eval_dirs(skill=None):
    return sorted(p.parent for p in EVALS.glob("*/evals.json") if not skill or p.parent.name == skill)


def print_findings(findings):
    groups = collections.defaultdict(list)
    for f in findings:
        groups[(f["rule"], f["id"])].append(f)
    for (rule, digest), group in sorted(groups.items()):
        paths = sorted({f["where"] for f in group})
        print(f"[{rule}] id={digest} value={group[0]['masked']} occurrences={len(group)}")
        for path in paths[:5]:
            print(f"   {path}")
        if len(paths) > 5:
            print(f"   … {len(paths) - 5} more")


def scan(args):
    selftest()
    roots = [d / "runs" for d in eval_dirs(args.skill) if (d / "runs").is_dir()]
    findings, stats = scan_tree(roots)
    print(f"scanned {stats['files']} files and the objects of {stats['git repos']} git repos in {len(roots)} runs folders")
    print_findings(findings)
    print(f"secrets found: {len(findings)}")
    return 1 if findings else 0


def export(args):
    selftest()
    literals = local_literals(args.redact_file)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = Path(args.out).resolve()
    name = f"skill-evals-{stamp}"
    stage = out / name
    stage.mkdir(parents=True)
    ignore = shutil.ignore_patterns(".git", "__pycache__", ".DS_Store")
    skills = eval_dirs(args.skill)
    for path in [EVALS / "README.md", EVALS / "eval.gitconfig"]:
        shutil.copy2(path, stage / path.name)
    shutil.copytree(EVALS / "harness", stage / "harness", ignore=ignore)
    removed_git = sum(1 for d in skills for _ in (d / "runs").glob("**/.git")) if skills else 0
    for skill in skills:
        shutil.copytree(skill, stage / skill.name, ignore=ignore, symlinks=True)

    counts = collections.Counter()
    for top, _, names in os.walk(stage):
        for filename in names:
            path = os.path.join(top, filename)
            if os.path.islink(path):
                target = redact(os.readlink(path).encode(), literals, counts).decode()
                os.unlink(path)
                os.symlink(target, path)
                continue
            with open(path, "rb") as handle:
                data = handle.read()
            new = redact(data, literals, counts)
            if new != data:
                with open(path, "wb") as handle:
                    handle.write(new)
    # Names carry identifiers too (an iteration folder named after the machine that ran it); rename deepest first.
    for top, dirs, names in os.walk(stage, topdown=False):
        for entry in dirs + names:
            renamed = entry
            for literal in literals:
                renamed = renamed.replace(literal, "redacted")
            if renamed != entry:
                os.rename(os.path.join(top, entry), os.path.join(top, renamed))
                counts["path-name"] += 1

    findings, stats = scan_tree([stage], extra=identity_leftovers(literals))
    leftover = identity_leftovers(literals)
    for top, dirs, names in os.walk(stage):
        for entry in dirs + names:
            relative = os.path.relpath(os.path.join(top, entry), stage).encode()
            for rule, value, _ in leftover(relative):
                findings.append({"rule": rule + " [path]", "where": os.path.join(top, entry), "line": 0,
                                 "masked": mask(value), "id": hashlib.sha256(value).hexdigest()[:10]})
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    record = {"created": stamp, "source_commit": commit, "skills": [s.name for s in skills], "files": stats["files"],
              "nested_git_folders_removed": removed_git, "replacements": dict(sorted(counts.items())),
              "secret_rules": sorted(SECRET_RULES), "findings_after_redaction": len(findings)}
    (stage / "EXPORT.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"copied {stats['files']} files from {len(skills)} skills; removed {removed_git} nested .git folders")
    print("replacements: " + (", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "none"))
    if findings:
        print_findings(findings)
        print(f"STOP: {len(findings)} findings remain in {stage}; no tarball was written")
        return 1
    tarball = out / f"{name}.tar.gz"
    with tarfile.open(tarball, "w:gz") as tar:
        tar.add(stage, arcname=name)
    shutil.rmtree(stage)
    digest = hashlib.sha256(tarball.read_bytes()).hexdigest()
    print(f"clean: {tarball} ({tarball.stat().st_size // (1 << 20)} MiB, sha256 {digest})")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    scan_parser = sub.add_parser("scan", help="scan evals/*/runs in place; exit 1 on any secret")
    scan_parser.add_argument("--skill", help="only this skill's runs")
    export_parser = sub.add_parser("export", help="write a scrubbed, scanned tarball of the evals")
    export_parser.add_argument("--skill", help="only this skill")
    export_parser.add_argument("--out", default=str(EVALS / "_export"), help="folder for the tarball (default evals/_export)")
    export_parser.add_argument("--redact-file", default=str(EVALS / ".export-redact"),
                               help="local, gitignored file: one more string to replace per line (default evals/.export-redact)")
    args = parser.parse_args(argv)
    return scan(args) if args.command == "scan" else export(args)


if __name__ == "__main__":
    sys.exit(main())
