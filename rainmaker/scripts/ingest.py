"""Ingest raw research JSON (discovery, company map, verification) into SQLite with deduplication.

Raw files are produced by research agents (see README) and live under data/raw/:
  data/raw/companies/*.json   -> companies table
  data/raw/r*/*.json          -> candidates (discovery rounds r1, r2, ...)
  data/raw/verify/*.json      -> verification results merged onto candidates

Usage:
  python scripts/ingest.py                # ingest everything new
  python scripts/ingest.py --run-id r1    # tag this ingest run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (ROOT, checkpoint, get_logger, load_settings, normalize_company,  # noqa: E402
                    normalize_name, now_iso, path, read_json)
from db import connect, init_db  # noqa: E402

log = get_logger("ingest")
SETTINGS = load_settings()
TIER1 = [c.lower() for c in SETTINGS["geography"]["tier1"]]
TIER2 = [c.lower() for c in SETTINGS["geography"]["tier2"]]


def infer_geo_tier(location: str, declared: str | None) -> str:
    """Prefer the researcher's declared tier; fall back to matching the public location string."""
    if declared in ("1", "2", "3"):
        return declared
    loc = (location or "").lower()
    if not loc or loc == "unknown":
        return "unknown"
    if any(c in loc for c in TIER1):
        return "1"
    if any(c in loc for c in TIER2):
        return "2"
    if "california" in loc or ", ca" in loc:
        return "2"
    return "3"


def _j(v) -> str:
    return json.dumps(v, ensure_ascii=False) if v is not None else "[]"


def upsert_source(conn, url: str, source_type: str = "web") -> int | None:
    url = (url or "").strip()
    if not url.startswith("http"):
        return None
    row = conn.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
    if row:
        conn.execute("UPDATE sources SET last_checked=? WHERE id=?", (now_iso(), row["id"]))
        return row["id"]
    cur = conn.execute(
        "INSERT INTO sources(url, source_type, first_seen, last_checked) VALUES (?,?,?,?)",
        (url, source_type, now_iso(), now_iso()),
    )
    return cur.lastrowid


