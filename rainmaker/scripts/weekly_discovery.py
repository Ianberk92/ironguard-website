"""Recurring talent-discovery runner.

What this script does by itself (no external services, no cost):
  --plan    : build this week's search plan (queries for new candidates, awards, role changes at target
              companies and re-verification of top candidates) -> checkpoints/weekly_plan_<date>.json
              and a ready-to-run research prompt -> checkpoints/weekly_prompt_<date>.md
  --report  : build the weekly intelligence report from database deltas -> reports/weekly_intel_<date>.md
  --all     : plan + report

What it does NOT do: it does not call a search engine itself (no authorized search API is configured).
The plan/prompt is meant to be executed by Claude Code (interactively, or headless via
`claude -p "$(cat checkpoints/weekly_prompt_<date>.md)"` from a scheduler) which writes new raw JSON into
data/raw/r<N>/ ; the standard pipeline (ingest -> score -> export -> dashboard -> qa) then runs.
See OPERATIONS.md for the scheduling options and what has/has not been configured.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, checkpoint, get_logger, load_settings, now_iso, path, today, write_json  # noqa: E402
from db import connect, init_db  # noqa: E402

log = get_logger("weekly")
S = load_settings()


def next_round_dir() -> str:
    existing = sorted(d.name for d in path("raw").glob("r*") if d.is_dir() and d.name[1:].isdigit())
    n = max([int(d[1:]) for d in existing] + [0]) + 1
    return f"r{n}"


def build_plan(conn) -> dict:
    year = datetime.now(timezone.utc).year
    companies = [r["name"] for r in conn.execute("SELECT name FROM companies WHERE geo_tier IN ('1','2') ORDER BY geo_tier, name LIMIT 40")]
    top = [dict(r) for r in conn.execute("SELECT full_name, current_company FROM candidates WHERE rank_overall IS NOT NULL ORDER BY rank_overall LIMIT 20")]
    stale = [dict(r) for r in conn.execute("SELECT full_name, current_company FROM candidates WHERE stale_flag=1 ORDER BY COALESCE(rank_overall, 9999) LIMIT 20")]
    queries = []
    for t in S["search"]["weekly_query_templates"]:
        if "{company}" in t:
            for c in companies[:25]:
                queries.append({"type": "company_watch", "query": t.format(company=c, year=year, candidate="")})
        elif "{candidate}" in t:
            for c in top + stale:
                queries.append({"type": "candidate_revalidate", "query": t.format(candidate=c["full_name"], company=c["current_company"] or "", year=year)})
        else:
            queries.append({"type": "discovery", "query": t.format(year=year, company="", candidate="")})
    # de-dup queries
    seen, uniq = set(), []
    for q in queries:
        if q["query"] not in seen:
            seen.add(q["query"])
            uniq.append(q)
    return {"date": today(), "round_dir": next_round_dir(), "queries": uniq, "watch_companies": companies,
            "revalidate_candidates": [c["full_name"] for c in top + stale]}


def build_prompt(plan: dict) -> str:
    rd = plan["round_dir"]
    return f"""# Weekly Rainmaker discovery run ({plan['date']})

You are continuing Operation Rainmaker for Ironguard IT. Read rainmaker/README.md and rainmaker/OPERATIONS.md first.
Rules: real people only; exact source URLs; classify claims VERIFIED / UNVERIFIED CLAIM / INFERRED; no personal contact data;
never infer residence from employer HQ; never claim someone is unhappy or looking.

Tasks:
1. Run the discovery queries below (WebSearch; WebFetch for pages). Write NEW candidates (not already in data/exports/candidates.csv)
   to rainmaker/data/raw/{rd}/weekly_<modality>.json using the discovery JSON schema in README.md.
2. Check each "watch" company for new sales hires, promotions, President's Club / award posts; record people as candidates with sources.
3. Re-validate the listed candidates: has the title, employer or location changed? Write results to
   rainmaker/data/raw/verify/revalidate_{plan['date']}.json using the verification schema (research_status "verified").
4. Run: python rainmaker/scripts/ingest.py && python rainmaker/scripts/score.py && python rainmaker/scripts/export.py && python rainmaker/scripts/dashboard.py && python rainmaker/scripts/qa.py
5. Run: python rainmaker/scripts/weekly_discovery.py --report  and summarize reports/weekly_intel_{plan['date']}.md for the CEO.

