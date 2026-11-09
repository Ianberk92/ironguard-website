"""Weighted, evidence-sensitive scoring, three rankings and sensitivity analysis.

Dimension scores (0-10 or null) come from the verification stage and live in candidates.scores.
Missing dimensions are NOT assigned the worst score: they take a neutral prior (config
missing_dimension_prior) and widen the candidate's score range (missing_dimension_bounds), and
they lower evidence_confidence. Three rankings are produced:
  1. producer  - best demonstrated revenue producers (evidence-weighted)
  2. executive - best potential future sales executives
  3. overall   - best overall for Ironguard IT (weighted model + practical recruitability)

Usage:
  python scripts/score.py            # score, rank, sensitivity -> DB + data/exports/rankings.json + reports/06_rankings.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, checkpoint, get_logger, load_settings, now_iso, path, write_json  # noqa: E402
from db import connect, init_db  # noqa: E402

log = get_logger("score")
S = load_settings()
W = S["weights"]
DIMS = list(W.keys())
PRIOR = float(S["missing_dimension_prior"])
LOW, HIGH = [float(x) for x in S["missing_dimension_bounds"]]
TIER_SCORES = S["geography"]["tier_scores"]


def weighted(scores: dict, weights: dict, fill: float) -> float:
    total = 0.0
    wsum = 0.0
    for d, w in weights.items():
        v = scores.get(d)
        v = fill if v is None else float(v)
        total += w * v
        wsum += w
    return round(total / wsum * 10, 2) if wsum else 0.0  # 0-100 scale


def evidence_confidence(scores: dict, verification: dict | None) -> float:
    """Share of weighted dimensions with evidence, blended with the verifier's own source-quality view."""
    present = sum(W[d] for d in DIMS if scores.get(d) is not None)
    coverage = present / sum(W.values())
    vq = None
    if verification:
        vq = verification.get("evidence_confidence")
    if vq is None:
        return round(coverage, 2)
    return round(0.5 * coverage + 0.5 * float(vq), 2)


def score_all(conn) -> list[dict]:
    rows = conn.execute("SELECT * FROM candidates").fetchall()
    out = []
    for r in rows:
        scores = json.loads(r["scores"] or "{}")
        verification = json.loads(r["verification"]) if r["verification"] else None
        # Only candidates with verifier-provided dimension scores are ranked; a geo tier alone is not a score.
        has_any = any(scores.get(d) is not None for d in DIMS if d != "geographic_compatibility")
        # geographic compatibility can be derived from tier when the verifier did not score it
        if has_any and scores.get("geographic_compatibility") is None and r["geo_tier"] in TIER_SCORES and r["geo_tier"] != "unknown":
            scores["geographic_compatibility"] = TIER_SCORES[r["geo_tier"]]
        if not has_any:
            out.append({"id": r["id"], "scored": False, "full_name": r["full_name"]})
            continue
        total = weighted(scores, W, PRIOR)
        low = weighted(scores, W, LOW)
        high = weighted(scores, W, HIGH)
        conf = evidence_confidence(scores, verification)
        recruit = r["recruitability"]
        if recruit is None and verification:
            recruit = verification.get("recruitability")
        recruit = float(recruit) if recruit is not None else 5.0
        pr = S["rankings"]["producer"]
        producer_raw = weighted(scores, {k: v for k, v in pr.items() if k != "evidence_weighting"}, PRIOR)
        producer = round(producer_raw * ((1 - pr["evidence_weighting"]) + pr["evidence_weighting"] * conf), 2)
        ex = S["rankings"]["executive"]
        exec_raw = weighted(scores, {k: v for k, v in ex.items() if k != "evidence_weighting"}, PRIOR)
        executive = round(exec_raw * ((1 - ex["evidence_weighting"]) + ex["evidence_weighting"] * conf), 2)
        ov = S["rankings"]["overall"]
        # Overall = fit model + recruitability, discounted by evidence confidence so that thinly-evidenced records
        # (whose missing dimensions sit at the neutral prior) cannot outrank well-evidenced ones.
        ew = ov.get("evidence_weighting", 0.0)
        overall = round((ov["base_weight"] * total + ov["recruitability_weight"] * recruit * 10) * ((1 - ew) + ew * conf), 2)
        missing = [d for d in DIMS if scores.get(d) is None]
        conn.execute(
            """UPDATE candidates SET scores=?, score_total=?, score_low=?, score_high=?, evidence_confidence=?, recruitability=?,
               producer_score=?, executive_score=?, overall_score=? WHERE id=?""",
            (json.dumps(scores), total, low, high, conf, recruit, producer, executive, overall, r["id"]),
        )
        out.append({"id": r["id"], "scored": True, "full_name": r["full_name"], "current_title": r["current_title"],
                    "current_company": r["current_company"], "geo_tier": r["geo_tier"], "archetype": r["archetype"],
                    "scores": scores, "score_total": total, "score_low": low, "score_high": high, "evidence_confidence": conf,
                    "recruitability": recruit, "producer_score": producer, "executive_score": executive, "overall_score": overall,
                    "missing_dimensions": missing, "research_status": r["research_status"], "public_profile_url": r["public_profile_url"]})
    return out


