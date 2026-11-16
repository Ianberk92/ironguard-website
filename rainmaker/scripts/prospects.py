"""Ingest target-account research (data/prospects/raw/*.json) into a prospects table and export a CRM-ready CSV.

Usage: python scripts/prospects.py   -> data/prospects/prospects.csv (Growably/Apollo import), reports/P_target_accounts.md
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, checkpoint, get_logger, normalize_company, now_iso, path, read_json  # noqa: E402
from db import connect, init_db  # noqa: E402

log = get_logger("prospects")

SCHEMA = """
CREATE TABLE IF NOT EXISTS prospects (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, name_norm TEXT NOT NULL UNIQUE, website TEXT, hq_city TEXT,
  employees_estimate TEXT, employees_source_url TEXT, sites TEXT, industry TEXT, platform_hint TEXT, trigger TEXT,
  trigger_source_url TEXT, trigger_date TEXT, buyer_titles_seen TEXT, incumbent_it_hint TEXT, icp_fit TEXT, notes TEXT,
  source_urls TEXT, confidence TEXT, segment TEXT, first_seen TEXT, last_verified TEXT,
  crm_status TEXT DEFAULT 'not_loaded', owner TEXT, next_action TEXT
);
"""


def main() -> None:
    init_db()
    conn = connect()
    conn.executescript(SCHEMA)
    n_new = 0
    raw = ROOT / "data" / "prospects" / "raw"
    for f in sorted(raw.glob("*.json")):
        data = read_json(f)
        seg = data.get("segment", f.stem)
        for a in data.get("accounts", []):
            name = (a.get("name") or "").strip()
            if not name:
                continue
            norm = normalize_company(name) or name.lower()
            if conn.execute("SELECT 1 FROM prospects WHERE name_norm=?", (norm,)).fetchone():
                conn.execute("UPDATE prospects SET last_verified=? WHERE name_norm=?", (now_iso(), norm))
                continue
            conn.execute(
                """INSERT INTO prospects(name,name_norm,website,hq_city,employees_estimate,employees_source_url,sites,industry,platform_hint,
                   trigger,trigger_source_url,trigger_date,buyer_titles_seen,incumbent_it_hint,icp_fit,notes,source_urls,confidence,segment,first_seen,last_verified,next_action)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (name, norm, a.get("website"), a.get("hq_city"), a.get("employees_estimate"), a.get("employees_source_url"), a.get("sites"), a.get("industry"),
                 a.get("platform_hint"), a.get("trigger"), a.get("trigger_source_url"), a.get("trigger_date"), a.get("buyer_titles_seen"), a.get("incumbent_it_hint"),
                 a.get("icp_fit"), a.get("notes"), json.dumps(a.get("source_urls", [])), a.get("confidence"), seg, now_iso(), now_iso(),
                 "Enrich in Apollo (users, buyer); assign sequence by trigger"))
            n_new += 1
    conn.commit()
    rows = conn.execute("SELECT * FROM prospects ORDER BY CASE icp_fit WHEN 'A' THEN 0 WHEN 'B' THEN 1 ELSE 2 END, hq_city, name").fetchall()
    out = ROOT / "data" / "prospects" / "prospects.csv"
    cols = ["name", "website", "hq_city", "employees_estimate", "sites", "industry", "platform_hint", "trigger", "trigger_date", "trigger_source_url",
            "buyer_titles_seen", "incumbent_it_hint", "icp_fit", "confidence", "segment", "notes", "crm_status", "next_action"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in cols})
    L = ["# P. Target accounts (first pass)", "", f"Generated {now_iso()}. {len(rows)} accounts; A = 50–300 employees, multi-site, named sector. Load A and B accounts into Growably; enrich in Apollo before outreach. Every trigger carries its source.", "",
         "| Fit | Company | City | Employees (est.) | Sites | Industry | Trigger | Date | Source |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['icp_fit']} | [{r['name']}]({r['website'] if (r['website'] or '').startswith('http') else 'https://' + (r['website'] or '')}) | {r['hq_city'] or ''} | {(r['employees_estimate'] or '')[:30]} | {(r['sites'] or '')[:60].replace('|','/')} | {(r['industry'] or '')[:30]} | {(r['trigger'] or '')[:90].replace('|','/')} | {(r['trigger_date'] or '')[:12]} | {('[link](' + r['trigger_source_url'] + ')') if (r['trigger_source_url'] or '').startswith('http') else ''} |")
    (path("reports") / "P_target_accounts.md").write_text("\n".join(L), encoding="utf-8")
    conn.close()
    checkpoint("prospects", new=n_new, total=len(rows))
    log.info("prospects: %s new, %s total -> %s", n_new, len(rows), out)


if __name__ == "__main__":
    main()