def ingest_companies(conn, run_id: str) -> int:
    n = 0
    for f in sorted((path("raw") / "companies").glob("*.json")):
        try:
            data = read_json(f)
        except json.JSONDecodeError as e:
            log.warning("skipping unreadable %s: %s", f, e)
            continue
        seg_label = data.get("segment_label", f.stem)
        for c in data.get("companies", []):
            name = (c.get("name") or "").strip()
            if not name:
                continue
            norm = normalize_company(name) or name.lower()
            existing = conn.execute("SELECT id, source_urls, people_seen FROM companies WHERE name_norm=?", (norm,)).fetchone()
            srcs = [u for u in c.get("source_urls", []) if isinstance(u, str)]
            people = c.get("people_seen", [])
            if existing:
                old_srcs = json.loads(existing["source_urls"] or "[]")
                old_people = json.loads(existing["people_seen"] or "[]")
                conn.execute(
                    "UPDATE companies SET source_urls=?, people_seen=?, last_verified=? WHERE id=?",
                    (_j(sorted(set(old_srcs + srcs))), _j(old_people + people), now_iso(), existing["id"]),
                )
            else:
                conn.execute(
                    """INSERT INTO companies(name,name_norm,website,hq_city,hq_state,socal_offices,segment,segment_label,
                       approx_revenue,revenue_source_url,employee_band,target_customers,services,geographic_presence,
                       sales_org_notes,sales_strength_indicators,relevant_sales_roles,why_attractive,geo_tier,confidence,
                       source_urls,people_seen,first_seen,last_verified)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (name, norm, c.get("website"), c.get("hq_city"), c.get("hq_state"), c.get("socal_offices"),
                     c.get("segment"), seg_label, c.get("approx_revenue"), c.get("revenue_source_url"), c.get("employee_band"),
                     c.get("target_customers"), c.get("services"), c.get("geographic_presence"), c.get("sales_org_notes"),
                     c.get("sales_strength_indicators"), c.get("relevant_sales_roles"), c.get("why_attractive_for_their_sellers"),
                     c.get("geo_tier"), c.get("confidence"), _j(srcs), _j(people), now_iso(), now_iso()),
                )
                n += 1
            for u in srcs:
                upsert_source(conn, u, "company")
        for q in data.get("queries_run", []):
            conn.execute(
                "INSERT OR IGNORE INTO search_log(run_id, modality, query, productive, note, run_at) VALUES (?,?,?,?,?,?)",
                (run_id, f"companies:{seg_label}", q.get("query"), 1 if q.get("productive") else 0, q.get("note"), now_iso()),
            )
    return n


def merge_candidate(conn, c: dict, modality: str) -> tuple[int, bool]:
    """Insert or merge a candidate. Returns (candidate_id, created)."""
    name = (c.get("full_name") or "").strip()
    norm = normalize_name(name)
    comp = (c.get("current_company") or "").strip()
    comp_norm = normalize_company(comp)
    row = conn.execute("SELECT * FROM candidates WHERE name_norm=? AND company_norm=?", (norm, comp_norm)).fetchone()
    same_name_other_company = None
    if not row:
        # Same person recorded with a differently-worded or unknown employer: merge when either company is unknown/blank
        # or one normalized company name contains the other (e.g. "visual edge" vs "visual edge national msp").
        for cand in conn.execute("SELECT * FROM candidates WHERE name_norm=?", (norm,)).fetchall():
            a, b = cand["company_norm"] or "", comp_norm or ""
            unknown = (not a) or (not b) or ("unknown" in a) or ("unknown" in b)
            overlap = bool(a and b and (a in b or b in a or a.split()[0] == b.split()[0]))
            if unknown or overlap:
                row = cand
                break
        if not row:
            same_name_other_company = conn.execute("SELECT id, current_company FROM candidates WHERE name_norm=?", (norm,)).fetchone()
    geo = infer_geo_tier(c.get("location_public"), c.get("geo_tier"))
    if row:
        mods = json.loads(row["discovery_modalities"] or "[]")
        if modality not in mods:
            mods.append(modality)
        # Keep the richer text fields; append notes rather than overwrite.
        def pick(field, new):
            old = row[field] or ""
            new = new or ""
            return new if len(new) > len(old) else old
        if comp and "unknown" not in comp.lower() and (row["current_company"] or "").strip().lower() in ("", "unknown"):
            conn.execute("UPDATE candidates SET current_company=?, company_norm=? WHERE id=?", (comp, comp_norm, row["id"]))
        conn.execute(
            """UPDATE candidates SET current_title=?, previous_employers=?, location_public=?, location_source_url=?, geo_tier=?,
               what_they_sell=?, msp_mssp_experience=?, net_new_evidence=?, segment_experience=?, leadership_evidence=?,
               entrepreneurial_evidence=?, key_quote=?, concerns=?, discovery_modalities=?, notes=?, last_verified=?,
               public_profile_url=COALESCE(NULLIF(public_profile_url,''), ?) WHERE id=?""",
            (pick("current_title", c.get("current_title")),
             _j(sorted(set(json.loads(row["previous_employers"] or "[]") + (c.get("previous_employers") or [])))),
             pick("location_public", c.get("location_public") if c.get("location_public") != "unknown" else ""),
             pick("location_source_url", c.get("location_source_url")),
             geo if geo != "unknown" else (row["geo_tier"] or "unknown"),
             pick("what_they_sell", c.get("what_they_sell")), pick("msp_mssp_experience", c.get("msp_mssp_experience")),
             pick("net_new_evidence", c.get("net_new_evidence")), pick("segment_experience", c.get("segment_experience")),
             pick("leadership_evidence", c.get("leadership_evidence")), pick("entrepreneurial_evidence", c.get("entrepreneurial_evidence")),
             pick("key_quote", c.get("key_quote")), pick("concerns", c.get("concerns")), _j(mods),
             ((row["notes"] or "") + "\n[" + modality + "] " + (c.get("notes") or "")).strip(), now_iso(),
             c.get("public_profile_url"), row["id"]),
        )
        cid, created = row["id"], False
    else:
        cur = conn.execute(
            """INSERT INTO candidates(full_name,name_norm,current_title,current_company,company_norm,previous_employers,
               location_public,location_source_url,geo_tier,years_experience,what_they_sell,msp_mssp_experience,net_new_evidence,
               segment_experience,leadership_evidence,entrepreneurial_evidence,archetype,public_profile_url,key_quote,concerns,
               discovery_modalities,confidence_discovery,notes,first_seen,last_verified,possible_duplicate_of,next_action)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (name, norm, c.get("current_title"), comp, comp_norm, _j(c.get("previous_employers") or []),
             c.get("location_public"), c.get("location_source_url"), geo, c.get("years_experience_estimate"),
             c.get("what_they_sell"), c.get("msp_mssp_experience"), c.get("net_new_evidence"), c.get("segment_experience"),
             c.get("leadership_evidence"), c.get("entrepreneurial_evidence"), c.get("archetype"), c.get("public_profile_url"),
             c.get("key_quote"), c.get("concerns"), _j([modality]), c.get("confidence"), c.get("notes"), now_iso(), now_iso(),
             same_name_other_company["id"] if same_name_other_company else None,
             "Triage: review evidence and decide whether to verify"),
        )
        cid, created = cur.lastrowid, True
        if same_name_other_company:
            log.info("possible duplicate: %s @ %s vs id %s @ %s", name, comp, same_name_other_company["id"], same_name_other_company["current_company"])
    for ev in c.get("performance_evidence", []) or []:
        conn.execute(
            "INSERT OR IGNORE INTO evidence(candidate_id, claim, classification, source_url, quote, checked_at, checked_by) VALUES (?,?,?,?,?,?,?)",
            (cid, ev.get("claim"), ev.get("classification", "UNVERIFIED CLAIM"), ev.get("source_url"), ev.get("quote"), now_iso(), modality),
        )
    for aw in c.get("awards_recognition", []) or []:
        conn.execute("INSERT OR IGNORE INTO awards(candidate_id, award, year, source_url) VALUES (?,?,?,?)",
                     (cid, aw.get("award"), aw.get("year"), aw.get("source_url")))
    for u in (c.get("source_urls") or []) + [c.get("public_profile_url") or ""]:
        sid = upsert_source(conn, u, "candidate")
        if sid:
            conn.execute("INSERT OR IGNORE INTO candidate_sources(candidate_id, source_id) VALUES (?,?)", (cid, sid))
    return cid, created


