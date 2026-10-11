#!/usr/bin/env bash
# Eval fixture for the super-linting skill: a deploy script.
set -euo pipefail
target=$1
rsync -az ./dist/ "$target":/srv/app/
