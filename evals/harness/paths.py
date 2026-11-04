"""Locate a skill's source directory in this repo."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def skill_dir(name):
    """Return plugins/<group>/skills/<name>; each skill name lives in exactly one plugin."""
    matches = sorted(ROOT.glob(f"plugins/*/skills/{name}/SKILL.md"))
    if len(matches) != 1:
        raise ValueError(f"Expected one plugins/*/skills/{name}/SKILL.md, found {len(matches)}")
    return matches[0].parent