def ingest_candidates(conn, run_id: str) -> tuple[int, int]:
    created = merged = 0
    for d in sorted(path("raw").glob("r*")):
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            try:
                data = read_json(f)
            except json.JSONDecodeError as e:
                log.warning("skipping unreadable %s: %s", f, e)
                continue
            modality = data.get("modality", f.stem)
            for c in data.get("candidates", []):
                name = (c.get("full_name") or "").strip()
                if not name or "unknown" in name.lower() or len(name.split()) < 2:
                    continue  # unnamed or placeholder records are not candidates
                _, was_created = merge_candidate(conn, c, modality)
                created += was_created
                merged += (not was_created)
            for q in data.get("queries_run", []):
                conn.execute(
                    "INSERT OR IGNORE INTO search_log(run_id, modality, query, productive, note, run_at) VALUES (?,?,?,?,?,?)",
                    (f"{run_id}:{d.name}", modality, q.get("query"), 1 if q.get("productive") else 0, q.get("note"), now_iso()),
                )
    return created, merged


def ingest_verification(conn) -> int:
    """Merge verification results. Each file: {"candidate_name":..., "current_company":..., "verification": {...}}
    or a list of such objects. The verification object carries dimension scores, evidence classifications, etc."""
    n = 0
    vdir = path("verified")
    if not vdir.exists():
        return 0
    # Process oldest files first so the most recent verification of a candidate wins.
    for f in sorted(vdir.glob("*.json"), key=lambda p: p.stat().st_mtime):
        try:
            data = read_json(f)
        except json.JSONDecodeError as e:
            log.warning("skipping unreadable %s: %s", f, e)
            continue
        items = data["records"] if isinstance(data, dict) and "records" in data else (data if isinstance(data, list) else [data])
        for item in items:
            name = item.get("candidate_name") or item.get("full_name")
            if not name:
                continue
            name = re.sub(r"\s*\(.*\)\s*$", "", name).strip()  # "Shannon Murray (Shannon Murray-Doffo)" -> "Shannon Murray"
            norm = normalize_name(name)
            row = conn.execute("SELECT id FROM candidates WHERE name_norm=? ORDER BY id LIMIT 1", (norm,)).fetchone()
            if not row:
                log.warning("verification for unknown candidate %s (file %s); inserting shell record", name, f.name)
                cid, _ = merge_candidate(conn, {"full_name": name, "current_company": item.get("current_company", ""),
                                                "current_title": item.get("current_title", ""), "source_urls": item.get("source_urls", [])}, "verify")
            else:
                cid = row["id"]
            v = item.get("verification", item)
            scores = v.get("dimension_scores") or {}
            def clean(val, allowed=None):
                val = (val or "").strip()
                low = val.lower()
                if not val or low.startswith(("unknown", "not stated", "unconfirmed", "not confirmed", "n/a")):
                    return ""
                if allowed is not None and val not in allowed:
                    return ""
                return val
            # Only override short display fields when the verifier confirmed a clean value; caveated strings stay in the JSON blob.
            title_c = clean(v.get("current_title_confirmed")) if len(v.get("current_title_confirmed") or "") <= 80 else ""
            company_c = clean(v.get("current_company_confirmed")) if len(v.get("current_company_confirmed") or "") <= 60 else ""
            loc_raw = v.get("location_confirmed") or ""
            loc_c = clean(loc_raw[:120].split(" - ")[0].split(". ")[0]) if loc_raw else ""
            m = re.search(r"(?i)\btier\s*([123])\b|^\s*([123])\b", v.get("geo_tier_confirmed") or "")
            tier_c = (m.group(1) or m.group(2)) if m and "unconfirmed" not in (v.get("geo_tier_confirmed") or "").lower()[:12] else ""
            conn.execute(
                """UPDATE candidates SET verification=?, scores=?, evidence_confidence=?, recruitability=?, research_status=?,
                   last_verified=?, stale_flag=0, next_action=?, concerns=COALESCE(NULLIF(?, ''), concerns),
                   current_title=COALESCE(NULLIF(?, ''), current_title), current_company=COALESCE(NULLIF(?, ''), current_company),
                   location_public=COALESCE(NULLIF(?, ''), location_public), geo_tier=COALESCE(NULLIF(?, ''), geo_tier),
                   archetype=COALESCE(NULLIF(?, ''), archetype), public_profile_url=COALESCE(NULLIF(?, ''), public_profile_url)
                   WHERE id=?""",
                (json.dumps(v, ensure_ascii=False), json.dumps(scores), v.get("evidence_confidence"), v.get("recruitability"),
                 v.get("research_status", "verified"), now_iso(), v.get("recommended_next_action"),
                 v.get("concerns_summary", ""), title_c, company_c,
                 loc_c, tier_c, v.get("archetype_confirmed", ""),
                 v.get("public_profile_url", ""), cid),
            )
            for ev in v.get("evidence", []) or []:
                conn.execute(
                    "INSERT OR IGNORE INTO evidence(candidate_id, claim, classification, source_url, quote, checked_at, checked_by) VALUES (?,?,?,?,?,?,?)",
                    (cid, ev.get("claim"), ev.get("classification", "UNKNOWN"), ev.get("source_url"), ev.get("quote"), now_iso(), "verification"),
                )
                upsert_source(conn, ev.get("source_url") or "", "verification")
            for u in v.get("source_urls", []) or []:
                sid = upsert_source(conn, u, "verification")
                if sid:
                    conn.execute("INSERT OR IGNORE INTO candidate_sources(candidate_id, source_id) VALUES (?,?)", (cid, sid))
            n += 1
    return n


