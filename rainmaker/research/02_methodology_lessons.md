# Methodology lessons after research round 1 (2026-11-09)

## Environment constraints discovered (material)

1. **Web search budget: 200 searches per turn, shared by every agent.** Round 1 launched 24 research agents in
   parallel; the first six consumed the budget (about 250 queries attempted, 200 executed) and the remaining 18
   modalities could not search at all. Every later round must be budget-planned: at most ~180 searches per turn,
   allocated by expected yield, with hard per-agent caps.
2. **Network policy blocks direct page fetches** (every external host returned ENOTFOUND or 403 from the proxy:
   crn.com, channelfutures.com, prnewswire.com, businesswire.com, globenewswire.com, linkedin.com, company sites).
   Only search-engine snippets are available as evidence. Consequence: titles and quotes come from snippets and
   aggregator listings, which lowers evidence confidence across the board. Allowing these domains in the
   environment's network settings would materially raise verification quality.
3. The search engine ignores `site:linkedin.com/in` operators; results are dominated by job boards and marketing
   pages. Plain phrase queries that pair an employer name with a sales title or "President's Club" work better and
   return LinkedIn snippets that include a stated location.

## What produced candidates (yield per modality)

| Modality | Productive / total queries | Candidates | Lesson |
|---|---|---|---|
| companies:sd_msps | 49/58 | 32 companies | Company mapping by city + award list is cheap and reliable |
| companies:oc_socal_msps | 31/54 | 30 companies | Same |
| geo_san_diego | 8/36 | 14 | Employer-name + title queries surface aggregator snippets naming staff |
| geo_orange_county | 9/34 | 9 | Same; `site:` operators wasted ~15 queries |
| awards_presidents_club | 8/37 | 10 | Extended-mode "President's Club" + employer + city returned located LinkedIn snippets (TPx) |
| awards_vendor_channel | 7/28 | 12 | CRN Next-Gen / WOTC releases name sales leaders, mostly outside SoCal |
| all other modalities | 0 | 0 | Never ran (budget exhausted) — highest priority for round 2 |

## Round-2 design rules

- Verification first: spend ~4 searches on each "investigate" candidate before any new discovery.
- Discovery second: by-company sweeps of Tier 1–2 MSPs (2 searches each) outperform generic modality queries.
- Never run more than 3 agents concurrently; give each a written cap (10–14 searches) and tell it the budget is shared.
- Use `"<Employer>" "President's Club"` and `"<Employer>" "account executive" San Diego` patterns; avoid `site:`.
- Prefer extended mode only for the final confirmation query on a named person.
- Record every query in `search_log` (automatic via ingest) and re-rank modalities after each round.

## Quality observations

- Aggregator sites (Prospeo, Datanyze, SignalHire, ContactOut, FinalScout, TheOrg, RocketReach) are useful for
  discovering names but are frequently stale; treat as UNVERIFIED CLAIM and confirm with a second source.
- Employer press releases are reliable for titles and dates but never for attainment numbers.
- Self-stated President's Club counts on LinkedIn are the most common attainment evidence; they need reference
  verification before they can drive an offer.
- Three duplicates in round 1 came from the same person being recorded with different employer wording; ingest now
  merges same-name records when either employer is unknown or the names overlap, and flags true same-name conflicts.

## After round 3 (2026-11-09, later)

Three rounds and roughly 560 searches establish a structural limit of web-only research for this brief: the search
engine does not surface LinkedIn profile snippets for sellers at sub-200-employee MSPs, and company-first or
award-pattern queries return job boards and data-broker directories instead of people. What did work: employer
press releases (titles and dates), employer-published team and bio pages, trade-press people moves, and
name-first confirmation queries once a name is known. What did not: discovering individual account executives at
small MSPs by employer or award term.

Implications for the search:
1. The verified approach list (one direct hunter, one MSP-native sales leader, one local enterprise-software
   producer) is what public web research can produce; it is not the ceiling of the market.
2. The highest-value next step is a people-data source (LinkedIn Recruiter Lite or Sales Navigator used manually by
   the CEO, or Apollo.io) to enumerate account executives at the ten most relevant employers, followed by name-first
   web confirmation (3 searches each) through this system. Cost and benefit are in research/03_optional_integrations.md.
3. Alumni of the relevant employers (former account executives now elsewhere) are a better pool than current staff
   for a public-web approach, because job changes generate press and profile updates.
4. Comp benchmarks observed in postings this round (useful for the offer): Managed Solution hunter AE base $65K–$95K;
   IT Solutions Consulting San Diego field AE base $70K–$100K; Agile IT CMMC/Microsoft AE $135K–$150K; Proficio senior
   regional sales manager $100K–$135K. The adopted $115K base sits above the MSP median and below cyber/enterprise.

## After round 4 (2026-11-10)

- Team-page enumeration worked only where the employer's own team page is indexed (one of sixteen small MSPs); re-querying
  the same team URL with different phrasing exposed additional names, so a second pass on an indexed team page is worth one
  query. Sub-25-person San Diego MSPs are owner-led or engineer-sold; stop spending budget on them.
- The alumni sweep and the 2025–26 job-change sweep produced the most useful new names per search (verified appointments
  with press sources), but they skew to VP/SVP-level sales leaders rather than individual hunters.
- Award-vocabulary queries ("President's Club", "Rookie of the Year") remain dominated by job boards; use them only
  name-first.
- A container restart interrupted a workflow mid-run; resuming with the saved run id replayed the finished agents from the
  journal and only re-ran the unfinished ones, so no search budget was lost. Keep run ids in the log.
- Decision for round 5: stop broad web discovery. Spend budget only on (a) name-first confirmation of names the CEO
  supplies from a manual LinkedIn pass, (b) the two or three strongest unconfirmed leads per round, and (c) re-validation
  of the approach list before any contact.
