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

## Round 3 plan (after round 2 completes)

Lessons from round 2 verification: employer-published pages (leadership pages, channel maps, code-of-conduct
documents, press releases) surfaced through search snippets resolved titles for 9 of 15 candidates; aggregator-only
names stayed unverifiable and should not receive further budget.

Priorities for the next 180 searches:
1. Direct sellers at the employers that proved relevant (2–3 searches each): TPx's direct San Diego sales team
   (not channel), Managed Solution's "100% hunter" account executives, Agile IT's sales team, Proficio's direct
   sellers, centrexIT business development, DeepSeas, Bird Rock Systems, Infracore, Xceptional.
2. Verify new names from the round-2 company sweep (4 searches each for the top 10).
3. Modalities still never run: UCaaS/telecom top producers, VAR/vendor sellers with President's Club in SD/OC,
   Microsoft/AWS partner sellers, builder scale stories.
4. Manual checks the CEO can do in minutes (no budget): LinkedIn location and title for the four
   "investigate" candidates listed in the private repository's playbook (reports/F2, section 7).

## Round 4 plan (after round 3)

Round 3 confirmed the structural limit of web-only discovery (see research/02_methodology_lessons.md). Round 4 should be
hybrid:
1. CEO (or a researcher with LinkedIn Recruiter Lite / Sales Navigator / Apollo.io) lists account executives and
   business-development managers at the ten most relevant employers (TPx direct sales, Managed Solution, Agile IT,
   Proficio, DeepSeas, Infracore, EVOTEK, Synoptek, IT Solutions Consulting Carlsbad office, TechMD) and pastes names
   and titles into data/raw/r4/manual_people.json (discovery schema, confidence low, source = profile URL).
2. The system spends the search budget on name-first confirmation (3 searches per name) and on alumni of those
   employers (press and profile updates make job-changers visible).
3. Manual checks that unblock current leads: location of the TPx honoree; current title of the Managed Solution VP; title
   of the Ivanti seller.
4. Remaining modalities: conference/podcast speakers and vendor award lists had near-zero yield for direct sellers and
   should not receive budget again.
