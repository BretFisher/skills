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
        # Installers copy only the plugin folder, so each plugin carries its own copy of assets/logo.png.
        icons = [
            (".claude-plugin/plugin.json", manifests.get(".claude-plugin/plugin.json", {}).get("icon")),
            (".cursor-plugin/plugin.json", manifests.get(".cursor-plugin/plugin.json", {}).get("logo")),
        ]
        interface = manifests.get("plugin.json", {}).get("extensions", {}).get("com.openai", {}).get("interface", {})
        icons += [(f"plugin.json {key}", interface.get(key)) for key in ("logo", "composerIcon")]
        for where, icon in icons:
            if not icon:
                problems.append(f"{rel}/{where}: set the logo to ./assets/logo.png")
            elif not (folder / icon).is_file():
                problems.append(f"{rel}/{where}: {icon} does not exist inside the plugin")
        copy = folder / "assets/logo.png"
        if not copy.is_file() or copy.read_bytes() != (ROOT / "assets/logo.png").read_bytes():
            problems.append(f"{rel}/assets/logo.png: copy assets/logo.png over it")
        name = first["name"]
        plugins[name] = rel
        for skill_md in sorted(folder.glob("skills/*/SKILL.md")):
            skill = skill_md.parent.name
            meta = frontmatter(skill_md)
            if meta.get("name") != skill:
                problems.append(f"{skill_md.relative_to(ROOT)}: name must be {skill}")
            if meta.get("license") != "MIT":
                problems.append(f"{skill_md.relative_to(ROOT)}: add license: MIT")
            openai_yaml = skill_md.parent / "agents/openai.yaml"
            if not openai_yaml.is_file():
                problems.append(f"{skill_md.parent.relative_to(ROOT)}: missing agents/openai.yaml")
            else:
                # Codex shows these in its UI; one brand color across every skill and plugin.
                fields = dict(re.findall(r'^  ([a-z_]+): "(.*)"$', openai_yaml.read_text(), re.M))
                if fields.get("brand_color") != interface.get("brandColor"):
                    problems.append(f"{openai_yaml.relative_to(ROOT)}: brand_color must equal plugin.json brandColor {interface.get('brandColor')}")
                if not fields.get("default_prompt"):
                    problems.append(f"{openai_yaml.relative_to(ROOT)}: add interface.default_prompt")
            if skill in owner:
                problems.append(f"skill {skill} is in both {owner[skill]} and {name}")
            owner[skill] = name

        # The Anthropic directory blocks a plugin without a README of 40+ words in its folder.
        readme_md = folder / "README.md"
        text = readme_md.read_text() if readme_md.is_file() else ""
        if len(text.split()) < 40:
            problems.append(f"{rel}/README.md: add a README of at least 40 words (Anthropic directory requires it)")
        for skill, plugin in owner.items():
            if plugin == name and f"(skills/{skill}/SKILL.md)" not in text:
                problems.append(f"{rel}/README.md: link {skill} to skills/{skill}/SKILL.md in the skills table")

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
        # `npx skills` groups a skill under its plugin only when the entry lists the skill's path.
        listed = sorted(f"./skills/{skill}" for skill, plugin in owner.items() if plugin == entry["name"])
        if rel and entry.get("skills") != listed:
            problems.append(f".claude-plugin/marketplace.json: {entry['name']} skills must be {listed} (sorted, same as the skills/ folder)")
        if "strict" in entry:
            problems.append(f".claude-plugin/marketplace.json: {entry['name']} sets strict; the plugin's own plugin.json is the manifest")
    # Claude Code reads the top-level description and Copilot reads metadata.description.
    if claude.get("metadata", {}).get("description") != claude.get("description"):
        problems.append(".claude-plugin/marketplace.json: metadata.description must equal description (Copilot reads metadata)")
    # skills.sh shows the repo page in these groups; one group per plugin, in marketplace order.
    groups = [sorted(g.get("skills", [])) for g in load("skills.sh.json").get("groupings", [])]
    by_plugin = [sorted(s for s, p in owner.items() if p == entry["name"]) for entry in claude["plugins"]]
    if groups != by_plugin:
        problems.append(f"skills.sh.json: groupings must list each plugin's skills in marketplace order, {by_plugin}, found {groups}")
    for old, new in claude.get("renames", {}).items():
        if new not in plugins:
            problems.append(f".claude-plugin/marketplace.json: renames {old} -> {new}, which is not a plugin")

    pi = load("package.json").get("pi", {}).get("skills", [])
    if pi != ["./plugins/*/skills"]:
        problems.append(f"package.json: pi.skills must be ['./plugins/*/skills'], found {pi}")

    readme = (ROOT / "README.md").read_text()
    # Each row links the skill name to its SKILL.md so readers can jump to the source.
    table = re.findall(r"^\| \[`([a-z0-9-]+)`\]\(([^)]+)\) +\| `(bretfisher-[a-z0-9-]+)` +\|", readme, re.M)
    rows = {skill: plugin for skill, _, plugin in table}
    if rows != owner:
        problems.append(f"README.md skills table must map skills to plugins as {owner}, found {rows}")
    for skill, link, _ in table:
        if not link.endswith(f"/skills/{skill}/SKILL.md") or not (ROOT / link).is_file():
            problems.append(f"README.md skills table: {skill} must link to its SKILL.md, found {link}")

    for problem in problems:
        print(problem)
    if problems:
        return 1
    print(f"check-plugins: {len(plugins)} plugins, {len(owner)} skills, 3 marketplaces agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