Queries ({len(plan['queries'])}):
""" + "\n".join(f"- [{q['type']}] {q['query']}" for q in plan["queries"]) + "\n\nWatch companies:\n" + "\n".join(f"- {c}" for c in plan["watch_companies"]) + "\n\nRe-validate:\n" + "\n".join(f"- {c}" for c in plan["revalidate_candidates"]) + "\n"


def build_report(conn) -> str:
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    new_c = conn.execute("SELECT full_name, current_title, current_company, geo_tier, confidence_discovery FROM candidates WHERE first_seen >= ? ORDER BY first_seen DESC", (since,)).fetchall()
    changes = conn.execute("SELECT c.full_name, s.field, s.old_value, s.new_value, s.changed_at FROM status_log s JOIN candidates c ON c.id=s.candidate_id WHERE s.changed_at >= ? ORDER BY s.changed_at DESC", (since,)).fetchall()
    new_aw = conn.execute("SELECT c.full_name, a.award, a.year FROM awards a JOIN candidates c ON c.id=a.candidate_id WHERE c.last_verified >= ? ORDER BY c.full_name", (since,)).fetchall()
    top = conn.execute("SELECT rank_overall, full_name, current_company, overall_score, evidence_confidence, recruiting_priority FROM candidates WHERE rank_overall IS NOT NULL ORDER BY rank_overall LIMIT 10").fetchall()
    stale = conn.execute("SELECT full_name, current_company, last_verified FROM candidates WHERE stale_flag=1 ORDER BY COALESCE(rank_overall, 9999) LIMIT 15").fetchall()
    new_co = conn.execute("SELECT name, segment, hq_city FROM companies WHERE first_seen >= ?", (since,)).fetchall()
    lines = [f"# Weekly Talent Intelligence Report — {today()}", "", f"Window: last 7 days (since {since[:10]}). Generated {now_iso()}.", "",
             f"## New candidates discovered ({len(new_c)})", ""]
    lines += [f"- {r['full_name']} — {r['current_title'] or ''}, {r['current_company'] or ''} (tier {r['geo_tier']}, confidence {r['confidence_discovery']})" for r in new_c] or ["- none"]
    lines += ["", f"## Role / status changes detected ({len(changes)})", ""]
    lines += [f"- {r['full_name']}: {r['field']} {r['old_value']} -> {r['new_value']} ({r['changed_at'][:10]})" for r in changes] or ["- none"]
    lines += ["", f"## Awards recorded for recently verified candidates ({len(new_aw)})", ""]
    lines += [f"- {r['full_name']}: {r['award']} {r['year'] or ''}" for r in new_aw] or ["- none"]
    lines += ["", f"## New target companies ({len(new_co)})", ""]
    lines += [f"- {r['name']} ({r['segment']}, {r['hq_city'] or ''})" for r in new_co] or ["- none"]
    lines += ["", "## Current top 10 (overall)", "", "| # | Candidate | Company | Score | Evidence conf. | Priority |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['rank_overall']} | {r['full_name']} | {r['current_company'] or ''} | {r['overall_score']} | {r['evidence_confidence']} | {r['recruiting_priority']} |" for r in top]
    lines += ["", f"## Records needing re-validation ({len(stale)})", ""]
    lines += [f"- {r['full_name']} ({r['current_company'] or ''}) last verified {str(r['last_verified'])[:10]}" for r in stale] or ["- none"]
    lines += ["", "## Recommended actions", "", "- Review new candidates and move promising ones to verification.",
              "- Re-validate stale top-30 records before any outreach.", "- Update outreach approval status for P1 candidates."]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    if not (a.plan or a.report or a.all):
        ap.print_help()
        return
    init_db()
    conn = connect()
    if a.plan or a.all:
        plan = build_plan(conn)
        pp = path("checkpoints") / f"weekly_plan_{plan['date']}.json"
        write_json(pp, plan)
        (path("checkpoints") / f"weekly_prompt_{plan['date']}.md").write_text(build_prompt(plan), encoding="utf-8")
        log.info("weekly plan written: %s (%s queries)", pp, len(plan["queries"]))
    if a.report or a.all:
        rep = build_report(conn)
        rp = path("reports") / f"weekly_intel_{today()}.md"
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(rep, encoding="utf-8")
        log.info("weekly report written: %s", rp)
    conn.close()
    checkpoint("weekly_discovery", plan=bool(a.plan or a.all), report=bool(a.report or a.all))


if __name__ == "__main__":
    main()
