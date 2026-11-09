"""Revenue-confidence model for the first 12 months of the Rainmaker hire (deliverable H2).

Builds month-by-month activity, pipeline, Insurance Readiness Review sales, managed-agreement signatures and
MRR under conservative / base / aggressive cases, plus 30/60/90/180-day go/no-go gates. Reuses the
assumptions in economics.py (all ASSUMED unless marked VERIFIED there).
Run: python scripts/ramp_plan.py -> reports/H2_revenue_confidence_plan.md and data/exports/ramp_plan.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import checkpoint, get_logger, now_iso, path, write_json  # noqa: E402
from economics import ASSUMPTIONS, blended_arr_per_client  # noqa: E402

log = get_logger("ramp")
A = ASSUMPTIONS

# Activity model (ASSUMED; calibrate against the seller's own history in the interview)
ACTIVITY = {
    "accounts_worked_per_week": {"value": 15, "note": "new target accounts entered into a multi-touch cadence each week (owner/COO/CFO level)"},
    "first_meetings_per_week_steady": {"value": 1.2, "note": "steady-state first meetings per week from month 3 (base case)"},
    "ramp_curve": {"value": [0.25, 0.6, 1.0], "note": "share of steady-state meeting rate in months 1, 2, 3+"},
    "review_attach_rate": {"value": 0.30, "note": "share of first meetings that buy an Insurance Readiness Review (fixed fee from $1,500)"},
    "review_fee": {"value": 2500, "note": "average Insurance Readiness Review fee (published 'from $1,500')"},
    "review_to_managed_conversion": {"value": 0.50, "note": "share of Review buyers that sign a managed agreement within 6 months"},
    "qualified_rate": {"value": A["fta_to_qualified"]["value"], "note": "first meeting -> qualified opportunity"},
    "close_rate": {"value": A["close_rate_qualified"]["value"], "note": "qualified opportunity -> signed"},
    "cycle_months": {"value": 3, "note": "qualified opportunity -> signature (blended ~92 days)"},
    "billing_lag_months": {"value": 1.5, "note": "signature -> first MRR invoice"},
    "inherited_warm_opps": {"value": 3, "note": "qualified opportunities the CEO hands over on day 1 from pre-hire pipeline work (see section 4)"},
}
CASES = {"conservative": 0.7, "base": 1.0, "aggressive": 1.3}


def simulate(mult: float) -> dict:
    arr_per = blended_arr_per_client()
    mrr_per = arr_per / 12
    meetings_m = []
    for m in range(1, 13):
        ramp = ACTIVITY["ramp_curve"]["value"][min(m - 1, 2)]
        meetings_m.append(ACTIVITY["first_meetings_per_week_steady"]["value"] * 4.33 * ramp * mult)
    qualified = [x * ACTIVITY["qualified_rate"]["value"] for x in meetings_m]
    qualified[0] += ACTIVITY["inherited_warm_opps"]["value"] * mult
    reviews = [x * ACTIVITY["review_attach_rate"]["value"] for x in meetings_m]
    cycle = ACTIVITY["cycle_months"]["value"]
    signatures = [0.0] * 12
    for m in range(12):
        src = m - cycle
        if src >= 0:
            signatures[m] += qualified[src] * ACTIVITY["close_rate"]["value"]
    # review-driven conversions add signatures ~4 months after the review
    for m in range(12):
        src = m - 4
        if src >= 0:
            signatures[m] += reviews[src] * ACTIVITY["review_to_managed_conversion"]["value"] * 0.35  # share not already counted in the opportunity funnel
    active_arr = 0.0
    rows = []
    cum_sig = cum_rev_fees = 0.0
    lag = ACTIVITY["billing_lag_months"]["value"]
    for m in range(12):
        started = signatures[m - 2] if m - 2 >= 0 else 0.0  # ~1.5 month lag, rounded to 2 months
        active_arr += started * arr_per
        cum_sig += signatures[m]
        cum_rev_fees += reviews[m] * ACTIVITY["review_fee"]["value"]
        rows.append({
            "month": m + 1, "first_meetings": round(meetings_m[m], 1), "qualified_opps_created": round(qualified[m], 1),
            "reviews_sold": round(reviews[m], 1), "signatures": round(signatures[m], 2), "cumulative_signatures": round(cum_sig, 1),
            "qualified_pipeline_value": round(sum(qualified[max(0, m - cycle + 1): m + 1]) * arr_per), "active_arr": round(active_arr),
            "mrr": round(active_arr / 12), "cumulative_review_fees": round(cum_rev_fees),
        })
    return {"multiplier": mult, "months": rows, "year1_signatures": round(cum_sig, 1), "year1_signed_arr": round(cum_sig * arr_per),
            "arr_run_rate_month12": rows[-1]["active_arr"], "review_fees_year1": round(cum_rev_fees)}


GATES = [
    {"day": 30, "gate": "Target list of 300+ ICP accounts built; 8+ first meetings held; 2+ Insurance Readiness Reviews proposed; CRM live with every touch logged", "if_missed": "Diagnose list quality and messaging with the CEO; no comp change"},
    {"day": 60, "gate": "16+ first meetings; 3+ Reviews sold; 6+ qualified opportunities; qualified pipeline ≥ $600K", "if_missed": "Joint pipeline review; CEO co-sells on next 5 meetings; adjust territory or offer"},
    {"day": 90, "gate": "24+ first meetings; 5+ Reviews sold; first managed agreement signed or 2 in proposal; pipeline ≥ $1.0M", "if_missed": "Formal checkpoint: continue with plan changes, or mutual exit under the agreed terms"},
    {"day": 120, "gate": "1-2 managed agreements signed (≥ $150K ARR total)", "if_missed": "Escalate: comp plan ramp draw ends per plan; decision on continuation"},
    {"day": 180, "gate": "3-4 agreements signed, $350K-$600K ARR; pipeline ≥ $1.5M; first referral from a new client", "if_missed": "Builder path on hold; focus on personal production"},
    {"day": 365, "gate": "$750K-$1.2M new ARR signed (base case); delivery capacity plan executed", "if_missed": "Reassess role and plan"},
]

PREHIRE = [
    ("Insurance Readiness Review campaign", "Email every Scorecard taker and inbound lead of the last 12 months with the fixed-fee Review offer timed to renewal season; goal: 3-5 Reviews in progress on the seller's day 1", "CEO + marketing, weeks 1-4"),
    ("Referral asks", "Ask the long-running 300+ person client and each 5-star reviewer for two introductions to peer CEOs/COOs with multiple sites", "CEO, weeks 1-2"),
    ("Broker channel", "Meet 5 cyber-insurance brokers and 3 CPAs in North County; position the Review as their client-readiness tool; agree a referral protocol", "CEO, weeks 1-6"),
    ("Named target list", "Build the first 100 ICP accounts (50-500 people, multi-site, M365/GWS, construction/engineering/tech/life sciences in SD County) with trigger notes", "CEO or contractor, weeks 1-3"),
    ("Proof assets", "Publish 2-3 more client reviews, one case study with approved metrics, and a one-page 'what is not included' sheet; fix stale old-site pages and the Temecula directory listing", "CEO, weeks 1-6"),
    ("Sales infrastructure", "Choose and configure the CRM, prospecting data tool and meeting scheduler; define pipeline stages and the weekly report", "CEO, weeks 2-4"),
    ("Delivery readiness", "Write the capacity plan: users supportable today, hiring trigger per $X MRR, onboarding slots per month", "CEO + ops lead, weeks 1-3"),
]


def main() -> None:
    arr_per = blended_arr_per_client()
    sims = {k: simulate(v) for k, v in CASES.items()}
    out = {"generated_at": now_iso(), "assumptions": ACTIVITY, "blended_arr_per_client": round(arr_per), "cases": sims, "gates": GATES, "prehire": PREHIRE}
    write_json(path("exports") / "ramp_plan.json", out)
    L = ["# H2. Revenue Confidence Plan — first 12 months of the Rainmaker hire", "",
         f"Generated {now_iso()} by `scripts/ramp_plan.py`. Model outputs, not forecasts; every input is an assumption to confirm against the hired seller's own history and Ironguard's real inbound numbers. Blended ARR per new client: ${arr_per:,.0f} (published pricing).", "",
         "## 1. Activity assumptions", "", "| Input | Value | Note |", "|---|---|---|"]
    for k, v in ACTIVITY.items():
        L.append(f"| {k} | {v['value']} | {v['note']} |")
    L += ["", "## 2. What 'new clients soon' looks like under three cases", "",
          "| Case | First meetings (yr 1) | Reviews sold (yr 1) | Managed agreements signed (yr 1) | New ARR signed (yr 1) | ARR run-rate at month 12 | Review fees (yr 1) |", "|---|---|---|---|---|---|---|"]
    for k, s in sims.items():
        fm = sum(r["first_meetings"] for r in s["months"]); rv = sum(r["reviews_sold"] for r in s["months"])
        L.append(f"| {k} (x{s['multiplier']}) | {fm:.0f} | {rv:.0f} | {s['year1_signatures']} | ${s['year1_signed_arr']:,} | ${s['arr_run_rate_month12']:,} | ${s['review_fees_year1']:,} |")
    L += ["", "### Base case, month by month", "", "| Month | First meetings | Qualified opps created | Reviews sold | Signatures | Cum. signatures | Qualified pipeline ($) | Active ARR ($) | MRR ($) |", "|---|---|---|---|---|---|---|---|---|"]
    for r in sims["base"]["months"]:
        L.append(f"| {r['month']} | {r['first_meetings']} | {r['qualified_opps_created']} | {r['reviews_sold']} | {r['signatures']} | {r['cumulative_signatures']} | {r['qualified_pipeline_value']:,} | {r['active_arr']:,} | {r['mrr']:,} |")
    L += ["", "Reading: with a working target list and the Insurance Readiness Review as the land offer, the first fixed-fee revenue arrives in month 1-2, the first managed agreement is realistic in month 4, and 2-3 agreements (roughly $300K-$450K ARR) by month 6 in the base case, consistent with the $0.75M-$1.2M year-one range in the economics model. The Review fees are small money but they are the earliest objective proof that the seller can open doors.", "",
          "## 3. Go / no-go gates (leading indicators you can check, not promises)", "", "| Day | Gate | If missed |", "|---|---|---|"]
    for g in GATES:
        L.append(f"| {g['day']} | {g['gate']} | {g['if_missed']} |")
    L += ["", "These gates are written into the offer letter as mutual expectations, with the ramp draw and the 90-day checkpoint tied to them. They protect the company and give the candidate a fair, explicit runway.", "",
          "## 4. Pre-hire pipeline work (start now, so the seller inherits warm opportunities)", "", "| Action | What | Owner / timing |", "|---|---|---|"]
    for a, w, o in PREHIRE:
        L.append(f"| {a} | {w} | {o} |")
    L += ["", "Target for day 1 of the hire: 3-5 Reviews in progress or proposed, 4+ qualified opportunities, 100 named accounts with trigger notes, CRM live, two client references ready to take calls.", "",
          "## 5. Why this gives confidence (and what would break it)", "",
          "- The deal math is favorable: one 75-user client is roughly $150K of ARR, so four or five signatures make a year. The funnel needed (about one first meeting a week at steady state) is ordinary for an experienced mid-market hunter.",
          "- The land offer is real and cheap to buy: a fixed-fee, read-only Insurance Readiness Review timed to insurance renewals creates a paid reason to meet and a natural conversion path.",
          "- The proof points are checkable: published pricing, no lock-in, written standards and client-owned credentials remove the three objections that stall MSP switches.",
          "- What would break it: no inbound or referral flow at all (fix with section 4), delivery capacity that cannot onboard two clients a month (fix with the capacity plan), or a seller whose history is account management rather than new-logo hunting (fix with Exercises 3, 6 and the reference checks).", ""]
    rp = path("reports") / "H2_revenue_confidence_plan.md"
    rp.write_text("\n".join(L), encoding="utf-8")
    checkpoint("ramp_plan", cases=len(CASES))
    log.info("revenue confidence plan written to %s", rp)


if __name__ == "__main__":
    main()
