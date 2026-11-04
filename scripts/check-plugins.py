#!/usr/bin/env python3
"""Fail when the plugin manifests, marketplaces, skills, and README disagree.

Each harness reads only its own file, so one stale copy breaks one harness
silently. Run from the repo root (make lint does). Prints one line per problem.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = ("plugin.json", ".claude-plugin/plugin.json", ".cursor-plugin/plugin.json")
SHARED = ("name", "description", "keywords", "license")
SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"


def load(path):
    return json.loads((ROOT / path).read_text())


def frontmatter(skill_md):
    text = skill_md.read_text()
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    return dict(re.findall(r"^([a-z-]+):\s*(.*)$", match.group(1), re.M)) if match else {}


def main():
    problems = []
    plugins = {}  # name -> plugin folder, relative to ROOT
    owner = {}  # skill name -> plugin name
    for folder in sorted(p for p in (ROOT / "plugins").iterdir() if p.is_dir()):
        rel = folder.relative_to(ROOT).as_posix()
        manifests = {m: load(f"{rel}/{m}") for m in MANIFESTS if (folder / m).is_file()}
        for missing in set(MANIFESTS) - set(manifests):
            problems.append(f"{rel}: missing {missing}")
        if not manifests:
            continue
        first = next(iter(manifests.values()))
        for m, data in manifests.items():
            if "version" in data:
                problems.append(f"{rel}/{m}: remove version so each commit is an update")
            for key in SHARED:
                if data.get(key) != first.get(key):
                    problems.append(f"{rel}/{m}: {key} differs from {next(iter(manifests))}")
        if manifests.get("plugin.json", {}).get("$schema") != SCHEMA:
            problems.append(f"{rel}/plugin.json: $schema must be {SCHEMA} (Codex rejects other versions)")
        name = first["name"]
        plugins[name] = rel
        for skill_md in sorted(folder.glob("skills/*/SKILL.md")):
            skill = skill_md.parent.name
            meta = frontmatter(skill_md)
            if meta.get("name") != skill:
                problems.append(f"{skill_md.relative_to(ROOT)}: name must be {skill}")
            if meta.get("license") != "MIT":
                problems.append(f"{skill_md.relative_to(ROOT)}: add license: MIT")
            if not (skill_md.parent / "agents/openai.yaml").is_file():
                problems.append(f"{skill_md.parent.relative_to(ROOT)}: missing agents/openai.yaml")
            if skill in owner:
                problems.append(f"skill {skill} is in both {owner[skill]} and {name}")
            owner[skill] = name

    claude = load(".claude-plugin/marketplace.json")
    codex = load(".agents/plugins/marketplace.json")
    cursor = load(".cursor-plugin/marketplace.json")
    sources = {
        ".claude-plugin/marketplace.json": {p["name"]: p["source"] for p in claude["plugins"]},
        ".agents/plugins/marketplace.json": {p["name"]: p["source"]["path"] for p in codex["plugins"]},
        ".cursor-plugin/marketplace.json": {p["name"]: "./" + p["source"] for p in cursor["plugins"]},
    }
    want = {name: f"./{rel}" for name, rel in plugins.items()}
    for path, got in sources.items():
        if got != want:
            problems.append(f"{path}: plugins and sources must be {want}, found {got}")
    for entry in claude["plugins"]:
        rel = plugins.get(entry["name"])
        if rel and entry.get("description") != load(f"{rel}/plugin.json").get("description"):
            problems.append(f".claude-plugin/marketplace.json: {entry['name']} description differs from {rel}/plugin.json")
        for key in ("skills", "strict"):
            if key in entry:
                problems.append(f".claude-plugin/marketplace.json: {entry['name']} sets {key}; the skills/ folder is the list")
    for old, new in claude.get("renames", {}).items():
        if new not in plugins:
            problems.append(f".claude-plugin/marketplace.json: renames {old} -> {new}, which is not a plugin")

    pi = load("package.json").get("pi", {}).get("skills", [])
    if pi != ["./plugins/*/skills"]:
        problems.append(f"package.json: pi.skills must be ['./plugins/*/skills'], found {pi}")

    readme = (ROOT / "README.md").read_text()
    rows = {skill: plugin for plugin, skill in
            re.findall(r"^\| `(bretfisher-[a-z0-9-]+)` +\| `([a-z0-9-]+)` +\|", readme, re.M)}
    if rows != owner:
        problems.append(f"README.md skills table must map skills to plugins as {owner}, found {rows}")

    for problem in problems:
        print(problem)
    if problems:
        return 1
    print(f"check-plugins: {len(plugins)} plugins, {len(owner)} skills, 3 marketplaces agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