def rank(conn, scored: list[dict]) -> dict:
    s = [c for c in scored if c["scored"]]
    rankings = {}
    for key, field in (("producer", "producer_score"), ("executive", "executive_score"), ("overall", "overall_score")):
        ordered = sorted(s, key=lambda c: (-c[field], -c["evidence_confidence"], c["full_name"]))
        for i, c in enumerate(ordered, 1):
            conn.execute(f"UPDATE candidates SET rank_{key}=? WHERE id=?", (i, c["id"]))
            c[f"rank_{key}"] = i
        rankings[key] = [{"rank": i, "id": c["id"], "name": c["full_name"], "company": c["current_company"],
                          "title": c["current_title"], "score": c[field], "evidence_confidence": c["evidence_confidence"],
                          "geo_tier": c["geo_tier"], "archetype": c["archetype"], "range": [c["score_low"], c["score_high"]]}
                         for i, c in enumerate(ordered, 1)]
    # archetype-specific lists
    rankings["rainmaker_A"] = [x for x in rankings["overall"] if (x["archetype"] or "").startswith("A")]
    rankings["builder_B"] = [x for x in rankings["overall"] if "B" in (x["archetype"] or "")]
    # recruiting priority tiers derived from overall rank
    for c in s:
        pr = "P1" if c["rank_overall"] <= 5 else "P2" if c["rank_overall"] <= 15 else "P3" if c["rank_overall"] <= 30 else "P4"
        conn.execute("UPDATE candidates SET recruiting_priority=? WHERE id=?", (pr, c["id"]))
    return rankings


def sensitivity(scored: list[dict]) -> dict:
    s = [c for c in scored if c["scored"]]
    scenarios = S["sensitivity_scenarios"]
    table = {}
    top5_count: dict[str, int] = {}
    top10_count: dict[str, int] = {}
    for name, w in scenarios.items():
        ordered = sorted(s, key=lambda c: -weighted(c["scores"], w, PRIOR))
        table[name] = [{"rank": i, "name": c["full_name"], "score": weighted(c["scores"], w, PRIOR)} for i, c in enumerate(ordered, 1)]
        for i, c in enumerate(ordered, 1):
            if i <= 5:
                top5_count[c["full_name"]] = top5_count.get(c["full_name"], 0) + 1
            if i <= 10:
                top10_count[c["full_name"]] = top10_count.get(c["full_name"], 0) + 1
    n = len(scenarios)
    stability = sorted(
        [{"name": k, "top5_in_scenarios": v, "top10_in_scenarios": top10_count.get(k, 0), "scenarios": n} for k, v in top5_count.items()],
        key=lambda x: (-x["top5_in_scenarios"], -x["top10_in_scenarios"], x["name"]),
    )
    # rank spread per candidate across scenarios
    spread = {}
    for name, rows in table.items():
        for row in rows:
            spread.setdefault(row["name"], []).append(row["rank"])
    spread_rows = sorted(
        [{"name": k, "best_rank": min(v), "worst_rank": max(v), "spread": max(v) - min(v)} for k, v in spread.items()],
        key=lambda x: (x["best_rank"], x["spread"]),
    )
    return {"scenarios": table, "top5_stability": stability, "rank_spread": spread_rows}


