"""Copy eval iterations from another clone of this repo over SSH, verify every file, then delete the remote copy.

Run it through `make eval-pull`. The remote side runs this same file from stdin with
`--list`, so both sides hash files with the same function. The remote needs `python3`
and `rsync`; this file uses only the standard library and no package imports so it can
run there without the repo.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SAFE_HOST = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@-]*$")
SAFE_REPO = re.compile(r"^[A-Za-z0-9._/-]+$")
SSH = ["ssh", "-o", "BatchMode=yes"]


def tree_manifest(root):
    """Return ({relative path: sha256 or 'link:<target>'}, newest mtime) for every file below root."""
    files, newest = {}, 0.0
    for top, dirs, names in os.walk(root):
        for name in dirs + names:
            path = os.path.join(top, name)
            newest = max(newest, os.lstat(path).st_mtime)
            rel = os.path.relpath(path, root)
            if os.path.islink(path):
                files[rel] = "link:" + os.readlink(path)
            elif name in names and os.path.isfile(path):
                digest = hashlib.sha256()
                with open(path, "rb") as handle:
                    for chunk in iter(lambda: handle.read(1 << 20), b""):
                        digest.update(chunk)
                files[rel] = digest.hexdigest()
    return files, newest


def list_iterations(repo, skill=None, iteration=None):
    """List evals/<skill>/runs/<iteration>/ directories with their file manifests."""
    evals = os.path.join(repo, "evals")
    if not os.path.isdir(os.path.join(evals, "harness")):
        raise SystemExit(f"{repo} is not a clone of this repo (no evals/harness/)")
    found = []
    for skill_name in sorted(os.listdir(evals)):
        runs = os.path.join(evals, skill_name, "runs")
        if (skill and skill_name != skill) or os.path.islink(runs) or not os.path.isdir(runs):
            continue
        for name in sorted(os.listdir(runs)):
            path = os.path.join(runs, name)
            if (iteration and name != iteration) or os.path.islink(path) or not os.path.isdir(path):
                continue
            if not SAFE_NAME.match(name):
                continue
            files, newest = tree_manifest(path)
            found.append({"skill": skill_name, "name": name, "files": files, "newest": newest})
    return found


def local_name(name, suffix):
    """Name the local copy so it cannot collide with an iteration made on this machine."""
    return f"{name}-{suffix}"


def default_suffix(host):
    return re.sub(r"[^A-Za-z0-9._-]", "-", host.split("@")[-1])


def decide(entry, dest, now, min_age_seconds):
    """Return copy, present (identical local copy exists), conflict (different local copy), or recent."""
    if now - entry["newest"] < min_age_seconds:
        return "recent"
    if dest.exists():
        return "present" if tree_manifest(dest)[0] == entry["files"] else "conflict"
    return "copy"


def remote_list(host, repo, skill, iteration):
    args = ["--list", repo] + (["--skill", skill] if skill else []) + (["--iteration", iteration] if iteration else [])
    result = subprocess.run(SSH + [host, "python3", "-"] + args, input=Path(__file__).read_text(),
                            capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(f"remote listing failed on {host}: {result.stderr.strip()}")
    return json.loads(result.stdout)


def validate(args):
    if not SAFE_HOST.match(args.host):
        raise SystemExit(f"unsafe host: {args.host!r}")
    parts = args.remote_repo.split("/")
    if not SAFE_REPO.match(args.remote_repo) or ".." in parts:
        raise SystemExit(f"unsafe remote repo path: {args.remote_repo!r} (letters, digits, . _ - / only; no ..)")
    for value in (args.skill, args.iteration, args.suffix):
        if value and not SAFE_NAME.match(value):
            raise SystemExit(f"unsafe name: {value!r}")


def pull(args):
    validate(args)
    root = Path(__file__).resolve().parents[2]
    suffix = args.suffix or default_suffix(args.host)
    listing = remote_list(args.host, args.remote_repo, args.skill, args.iteration)
    if not listing["iterations"]:
        print(f"no eval iterations on {args.host}:{args.remote_repo} match")
        return 0
    errors = 0
    for entry in listing["iterations"]:
        remote_path = f"{args.remote_repo}/evals/{entry['skill']}/runs/{entry['name']}"
        dest = root / "evals" / entry["skill"] / "runs" / local_name(entry["name"], suffix)
        label = f"{entry['skill']}/{entry['name']} -> {dest.relative_to(root)}"
        action = decide(entry, dest, listing["now"], args.min_age * 60)
        if action == "recent":
            print(f"skip {label}: a file changed in the last {args.min_age} min; the run may still be going")
            continue
        if action == "conflict":
            print(f"STOP {label}: a different local copy exists; remote kept")
            errors += 1
            continue
        if args.dry_run:
            print(f"dry-run {label}: would {'copy, verify, and ' if action == 'copy' else 'verify and '}"
                  f"{'keep' if args.keep else 'delete'} the remote ({len(entry['files'])} files)")
            continue
        if action == "copy":
            dest.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["rsync", "-a", f"{args.host}:{remote_path}/", f"{dest}/"], check=True)
            if tree_manifest(dest)[0] != entry["files"]:
                print(f"STOP {label}: copied files differ from the remote; remote kept")
                errors += 1
                continue
        note = f"{len(entry['files'])} files, every SHA-256 matches"
        if args.keep:
            print(f"ok {label}: {note}; remote kept")
            continue
        subprocess.run(SSH + [args.host, "rm", "-rf", "--", remote_path, "&&", "test", "!", "-e", remote_path],
                       check=True)
        print(f"ok {label}: {note}; remote deleted")
    return 1 if errors else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--list", metavar="REPO", help=argparse.SUPPRESS)
    parser.add_argument("--host", help="SSH host (an alias from your SSH config)")
    parser.add_argument("--remote-repo", help="the repo clone on the host, absolute or relative to the remote home")
    parser.add_argument("--skill", help="only this skill's runs")
    parser.add_argument("--iteration", help="only this iteration directory name, e.g. iteration-27")
    parser.add_argument("--suffix", help="appended to each local iteration name (default: the host name)")
    parser.add_argument("--min-age", type=int, default=60, help="skip iterations with a file newer than this many minutes")
    parser.add_argument("--keep", action="store_true", help="verify the copy but keep the remote iterations")
    parser.add_argument("--dry-run", action="store_true", help="print the plan; copy and delete nothing")
    args = parser.parse_args(argv)
    if args.list:
        json.dump({"now": time.time(), "iterations": list_iterations(args.list, args.skill, args.iteration)},
                  sys.stdout)
        return 0
    if not args.host or not args.remote_repo:
        parser.error("--host and --remote-repo are required")
    return pull(args)


if __name__ == "__main__":
    sys.exit(main())
