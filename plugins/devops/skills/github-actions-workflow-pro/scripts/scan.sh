#!/usr/bin/env bash
# scan.sh — run a scanner with the GitHub token set inside this process.
#
# Why: zizmor (online audits) and pinact (tag resolution, min-age checks) read the
# token from the environment. Writing `GH_TOKEN=$(gh auth token) zizmor ...` on the
# caller's command line puts the token into shell traces (`set -x`), agent
# transcripts, and logs. This script fetches the token itself and exec's the tool,
# so the caller's command line, trace, and transcript only ever show `scan.sh`.
# A caller's `set -x` does not propagate into a child script.
#
# Usage:
#   scripts/scan.sh zizmor [zizmor args...]        # GH_TOKEN set from `gh auth token`
#   scripts/scan.sh pinact [pinact args...]        # GITHUB_TOKEN set from `gh auth token`
#   scripts/scan.sh actionlint|poutine|gasa [args] # no token needed; runs the tool as-is
#                                                  # (gasa uses your gh login itself)
#   scripts/scan.sh --help
#
# Token source: an already-exported GH_TOKEN / GITHUB_TOKEN wins (CI); otherwise
# `gh auth token`. If gh is not authenticated the tool still runs, and zizmor prints
# its own "offline mode" warning; pinact will fail on API calls and say so.
#
# Exit codes: the tool's own. 2 = bad arguments, 5 = tool not installed.
set -euo pipefail
set +x  # never trace inside this script, even if the caller exported SHELLOPTS

usage() { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; }

tool="${1:-}"
case "$tool" in
  ""|-h|--help) usage; [ -n "$tool" ]; exit 2 ;;
esac
shift

if ! command -v "$tool" >/dev/null 2>&1; then
  echo "scan.sh: $tool is not installed (brew install $tool)" >&2
  exit 5
fi

token=""
need_token() {
  if [ -n "${GH_TOKEN:-}" ]; then token="$GH_TOKEN"
  elif [ -n "${GITHUB_TOKEN:-}" ]; then token="$GITHUB_TOKEN"
  elif command -v gh >/dev/null 2>&1; then token="$(gh auth token 2>/dev/null || true)"
  fi
  if [ -z "$token" ]; then
    echo "scan.sh: no GitHub token (gh not authenticated); running $tool without one" >&2
  fi
}

case "$tool" in
  zizmor)
    need_token
    [ -n "$token" ] && export GH_TOKEN="$token"
    ;;
  pinact)
    need_token
    [ -n "$token" ] && export GITHUB_TOKEN="$token"
    ;;
  actionlint|poutine|gasa|shellcheck)
    ;;
  *)
    echo "scan.sh: unknown tool '$tool' (zizmor, pinact, actionlint, poutine, gasa)" >&2
    exit 2
    ;;
esac

exec "$tool" "$@"
