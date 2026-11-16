export const meta = {
  name: 'rainmaker-desk-triage-r1',
  description: 'Score round-1 candidates from captured evidence only (no web), calibrate, and plan round-2 verification queries',
  phases: [{ title: 'Triage', detail: 'six batch scorers (8 candidates each)' }, { title: 'Calibrate', detail: 'one consistency reviewer' }],
}

const BATCHES = [1, 2, 3, 4, 5, 6]
const IN = '/home/user/ironguard-website/rainmaker/data/exports'
const OUT = '/home/user/ironguard-website/rainmaker/data/raw/verify'

const RUBRIC = `You are a partner at a retained executive search firm doing a DESK TRIAGE for Ironguard IT (Carlsbad, CA; ~$1.5-2M revenue managed IT + cybersecurity provider; clients 50-500 employees; published pricing $150-$200/user/month; senior-led). The CEO wants an exceptional B2B new-business sales professional (Rainmaker, archetype A) or an entrepreneurial sales executive who can also build a sales org (Builder, archetype B), ideally in San Diego County (Tier 1) or Southern California (Tier 2), with national (Tier 3) allowed for outstanding people.

NO WEB ACCESS IS AVAILABLE IN THIS STAGE. Do not call WebSearch or WebFetch. Work only from the evidence captured in the input file. You may use Read and Write.

Score each candidate on seven dimensions, 0-10, ONLY where the captured evidence supports a judgment; otherwise null. Never treat missing evidence as a zero and never invent. Dimensions:
- new_business_production: attributable net-new revenue/logos/quota attainment (self-stated President's Club counts as weak-positive evidence, third-party as strong)
- msp_recurring_experience: selling recurring managed IT / MSSP / managed cloud / UCaaS-type services to end customers (vendor-to-MSP sellers and enterprise VAR sellers score lower)
- sales_ability: signals of exceptional selling (repeat awards, top-rep rankings, building territories from zero, promotions through sales ranks)
- entrepreneurial_fit: comfort in a small company; founder/exit history; built territories/teams from scratch; current scale (a CRO of a $100M+ platform usually scores LOW here due to scale/comp mismatch)
- build_sales_operation: hired/coached sellers, designed plans, built process/partner channels
- executive_potential: leadership trajectory and scope
- geographic_compatibility: 10 = stated residence in San Diego County, 7 = stated Orange County/SoCal, 4 = stated elsewhere in US, null = location not stated (do NOT infer from employer HQ)

Also produce:
- evidence_confidence (0-1): quality of sources behind the scores (third-party press/award lists ~0.6-0.8; employer releases ~0.5; self-stated LinkedIn ~0.3-0.4; single aggregator listing ~0.1-0.2; name/title only ~0.1)
- recruitability (0-10): practical likelihood this person could be attracted and afforded by a ~$2M company (very senior/just-promoted/large-platform executives score low; strong individual sellers with a SoCal base score high; unknown location moderate)
- archetype_confirmed: A, B, or A+B based on evidence
- triage_decision: "investigate" (worth spending round-2 search budget), "hold" (keep in universe, revisit later), or "reject" (clearly out of scope: junior, not sales, out of comp range with no upside, stale data >5 years with no current signal), with triage_reason
- round2_queries: 3-5 precise web-search queries that would most efficiently confirm identity, current title/employer, location and attainment (e.g. "\"Full Name\" \"Company\" linkedin", "\"Full Name\" \"President's Club\"", "\"Full Name\" site:linkedin.com/in"). Only for investigate/hold.
- biggest_unknown: the single most important thing to verify
- likely_motivations: ONLY if supportable by evidence (e.g. "built a territory from zero, suggests appetite for autonomy"); otherwise "unknown"
- recommended_next_action
- research_status: "triaged" (always, in this stage)
Keep evidence classifications as captured (VERIFIED / UNVERIFIED CLAIM / INFERRED); add "UNKNOWN" items for key missing facts.

Scale calibration: a 10 on new_business_production requires third-party-verified, attributable $1M+ new ARR or repeated top-rep rankings at a relevant firm; a 7 is strong but self-stated multi-year President's Club at a relevant firm; a 4 is a credible sales title at a relevant firm with no attainment evidence (score 4 only if there is at least a credible employer press release; aggregator-only title evidence -> null for production but may still score 3-5 on msp_recurring_experience if the employer clearly sells managed services).`

