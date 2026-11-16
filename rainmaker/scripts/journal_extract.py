"""Normalize workflow agent results into raw research files.

Research agents sometimes save free-form JSON; the schema-validated result they return to the workflow is the
authoritative record. This reads a workflow journal (journal.jsonl) and writes normalized discovery files
(data/raw/<round>/<label>.json) and verification files (data/raw/verify/<round>_<slug>.json).
Usage: python scripts/journal_extract.py <journal.jsonl> <round_dir e.g. r2>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import get_logger, path, write_json  # noqa: E402

log = get_logger("journal")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def main(journal: str, rnd: str) -> None:
    started = {}
    n_disc = n_ver = 0
    for line in open(journal, encoding="utf-8"):
        try:
            j = json.loads(line)
        except json.JSONDecodeError:
            continue
        if j.get("type") == "started":
            started[j.get("key")] = j.get("label") or j.get("key")
        if j.get("type") != "result" or not isinstance(j.get("result"), dict):
            continue
        r = j["result"]
        label = started.get(j.get("key"), j.get("key") or "agent")
        if "candidates" in r and isinstance(r["candidates"], list):
            mod = r.get("modality") or slug(label)
            out = {"modality": mod, "candidates": r["candidates"], "queries_run": r.get("queries_run", []),
                   "observations": r.get("observations", ""), "searches_used": r.get("searches_used")}
            write_json(path("raw") / rnd / f"{slug(label)}.json", out)
            n_disc += 1
        elif "verification" in r and r.get("candidate_name"):
            write_json(path("verified") / f"{rnd}_{slug(r['candidate_name'])}.json", r)
            n_ver += 1
    log.info("normalized %s discovery files and %s verification files from %s", n_disc, n_ver, journal)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "r2")
