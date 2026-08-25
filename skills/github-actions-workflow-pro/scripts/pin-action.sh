#!/usr/bin/env bash
# pin-action.sh — resolve a GitHub Action (or reusable workflow) reference to a
# full commit SHA, choosing the newest release that is at least MIN_AGE_DAYS old.
#
# Why the age rule: a compromised release is usually noticed and yanked within
# days. Waiting before adopting a release lets the ecosystem catch it first.
#
# Requires: gh (authenticated), bash 4+. No jq binary needed — gh's --jq is used.
set -euo pipefail

MIN_AGE_DAYS=7
ALLOW_FRESH=0
LINE_OUTPUT=0

usage() {
  cat <<'EOF'
Usage: pin-action.sh [options] owner/repo[/subpath][@ref]

Resolve an action reference to `owner/repo[/subpath]@<full-sha> # <tag>`.

Without @ref: pick the highest semver release (vX.Y[.Z], no suffix) published
at least --min-age-days ago (default 7). Falls back to semver tags when the
repo has no releases, and to the default branch HEAD when it has neither
(source "branch", comment "# main YYYY-MM-DD", warning on stderr).

With @ref: resolve exactly that tag. Still fails if it is younger than the
minimum age unless --allow-fresh is passed.

Options:
  --min-age-days N   Minimum release age in days (default 7)
  --allow-fresh      Accept a release younger than the minimum age
  --line             Print a ready-to-paste `uses:` line instead of JSON
  -h, --help         Show this help

Output (JSON on stdout, diagnostics on stderr):
  {"uses":"actions/checkout@<sha>","tag":"v7.0.1","comment":"# v7.0.1",
   "published":"2026-07-20T15:10:05Z","age_days":36,"source":"release"}

Exit codes:
  0 resolved     2 bad arguments     3 repo or ref not found
  4 every release or tag is too fresh (use --allow-fresh or an older @ref)
  5 gh missing or not authenticated

Examples:
  pin-action.sh actions/checkout
  pin-action.sh --line docker/build-push-action
  pin-action.sh github/codeql-action/upload-sarif@v3
  pin-action.sh --min-age-days 14 actions/setup-node
EOF
}

die() { echo "pin-action: $2" >&2; exit "$1"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --min-age-days) [ $# -ge 2 ] || die 2 "--min-age-days needs a value"; MIN_AGE_DAYS="$2"; shift 2 ;;
    --allow-fresh)  ALLOW_FRESH=1; shift ;;
    --line)         LINE_OUTPUT=1; shift ;;
    -h|--help)      usage; exit 0 ;;
    -*)             die 2 "unknown option: $1 (see --help)" ;;
    *)              break ;;
  esac
