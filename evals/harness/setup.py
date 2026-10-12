"""Named fixture preparation for the Kubernetes updater eval."""

import hashlib
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[2]
ADAPTER = "k8s-restore-kyaml"


def validate_adapter(spec, skill):
    name = spec.get("setup_adapter")
    if name and (name != ADAPTER or skill != "k8s-catch-up" or spec["id"] != 12):
        raise ValueError("Unsupported fixture setup adapter")
    if spec.get("setup") and not name:
        raise ValueError(f"Eval {spec['id']} has procedural setup; add a tested setup adapter before running it")
    return name


def source_plan(cache):
    """Verify existing local checkouts; never clone, fetch, or change host files."""
    repos = {}
    for name in ("enhancements", "website"):
        path = cache / name
        if not (path / ".git").is_dir():
            raise ValueError(f"Missing local Kubernetes source checkout: {path}")
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
        digest = hashlib.sha256()
        for file in sorted(path.rglob("*")):
            if ".git" in file.relative_to(path).parts:
                continue
            if file.is_symlink() and (not file.resolve().is_relative_to(path.resolve()) or
                                      file.is_dir() or ".git" in file.resolve().relative_to(path.resolve()).parts):
                raise ValueError(f"External symlink in source checkout: {file}")
            if not file.is_file():
                continue
            digest.update(str(file.relative_to(path)).encode())
            digest.update(file.read_bytes())
        repos[name] = {"commit": head, "content_sha256": digest.hexdigest()}
    return {"cache": str(cache.resolve()), "repositories": repos}


def prepare_updater(work, home, plan):
    skill = work / "skills/k8s-catch-up"
    shutil.copytree(ROOT / "skills/k8s-catch-up", skill, ignore=shutil.ignore_patterns("__pycache__"))
    (skill / "references/kubectl-cli/kyaml-output-format.md").unlink()
    subprocess.run(["python3", str(skill / "scripts/k8s-features.py"), "index", "--write"],
                   cwd=work, check=True, capture_output=True, text=True)
    cache = Path(plan["cache"])
    if source_plan(cache) != plan:
        raise ValueError("Local Kubernetes sources changed since planning")
    destination = home / "cache/k8s-catch-up"
    # Plain data copies support --offline without exposing host checkouts or Git
    # credentials. The helper's offline check only requires a .git directory.
    for name in plan["repositories"]:
        target = destination / name
        shutil.copytree(cache / name, target, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        (target / ".git").mkdir()
    return skill
