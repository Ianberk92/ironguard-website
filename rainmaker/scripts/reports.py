"""Generate evidence-linked reports from the database:
  reports/B_target_company_intelligence.md
  reports/D_ranked_top_15.md
  candidates/dossier_<rank>_<name>.md  (top N by overall rank; default 5)
  reports/E_top5_dossiers_index.md
Usage: python scripts/reports.py [--dossiers 5]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, checkpoint, get_logger, load_settings, now_iso, path  # noqa: E402
from db import connect, init_db  # noqa: E402

log = get_logger("reports")
S = load_settings()
LABELS = S["dimension_labels"]


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def md_link(name, url):
    return f"[{name}]({url})" if url and str(url).startswith("http") else name


def company_report(conn) -> None:
    rows = conn.execute("SELECT * FROM companies ORDER BY geo_tier, segment, name").fetchall()
    cands = {r["company_norm"]: r["n"] for r in conn.execute("SELECT company_norm, COUNT(*) n FROM candidates GROUP BY company_norm")}
    L = ["# B. Target Company Intelligence", "", f"Generated {now_iso()}. {len(rows)} organizations mapped. Revenue figures are third-party estimates unless the source column says otherwise; 'unknown' means no credible figure was seen. "
         "'Why attractive' is structural reasoning only, never a claim about any individual.", ""]
    for tier, title in (("1", "Tier 1 — San Diego County"), ("2", "Tier 2 — Orange County / SoCal"), ("3", "Tier 3 — National with SoCal relevance")):
        sub = [r for r in rows if str(r["geo_tier"]) == tier]
        if not sub:
            continue
        L += [f"## {title} ({len(sub)})", "", "| Company | Segment | HQ | Approx. revenue | Target customers | Sales org / roles seen | Strength indicators | Why a seller there might consider Ironguard | Conf. | Sources |", "|---|---|---|---|---|---|---|---|---|---|"]
        for r in sub:
            srcs = [u for u in json.loads(r["source_urls"] or "[]") if str(u).startswith("http")]
            src_md = " ".join(f"[{i+1}]({u})" for i, u in enumerate(srcs[:4])) or "mention only (no page seen)"
            L.append("| " + " | ".join([
                md_link(r["name"], r["website"]), r["segment"] or "", f"{r['hq_city'] or ''}, {r['hq_state'] or ''}",
                (r["approx_revenue"] or "unknown")[:160].replace("|", "/"), (r["target_customers"] or "")[:140].replace("|", "/"),
                ((r["sales_org_notes"] or "") + " " + (r["relevant_sales_roles"] or ""))[:220].replace("|", "/"),
                (r["sales_strength_indicators"] or "")[:160].replace("|", "/"), (r["why_attractive"] or "")[:200].replace("|", "/"),
                r["confidence"] or "", src_md]) + " |")
        L.append("")
    L += ["## Coverage notes", "", "- Companies were mapped by segment researchers using public lists (MSP 501, CRN, Inc 5000), directories and company sites; see `data/exports/companies.csv` for full text fields.",
          "- Segments not yet covered because the research budget ran out: national MSP platforms, MSSP/cyber services, Microsoft/AWS partners, VARs, UCaaS (see research/04_round2_plan.md).", ""]
    (path("reports") / "B_target_company_intelligence.md").write_text("\n".join(L), encoding="utf-8")


def ev_rows(conn, cid):
    return conn.execute("SELECT claim, classification, source_url, quote FROM evidence WHERE candidate_id=? ORDER BY CASE classification WHEN 'VERIFIED' THEN 0 WHEN 'INFERRED' THEN 1 WHEN 'UNVERIFIED CLAIM' THEN 2 ELSE 3 END", (cid,)).fetchall()


def top15(conn) -> list:
    rows = conn.execute("SELECT * FROM candidates WHERE rank_overall IS NOT NULL ORDER BY rank_overall LIMIT 15").fetchall()
    status_note = "PROVISIONAL" if any(r["research_status"] == "triaged" for r in rows) else "VERIFIED"
    L = [f"# D. Ranked Top 15 — {status_note}", "", f"Generated {now_iso()}. Ranking = overall score (80% weighted evidence model + 20% practical recruitability). "
         "Status 'triaged' means scored from captured public evidence only, not yet independently verified; treat as leads requiring diligence, not proven rainmakers. "
         "Range shows the score if unscored dimensions were low (2/10) vs high (8/10).", "",
         "| # | Candidate | Title | Company | Location (public) | Tier | Type | Overall | Range | Producer rank | Executive rank | Evidence conf. | Status | Strongest evidence | Biggest unknown |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        v = json.loads(r["verification"]) if r["verification"] else {}
        ev = ev_rows(conn, r["id"])
        strongest = next((e for e in ev if e["classification"] == "VERIFIED"), ev[0] if ev else None)
        L.append("| " + " | ".join([
            str(r["rank_overall"]), md_link(r["full_name"], r["public_profile_url"]), (r["current_title"] or "")[:60].replace("|", "/"), (r["current_company"] or "")[:45].replace("|", "/"),
            (r["location_public"] or "unknown")[:40].replace("|", "/"), str(r["geo_tier"]), r["archetype"] or "", f"{r['overall_score']:.0f}", f"{r['score_low']:.0f}–{r['score_high']:.0f}",
            str(r["rank_producer"]), str(r["rank_executive"]), f"{r['evidence_confidence']:.2f}", r["research_status"],
            (f"{strongest['classification']}: {strongest['claim']}" if strongest else "none")[:140].replace("|", "/"), (v.get("biggest_unknown") or "")[:120].replace("|", "/")]) + " |")
    L += ["", "## Why the three rankings differ", "", "- **Producer** ranking weights attributable new-business evidence and sales ability, discounted by evidence confidence, so self-stated awards rank below third-party-verified results.",
          "- **Executive** ranking weights builder dimensions (built a sales operation, leadership scope, entrepreneurial record); senior executives at large platforms rise here even when they are impractical hires.",
          "- **Overall** adds practical recruitability (scale/comp fit, location, timing), which pushes over-scaled or just-promoted executives down and SoCal individual producers up.", ""]
    (path("reports") / "D_ranked_top_15.md").write_text("\n".join(L), encoding="utf-8")
    return rows


def dossier(conn, r, rank: int) -> Path:
    v = json.loads(r["verification"]) if r["verification"] else {}
    scores = json.loads(r["scores"] or "{}")
    ev = ev_rows(conn, r["id"])
    awards = conn.execute("SELECT award, year, source_url FROM awards WHERE candidate_id=?", (r["id"],)).fetchall()
    srcs = [s["url"] for s in conn.execute("SELECT s.url FROM sources s JOIN candidate_sources cs ON cs.source_id=s.id WHERE cs.candidate_id=?", (r["id"],))]
    prev = json.loads(r["previous_employers"] or "[]")
    mods = json.loads(r["discovery_modalities"] or "[]")
    status = "PROVISIONAL — desk-triaged from public evidence, not yet independently verified" if r["research_status"] == "triaged" else r["research_status"]
    def u(x):
        return x if x and str(x).strip() and str(x).lower() != "unknown" else "UNKNOWN"
    L = [f"# Dossier #{rank}: {r['full_name']}", "", f"Status: {status} · Generated {now_iso()} · Overall score {r['overall_score']:.0f} (range {r['score_low']:.0f}–{r['score_high']:.0f}) · Evidence confidence {r['evidence_confidence']:.2f} · Recruitability {r['recruitability']:.1f}/10", "",
         "## 1. Profile (22 required fields)", "", "| # | Field | Value | Class |", "|---|---|---|---|"]
    fields = [
        ("Full name", r["full_name"], "VERIFIED (name appears in cited sources)"),
        ("Current role", v.get("current_title_confirmed") or r["current_title"], "UNVERIFIED CLAIM unless a third-party source below says otherwise"),
        ("Current company", v.get("current_company_confirmed") or r["current_company"], "see evidence"),
        ("Previous relevant employers", ", ".join(prev) if prev else "UNKNOWN", "UNKNOWN" if not prev else "UNVERIFIED CLAIM"),
        ("Geographic location (public)", v.get("location_confirmed") or r["location_public"], "VERIFIED only if a public source states it; never inferred from employer HQ"),
        ("Years of relevant experience", r["years_experience"], "INFERRED/UNKNOWN"),
        ("Services/products sold", r["what_they_sell"], "INFERRED from employer"),
        ("MSP/MSSP knowledge", r["msp_mssp_experience"], "INFERRED"),
        ("Net-new business experience", r["net_new_evidence"], "see evidence"),
        ("Enterprise / mid-market selling", r["segment_experience"], "INFERRED"),
        ("Evidence of sales performance", "; ".join(f"[{e['classification']}] {e['claim']}" for e in ev[:5]) or "UNKNOWN", "per item"),
        ("Evidence of leadership ability", r["leadership_evidence"], "see evidence"),
        ("Evidence of entrepreneurial initiative", r["entrepreneurial_evidence"], "see evidence"),
        ("Public recognition / awards", "; ".join(f"{a['award']} {a['year'] or ''}".strip() for a in awards) or "UNKNOWN", "VERIFIED if third-party list; else UNVERIFIED CLAIM"),
        ("Potential fit with Ironguard IT", v.get("score_rationale", {}).get("entrepreneurial_fit") or "see scores", "analyst judgment"),
        ("Potential concerns", v.get("concerns_summary") or r["concerns"], "analyst judgment"),
        ("Compensation estimate", "UNKNOWN — no public data; see economics model for market ranges by role type", "UNKNOWN"),
        ("Possible recruiting value proposition", v.get("likely_motivations") or "unknown", "INFERRED only where stated"),
        ("Public professional profile", r["public_profile_url"] or "UNKNOWN", "VERIFIED URL"),
        ("Sources supporting important claims", f"{len(srcs)} sources (section 4)", "VERIFIED URLs"),
        ("Confidence in assessment", f"{r['evidence_confidence']:.2f} (0–1)", "computed"),
        ("Recommended next action", v.get("recommended_next_action") or r["next_action"], "analyst"),
    ]
    for i, (k, val, cls) in enumerate(fields, 1):
        L.append(f"| {i} | {k} | {str(u(val))[:500].replace('|', '/')} | {cls} |")
    L += ["", "## 2. Dimension scores (0–10; blank = unknown, not zero)", "", "| Dimension | Weight | Score | Rationale |", "|---|---|---|---|"]
    for d, w in S["weights"].items():
        sc = scores.get(d)
        L.append(f"| {LABELS[d]} | {w*100:.0f}% | {'' if sc is None else sc} | {(v.get('score_rationale', {}).get(d) or '')[:300].replace('|', '/')} |")
    L += ["", "## 3. Evidence ledger", "", "| Class | Claim | Quote | Source |", "|---|---|---|---|"]
    for e in ev:
        L.append(f"| {e['classification']} | {(e['claim'] or '')[:200].replace('|', '/')} | {(e['quote'] or '')[:160].replace('|', '/')} | {md_link('link', e['source_url']) if e['source_url'] else ''} |")
    L += ["", "## 4. Sources", ""] + [f"- {s}" for s in srcs]
    L += ["", "## 5. Open questions and round-2 verification plan", "", f"**Biggest unknown:** {u(v.get('biggest_unknown'))}", "", "Queries planned:"] + [f"- `{q}`" for q in v.get("round2_queries", [])]
    L += ["", f"**Triage decision:** {v.get('triage_decision', 'n/a')} — {v.get('triage_reason', '')}", "", f"Discovered via: {', '.join(mods)}", ""]
    L += ["## 6. Recruiting notes", "", f"- Archetype: {v.get('archetype_confirmed') or r['archetype']}", f"- Likely motivations (only if supportable): {u(v.get('likely_motivations'))}",
          "- Compensation positioning: see reports/G_compensation_economics_model.md; choose the scenario after the screening call reveals current OTE range.",
          "- Outreach: see outreach/ for the personalized draft (requires CEO approval before sending).", ""]
    p = path("candidates") / f"dossier_{rank:02d}_{slug(r['full_name'])}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(L), encoding="utf-8")
    return p


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dossiers", type=int, default=5)
    a = ap.parse_args()
    init_db()
    conn = connect()
    company_report(conn)
    rows = top15(conn)
    for old in path("candidates").glob("dossier_*.md"):
        old.unlink()  # dossiers are regenerated from the database each run
    # Dossiers go to the approach list first (P1, then P2), then down the overall ranking.
    prio = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
    ordered = sorted(conn.execute("SELECT * FROM candidates WHERE rank_overall IS NOT NULL").fetchall(),
                     key=lambda r: (prio.get(r["recruiting_priority"], 9), r["rank_overall"]))
    paths = []
    for i, r in enumerate(ordered[: a.dossiers], 1):
        paths.append(dossier(conn, r, i))
    idx = ["# E. Top 5 Intelligence Dossiers — index", "", f"Generated {now_iso()}", ""] + [f"- [{p.name}]({'../candidates/' + p.name})" for p in paths]
    (path("reports") / "E_top5_dossiers_index.md").write_text("\n".join(idx), encoding="utf-8")
    conn.close()
    checkpoint("reports", dossiers=len(paths))
    log.info("reports written (%s dossiers)", len(paths))


if __name__ == "__main__":
    main()
