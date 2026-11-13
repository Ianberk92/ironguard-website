export const meta = {
  name: 'rainmaker-round4',
  description: 'Round 4: verify investigate-list candidates, sweep Tier 1-2 companies for sellers, run never-executed discovery modalities, within a fixed web-search budget',
  phases: [
    { title: 'Verify', detail: 'one agent per investigate candidate, 4 searches each' },
    { title: 'ByCompany', detail: 'employer team-page enumeration then name confirmation, 3 searches per company' },
    { title: 'Discover', detail: 'modalities not yet run, ~20 searches each' },
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
  `${COMMON}\n\nTASK: VERIFY ONE CANDIDATE. HARD CAP: ${PER_CAND} WebSearch calls.\nCandidate: ${c.name} — recorded employer: ${c.company} (candidate_id ${c.id}). Biggest unknown from desk triage: ${c.biggest_unknown}\nSuggested queries (adapt as needed): ${JSON.stringify(c.queries)}\nConfirm or refute current title/employer, public location, and the performance claims; look for third-party evidence (press, award lists) and disqualifiers. Score the seven dimensions 0-10 only where evidence supports (else null). Set research_status "verified" (or "rejected"). Use Write to save the record to ${RAW}/verify/r4_${slug(c.name)}.json, then return it as structured output. Report searches_used honestly.`,
  { label: `verify:${slug(c.name)}`, phase: 'Verify', schema: VER_SCHEMA }
)))
log(`Verified ${verified.filter(Boolean).length}/${VERIFY.length}; searches used ≈ ${verified.filter(Boolean).reduce((n, v) => n + (v.searches_used || 0), 0)}`)

phase('ByCompany')
const chunks = []
for (let i = 0; i < COMPANIES.length; i += 4) chunks.push(COMPANIES.slice(i, i + 4))
const byco = await parallel(chunks.map((ch, i) => () => agent(
  `${COMMON}\n\nTASK: FIND SELLERS AT THESE COMPANIES. HARD CAP: ${ch.length * PER_CO} WebSearch calls (${PER_CO} per company).\nCompanies: ${JSON.stringify(ch)}\nRounds 2-3 lesson: for sub-100-person MSPs the ONLY productive pattern was the employer's own team/leadership page surfaced through search, then one confirmation query per surfaced name. For each company: (1) "<Company>" "our team" OR "meet the team" OR "leadership" OR "about us" <city>; (2) if names appear, "<Name>" "<Company>" to confirm title; (3) "<Company>" "business development" OR "account executive" OR "sales" <city>. Record every DIRECT sales-titled person (account executive, business development, sales director/manager) with exact URL and snippet; record owners/engineers only in notes. Use Write to save to ${RAW}/r4/by_company_${i + 1}.json (modality "by_company"), then return structured output.`,
  { label: `bycompany:${i + 1}`, phase: 'ByCompany', schema: CAND_SCHEMA }
)))
log(`By-company agents done: ${byco.filter(Boolean).length}/${chunks.length}; candidates ${byco.filter(Boolean).reduce((n, r) => n + r.candidates.length, 0)}`)

phase('Discover')
const MODS = [
  { key: 'alumni_relevant_employers', brief: `ALUMNI SWEEP: people who FORMERLY sold at the relevant San Diego/SoCal employers and are now elsewhere (job changes generate press and profile updates, so they are more visible than current staff). Employers: Managed Solution, Agile IT, TPx/TelePacific, Proficio, DeepSeas/Security On-Demand, centrexIT, Infracore, Bird Rock Systems, EVOTEK, Synoptek, IT Solutions Consulting (San Diego). Queries like: "formerly" OR "previously" "Managed Solution" "account executive" San Diego; "former" "TelePacific" OR "TPx" "account executive" "San Diego" managed services; "Agile IT" alumni "account executive"; "joined" "from Proficio" sales; "previously at centrexIT" sales; "after" "years at TPx" "San Diego" sales director. Record current employer, title and any attainment statements verbatim.` },
  { key: 'oc_temecula_msp_sellers', brief: `Direct account executives and business-development leaders at Orange County, Temecula/Murrieta and Inland Empire MSPs/MSSPs with attainment signals: TechMD (now Integris), KaufmanIT, BRITECITY, Technijian, Alvaka, Right Click, CAL IT Group, Affant, AdVran, Umetech (Temecula), Unique Solutions MSP, Just Smart Business Technologies (Murrieta), eTop (Redlands), Consilien, DivergeIT, AllSafe IT. Use team-page and "<Company>" "business development" OR "account executive" Irvine OR Temecula patterns, then confirm names. Record stated locations verbatim.` },
  { key: 'sd_cyber_saas_top_producers', brief: `Top-producing DIRECT sellers in San Diego County of recurring B2B security/IT software or services to SMB and mid-market buyers (an adjacent hunter pool that understands recurring revenue and security buyers): sellers at cybersecurity SaaS and IT software firms with San Diego sales offices (e.g. Cloudflare? no SD office; focus on firms with SD presence such as Netsurion, Seceon, Cyberark? verify), plus "President's Club" "San Diego" "account executive" cybersecurity OR "managed services" OR SaaS; "Rookie of the Year" "San Diego" "account executive" software 2024 OR 2025; "#1 rep" "San Diego" "account executive" B2B. Mark that these sellers lack MSP delivery context as a concern.` },
  { key: 'bd_hires_sd_2025_2026', brief: `Job-change signals: people announced or self-announced in 2025-2026 as joining a San Diego/SoCal MSP, MSSP, cloud partner or IT solutions provider as Director of Business Development, Account Executive, Senior AE, Sales Manager or VP Sales, or announcing a move in a LinkedIn post indexed by search. Queries like: "joins" "as Director of Business Development" "San Diego" managed IT 2025 OR 2026; "excited to announce" "account executive" "managed services" "San Diego" 2026; "new role" "business development" MSP "San Diego" OR Carlsbad 2025; "has joined" "managed services" "sales" "Orange County" 2026; "welcomes" "account executive" MSP San Diego 2025.` },
]
const perAgent = Math.max(6, Math.min(20, Math.floor(DISC_BUDGET / MODS.length)))
const disc = DISC_BUDGET >= 24 ? await parallel(MODS.map(m => () => agent(
  `${COMMON}\n\nTASK: DISCOVERY MODALITY "${m.key}". HARD CAP: ${perAgent} WebSearch calls.\n${m.brief}\nRecord qualified people (sellers/sales leaders of recurring IT/security services) with exact URL and snippet. Use Write to save to ${RAW}/r4/${m.key}.json (modality "${m.key}"), then return structured output.`,
  { label: `discover:${m.key}`, phase: 'Discover', schema: CAND_SCHEMA }
))) : []
if (DISC_BUDGET < 24) log('Discovery phase skipped: insufficient remaining search budget')
return { run_date: RUN_DATE, verified: verified.filter(Boolean).map(v => ({ name: v.candidate_name, status: v.verification.research_status, decision: v.verification.triage_decision, searches: v.searches_used })),
  by_company_candidates: byco.filter(Boolean).reduce((n, r) => n + r.candidates.length, 0), discovery_candidates: disc.filter(Boolean).reduce((n, r) => n + r.candidates.length, 0),
  observations: [...byco.filter(Boolean), ...disc.filter(Boolean)].map(r => ({ modality: r.modality, searches: r.searches_used, observations: r.observations })) }
