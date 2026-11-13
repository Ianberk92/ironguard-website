"""Turn sales-titled people noticed during company mapping (companies[].people_seen) into low-confidence candidate leads.

Writes data/raw/r<round>/company_people_seen.json in the discovery schema. Usage: python scripts/leads_from_companies.py r1
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import get_logger, path, read_json, write_json  # noqa: E402

log = get_logger("leads")
SALES = re.compile(r"sales|account exec|business development|revenue|growth|client|partner|bdm|bdr|hunter", re.I)
EXCLUDE = re.compile(r"\b(ceo|founder|owner|president|coo|cfo|cto|engineer|marketing)\b", re.I)


def main(round_dir: str = "r1") -> None:
    out = []
    for f in sorted((path("raw") / "companies").glob("*.json")):
        data = read_json(f)
        for c in data.get("companies", []):
            for p in c.get("people_seen", []) or []:
                title = p.get("title") or ""
                if not p.get("name") or not SALES.search(title) or (EXCLUDE.search(title) and not re.search(r"sales|revenue", title, re.I)):
                    continue
                if not str(p.get("source_url", "")).startswith("http"):
                    continue  # every lead must carry a real source URL
                out.append({
                    "full_name": p["name"], "current_title": title, "current_company": c["name"], "previous_employers": [],
                    "location_public": "unknown", "location_source_url": "", "years_experience_estimate": "unknown",
                    "what_they_sell": c.get("services", ""), "msp_mssp_experience": f"Works at {c['name']} ({c.get('segment')})",
                    "net_new_evidence": "unknown", "segment_experience": c.get("target_customers", ""),
                    "performance_evidence": [{"claim": f"{title} at {c['name']}", "classification": "UNVERIFIED CLAIM", "source_url": p.get("source_url", ""), "quote": ""}],
                    "leadership_evidence": "unknown", "entrepreneurial_evidence": "unknown", "awards_recognition": [],
                    "archetype": "B" if re.search(r"vp|vice president|director|head|chief", title, re.I) else "A",
                    "public_profile_url": p.get("source_url", ""), "source_urls": [u for u in [p.get("source_url")] + (c.get("source_urls") or [])[:2] if u],
                    "key_quote": f"{p['name']} — {title} ({c['name']})", "concerns": "Name and title only, noticed while mapping the employer; no performance evidence yet",
                    "geo_tier": c.get("geo_tier", "unknown"), "confidence": "low", "notes": "lead from company map people_seen",
                })
    target = path("raw") / round_dir / "company_people_seen.json"
    write_json(target, {"modality": "company_people_seen", "candidates": out, "queries_run": [], "observations": "Derived from company-map people_seen fields; no searches run."})
    log.info("wrote %s leads to %s", len(out), target)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "r1")
