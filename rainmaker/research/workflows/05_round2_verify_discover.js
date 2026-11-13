export const meta = {
  name: 'rainmaker-round2',
  description: 'Round 2: verify investigate-list candidates, sweep Tier 1-2 companies for sellers, run never-executed discovery modalities, within a fixed web-search budget',
  phases: [
    { title: 'Verify', detail: 'one agent per investigate candidate, 4 searches each' },
    { title: 'ByCompany', detail: 'five companies per agent, 2 searches per company' },
    { title: 'Discover', detail: 'modalities that never ran in round 1, 14 searches each' },
  ],
}

// args is produced by: python3 rainmaker/scripts/round2_args.py --budget 180 > rainmaker/data/exports/round2_args.json
// and passed verbatim as the Workflow `args` input (with run_date filled in).
const A = args || {}
const RUN_DATE = A.run_date || 'unknown date'
const VERIFY = A.verify || []
const COMPANIES = A.companies || []
const PER_CAND = A.per_candidate || 4
const PER_CO = A.per_company || 2
const DISC_BUDGET = A.discovery_budget_remaining || 0
const RAW = '/home/user/ironguard-website/rainmaker/data/raw'

const COMMON = `Confidential executive-search research for Ironguard IT (Carlsbad, CA; ~$1.5-2M managed IT + cybersecurity provider seeking an exceptional new-business sales professional or sales-executive builder). Today is ${RUN_DATE}.
TOOLS: first call ToolSearch with query "select:WebSearch,WebFetch" (max_results 2). WebFetch is blocked for most hosts in this environment; rely on WebSearch snippets. The web-search budget is SHARED by all agents this turn and strictly limited: you have a HARD CAP stated below. If any search returns "budget is used up", stop searching immediately and write what you have. Avoid "site:" operators (ignored by the engine); pair the person or employer name with a sales title, a city, or "President's Club". Use mode "standard"; use "extended" only for one final confirmation query on a named person.
EVIDENCE RULES: real people only, exact URLs, verbatim snippet quotes; classify VERIFIED / INFERRED / UNKNOWN / UNVERIFIED CLAIM; never infer residence from employer HQ; no personal contact data; never claim anyone is unhappy or looking; write "unknown" rather than guessing.`

const VER_SCHEMA = { type: 'object', properties: { candidate_name: { type: 'string' }, candidate_id: { type: 'integer' }, current_company: { type: 'string' }, searches_used: { type: 'integer' },
  verification: { type: 'object', properties: {
    current_title_confirmed: { type: 'string' }, current_company_confirmed: { type: 'string' }, location_confirmed: { type: 'string' }, geo_tier_confirmed: { type: 'string' },
    archetype_confirmed: { type: 'string', enum: ['A', 'B', 'A+B'] }, public_profile_url: { type: 'string' },
    dimension_scores: { type: 'object', properties: { new_business_production: { type: ['number', 'null'] }, msp_recurring_experience: { type: ['number', 'null'] }, sales_ability: { type: ['number', 'null'] }, entrepreneurial_fit: { type: ['number', 'null'] }, build_sales_operation: { type: ['number', 'null'] }, executive_potential: { type: ['number', 'null'] }, geographic_compatibility: { type: ['number', 'null'] } },
      required: ['new_business_production', 'msp_recurring_experience', 'sales_ability', 'entrepreneurial_fit', 'build_sales_operation', 'executive_potential', 'geographic_compatibility'] },
    score_rationale: { type: 'object', additionalProperties: { type: 'string' } },
    evidence: { type: 'array', items: { type: 'object', properties: { claim: { type: 'string' }, classification: { type: 'string', enum: ['VERIFIED', 'INFERRED', 'UNKNOWN', 'UNVERIFIED CLAIM'] }, source_url: { type: 'string' }, quote: { type: 'string' } }, required: ['claim', 'classification', 'source_url'] } },
    evidence_confidence: { type: 'number' }, recruitability: { type: 'number' }, triage_decision: { type: 'string', enum: ['investigate', 'hold', 'reject'] }, triage_reason: { type: 'string' },
    round2_queries: { type: 'array', items: { type: 'string' } }, biggest_unknown: { type: 'string' }, likely_motivations: { type: 'string' }, concerns_summary: { type: 'string' },
    recommended_next_action: { type: 'string' }, research_status: { type: 'string', enum: ['verified', 'deep_dive', 'rejected', 'triaged'] }, source_urls: { type: 'array', items: { type: 'string' } } },
    required: ['current_title_confirmed', 'current_company_confirmed', 'location_confirmed', 'geo_tier_confirmed', 'archetype_confirmed', 'dimension_scores', 'score_rationale', 'evidence', 'evidence_confidence', 'recruitability', 'triage_decision', 'triage_reason', 'round2_queries', 'biggest_unknown', 'likely_motivations', 'concerns_summary', 'recommended_next_action', 'research_status', 'source_urls'] } },
  required: ['candidate_name', 'candidate_id', 'current_company', 'searches_used', 'verification'] }

