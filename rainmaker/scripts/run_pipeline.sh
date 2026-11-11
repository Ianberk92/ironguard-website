#!/usr/bin/env bash
# Rebuild everything from raw research JSON: ingest -> score -> export -> dashboard -> qa
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PYTHON:-python3}"
"$PY" "$HERE/db.py" init
"$PY" "$HERE/ingest.py" --run-id "${RUN_ID:-pipeline-$(date -u +%Y%m%dT%H%M%SZ)}"
"$PY" "$HERE/score.py"
"$PY" "$HERE/export.py"
"$PY" "$HERE/dashboard.py"
"$PY" "$HERE/reports.py"
"$PY" "$HERE/prospects.py"
"$PY" "$HERE/site.py"
"$PY" "$HERE/bundle.py"
"$PY" "$HERE/qa.py" || { echo "QA reported blocking issues (see reports/qa_report.md)"; exit 1; }
echo "pipeline complete"
