#!/usr/bin/env bash
# Sync the full rainmaker working tree (INCLUDING research data) into the private repository clone and push.
# Usage: scripts/sync_to_private.sh [/path/to/private/clone] ["commit message"]
# The public website repo only ever receives tooling; this script is how data reaches its private home.
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-/home/user/operation-rainmaker}"
MSG="${2:-Research sync $(date -u +%Y-%m-%dT%H:%M:%SZ)}"
[ -d "$DEST/.git" ] || { echo "private clone not found at $DEST"; exit 1; }
# copy everything except noise; keep the destination's .git and its own .gitignore/notice
find "$DEST" -mindepth 1 -maxdepth 1 ! -name .git ! -name .github ! -name .gitignore ! -name PRIVATE_REPO_NOTICE.md -exec rm -rf {} +
cp -a "$SRC"/. "$DEST"/
rm -rf "$DEST"/logs "$DEST"/data/raw/verify/_batches "$DEST"/data/exports/triage_batch_*.json "$DEST"/data/exports/triage_input.json "$DEST"/data/exports/*.zip "$DEST"/data/*.db-wal "$DEST"/data/*.db-shm 2>/dev/null || true
find "$DEST" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
# the private repo versions data, so drop the public-repo exclusions
cat > "$DEST/.gitignore" <<'IGN'
# Private repository: research data IS versioned here. Keep only noise out.
__pycache__/
*.pyc
logs/
*.db-wal
*.db-shm
.env
data/exports/*.zip
data/raw/verify/_batches/
IGN
cd "$DEST"
git pull -q --rebase origin "$(git rev-parse --abbrev-ref HEAD)" 2>/dev/null || true
git add -A
if git diff --cached --quiet; then echo "nothing to sync"; exit 0; fi
git -c user.name="${GIT_AUTHOR_NAME:-Claude}" -c user.email="${GIT_AUTHOR_EMAIL:-noreply@anthropic.com}" commit -q -m "$MSG"
git push origin HEAD
echo "synced to $DEST and pushed"
