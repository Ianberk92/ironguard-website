"""Quality assurance checks over the database and deliverables.

Checks: duplicate candidates, missing/invalid source URLs, evidence without sources, placeholder
text, scoring consistency (recomputes totals), export freshness, dashboard presence, stale records.
Writes reports/qa_report.md and exits non-zero if any BLOCKING check fails.

Usage: python scripts/qa.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, checkpoint, get_logger, load_settings, now_iso, path  # noqa: E402
from db import connect, init_db  # noqa: E402
from score import DIMS, PRIOR, W, weighted  # noqa: E402

log = get_logger("qa")
PLACEHOLDERS = re.compile(r"\b(lorem ipsum|john doe|jane doe|tbd|placeholder|example\.com|xxx+)\b", re.I)
URL_RE = re.compile(r"^https?://[^\s]+$")


def main() -> int:
    init_db()
    conn = connect()
    results = []  # (severity, check, detail)

    def add(sev, check, detail=""):
        results.append((sev, check, detail))

    # 1. duplicates
    dups = conn.execute("SELECT name_norm, COUNT(*) n, GROUP_CONCAT(id) ids, GROUP_CONCAT(current_company, ' | ') comps FROM candidates GROUP BY name_norm HAVING n>1").fetchall()
    if dups:
        add("WARN", "possible duplicate candidates (same normalized name, different company)",
            "; ".join(f"{d['name_norm']} ids={d['ids']} ({d['comps']})" for d in dups))
    else:
        add("PASS", "no duplicate candidate names")

    # 2. source URLs
    missing_src = conn.execute("SELECT c.id, c.full_name FROM candidates c LEFT JOIN candidate_sources cs ON cs.candidate_id=c.id WHERE cs.candidate_id IS NULL").fetchall()
    if missing_src:
        add("BLOCK", f"{len(missing_src)} candidates with no source URL", ", ".join(f"{r['full_name']} (id {r['id']})" for r in missing_src[:20]))
    else:
        add("PASS", "every candidate has at least one source URL")
    bad_urls = [r["url"] for r in conn.execute("SELECT url FROM sources") if not URL_RE.match(r["url"])]
    add("WARN" if bad_urls else "PASS", f"{len(bad_urls)} malformed source URLs", ", ".join(bad_urls[:10]))

    # 3. evidence
    ev_nosrc = conn.execute("SELECT COUNT(*) FROM evidence WHERE source_url IS NULL OR source_url NOT LIKE 'http%'").fetchone()[0]
    add("WARN" if ev_nosrc else "PASS", f"{ev_nosrc} evidence rows without a URL source")
    bad_class = conn.execute("SELECT COUNT(*) FROM evidence WHERE classification NOT IN ('VERIFIED','INFERRED','UNKNOWN','UNVERIFIED CLAIM')").fetchone()[0]
    add("BLOCK" if bad_class else "PASS", f"{bad_class} evidence rows with invalid classification")

    # 4. placeholders
    ph = []
    for r in conn.execute("SELECT id, full_name, key_quote, notes, concerns FROM candidates"):
        blob = " ".join(str(r[k] or "") for k in ("full_name", "key_quote", "notes", "concerns"))
        if PLACEHOLDERS.search(blob):
            ph.append(f"{r['full_name']} (id {r['id']})")
    add("BLOCK" if ph else "PASS", f"{len(ph)} candidate records containing placeholder text", ", ".join(ph[:10]))

    # 5. scoring consistency
    mism = []
    scored = 0
    for r in conn.execute("SELECT id, full_name, scores, score_total FROM candidates WHERE score_total IS NOT NULL"):
        scored += 1
        recomputed = weighted(json.loads(r["scores"] or "{}"), W, PRIOR)
        if abs(recomputed - (r["score_total"] or 0)) > 0.05:
            mism.append(f"{r['full_name']}: stored {r['score_total']} vs recomputed {recomputed}")
    add("BLOCK" if mism else "PASS", f"scoring consistency over {scored} scored candidates", "; ".join(mism[:10]))
    out_of_range = conn.execute("SELECT COUNT(*) FROM candidates WHERE score_total<0 OR score_total>100 OR evidence_confidence<0 OR evidence_confidence>1").fetchone()[0]
    add("BLOCK" if out_of_range else "PASS", f"{out_of_range} scores out of range")

    # 6. verified candidates must have evidence rows
    no_ev = conn.execute("SELECT c.full_name FROM candidates c WHERE c.research_status IN ('verified','deep_dive') AND NOT EXISTS (SELECT 1 FROM evidence e WHERE e.candidate_id=c.id)").fetchall()
    add("WARN" if no_ev else "PASS", f"{len(no_ev)} verified candidates without evidence rows", ", ".join(r[0] for r in no_ev[:10]))

    # 7. freshness
    stale = conn.execute("SELECT COUNT(*) FROM candidates WHERE stale_flag=1").fetchone()[0]
    add("INFO", f"{stale} candidates flagged stale (older than {load_settings()['freshness_days']} days)")

    # 8. exports and dashboard
    for f in ("candidates.csv", "companies.csv", "evidence.csv", "rainmaker_database.xlsx"):
        p = path("exports") / f
        add("PASS" if p.exists() and p.stat().st_size > 0 else "BLOCK", f"export present: {f}")
    dash = path("dashboard")
    if dash.exists():
        txt = dash.read_text(encoding="utf-8", errors="ignore")
        ok = "<html" in txt.lower() and "</html>" in txt.lower()
        add("PASS" if ok else "BLOCK", "dashboard HTML well-formed")
    else:
        add("BLOCK", "dashboard missing")

    # 9. deliverables present
    for f in ("A_executive_summary.md", "B_target_company_intelligence.md", "D_ranked_top_15.md", "F_top3_recruitment_plan.md",
              "G_compensation_economics_model.md", "06_rankings.md"):
        p = path("reports") / f
        add("PASS" if p.exists() else "WARN", f"report present: {f}")

    conn.close()
    blocking = [r for r in results if r[0] == "BLOCK"]
    lines = [f"# QA Report ({now_iso()})", "", f"Result: {'FAIL' if blocking else 'PASS'} ({len(blocking)} blocking issues)", "",
             "| Severity | Check | Detail |", "|---|---|---|"]
    for sev, check, detail in results:
        lines.append(f"| {sev} | {check} | {detail[:300]} |")
    rp = path("reports") / "qa_report.md"
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text("\n".join(lines), encoding="utf-8")
    checkpoint("qa", blocking=len(blocking), checks=len(results))
    print("\n".join(lines))
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
