#!/usr/bin/env bash
# validate.sh — run actionlint, zizmor, poutine, and pinact --check on workflow files in one call.
#
# Why: the Validate step used to be four commands, each a tool call the model paid for on every
# pass, and a forgotten flag on one of them changed the result. One call, fixed flags, one summary.
# zizmor and pinact run through scan.sh, which sets the GitHub token inside its own process, so the
# token never appears in a command line, trace, or transcript.
#
# Usage:
#   scripts/validate.sh [--dir <repo-root>] <workflow-file>...
#     --dir   repository root poutine scans (default: current directory; poutine reads
#             <root>/.github/workflows itself and ignores the file list)
#
# Output: each tool's findings under a "== <tool>" header and a per-tool "clean" or "findings" line,
# then one summary line: "validate: clean" or "validate: N tool(s) reported findings".
# A tool that is not installed prints "<tool>: absent (brew install <tool>)" and does not fail the run;
# the caller reports it by name.
#
# Exit codes: 0 clean, 1 at least one tool reported findings, 2 bad arguments.
set -euo pipefail
set +x

here="$(cd "$(dirname "$0")" && pwd)"
scan="$here/scan.sh"
root="."
files=()

usage() { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --dir) root="${2:?--dir needs a path}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "validate.sh: unknown option $1" >&2; usage; exit 2 ;;
    *) files+=("$1"); shift ;;
  esac
done
[ ${#files[@]} -gt 0 ] || { echo "validate.sh: no workflow files given" >&2; usage; exit 2; }

fail=0
absent=()

run_tool() {
  # run_tool <tool-name> <command...>; the tool's own exit code decides clean vs findings
  local name="$1"; shift
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "$name: absent (brew install $name)"
    absent+=("$name")
    return 0
  fi
  printf '\n== %s\n' "$name"
  if "$@"; then
    echo "$name: clean"
  else
    echo "$name: findings"
    fail=$((fail + 1))
  fi
}

run_tool actionlint actionlint "${files[@]}"
run_tool zizmor "$scan" zizmor --no-progress --collect=all "${files[@]}"
run_tool poutine poutine analyze_local "$root" --quiet --disable-version-check --fail-on-violation
run_tool pinact "$scan" pinact run --check --verify-comment --min-age 7 --verify-min-age "${files[@]}"

echo
if [ "$fail" -eq 0 ]; then
  if [ ${#absent[@]} -gt 0 ]; then
    echo "validate: clean (absent: ${absent[*]})"
  else
    echo "validate: clean"
  fi
else
  echo "validate: $fail tool(s) reported findings"
  exit 1
fi