const REC_SCHEMA = {
  type: 'object',
  properties: {
    records: { type: 'array', items: { type: 'object', properties: {
      candidate_name: { type: 'string' }, candidate_id: { type: 'integer' }, current_company: { type: 'string' },
      verification: { type: 'object', properties: {
        current_title_confirmed: { type: 'string' }, current_company_confirmed: { type: 'string' }, location_confirmed: { type: 'string' },
        geo_tier_confirmed: { type: 'string' }, archetype_confirmed: { type: 'string', enum: ['A', 'B', 'A+B'] }, public_profile_url: { type: 'string' },
        dimension_scores: { type: 'object', properties: {
          new_business_production: { type: ['number', 'null'] }, msp_recurring_experience: { type: ['number', 'null'] }, sales_ability: { type: ['number', 'null'] },
          entrepreneurial_fit: { type: ['number', 'null'] }, build_sales_operation: { type: ['number', 'null'] }, executive_potential: { type: ['number', 'null'] },
          geographic_compatibility: { type: ['number', 'null'] } },
          required: ['new_business_production', 'msp_recurring_experience', 'sales_ability', 'entrepreneurial_fit', 'build_sales_operation', 'executive_potential', 'geographic_compatibility'] },
        score_rationale: { type: 'object', additionalProperties: { type: 'string' } },
        evidence: { type: 'array', items: { type: 'object', properties: { claim: { type: 'string' }, classification: { type: 'string', enum: ['VERIFIED', 'INFERRED', 'UNKNOWN', 'UNVERIFIED CLAIM'] }, source_url: { type: 'string' }, quote: { type: 'string' } }, required: ['claim', 'classification', 'source_url'] } },
        evidence_confidence: { type: 'number' }, recruitability: { type: 'number' },
        triage_decision: { type: 'string', enum: ['investigate', 'hold', 'reject'] }, triage_reason: { type: 'string' },
        round2_queries: { type: 'array', items: { type: 'string' } }, biggest_unknown: { type: 'string' }, likely_motivations: { type: 'string' },
        concerns_summary: { type: 'string' }, recommended_next_action: { type: 'string' }, research_status: { type: 'string' }, source_urls: { type: 'array', items: { type: 'string' } },
      }, required: ['current_title_confirmed', 'current_company_confirmed', 'location_confirmed', 'geo_tier_confirmed', 'archetype_confirmed', 'dimension_scores', 'score_rationale', 'evidence', 'evidence_confidence', 'recruitability', 'triage_decision', 'triage_reason', 'round2_queries', 'biggest_unknown', 'likely_motivations', 'concerns_summary', 'recommended_next_action', 'research_status', 'source_urls'] },
    }, required: ['candidate_name', 'candidate_id', 'current_company', 'verification'] } },
    batch_observations: { type: 'string' },
  },
  required: ['records', 'batch_observations'],
}

phase('Triage')
const batches = await parallel(BATCHES.map(i => () => agent(
  `${RUBRIC}\n\nINPUT: Read ${IN}/triage_batch_${i}.json (a JSON list of candidate records with evidence, awards and sources). Produce one verification record per candidate (keep candidate_id and candidate_name exactly as in the input). Before returning, use Write to save {"records": [...]} to ${OUT}/triage_batch_${i}.json. Then return the same structured output.`,
  { label: `triage:batch${i}`, phase: 'Triage', schema: REC_SCHEMA }
)))
const ok = batches.filter(Boolean)
const all = ok.flatMap(b => b.records)
log(`Triage batches done: ${ok.length}/${BATCHES.length}; records: ${all.length}`)

phase('Calibrate')
const CAL_SCHEMA = {
  type: 'object',
  properties: {
    adjustments: { type: 'array', items: { type: 'object', properties: { candidate_name: { type: 'string' }, field: { type: 'string' }, old_value: { type: 'string' }, new_value: { type: 'string' }, reason: { type: 'string' } }, required: ['candidate_name', 'field', 'old_value', 'new_value', 'reason'] } },
    investigate_list: { type: 'array', items: { type: 'string' } },
    calibration_notes: { type: 'string' },
  },
  required: ['adjustments', 'investigate_list', 'calibration_notes'],
}
const cal = await agent(
  `${RUBRIC}\n\nYOU ARE THE CALIBRATION REVIEWER. Read all files ${OUT}/triage_batch_1.json through triage_batch_6.json (some may be missing). Check that scores are consistent across batches using the scale calibration above (e.g., two people with the same evidence quality should get the same scores; aggregator-only titles must not have production scores; CROs of large platforms must have low entrepreneurial_fit and recruitability; self-stated President's Club should not exceed 7 on production). Adjust specific values where needed and record every adjustment. Then write the merged, calibrated list of ALL records to ${OUT}/triage_r1_calibrated.json as {"records": [...]} (same record schema), and return the adjustments, the investigate_list (candidate names with triage_decision investigate, ordered by priority for round-2 search budget) and calibration_notes.`,
  { label: 'calibrate', phase: 'Calibrate', schema: CAL_SCHEMA }
)
return { records: all.length, batches_ok: ok.length, calibration: cal, observations: ok.map(b => b.batch_observations) }