def write_report(rankings: dict, sens: dict, scored: list[dict]) -> None:
    rp = path("reports") / "06_rankings.md"
    rp.parent.mkdir(parents=True, exist_ok=True)
    unscored = [c["full_name"] for c in scored if not c["scored"]]
    lines = [f"# Candidate Rankings (generated {now_iso()})", "",
             "Scores are 0-100. Range = score if every missing dimension were scored at the low bound (2/10) vs the high bound (8/10). "
             "Evidence confidence 0-1 = share of weighted dimensions with evidence, blended with verifier source quality. "
             "Producer and executive scores are multiplied by (1 - w) + w x confidence; overall = (0.8 x weighted model + 0.2 x recruitability) x (0.5 + 0.5 x confidence).", ""]
    for key, title in (("producer", "1. Best demonstrated revenue producers"),
                       ("executive", "2. Best potential future sales executives"),
                       ("overall", "3. Best overall candidates for Ironguard IT (fit, economics, recruitability)")):
        lines += [f"## {title}", "", "| # | Candidate | Title | Company | Score | Range | Evidence conf. | Tier | Archetype |", "|---|---|---|---|---|---|---|---|---|"]
        for x in rankings[key][:20]:
            lines.append(f"| {x['rank']} | {x['name']} | {x['title'] or ''} | {x['company'] or ''} | {x['score']} | {x['range'][0]}–{x['range'][1]} | {x['evidence_confidence']} | {x['geo_tier']} | {x['archetype'] or ''} |")
        lines.append("")
    lines += ["## Rainmaker (A) ranking", "", "| # | Candidate | Company | Overall |", "|---|---|---|---|"]
    for i, x in enumerate(rankings["rainmaker_A"][:15], 1):
        lines.append(f"| {i} | {x['name']} | {x['company'] or ''} | {x['score']} |")
    lines += ["", "## Builder (B) ranking", "", "| # | Candidate | Company | Overall |", "|---|---|---|---|"]
    for i, x in enumerate(rankings["builder_B"][:15], 1):
        lines.append(f"| {i} | {x['name']} | {x['company'] or ''} | {x['score']} |")
    lines += ["", "## Sensitivity analysis", "", f"Scenarios: {', '.join(S['sensitivity_scenarios'].keys())}", "",
              "| Candidate | Top-5 in N scenarios | Top-10 in N scenarios |", "|---|---|---|"]
    for x in sens["top5_stability"][:15]:
        lines.append(f"| {x['name']} | {x['top5_in_scenarios']}/{x['scenarios']} | {x['top10_in_scenarios']}/{x['scenarios']} |")
    lines += ["", "| Candidate | Best rank | Worst rank | Spread |", "|---|---|---|---|"]
    for x in sens["rank_spread"][:20]:
        lines.append(f"| {x['name']} | {x['best_rank']} | {x['worst_rank']} | {x['spread']} |")
    if unscored:
        lines += ["", f"## Not yet scored ({len(unscored)})", "", "These candidates were discovered but not verified/scored; they are leads, not ranked prospects.", ""]
        lines += [f"- {n}" for n in sorted(unscored)]
    rp.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    init_db()
    conn = connect()
    scored = score_all(conn)
    rankings = rank(conn, scored)
    sens = sensitivity(scored)
    conn.commit()
    conn.close()
    out = {"generated_at": now_iso(), "weights": W, "rankings": rankings, "sensitivity": sens,
           "scored_count": sum(1 for c in scored if c["scored"]), "unscored_count": sum(1 for c in scored if not c["scored"])}
    write_json(path("exports") / "rankings.json", out)
    write_report(rankings, sens, scored)
    checkpoint("score", scored=out["scored_count"], unscored=out["unscored_count"])
    log.info("scored %s candidates (%s unscored)", out["scored_count"], out["unscored_count"])


if __name__ == "__main__":
    main()
