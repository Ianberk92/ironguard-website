#!/bin/bash
# Publish the site to GitHub Pages (Ianberk92/ironguard-website).
# Copies ONLY public files (no docs/, marketing/, preview/, .claude/) and pushes.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
git clone -q "https://github.com/Ianberk92/ironguard-website.git" "$TMP/repo"
rsync -a --delete \
  --exclude=".git" --exclude=".claude" --exclude="docs" --exclude="marketing" \
  --exclude="preview" --exclude="README.md" --exclude="publish.sh" \
  --exclude="assets/founder-original.jpeg" --exclude=".DS_Store" \
  "$SRC/" "$TMP/repo/"
cd "$TMP/repo"
git add -A
if git diff --cached --quiet; then echo "No changes to publish."; else
  git -c user.name="Ian Berkowitz" -c user.email="Ianberk92@users.noreply.github.com" \
    commit -q -m "Site update $(date +%Y-%m-%d)"
  git push -q origin main
  echo "Published. Live in ~1 minute."
fi
rm -rf "$TMP"
