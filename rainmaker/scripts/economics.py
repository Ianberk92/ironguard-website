"""Compensation scenarios and revenue-production economics for the Rainmaker hire (deliverable G).

Everything here is a model. Inputs are listed in ASSUMPTIONS with their status:
  VERIFIED  = from Ironguard's published pricing/terms
  ASSUMED   = analyst assumption (industry-typical range given); must be confirmed by the CEO
Run: python scripts/economics.py  -> reports/G_compensation_economics_model.md and data/exports/economics.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import checkpoint, get_logger, now_iso, path, write_json  # noqa: E402

log = get_logger("economics")

ASSUMPTIONS = {
    "price_per_user_month": {"value": 165, "status": "VERIFIED range / ASSUMED midpoint", "note": "Published $150-$200 per user per month; $165 blended midpoint"},
    "min_users": {"value": 25, "status": "VERIFIED", "note": "Managed plans start at 25 users"},
    "onboarding_fee_x_mrr": {"value": 1.0, "status": "ASSUMED", "note": "Fixed-fee onboarding; modeled at 1x first month's MRR (typical MSP range 0.5-2x)"},
    "managed_gross_margin": {"value": 0.45, "status": "ASSUMED", "note": "MSP managed-services gross margin commonly 35-60%; best-in-class >50%; 45% used. Confirm with Ironguard P&L"},
    "project_gross_margin": {"value": 0.35, "status": "ASSUMED", "note": "Project/professional-services margin"},
    "project_revenue_ratio": {"value": 0.15, "status": "ASSUMED", "note": "First-year project revenue per new client as a share of its ARR (site launches, migrations)"},
    "client_size_users": {"value": {"small": 40, "mid": 75, "large": 150}, "status": "ASSUMED", "note": "Within the stated 50-500 ICP; first-year wins skew smaller"},
    "client_mix": {"value": {"small": 0.40, "mid": 0.45, "large": 0.15}, "status": "ASSUMED", "note": "Share of new logos by size"},
    "sales_cycle_days": {"value": {"small": 60, "mid": 100, "large": 150}, "status": "ASSUMED", "note": "Qualified opportunity to signature"},
    "close_rate_qualified": {"value": 0.25, "status": "ASSUMED", "note": "Qualified opportunity -> signed (MSP range 20-35% with a strong seller)"},
    "fta_to_qualified": {"value": 0.50, "status": "ASSUMED", "note": "First meetings that become qualified opportunities"},
    "accounts_to_fta": {"value": 0.04, "status": "ASSUMED", "note": "Targeted accounts (multi-touch outbound + network) that yield a first meeting"},
    "pipeline_coverage": {"value": 3.0, "status": "ASSUMED", "note": "Qualified pipeline / target"},
    "ramp_months_to_first_close": {"value": 3, "status": "ASSUMED", "note": "Month of first signature for an experienced MSP hunter"},
    "billing_lag_months": {"value": 1.5, "status": "ASSUMED", "note": "Signature to first MRR invoice (onboarding project)"},
    "annual_logo_churn": {"value": 0.10, "status": "ASSUMED", "note": "Month-to-month terms; 10%/yr logo churn"},
    "year2_growth_vs_year1": {"value": 1.30, "status": "ASSUMED", "note": "Seller's year-2 new ARR vs year-1"},
    "delivery_cost_per_arr": {"value": 0.0, "status": "NOTE", "note": "Delivery labor is inside the gross-margin assumption; delivery HIRES are addressed in the phased plan"},
    "enablement_annual": {"value": {"CRM": 3000, "prospecting_data_tool": 8000, "events_travel_local": 10000, "marketing_support": 36000, "sales_tools_misc": 3000}, "status": "ASSUMED", "note": "Year-1 sales enablement budget, excluding an SDR"},
    "market_comp_reference": {"value": "MSP AE postings (2026): base $60K-$105K, OTE $100K-$175K; hunter/closer roles $85K-$100K base, $150K-$175K+ OTE; senior enterprise/MSSP hunters and sales leaders in SoCal commonly $200K-$350K OTE", "status": "ASSUMED / observed postings", "note": "From job postings reviewed 2026-11-09 (TrinWare, Pine Services, Integrated Technologies, Huntress) and general market knowledge; not a survey"},
}

SCENARIOS = {
    "S1_low_base_high_upside": {
        "label": "1. Lower base, substantial uncapped upside",
        "base": 85000, "ramp_draw_monthly": 5000, "ramp_draw_months": 4,
        "new_arr_rate": 0.15, "accelerator_rate": 0.20, "accelerator_threshold_arr": 750000,
        "project_rate": 0.08, "year2_residual_rate": 0.02, "ltip": "none",
        "payment_timing": "50% of commission at signature, 50% after 3 months of MRR collected; clawback if client churns within 6 months",
        "fit": "Candidate who is confident in their own production and wants maximum upside; typical of a Rainmaker leaving a capped plan",
    },
    "S2_competitive_midmarket": {
        "label": "2. Competitive mid-market base and commission",
        "base": 115000, "ramp_draw_monthly": 4000, "ramp_draw_months": 4,
        "new_arr_rate": 0.12, "accelerator_rate": 0.15, "accelerator_threshold_arr": 900000,
        "project_rate": 0.06, "year2_residual_rate": 0.0, "ltip": "none",
        "payment_timing": "50% at signature, 50% after 3 months of MRR collected; clawback within 6 months",
        "fit": "Proven MSP/MSSP account executive currently at $150K-$220K OTE",
    },
    "S3_premium_proven": {
        "label": "3. Premium package for an unusually strong, proven candidate",
        "base": 145000, "ramp_draw_monthly": 5000, "ramp_draw_months": 6,
        "new_arr_rate": 0.12, "accelerator_rate": 0.16, "accelerator_threshold_arr": 1000000,
        "project_rate": 0.06, "year2_residual_rate": 0.02,
        "ltip": "Performance LTIP (CEO decision): e.g., $50K cash bonus at $2.5M cumulative new ARR and $100K at $5M, or phantom equity 2-4% vesting on the same milestones; nothing promised in outreach",
        "payment_timing": "50% at signature, 50% after 3 months of MRR collected; clawback within 6 months; LTIP milestones paid on retained ARR only",
        "fit": "Rainmaker+Builder with verifiable $1M+ annual new-ARR history and a SoCal network; expected title path to VP Sales on results",
    },
}

TARGETS = [500000, 1000000, 2000000]


def blended_arr_per_client() -> float:
    a = ASSUMPTIONS
    users = sum(a["client_size_users"]["value"][k] * a["client_mix"]["value"][k] for k in a["client_mix"]["value"])
    return users * a["price_per_user_month"]["value"] * 12


def activity_for(target_arr: float) -> dict:
    a = ASSUMPTIONS
    arr_per = blended_arr_per_client()
    clients = target_arr / arr_per
    opps = clients / a["close_rate_qualified"]["value"]
    ftas = opps / a["fta_to_qualified"]["value"]
    accounts = ftas / a["accounts_to_fta"]["value"]
    cycle = sum(a["sales_cycle_days"]["value"][k] * a["client_mix"]["value"][k] for k in a["client_mix"]["value"])
    selling_months = 12 - a["ramp_months_to_first_close"]["value"] + 1
    gp = target_arr * a["managed_gross_margin"]["value"]
    proj = target_arr * a["project_revenue_ratio"]["value"]
    return {
        "target_new_arr": target_arr, "avg_arr_per_client": round(arr_per), "clients_needed": round(clients, 1),
        "qualified_opps_needed": round(opps, 1), "first_meetings_needed": round(ftas), "targeted_accounts_needed": round(accounts),
        "qualified_pipeline_needed": round(target_arr * a["pipeline_coverage"]["value"]), "blended_cycle_days": round(cycle),
        "closes_per_month_after_ramp": round(clients / selling_months, 2), "first_meetings_per_week": round(ftas / 48, 1),
        "annualized_gross_profit_on_arr": round(gp), "first_year_project_revenue": round(proj),
        "first_year_onboarding_fees": round(target_arr / 12 * a["onboarding_fee_x_mrr"]["value"]),
    }


def commission(sc: dict, arr: float, project_rev: float) -> float:
    base_part = sc["new_arr_rate"] * min(arr, sc["accelerator_threshold_arr"])
    accel_part = sc["accelerator_rate"] * max(0.0, arr - sc["accelerator_threshold_arr"])
    return base_part + accel_part + sc["project_rate"] * project_rev


def simulate(sc: dict, year1_arr: float, months: int = 36) -> dict:
    """Monthly cash model: year-1 ARR closes evenly from ramp month to 12; year-2 ARR = year1 x growth, evenly over months 13-24;
    year-3 same as year 2. MRR bills after billing lag; churn applied monthly; commission split 50/50 (signature / +3 months)."""
    a = ASSUMPTIONS
    gm = a["managed_gross_margin"]["value"]
    pgm = a["project_gross_margin"]["value"]
    proj_ratio = a["project_revenue_ratio"]["value"]
    lag = a["billing_lag_months"]["value"]
    churn_m = a["annual_logo_churn"]["value"] / 12
    ramp = a["ramp_months_to_first_close"]["value"]
    y2 = year1_arr * a["year2_growth_vs_year1"]["value"]
    enable = sum(a["enablement_annual"]["value"].values())
    closes = {}  # month -> ARR closed
    for m in range(ramp, 13):
        closes[m] = closes.get(m, 0) + year1_arr / (13 - ramp)
    for m in range(13, 25):
        closes[m] = closes.get(m, 0) + y2 / 12
    for m in range(25, months + 1):
        closes[m] = closes.get(m, 0) + y2 / 12
    cum_gp = cum_cost = 0.0
    payback = None
    rows = []
    active_arr = 0.0
    pending_commission = {}
    yearly = {}
    for m in range(1, months + 1):
        yr = (m - 1) // 12 + 1
        y = yearly.setdefault(yr, {"arr_closed": 0.0, "revenue": 0.0, "gross_profit": 0.0, "comp": 0.0, "enablement": 0.0})
        # billing: ARR closed at month k starts billing at k + lag
        started = sum(v for k, v in closes.items() if k + lag <= m and k + lag > m - 1)
        active_arr = active_arr * (1 - churn_m) + started
        mrr = active_arr / 12
        closed = closes.get(m, 0.0)
        onboarding = closed / 12 * a["onboarding_fee_x_mrr"]["value"]
        project = closed * proj_ratio
        revenue = mrr + onboarding + project
        gp = mrr * gm + onboarding * pgm + project * pgm
        # commission on this month's closes: split 50/50
        c = commission(sc, closed, project) if closed else 0.0
        # year-level accelerator approximated per-close by applying rate to cumulative within year
        year_closed_before = sum(v for k, v in closes.items() if (k - 1) // 12 + 1 == yr and k < m)
        c = (commission(sc, year_closed_before + closed, 0) - commission(sc, year_closed_before, 0)) + sc["project_rate"] * project
        pending_commission[m] = pending_commission.get(m, 0) + c * 0.5
        pending_commission[m + 3] = pending_commission.get(m + 3, 0) + c * 0.5
        comp = sc["base"] / 12 + pending_commission.get(m, 0.0)
        if m <= sc["ramp_draw_months"]:
            comp += sc["ramp_draw_monthly"]
        if m > 12 and sc["year2_residual_rate"]:
            comp += sc["year2_residual_rate"] * mrr  # residual on retained recurring from month 13
        en = enable / 12 if m <= 12 else enable * 0.7 / 12
        cum_gp += gp
        cum_cost += comp + en
        y["arr_closed"] += closed; y["revenue"] += revenue; y["gross_profit"] += gp; y["comp"] += comp; y["enablement"] += en
        if payback is None and cum_gp >= cum_cost and m > 1:
            payback = m
        rows.append({"month": m, "arr_closed": round(closed), "active_arr": round(active_arr), "revenue": round(revenue), "gp": round(gp), "comp": round(comp), "cum_gp": round(cum_gp), "cum_cost": round(cum_cost)})
    for yr, y in yearly.items():
        y["comp_pct_of_revenue"] = round(y["comp"] / y["revenue"], 2) if y["revenue"] else None
        y["gp_after_comp_and_enablement"] = round(y["gross_profit"] - y["comp"] - y["enablement"])
        for k in ("arr_closed", "revenue", "gross_profit", "comp", "enablement"):
            y[k] = round(y[k])
    return {"year1_new_arr": year1_arr, "payback_month": payback, "yearly": yearly, "month36_active_arr": round(active_arr),
            "cum_gp_36": round(cum_gp), "cum_cost_36": round(cum_cost), "net_36": round(cum_gp - cum_cost)}


def ote_table(sc: dict) -> list[dict]:
    rows = []
    for t in TARGETS:
        proj = t * ASSUMPTIONS["project_revenue_ratio"]["value"]
        c = commission(sc, t, proj)
        draw = sc["ramp_draw_monthly"] * sc["ramp_draw_months"]
        total = sc["base"] + c + draw
        first_year_rev = t * (1 + ASSUMPTIONS["onboarding_fee_x_mrr"]["value"] / 12) + proj
        rows.append({"new_arr": t, "commission": round(c), "ramp_draw": draw, "total_cash_comp_year1": round(total),
                     "comp_pct_of_first_year_contracted_revenue": round(total / first_year_rev, 2),
                     "comp_pct_of_annualized_gp": round(total / (t * ASSUMPTIONS["managed_gross_margin"]["value"] + proj * ASSUMPTIONS["project_gross_margin"]["value"]), 2)})
    return rows


def phased_plan() -> list[dict]:
    return [
        {"phase": "Months 0-3", "hire": "Rainmaker (this search) + CRM + prospecting data + local events budget", "target": "Pipeline $1.5M qualified; first Insurance Readiness Reviews sold", "delivery": "Confirm current capacity in users; document engineer-per-ARR ratio"},
        {"phase": "Months 4-12", "hire": "Part-time SDR/marketing support (contract) once 20+ first meetings/quarter are proven", "target": "$750K-$1.2M new ARR signed in year 1 (best case for one seller)", "delivery": "Hire 1 engineer per ~$600K-$800K of new ARR (ASSUMED ratio; validate)"},
        {"phase": "Months 12-18", "hire": "Second account executive (or promote Rainmaker to player-coach if Builder archetype)", "target": "Run-rate new ARR $2M+/yr across two sellers", "delivery": "Service-desk lead; standardize onboarding factory"},
        {"phase": "Months 18-24", "hire": "Third seller or channel/referral program; sales ops tooling", "target": "Cumulative new ARR $3M-$4.5M by month 24; $5M requires upside execution plus larger logos", "delivery": "Team of roughly 15-25 total staff at $5M-$7M revenue (MSP revenue per employee ~$150K-$250K, ASSUMED)"},
    ]


def main() -> None:
    arr_per = blended_arr_per_client()
    activities = [activity_for(t) for t in TARGETS]
    scen = {}
    for key, sc in SCENARIOS.items():
        scen[key] = {"ote": ote_table(sc), "simulations": {str(t): simulate(sc, t) for t in TARGETS}}
    out = {"generated_at": now_iso(), "assumptions": ASSUMPTIONS, "blended_arr_per_client": round(arr_per), "activity": activities,
           "scenarios": {k: {**SCENARIOS[k], **scen[k]} for k in SCENARIOS}, "phased_plan": phased_plan()}
    write_json(path("exports") / "economics.json", out)

    L = []
    L += ["# G. Compensation and Economics Model", "", f"Generated {now_iso()} by `scripts/economics.py`. Every number below is a model output; inputs are listed with their status. Nothing here is an approved budget.", ""]
    L += ["## 1. Inputs and assumptions", "", "| Input | Value | Status | Note |", "|---|---|---|---|"]
    for k, v in ASSUMPTIONS.items():
        val = v["value"] if not isinstance(v["value"], dict) else ", ".join(f"{a}={b}" for a, b in v["value"].items())
        L.append(f"| {k} | {val} | {v['status']} | {v['note']} |")
    L += ["", f"**Blended ARR per new client: ${arr_per:,.0f}** (≈ {arr_per/12/ASSUMPTIONS['price_per_user_month']['value']:.0f} users at ${ASSUMPTIONS['price_per_user_month']['value']}/user/month).", ""]
    L += ["## 2. What it takes to deliver $500K, $1M and $2M of new annualized recurring revenue", "",
          "| Metric | $500K | $1M | $2M |", "|---|---|---|---|"]
    keys = [("clients_needed", "New clients needed"), ("avg_arr_per_client", "Average ARR per client ($)"), ("qualified_opps_needed", "Qualified opportunities needed"),
            ("first_meetings_needed", "First meetings needed"), ("first_meetings_per_week", "First meetings per week"), ("targeted_accounts_needed", "Targeted accounts worked"),
            ("qualified_pipeline_needed", "Qualified pipeline required ($, 3x coverage)"), ("blended_cycle_days", "Blended sales cycle (days)"),
            ("closes_per_month_after_ramp", "Closes per month after ramp"), ("annualized_gross_profit_on_arr", "Annualized gross profit on the ARR ($)"),
            ("first_year_project_revenue", "Attached first-year project revenue ($)"), ("first_year_onboarding_fees", "Onboarding fees ($)")]
    for k, label in keys:
        L.append(f"| {label} | " + " | ".join(f"{a[k]:,}" if isinstance(a[k], (int, float)) else str(a[k]) for a in activities) + " |")
    L += ["", "Reading: $500K is a solid first year for one experienced MSP hunter starting from zero; $1M is an excellent year and requires roughly one first meeting per week plus a working inbound engine; $2M from one seller in one year is not credible at this deal size without an SDR, marketing support and several 150+ user logos.", ""]
    L += ["## 3. Three compensation scenarios", ""]
    for key, sc in SCENARIOS.items():
        L += [f"### {sc['label']}", "", f"- Base salary: ${sc['base']:,}", f"- Ramp draw (non-recoverable): ${sc['ramp_draw_monthly']:,}/month for {sc['ramp_draw_months']} months",
              f"- New recurring revenue commission: {sc['new_arr_rate']*100:.0f}% of first-year contracted recurring revenue, uncapped; accelerator {sc['accelerator_rate']*100:.0f}% above ${sc['accelerator_threshold_arr']:,} new ARR in a plan year",
              f"- Project commission: {sc['project_rate']*100:.0f}% of attached project revenue", f"- Year-2 residual on retained recurring: {sc['year2_residual_rate']*100:.0f}%",
              f"- Long-term incentive: {sc['ltip']}", f"- Payment timing / retention: {sc['payment_timing']}", f"- Best fit: {sc['fit']}", "",
              "| Year-1 new ARR | Commission | Ramp draw | Total cash comp | Comp as % of first-year contracted revenue | Comp as % of annualized GP |", "|---|---|---|---|---|---|"]
        for r in scen[key]["ote"]:
            L.append(f"| ${r['new_arr']:,} | ${r['commission']:,} | ${r['ramp_draw']:,} | ${r['total_cash_comp_year1']:,} | {r['comp_pct_of_first_year_contracted_revenue']*100:.0f}% | {r['comp_pct_of_annualized_gp']*100:.0f}% |")
        L += ["", "36-month cash simulation (deals close evenly after ramp; MRR bills after the onboarding lag; 10% annual churn; year-2 production = 1.3x year 1):", "",
              "| Year-1 new ARR | Payback month | Y1 revenue | Y1 GP | Y1 comp | Y2 revenue | Y2 GP | Y2 comp | Active ARR at month 36 | Net GP after comp+enablement, 36 mo |", "|---|---|---|---|---|---|---|---|---|---|"]
        for t, sim in scen[key]["simulations"].items():
            y1, y2 = sim["yearly"][1], sim["yearly"][2]
            L.append(f"| ${int(t):,} | {sim['payback_month'] or '>36'} | ${y1['revenue']:,} | ${y1['gross_profit']:,} | ${y1['comp']:,} | ${y2['revenue']:,} | ${y2['gross_profit']:,} | ${y2['comp']:,} | ${sim['month36_active_arr']:,} | ${sim['net_36']:,} |")
        L.append("")
    L += ["## 4. Design notes", "",
          "- **Commission on first-year contracted recurring revenue** (not on MRR multiples) keeps the plan simple and ties pay to ARR; 12-15% of year-1 recurring revenue equals roughly 27-33% of first-year gross profit at a 45% margin, which is sustainable.",
          "- **Gross-profit-based incentives** are an alternative (e.g., 25-30% of first-year GP); they protect margin when a seller discounts but require sharing margin data. Recommended as the accelerator basis only if margin by client is tracked.",
          "- **Retention requirement**: pay 50% at signature, 50% after three months of collected MRR; claw back on churn inside six months. This matches the month-to-month contract terms.",
          "- **New recurring revenue incentive**: accelerators above threshold reward the second half of the year; a quarterly 'new logo' kicker ($2,500 per 100+ user logo) is an optional lever.",
          "- **Ramp**: expect the first signature in month 3-4 and first MRR in month 5-6; a non-recoverable draw bridges the gap without inflating base.",
          "- **Enablement**: budget roughly $60K in year 1 (CRM, prospecting data, local events, marketing support) before any SDR.",
          "- **Long-term incentives**: phantom equity or cash LTIP tied to retained new ARR milestones is the honest way to offer 'ownership-like' upside without granting equity today; requires the CEO's decision and legal drafting.", ""]
    L += ["## 5. Can one salesperson add $5M in 12-24 months?", "",
          "No, not credibly at Ironguard's deal size. One strong seller starting from zero can sign roughly $0.75M-$1.2M of new ARR in year one and $1.2M-$2M in year two (cumulative $2M-$3M). Reaching $5M of added annual revenue in 24 months needs two to three sellers, demand generation, and delivery hiring in step. Phased plan:", "",
          "| Phase | Hire / investment | Revenue target | Delivery implication |", "|---|---|---|---|"]
    for p in phased_plan():
        L.append(f"| {p['phase']} | {p['hire']} | {p['target']} | {p['delivery']} |")
    L += ["", "Delivery capacity is the binding constraint: at $165/user, $5M of ARR is roughly 2,500 managed users. Confirm the engineer-per-user ratio and hiring lead times before promising growth to a candidate.", "",
          "## 6. Unverified assumptions to confirm with the CEO", "",
          "1. Actual gross margin on managed services and on projects. 2. Current MRR, client count and churn. 3. Realistic onboarding capacity per month. 4. Inbound lead volume today (Scorecard, guide, site). 5. Whether the Insurance Readiness Review converts to managed agreements and at what rate. 6. Appetite for phantom equity / LTIP. 7. Approved compensation budget ceiling.", ""]
    rp = path("reports") / "G_compensation_economics_model.md"
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text("\n".join(L), encoding="utf-8")
    checkpoint("economics", scenarios=len(SCENARIOS))
    log.info("economics report written to %s", rp)


if __name__ == "__main__":
    main()
