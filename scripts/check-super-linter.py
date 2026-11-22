#!/usr/bin/env python3
"""Exit 1 when super-linter's supported-linters table differs from our snapshot.

Why: the super-linting skill ships its own copy of super-linter's linter list
(references/linter-commands.md and references/more-linters.md), so agents never
fetch a URL. This check tells a maintainer when that copy is stale.

Usage:
  check-super-linter.py            compare upstream with scripts/super-linter-linters.txt
  check-super-linter.py --update   rewrite the snapshot from upstream

After an update, change the two reference files to match and set their
"Last checked" date. Needs the network.
"""

import difflib
import re
import sys
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/super-linter/super-linter/main/README.md"
SNAPSHOT = Path(__file__).resolve().parent / "super-linter-linters.txt"


def table(readme):
    section = readme.split("## Supported linters and formatters", 1)[1].split("\n## ", 1)[0]
    rows = []
    for line in section.splitlines():
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        cells = [re.sub(r"\s+", " ", re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", c).replace("**", "")) for c in cells]
        if cells[0] == "Language":
            continue
        rows.append(" | ".join(cells).rstrip())
    return rows


def main():
    with urllib.request.urlopen(URL, timeout=30) as response:
        upstream = table(response.read().decode())
    if "--update" in sys.argv:
        SNAPSHOT.write_text("\n".join(upstream) + "\n")
        print(f"super-linter-check: wrote {len(upstream)} rows to {SNAPSHOT.name}; now update the references and their date")
        return 0
    ours = SNAPSHOT.read_text().splitlines()
    diff = list(difflib.unified_diff(ours, upstream, "snapshot", "upstream", lineterm=""))
    if not diff:
        print(f"super-linter-check: {len(upstream)} rows match upstream")
        return 0
    print("\n".join(diff))
    print("super-linter-check: differs; run with --update, then update the super-linting references and their date")
    return 1


if __name__ == "__main__":
    sys.exit(main())