def flag_stale(conn) -> int:
    days = SETTINGS.get("freshness_days", 90)
    cur = conn.execute(
        "UPDATE candidates SET stale_flag=1 WHERE last_verified IS NOT NULL AND julianday('now') - julianday(last_verified) > ?",
        (days,),
    )
    return cur.rowcount


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=f"ingest-{now_iso()}")
    args = ap.parse_args()
    init_db()
    conn = connect()
    started = now_iso()
    nc = ingest_companies(conn, args.run_id)
    created, merged = ingest_candidates(conn, args.run_id)
    nv = ingest_verification(conn)
    stale = flag_stale(conn)
    # update source yield counts
    conn.execute("""UPDATE sources SET candidates_yielded = (SELECT COUNT(*) FROM candidate_sources cs WHERE cs.source_id = sources.id)""")
    stats = {"companies_new": nc, "candidates_new": created, "candidates_merged": merged, "verifications": nv, "stale_flagged": stale}
    conn.execute("INSERT OR REPLACE INTO runs(run_id, started_at, finished_at, phase, stats) VALUES (?,?,?,?,?)",
                 (args.run_id, started, now_iso(), "ingest", json.dumps(stats)))
    conn.commit()
    conn.close()
    checkpoint("ingest", **stats)
    log.info("ingest complete: %s", stats)


if __name__ == "__main__":
    main()
