"""Export the candidate database to CSV and Excel for review.

Usage: python scripts/export.py
Outputs: data/exports/candidates.csv, companies.csv, evidence.csv, search_log.csv, rainmaker_database.xlsx
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import checkpoint, get_logger, path  # noqa: E402
from db import connect, init_db  # noqa: E402

log = get_logger("export")

CANDIDATE_COLS = [
    "id", "full_name", "current_title", "current_company", "location_public", "geo_tier", "archetype",
    "research_status", "recruiting_priority", "rank_overall", "rank_producer", "rank_executive",
    "overall_score", "producer_score", "executive_score", "score_total", "score_low", "score_high",
    "evidence_confidence", "recruitability", "what_they_sell", "msp_mssp_experience", "net_new_evidence",
    "leadership_evidence", "entrepreneurial_evidence", "concerns", "public_profile_url", "key_quote",
    "discovery_modalities", "confidence_discovery", "contact_status", "outreach_approval_status",
    "interview_status", "next_action", "first_seen", "last_verified", "stale_flag", "possible_duplicate_of",
]


def rows(conn, sql):
    cur = conn.execute(sql)
    cols = [d[0] for d in cur.description]
    return cols, [dict(zip(cols, r)) for r in cur.fetchall()]


def write_csv(p: Path, cols, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in data:
            w.writerow(r)


def main() -> None:
    init_db()
    conn = connect()
    out = path("exports")
    out.mkdir(parents=True, exist_ok=True)
    sets = {}
    _, cands = rows(conn, "SELECT * FROM candidates ORDER BY COALESCE(rank_overall, 9999), full_name")
    sets["candidates"] = (CANDIDATE_COLS, cands)
    cols, comps = rows(conn, "SELECT id,name,segment,hq_city,hq_state,socal_offices,geo_tier,approx_revenue,revenue_source_url,employee_band,target_customers,services,sales_org_notes,sales_strength_indicators,relevant_sales_roles,why_attractive,confidence,website,source_urls FROM companies ORDER BY geo_tier, name")
    sets["companies"] = (cols, comps)
    cols, ev = rows(conn, "SELECT e.id, c.full_name, e.claim, e.classification, e.source_url, e.quote, e.checked_at, e.checked_by FROM evidence e JOIN candidates c ON c.id=e.candidate_id ORDER BY c.full_name")
    sets["evidence"] = (cols, ev)
    cols, sl = rows(conn, "SELECT run_id, modality, query, productive, note, run_at FROM search_log ORDER BY run_at")
    sets["search_log"] = (cols, sl)
    cols, srcs = rows(conn, "SELECT url, source_type, candidates_yielded, first_seen, last_checked FROM sources ORDER BY candidates_yielded DESC")
    sets["sources"] = (cols, srcs)
    for name, (cols, data) in sets.items():
        write_csv(out / f"{name}.csv", cols, data)
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
        wb = Workbook()
        wb.remove(wb.active)
        for name, (cols, data) in sets.items():
            ws = wb.create_sheet(name[:31])
            ws.append(cols)
            for c in ws[1]:
                c.font = Font(bold=True)
            for r in data:
                ws.append([("" if r.get(k) is None else str(r.get(k)))[:32000] for k in cols])
            ws.freeze_panes = "A2"
        wb.save(out / "rainmaker_database.xlsx")
    except ImportError:
        log.warning("openpyxl not available; skipped xlsx export")
    conn.close()
    checkpoint("export", candidates=len(cands), companies=len(comps), evidence=len(ev))
    log.info("exported %s candidates, %s companies, %s evidence rows to %s", len(cands), len(comps), len(ev), out)


if __name__ == "__main__":
    main()
