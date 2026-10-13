#!/usr/bin/env bash
# Commit the run's data changes and push, retrying if another run pushed first.
set -euo pipefail
msg="${1:-Data update}"
git config user.name "w4d-data-bot"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
for p in data/world data/recipes pipeline/state pipeline/nutrients.json; do
  [ -e "$p" ] && git add "$p"
done
if git diff --cached --quiet; then
  echo "No data changes to commit."
  exit 0
fi
git commit -q -m "$msg"
for attempt in 1 2 3 4 5; do
  if git push -q; then
    echo "Pushed: $msg"
    # Ask GitHub Pages to publish now (pushes made by workflows don't always trigger it).
    gh api -X POST "repos/${GITHUB_REPOSITORY}/pages/builds" >/dev/null 2>&1 || true
    exit 0
  fi
  echo "Push rejected (attempt $attempt); rebasing on the latest data…"
  git pull -q --rebase --autostash -X theirs || { git rebase --abort || true; git pull -q --no-rebase --autostash -X ours; }
  sleep $((attempt * 5))
done
echo "Could not push after 5 attempts." >&2
exit 1