const CAND_SCHEMA = { type: 'object', properties: { modality: { type: 'string' }, searches_used: { type: 'integer' },
  candidates: { type: 'array', items: { type: 'object', properties: {
    full_name: { type: 'string' }, current_title: { type: 'string' }, current_company: { type: 'string' }, previous_employers: { type: 'array', items: { type: 'string' } },
    location_public: { type: 'string' }, location_source_url: { type: 'string' }, years_experience_estimate: { type: 'string' }, what_they_sell: { type: 'string' },
    msp_mssp_experience: { type: 'string' }, net_new_evidence: { type: 'string' }, segment_experience: { type: 'string' },
    performance_evidence: { type: 'array', items: { type: 'object', properties: { claim: { type: 'string' }, classification: { type: 'string', enum: ['VERIFIED', 'UNVERIFIED CLAIM', 'INFERRED'] }, source_url: { type: 'string' }, quote: { type: 'string' } }, required: ['claim', 'classification', 'source_url'] } },
    leadership_evidence: { type: 'string' }, entrepreneurial_evidence: { type: 'string' }, awards_recognition: { type: 'array', items: { type: 'object', properties: { award: { type: 'string' }, year: { type: 'string' }, source_url: { type: 'string' } }, required: ['award', 'source_url'] } },
    archetype: { type: 'string', enum: ['A', 'B', 'A+B'] }, public_profile_url: { type: 'string' }, source_urls: { type: 'array', items: { type: 'string' } }, key_quote: { type: 'string' }, concerns: { type: 'string' },
    geo_tier: { type: 'string', enum: ['1', '2', '3', 'unknown'] }, confidence: { type: 'string', enum: ['high', 'medium', 'low'] }, notes: { type: 'string' } },
    required: ['full_name', 'current_title', 'current_company', 'public_profile_url', 'source_urls', 'key_quote', 'archetype', 'confidence', 'geo_tier', 'performance_evidence', 'location_public', 'what_they_sell', 'msp_mssp_experience', 'net_new_evidence', 'concerns'] } },
  queries_run: { type: 'array', items: { type: 'object', properties: { query: { type: 'string' }, productive: { type: 'boolean' }, note: { type: 'string' } }, required: ['query', 'productive'] } },
  observations: { type: 'string' } }, required: ['modality', 'searches_used', 'candidates', 'queries_run', 'observations'] }

