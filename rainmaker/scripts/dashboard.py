"""Generate the executive dashboard (dashboard/index.html) from the database.

Static, self-contained HTML (no external assets), light/dark aware, clickable candidate names.
Usage: python scripts/dashboard.py
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, checkpoint, get_logger, load_settings, now_iso, path  # noqa: E402
from db import connect, init_db, stats  # noqa: E402

log = get_logger("dashboard")
S = load_settings()


def esc(v) -> str:
    return html.escape("" if v is None else str(v))


def name_link(r) -> str:
    url = r["public_profile_url"] or ""
    if url.startswith("http"):
        return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(r["full_name"])}</a>'
    return esc(r["full_name"])


def tier_label(t) -> str:
    return {"1": "Tier 1 · SD County", "2": "Tier 2 · SoCal", "3": "Tier 3 · National"}.get(str(t), "Location unknown")


def meter(v, maxv=1.0) -> str:
    v = 0 if v is None else float(v)
    pct = max(0, min(100, round(v / maxv * 100)))
    return f'<span class="meter" title="{v:.2f}"><span class="meter-fill" style="width:{pct}%"></span></span><span class="num">{v:.2f}</span>'


def table(rows, cols, empty="No records yet.") -> str:
    if not rows:
        return f'<p class="muted">{esc(empty)}</p>'
    head = "".join(f"<th>{esc(c[0])}</th>" for c in cols)
    body = []
    for r in rows:
        body.append("<tr>" + "".join(f"<td>{c[1](r)}</td>" for c in cols) + "</tr>")
    return f'<div class="tablewrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def main() -> None:
    init_db()
    conn = connect()
    st = stats()
    q = conn.execute
    ranked = q("SELECT * FROM candidates WHERE rank_overall IS NOT NULL ORDER BY rank_overall").fetchall()
    top15 = ranked[:15]
    local = [r for r in ranked if r["geo_tier"] in ("1", "2")][:8]
    national = [r for r in ranked if r["geo_tier"] == "3"][:8]
    rainmakers = [r for r in ranked if (r["archetype"] or "").startswith("A")][:8]
    builders = [r for r in ranked if "B" in (r["archetype"] or "")][:8]
    producers = q("SELECT * FROM candidates WHERE rank_producer IS NOT NULL ORDER BY rank_producer LIMIT 8").fetchall()
    execs = q("SELECT * FROM candidates WHERE rank_executive IS NOT NULL ORDER BY rank_executive LIMIT 8").fetchall()
    diligence = q("""SELECT * FROM candidates WHERE rank_overall IS NOT NULL AND (evidence_confidence < 0.5 OR stale_flag=1)
                     ORDER BY rank_overall LIMIT 12""").fetchall()
    unverified = q("SELECT COUNT(*) FROM candidates WHERE research_status='discovered'").fetchone()[0]
    verified = q("SELECT COUNT(*) FROM candidates WHERE research_status IN ('verified','deep_dive')").fetchone()[0]
    deep = q("SELECT COUNT(*) FROM candidates WHERE research_status='deep_dive'").fetchone()[0]
    strong = q("SELECT COUNT(*) FROM candidates WHERE recruiting_priority IN ('P1','P2')").fetchone()[0]
    outreach = q("SELECT * FROM candidates WHERE recruiting_priority='P1' ORDER BY rank_overall").fetchall()
    runs = q("SELECT run_id, phase, finished_at, stats FROM runs ORDER BY finished_at DESC LIMIT 6").fetchall()
    cp_path = ROOT / "checkpoints" / "status.json"
    cp = json.loads(cp_path.read_text(encoding="utf-8")) if cp_path.exists() else {}
    modality_yield = q("""SELECT modality, COUNT(*) n, SUM(productive) p FROM search_log GROUP BY modality ORDER BY p DESC LIMIT 12""").fetchall()
    companies_t1 = q("SELECT COUNT(*) FROM companies WHERE geo_tier='1'").fetchone()[0]
    companies_t2 = q("SELECT COUNT(*) FROM companies WHERE geo_tier='2'").fetchone()[0]

    funnel = [("Universe discovered", st["candidates"]), ("Verified", verified), ("Strong prospects (P1-P2)", strong), ("Deep-dive dossiers", deep), ("Approach first (P1)", len(outreach))]
    fmax = max([v for _, v in funnel] + [1])
    funnel_html = "".join(
        f'<div class="frow"><span class="flabel">{esc(l)}</span><span class="fbar"><span class="ffill" style="width:{0 if not v else max(2, round(v / fmax * 100))}%; background: var(--ord-{i+1})"></span></span><span class="num">{v}</span></div>'
        for i, (l, v) in enumerate(funnel))

    base_cols = [
        ("#", lambda r: esc(r["rank_overall"])),
        ("Candidate", name_link),
        ("Title", lambda r: esc(r["current_title"])),
        ("Company", lambda r: esc(r["current_company"])),
        ("Location", lambda r: f'{esc(r["location_public"] if r["location_public"] and r["location_public"] != "unknown" else "unknown")}<br><span class="muted small">{tier_label(r["geo_tier"])}</span>'),
        ("Type", lambda r: esc(r["archetype"])),
        ("Score", lambda r: f'<span class="num">{r["overall_score"]:.0f}</span> <span class="muted small">({r["score_low"]:.0f}–{r["score_high"]:.0f})</span>'),
        ("Evidence", lambda r: meter(r["evidence_confidence"])),
        ("Priority", lambda r: f'<span class="pill">{esc(r["recruiting_priority"])}</span>'),
    ]
    short_cols = [base_cols[1], base_cols[3], base_cols[6], base_cols[7]]
    prod_cols = [("#", lambda r: esc(r["rank_producer"])), base_cols[1], base_cols[3], ("Producer score", lambda r: f'<span class="num">{r["producer_score"]:.0f}</span>'), base_cols[7]]
    exec_cols = [("#", lambda r: esc(r["rank_executive"])), base_cols[1], base_cols[3], ("Executive score", lambda r: f'<span class="num">{r["executive_score"]:.0f}</span>'), base_cols[7]]
    dil_cols = [base_cols[1], base_cols[3], base_cols[7], ("Why", lambda r: esc("stale record" if r["stale_flag"] else "evidence confidence below 0.5")), ("Next action", lambda r: esc(r["next_action"]))]
    out_cols = [base_cols[0], base_cols[1], base_cols[3], ("Contact status", lambda r: esc(r["contact_status"])), ("Outreach approval", lambda r: esc(r["outreach_approval_status"])), ("Next action", lambda r: esc(r["next_action"]))]

    kpis = [
        ("Companies researched", st["companies"], f"{companies_t1} San Diego County · {companies_t2} SoCal"),
        ("Unique candidates", st["candidates"], f"{unverified} discovered, not yet verified"),
        ("Candidates verified", verified, f"{deep} with deep-dive dossiers"),
        ("Strong prospects", strong, "priority P1–P2"),
        ("Evidence rows", st["evidence"], f"{st['sources']} unique sources"),
        ("Stale records", st["stale"], f"older than {S['freshness_days']} days"),
    ]
    kpi_html = "".join(f'<div class="tile"><div class="label">{esc(l)}</div><div class="value">{v:,}</div><div class="sub muted">{esc(s)}</div></div>' for l, v, s in kpis)

    progress_rows = "".join(f"<li><b>{esc(k)}</b> — {esc(v.get('at', ''))} " + esc(", ".join(f"{a}={b}" for a, b in v.items() if a not in ('phase', 'at'))) + "</li>" for k, v in (cp.get("phases") or {}).items())
    mod_rows = "".join(f'<tr><td>{esc(m["modality"])}</td><td class="num">{m["n"]}</td><td class="num">{m["p"] or 0}</td></tr>' for m in modality_yield)

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rainmaker Dashboard</title>
<style>
:root{{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--border:rgba(11,11,11,.10);
--accent:#2a78d6;--track:#cde2fb;--ord-1:#86b6ef;--ord-2:#5598e7;--ord-3:#2a78d6;--ord-4:#1c5cab;--ord-5:#104281;--good:#006300}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--border:rgba(255,255,255,.10);
--accent:#3987e5;--track:#184f95;--ord-1:#184f95;--ord-2:#256abf;--ord-3:#3987e5;--ord-4:#6da7ec;--ord-5:#9ec5f4;--good:#0ca30c}}}}
:root[data-theme="dark"]{{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--border:rgba(255,255,255,.10);
--accent:#3987e5;--track:#184f95;--ord-1:#184f95;--ord-2:#256abf;--ord-3:#3987e5;--ord-4:#6da7ec;--ord-5:#9ec5f4;--good:#0ca30c}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--page);color:var(--ink);font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}}
main{{max-width:1240px;margin:0 auto;padding:24px 16px 48px}}h1{{font-size:24px;margin:0 0 4px}}h2{{font-size:17px;margin:28px 0 10px}}
.sub,.muted{{color:var(--ink2)}}.small{{font-size:12px}}.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-top:16px}}
.tile{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px}}.tile .label{{font-size:13px;color:var(--ink2)}}
.tile .value{{font-size:30px;font-weight:600;margin:4px 0 2px}}.tile .sub{{font-size:12px}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin-top:10px}}
.tablewrap{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}th{{text-align:left;color:var(--ink2);font-weight:600;font-size:12.5px;border-bottom:1px solid var(--grid);padding:8px 8px}}
td{{padding:8px 8px;border-bottom:1px solid var(--grid);vertical-align:top}}tr:last-child td{{border-bottom:0}}a{{color:var(--accent);text-decoration:none}}a:hover{{text-decoration:underline}}
.num{{font-variant-numeric:tabular-nums}}.pill{{display:inline-block;border:1px solid var(--border);border-radius:999px;padding:1px 8px;font-size:12px}}
.meter{{display:inline-block;width:72px;height:8px;border-radius:999px;background:var(--track);vertical-align:middle;margin-right:6px;overflow:hidden}}.meter-fill{{display:block;height:100%;background:var(--accent);border-radius:999px}}
.frow{{display:grid;grid-template-columns:200px 1fr 48px;gap:10px;align-items:center;margin:6px 0}}.fbar{{height:10px;background:transparent;border-radius:4px;overflow:hidden}}.ffill{{display:block;height:100%;border-radius:4px}}
.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:12px}}ul{{margin:6px 0;padding-left:18px}}footer{{margin-top:32px;font-size:12px;color:var(--muted)}}
</style></head><body><main>
<h1>Operation Rainmaker — Executive Dashboard</h1>
<div class="sub">Ironguard IT · confidential recruiting intelligence · last update {esc(now_iso())}</div>
<div class="kpis">{kpi_html}</div>

<h2>Research funnel</h2><div class="card">{funnel_html}</div>

<h2>Top-ranked candidates (overall: fit, economics, recruitability)</h2>
<div class="card">{table(top15, base_cols)}</div>

<div class="grid2">
<div><h2>Best local candidates (Tier 1–2)</h2><div class="card">{table(local, short_cols, "No ranked local candidates yet.")}</div></div>
<div><h2>Best national candidates (Tier 3)</h2><div class="card">{table(national, short_cols, "No ranked national candidates yet.")}</div></div>
<div><h2>Rainmakers (archetype A)</h2><div class="card">{table(rainmakers, short_cols, "No ranked rainmakers yet.")}</div></div>
<div><h2>Builders (archetype B)</h2><div class="card">{table(builders, short_cols, "No ranked builders yet.")}</div></div>
<div><h2>Best demonstrated revenue producers</h2><div class="card">{table(producers, prod_cols)}</div></div>
<div><h2>Best potential future sales executives</h2><div class="card">{table(execs, exec_cols)}</div></div>
</div>

<h2>Recommended outreach priorities (P1) — approval required before any contact</h2>
<div class="card">{table(outreach, out_cols, "No P1 candidates yet.")}</div>

<h2>Candidates needing further diligence</h2>
<div class="card">{table(diligence, dil_cols, "None flagged.")}</div>

<div class="grid2">
<div><h2>Research progress</h2><div class="card"><ul>{progress_rows or '<li class="muted">No checkpoints yet.</li>'}</ul>
<p class="small muted">Recent runs: {esc("; ".join(f"{r['run_id']} ({r['phase']}, {r['finished_at']})" for r in runs) or "none")}</p></div></div>
<div><h2>Search modalities by yield</h2><div class="card"><div class="tablewrap"><table><thead><tr><th>Modality</th><th>Queries</th><th>Productive</th></tr></thead><tbody>{mod_rows or '<tr><td colspan=3 class="muted">No search log yet.</td></tr>'}</tbody></table></div></div></div>
</div>

<h2>Next actions</h2>
<div class="card"><ul>
<li>Review the Top 3 recruitment plan (reports/F_top3_recruitment_plan.md) and the approach/offer playbook (reports/F2_approach_and_offer_playbook.md); approve or decline outreach per candidate.</li>
<li>Start the pre-hire pipeline actions in the revenue confidence plan (reports/H2_revenue_confidence_plan.md, section 4) so the hire inherits warm opportunities.</li>
<li>Confirm compensation guardrails from the economics model (reports/G_compensation_economics_model.md) before any conversation.</li>
<li>Candidates listed under diligence need re-verification before outreach; see candidates/ dossiers for open questions.</li>
<li>Run <code>scripts/run_pipeline.sh</code> after each research batch to refresh this dashboard.</li>
</ul></div>
<footer>Generated by rainmaker/scripts/dashboard.py · Scores 0–100; range shows the effect of unscored dimensions · Evidence meter 0–1 · Names link to public professional profiles where available.</footer>
</main></body></html>"""
    out = path("dashboard")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    conn.close()
    checkpoint("dashboard", candidates=st["candidates"], ranked=len(ranked))
    log.info("dashboard written to %s", out)


if __name__ == "__main__":
    main()