done
[ $# -eq 1 ] || { usage >&2; exit 2; }
[[ "$MIN_AGE_DAYS" =~ ^[0-9]+$ ]] || die 2 "--min-age-days must be an integer, got: $MIN_AGE_DAYS"

command -v gh >/dev/null || die 5 "gh CLI not found; install it and run 'gh auth login'"
gh auth status >/dev/null 2>&1 || die 5 "gh is not authenticated; run 'gh auth login'"

# Parse owner/repo[/subpath][@ref]
SPEC="$1"
REF="${SPEC##*@}"; [ "$REF" = "$SPEC" ] && REF=""
PATHPART="${SPEC%@*}"
OWNER="${PATHPART%%/*}"
REST="${PATHPART#*/}"
REPO="${REST%%/*}"
SUBPATH="${REST#"$REPO"}"; SUBPATH="${SUBPATH#/}"
[ -n "$OWNER" ] && [ -n "$REPO" ] && [ "$OWNER" != "$PATHPART" ] || die 2 "expected owner/repo[/subpath][@ref], got: $SPEC"
FULL="$OWNER/$REPO"
MIN_AGE_SECONDS=$((MIN_AGE_DAYS * 86400))

gh api "repos/$FULL" --jq .full_name >/dev/null 2>&1 || die 3 "repository not found or not accessible: $FULL"

# tag_to_commit <tag> -> commit sha (derefs annotated tags)
tag_to_commit() {
  local tag="$1" type sha
  read -r type sha < <(gh api "repos/$FULL/git/ref/tags/$tag" --jq '"\(.object.type) \(.object.sha)"' 2>/dev/null) \
    || die 3 "tag not found: $FULL@$tag"
  [ -n "$sha" ] || die 3 "tag not found: $FULL@$tag"
  if [ "$type" = "tag" ]; then
    sha=$(gh api "repos/$FULL/git/tags/$sha" --jq .object.sha)
  fi
  printf '%s\n' "$sha"
}

# commit_date <sha> -> ISO8601 committer date
commit_date() { gh api "repos/$FULL/git/commits/$1" --jq .committer.date; }

# age_seconds <iso8601> -> whole seconds since that instant (jq does the date math)
age_seconds() { gh api /rate_limit --jq "(now - (\"$1\"|fromdateiso8601)) | floor"; }

TAG="" PUBLISHED="" SOURCE=""
if [ -n "$REF" ]; then
  TAG="$REF"
  # Prefer the release publish date; bare tags fall back to the commit date below.
  # (gh prints the 404 body on stdout, so discard the output on failure.)
  PUBLISHED=$(gh api "repos/$FULL/releases/tags/$TAG" --jq .published_at 2>/dev/null) || PUBLISHED=""
  if [ -n "$PUBLISHED" ]; then SOURCE="release"; else SOURCE="tag"; fi
else
  # Highest semver release (not newest by date: backports like v3.1.0-node20 are
  # published after v8.x) among non-draft, non-prerelease releases at least MIN_AGE old.
  # Only plain vX.Y[.Z] tags count; suffixed tags are backports or previews.
  SEMVER_FILTER='select(.tag_name | test("^v?[0-9]+\\.[0-9]+(\\.[0-9]+)?$"))'
  SEMVER_KEY='(.tag_name | ltrimstr("v") | split(".") | map(tonumber))'
  read -r TAG PUBLISHED < <(gh api "repos/$FULL/releases?per_page=100" \
    --jq "[.[] | select(.draft==false and .prerelease==false) | $SEMVER_FILTER | select((now - (.published_at|fromdateiso8601)) >= $MIN_AGE_SECONDS)] | max_by($SEMVER_KEY) | select(.) | \"\(.tag_name) \(.published_at)\"" 2>/dev/null) || true
  if [ -n "$TAG" ]; then
    SOURCE="release"
  else
    # No eligible release. Either every semver release is too fresh, or there are none.
    NEWEST=$(gh api "repos/$FULL/releases?per_page=100" \
      --jq "[.[] | select(.draft==false and .prerelease==false) | $SEMVER_FILTER] | max_by($SEMVER_KEY) | select(.) | \"\(.tag_name) \(.published_at)\"" 2>/dev/null) || NEWEST=""
    if [ -n "$NEWEST" ]; then
      if [ "$ALLOW_FRESH" -eq 1 ]; then
        read -r TAG PUBLISHED <<<"$NEWEST"; SOURCE="release"
      else
        die 4 "every release of $FULL is younger than $MIN_AGE_DAYS days (newest: $NEWEST); wait, pin an older @ref, or pass --allow-fresh"
      fi
    else
      # Tags without releases: highest semver tag whose commit is old enough.
      SOURCE="tag"
      while read -r t; do
        [ -n "$t" ] || continue
        d=$(commit_date "$(tag_to_commit "$t")")
        if [ "$(age_seconds "$d")" -ge "$MIN_AGE_SECONDS" ] || [ "$ALLOW_FRESH" -eq 1 ]; then
          TAG="$t"; PUBLISHED="$d"; break
        fi
      done < <(gh api "repos/$FULL/tags?per_page=100" \
        --jq "[.[] | select(.name | test(\"^v?[0-9]+\\\\.[0-9]+(\\\\.[0-9]+)?$\"))] | sort_by(.name | ltrimstr(\"v\") | split(\".\") | map(tonumber)) | reverse | .[].name")
      if [ -z "$TAG" ]; then
        TAG_COUNT=$(gh api "repos/$FULL/tags?per_page=1" --jq length 2>/dev/null || echo 0)
        if [ "$TAG_COUNT" -gt 0 ]; then
          die 4 "every semver tag of $FULL is younger than $MIN_AGE_DAYS days; wait, pin an older @ref, or pass --allow-fresh"
        fi
        # Nothing to pin to but a branch. Pin its HEAD so the ref is at least immutable,
        # and say so: Dependabot will not bump a branch SHA, so this pin needs a human.
        BRANCH=$(gh api "repos/$FULL" --jq .default_branch)
        SHA=$(gh api "repos/$FULL/commits/$BRANCH" --jq .sha)
        PUBLISHED=$(commit_date "$SHA")
        SOURCE="branch"
        TAG="$BRANCH ${PUBLISHED%%T*}"
        echo "pin-action: $FULL has no tags or releases; pinning HEAD of '$BRANCH'. Dependabot cannot update a branch pin, so ask the owner to tag releases." >&2
      fi
    fi
  fi
fi

[ "$SOURCE" = "branch" ] || SHA=$(tag_to_commit "$TAG")

# A moving major tag (v4) points at some exact release (v4.2.1). Prefer the most
# specific tag name on the same commit so the comment says which version was pinned.
SPECIFIC=""
[ "$SOURCE" = "branch" ] || SPECIFIC=$(gh api "repos/$FULL/tags?per_page=100" \
  --jq "[.[] | select(.commit.sha==\"$SHA\") | .name] | sort_by(length) | last // empty" 2>/dev/null) || SPECIFIC=""
if [ -n "$SPECIFIC" ] && [ "$SPECIFIC" != "$TAG" ]; then
  TAG="$SPECIFIC"
  if [ -z "$PUBLISHED" ]; then
    PUBLISHED=$(gh api "repos/$FULL/releases/tags/$TAG" --jq .published_at 2>/dev/null) || PUBLISHED=""
    [ -n "$PUBLISHED" ] && SOURCE="release"
  fi
fi

[ -n "$PUBLISHED" ] || PUBLISHED=$(commit_date "$SHA")
AGE_DAYS=$(( $(age_seconds "$PUBLISHED") / 86400 ))

if [ -n "$REF" ] && [ "$AGE_DAYS" -lt "$MIN_AGE_DAYS" ] && [ "$ALLOW_FRESH" -eq 0 ]; then
  die 4 "$FULL@$TAG is only $AGE_DAYS days old (minimum $MIN_AGE_DAYS); pick an older ref or pass --allow-fresh"
fi

USES="$FULL${SUBPATH:+/$SUBPATH}@$SHA"
if [ "$LINE_OUTPUT" -eq 1 ]; then
  printf 'uses: %s # %s\n' "$USES" "$TAG"
else
  printf '{"uses":"%s","tag":"%s","comment":"# %s","published":"%s","age_days":%s,"source":"%s"}\n' \
    "$USES" "$TAG" "$TAG" "$PUBLISHED" "$AGE_DAYS" "$SOURCE"
fi
