# Round-2 research plan (ready to run; needs a new turn because the search budget is per turn)

## Why a new turn is needed
The environment allows 200 web searches per turn, shared by every agent, and blocks direct page fetches. Round 1
used the full budget. Each follow-up message from the CEO (e.g., "continue") resets the budget to 200.

## Budget allocation for round 2 (180 searches, 20 held in reserve)

| Block | Agents | Searches | Purpose |
|---|---|---|---|
| Verify | 1 per "investigate" candidate (≤16) | 4 each (≤64) | Confirm title/employer/location, find third-party attainment evidence, disqualify |
| By-company | 6 agents × 5 companies | 2 per company (60) | Sellers at Tier 1–2 MSPs/MSSPs mapped in round 1 |
| Discover | 4 agents | ~14 each (56) | Modalities that never ran: SoCal sales-leader press releases, founder exits, MSSP sellers, conference/podcast speakers |

## How to run (next turn)

```bash
python3 rainmaker/scripts/round2_args.py --budget 180 > rainmaker/data/exports/round2_args.json
# then launch the Workflow tool with scriptPath = rainmaker/research/workflows/05_round2_verify_discover.js
# and args = contents of round2_args.json (fill run_date)
# afterwards:
rainmaker/scripts/run_pipeline.sh && python3 rainmaker/scripts/reports.py
```

Agents are told the cap is hard and to stop at the first "budget used up" response, so a round never silently
starves later agents again. Rounds 3+ repeat the same shape: re-verify the new investigate list, sweep the next
30 companies, run the remaining modalities (UCaaS, VAR/vendor, cloud partners, builder scale stories).

## Environment changes that would raise quality (CEO decision)

1. Raise `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION` in the environment settings (more searches per turn).
2. Allow these domains in the environment's network settings so pages (not just snippets) can be read:
   crn.com, channelfutures.com, prnewswire.com, businesswire.com, globenewswire.com, einpresswire.com, ocbj.com,
   sdbj.com, msspalert.com, channele2e.com, inc.com, plus target-company websites. LinkedIn cannot be fetched
   regardless and should be used manually.
3. Optional paid tools: see research/03_optional_integrations.md (LinkedIn Recruiter Lite is the highest-value, lowest-cost step).
