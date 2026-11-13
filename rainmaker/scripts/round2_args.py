"""Build the args object for the round-2 workflow (verification of 'investigate' candidates + by-company discovery)
within a fixed search budget. Usage: python scripts/round2_args.py [--budget 180] [--out data/exports/round2_args.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import path  # noqa: E402
from db import connect, init_db  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=int, default=180)
    ap.add_argument("--per-candidate", type=int, default=4)
    ap.add_argument("--per-company", type=int, default=2)
    ap.add_argument("--max-candidates", type=int, default=16)
    ap.add_argument("--max-companies", type=int, default=30)
    ap.add_argument("--out", default=str(path("exports") / "round2_args.json"))
    a = ap.parse_args()
    init_db()
    conn = connect()
    cands = []
    for r in conn.execute("SELECT * FROM candidates WHERE verification IS NOT NULL ORDER BY COALESCE(rank_overall, 9999)"):
        v = json.loads(r["verification"])
        if v.get("triage_decision") == "investigate":
            cands.append({"id": r["id"], "name": r["full_name"], "company": r["current_company"], "queries": v.get("round2_queries", [])[: a.per_candidate], "biggest_unknown": v.get("biggest_unknown", "")})
    cands = cands[: a.max_candidates]
    comps = [{"name": r["name"], "website": r["website"], "city": r["hq_city"], "tier": r["geo_tier"]}
             for r in conn.execute("SELECT name, website, hq_city, geo_tier FROM companies WHERE geo_tier IN ('1','2') AND segment IN ('MSP','MSSP','MSP_PLATFORM','CYBER_SERVICES','CLOUD_MS_AWS_PARTNER') ORDER BY geo_tier, name")][: a.max_companies]
    spend_c = len(cands) * a.per_candidate
    spend_co = len(comps) * a.per_company
    remaining = a.budget - spend_c - spend_co
    out = {"run_date": None, "budget_total": a.budget, "verify": cands, "companies": comps, "per_candidate": a.per_candidate, "per_company": a.per_company,
           "discovery_budget_remaining": max(0, remaining), "notes": f"verification {spend_c} + by-company {spend_co} + discovery {max(0, remaining)} = {a.budget}"}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {a.out}: {out['notes']}")


if __name__ == "__main__":
    main()
