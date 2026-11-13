# Operation Rainmaker — Executive Sales Talent Intelligence System

Confidential recruiting-intelligence system built for the CEO of Ironguard IT (Carlsbad, CA) to find,
verify, rank and recruit an exceptional new-business sales professional ("Rainmaker") or an
entrepreneurial sales executive ("Builder").

> **Confidentiality.** The canonical home of this system, INCLUDING all research data, is the private
> repository `Ianberk92/operation-rainmaker`. This copy inside the public `ironguard-website` repository
> (which deploys the live website) carries tooling, configuration, templates and methodology only; everything
> that names a real person is excluded by `rainmaker/.gitignore`. After each research round run
> `scripts/sync_to_private.sh` to push the full working tree (with data) to the private repo. See OPERATIONS.md.

## What is delivered

| Deliverable | Location | Committed? |
|---|---|---|
| A. Executive summary | `reports/A_executive_summary.md` | no (names people) |
| B. Target company intelligence | `reports/B_target_company_intelligence.md`, `companies/` | no |
| C. Candidate database | `data/rainmaker.db` (SQLite), `data/exports/*.csv`, `data/exports/rainmaker_database.xlsx` | no |
| D. Ranked top 15 | `reports/D_ranked_top_15.md`, `reports/06_rankings.md` | no |
| E. Top 5 intelligence dossiers | `candidates/dossier_*.md` | no |
| F. Top 3 recruitment plan | `reports/F_top3_recruitment_plan.md` | no |
| G. Compensation and economics model | `reports/G_compensation_economics_model.md`, `scripts/economics.py` | yes (no personal data) |
| F2. Approach, offer and conviction playbook | `reports/F2_approach_and_offer_playbook.md` | private repo only (names people) |
| H2. Revenue confidence plan (12-month ramp model, gates, pre-hire pipeline) | `reports/H2_revenue_confidence_plan.md`, `scripts/ramp_plan.py` | script yes; report regenerable |
| H. Candidate assessment toolkit | `assessment/` | yes |
| I. Personalized outreach pack | `outreach/` | no (templates in `assessment/outreach_templates.md` are committed) |
| J. Research dashboard | `dashboard/index.html` (generated) | no |
| K. Operational documentation | `README.md`, `OPERATIONS.md`, `research/` | yes |
| Phase 1 commercial profile | `research/01_ironguard_commercial_profile.md` | yes |

## Architecture (lightweight, no services, no API keys)

```
rainmaker/
  config/settings.json      weights, geography tiers, search templates, paths, privacy rules
  scripts/
    common.py               paths, logging (logs/rainmaker.log), checkpoints (checkpoints/status.json), name normalization
    db.py                   SQLite schema (candidates, companies, evidence, awards, sources, search_log, runs, status_log)
    ingest.py               raw research JSON -> database, with deduplication and source tracking
    score.py                weighted scoring, evidence confidence, 3 rankings, sensitivity analysis -> reports/06_rankings.md
    export.py               CSV + XLSX exports
    dashboard.py            static HTML executive dashboard
    qa.py                   quality gates (duplicates, sources, placeholders, score consistency, exports)
    reports.py              company intelligence (B), ranked top 15 (D), top-N dossiers (E) from the database
    leads_from_companies.py turns sales-titled names noticed during company mapping into low-confidence leads
    round2_args.py          builds the budgeted args for the round-2 workflow (verify + by-company + discovery)
    economics.py            compensation scenarios and revenue-production math (deliverable G)
    ramp_plan.py            12-month revenue-confidence model, go/no-go gates, pre-hire pipeline checklist (H2)
    weekly_discovery.py     recurring discovery plan + weekly intelligence report
    run_pipeline.sh         ingest -> score -> export -> dashboard -> qa
  data/raw/companies/*.json research output: company map
  data/raw/r<N>/*.json      research output: candidate discovery rounds
  data/raw/verify/*.json    research output: verification / deep-dive results
  research/                 methodology notes and Phase 1 analysis
  assessment/               interview exercises, scorecards, reference-check guide, outreach templates
```