const slug = s => (s || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')

phase('Verify')
const verified = await parallel(VERIFY.map(c => () => agent(
  `${COMMON}\n\nTASK: VERIFY ONE CANDIDATE. HARD CAP: ${PER_CAND} WebSearch calls.\nCandidate: ${c.name} — recorded employer: ${c.company} (candidate_id ${c.id}). Biggest unknown from desk triage: ${c.biggest_unknown}\nSuggested queries (adapt as needed): ${JSON.stringify(c.queries)}\nConfirm or refute current title/employer, public location, and the performance claims; look for third-party evidence (press, award lists) and disqualifiers. Score the seven dimensions 0-10 only where evidence supports (else null). Set research_status "verified" (or "rejected"). Use Write to save the record to ${RAW}/verify/r2_${slug(c.name)}.json, then return it as structured output. Report searches_used honestly.`,
  { label: `verify:${slug(c.name)}`, phase: 'Verify', schema: VER_SCHEMA }
)))
log(`Verified ${verified.filter(Boolean).length}/${VERIFY.length}; searches used ≈ ${verified.filter(Boolean).reduce((n, v) => n + (v.searches_used || 0), 0)}`)

phase('ByCompany')
const chunks = []
for (let i = 0; i < COMPANIES.length; i += 5) chunks.push(COMPANIES.slice(i, i + 5))
const byco = await parallel(chunks.map((ch, i) => () => agent(
  `${COMMON}\n\nTASK: FIND SELLERS AT THESE COMPANIES. HARD CAP: ${ch.length * PER_CO} WebSearch calls (${PER_CO} per company).\nCompanies: ${JSON.stringify(ch)}\nFor each company run e.g. "<Company>" "account executive" OR "director of sales" OR "vice president of sales", then "<Company>" "President's Club" OR "top producer" OR "sales" award. Record every sales-titled person seen with exact URL and snippet. Use Write to save to ${RAW}/r2/by_company_${i + 1}.json (modality "by_company"), then return structured output.`,
  { label: `bycompany:${i + 1}`, phase: 'ByCompany', schema: CAND_SCHEMA }
)))
log(`By-company agents done: ${byco.filter(Boolean).length}/${chunks.length}; candidates ${byco.filter(Boolean).reduce((n, r) => n + r.candidates.length, 0)}`)

phase('Discover')
const MODS = [
  { key: 'press_socal_hires', brief: `Press releases and business-journal "people on the move" items (2023-2026) announcing VP of Sales / Director of Sales / CRO / Business Development hires or promotions at MSPs, MSSPs and cloud partners in San Diego, Orange County, Temecula and LA. Queries like: "appointed" "vice president of sales" "managed services" "San Diego"; "San Diego Business Journal" "people on the move" IT services sales; "Orange County Business Journal" "on the move" MSP sales.` },
  { key: 'entrepreneurs_exits_socal', brief: `Founders/co-founders of Southern California MSPs acquired 2019-2026 (by Thrive, Ntiva, Magna5, Evergreen, New Charter, Sourcepass, Integris, Meriplex, IT Partners+, Omega, Cyber Advisors, Impact Networking, Synoptek, Dataprise, Coretelligent, VC3, KaufmanIT, TechMD) who were the commercial founder, and their current roles. Queries like: "acquires" "San Diego" managed services provider 2024; "TechMD acquires"; "VC3 acquires" California; "KaufmanIT acquires"; "founder" MSP "acquired" "vice president of sales" California.` },
  { key: 'mssp_cyber_sellers', brief: `Account executives and sales leaders at MSSPs/cyber services firms with SoCal presence (Proficio Carlsbad, DeepSeas San Diego, Arctic Wolf, Critical Start, Cyderes, Optiv, GuidePoint, Novacoast, FIT Solutions) with new-logo/attainment evidence. Queries like: "Proficio" "account executive" "President's Club"; "DeepSeas" "director of sales"; "Arctic Wolf" "San Diego" "President's Club"; "GuidePoint Security" "San Diego" account executive.` },
  { key: 'conferences_podcasts', brief: `Sales-focused speakers and podcast guests from MSPs/MSSPs (IT Nation, Pax8 Beyond, DattoCon/Kaseya Connect, Right of Boom, SMB TechFest Orange County, Surf and Sales San Diego, The MSP Sales Podcast, Sales Success Stories) who currently sell or lead sales at an MSP/MSSP, SoCal preferred. Queries like: "SMB TechFest" speaker "sales" MSP; "Surf and Sales" guest "managed services"; "IT Nation" 2025 speaker "VP of Sales" MSP; "Pax8 Beyond" speaker "account executive" MSP.` },
]
const perAgent = Math.max(6, Math.floor(DISC_BUDGET / MODS.length))
const disc = DISC_BUDGET >= 24 ? await parallel(MODS.map(m => () => agent(
  `${COMMON}\n\nTASK: DISCOVERY MODALITY "${m.key}". HARD CAP: ${perAgent} WebSearch calls.\n${m.brief}\nRecord qualified people (sellers/sales leaders of recurring IT/security services) with exact URL and snippet. Use Write to save to ${RAW}/r2/${m.key}.json (modality "${m.key}"), then return structured output.`,
  { label: `discover:${m.key}`, phase: 'Discover', schema: CAND_SCHEMA }
))) : []
if (DISC_BUDGET < 24) log('Discovery phase skipped: insufficient remaining search budget')
return { run_date: RUN_DATE, verified: verified.filter(Boolean).map(v => ({ name: v.candidate_name, status: v.verification.research_status, decision: v.verification.triage_decision, searches: v.searches_used })),
  by_company_candidates: byco.filter(Boolean).reduce((n, r) => n + r.candidates.length, 0), discovery_candidates: disc.filter(Boolean).reduce((n, r) => n + r.candidates.length, 0),
  observations: [...byco.filter(Boolean), ...disc.filter(Boolean)].map(r => ({ modality: r.modality, searches: r.searches_used, observations: r.observations })) }