Research is performed by Claude Code research agents (web search + page reads) that write JSON in the
schemas below. The Python pipeline is deterministic and re-runnable; nothing is fetched by the scripts.

## Quick start

```bash
cd rainmaker
python3 scripts/db.py init
./scripts/run_pipeline.sh          # ingest -> score -> export -> dashboard -> qa
python3 scripts/reports.py         # B, D and the top-5 dossiers
python3 scripts/economics.py       # G
python3 scripts/ramp_plan.py       # H2
open dashboard/index.html          # or xdg-open / start
python3 scripts/db.py stats
```

Requires Python 3.10+. `openpyxl` is optional (Excel export).

## Data schemas

### Discovery record (`data/raw/r<N>/<modality>.json`)
```json
{"modality": "geo_san_diego",
 "candidates": [{"full_name": "", "current_title": "", "current_company": "", "previous_employers": [],
   "location_public": "unknown", "location_source_url": "", "years_experience_estimate": "", "what_they_sell": "",
   "msp_mssp_experience": "", "net_new_evidence": "", "segment_experience": "",
   "performance_evidence": [{"claim": "", "classification": "VERIFIED|UNVERIFIED CLAIM|INFERRED", "source_url": "", "quote": ""}],
   "leadership_evidence": "", "entrepreneurial_evidence": "", "awards_recognition": [{"award": "", "year": "", "source_url": ""}],
   "archetype": "A|B|A+B", "public_profile_url": "", "source_urls": [], "key_quote": "", "concerns": "",
   "geo_tier": "1|2|3|unknown", "confidence": "high|medium|low", "notes": ""}],
 "queries_run": [{"query": "", "productive": true, "note": ""}], "observations": ""}
```

### Verification record (`data/raw/verify/<name>.json`)
```json
{"candidate_name": "", "current_company": "", "verification": {
   "current_title_confirmed": "", "current_company_confirmed": "", "location_confirmed": "", "geo_tier_confirmed": "",
   "archetype_confirmed": "", "public_profile_url": "",
   "dimension_scores": {"new_business_production": null, "msp_recurring_experience": null, "sales_ability": null,
                        "entrepreneurial_fit": null, "build_sales_operation": null, "executive_potential": null,
                        "geographic_compatibility": null},
   "score_rationale": {"new_business_production": "..."},
   "evidence": [{"claim": "", "classification": "VERIFIED|INFERRED|UNKNOWN|UNVERIFIED CLAIM", "source_url": "", "quote": ""}],
   "evidence_confidence": 0.0, "recruitability": 0.0, "concerns_summary": "", "research_status": "verified|deep_dive|rejected",
   "recommended_next_action": "", "source_urls": []}}
```
Dimension scores are 0–10 or `null` (unknown). Null is never treated as zero: the scorer uses a neutral
prior and reports a low/high range (see `config/settings.json`).

## Scoring model

Weights (config): new-business production 25%, MSP/MSSP recurring experience 20%, exceptional sales ability
15%, entrepreneurial fit 15%, ability to build a sales operation 10%, executive potential 10%, geography 5%.
Evidence confidence = share of weighted dimensions with evidence, blended with verifier source quality.
Rankings: (1) producer (evidence-weighted production), (2) executive (builder dimensions), (3) overall
(80% weighted model + 20% practical recruitability). Sensitivity analysis re-ranks under six alternative
weight sets and reports top-5 stability.

## Evidence classes

VERIFIED (credible third party, employer release, award list) · INFERRED (reasonable interpretation,
reason stated) · UNKNOWN · UNVERIFIED CLAIM (self-stated, e.g. a LinkedIn headline). No sales results,
compensation or interest are ever invented; missing data stays missing.

## Privacy and ethics

Only public professional information is collected (name, title, employer, public profile URL, public
statements and awards). No personal emails, phone numbers, home addresses, photos or protected
characteristics. No one is contacted without the CEO's explicit approval (see `outreach_approval_status`).
No scraping behind logins, no anti-bot evasion. California non-compete law and trade-secret obligations
are addressed in the recruitment plan; the process never solicits a prior employer's confidential data.
