export const meta = {
  name: 'rainmaker-company-map',
  description: 'Map MSP/MSSP/VAR/cloud/UCaaS companies likely to employ Ironguard IT\'s ideal salesperson (SoCal + national)',
  phases: [{ title: 'Companies', detail: 'seven segment researchers, web research, structured output' }],
}

const RUN_DATE = (args && args.run_date) || '2026-11-09'
const OUT_DIR = '/home/user/ironguard-website/rainmaker/data/raw/companies'

const PREAMBLE = `You are a senior researcher at a retained executive search firm on a confidential engagement for Ironguard IT (Carlsbad, CA; roughly $1.5-2M revenue managed IT + cybersecurity provider; clients 50-500 employees, multi-site; published pricing $150-200/user/month; Microsoft 365 and Google Workspace; senior-led). The CEO wants to recruit an exceptional B2B new-business sales professional who can originate net-new recurring managed-services revenue. Today is ${RUN_DATE}.

YOUR JOB IN THIS STAGE: build a TARGET-COMPANY MAP, i.e. organizations likely to employ that kind of salesperson. You are mapping companies, not people, but record any sales people you happen to see (name, title, URL) in people_seen.

TOOLS: Your very first tool call must be ToolSearch with query "select:WebSearch,WebFetch" and max_results 2 to load the web tools. Then use WebSearch (mode "standard"; switch to "extended" when results are thin) and WebFetch (to read company pages, award lists like Channel Futures MSP 501 / CRN MSP 500 / Inc 5000, directories like Clutch or Cloudtango, press releases). Do not bypass logins or anti-bot measures. Run at least 12 distinct searches.

EVIDENCE RULES: Only include companies that appear in a result or page you actually saw; record the exact URLs. Revenue: only record a figure when a source states it (MSP 501 / Inc 5000 / press / ZoomInfo-style snippets count, but label the source). Otherwise "unknown". Never invent revenue, headcount, or claims that employees are unhappy or looking to leave. Describe "why_attractive_for_their_sellers" only as neutral structural reasoning (e.g. "large PE-backed platform where an individual seller has limited strategic influence" or "small owner-led firm where a top seller is already near the top of the earnings ladder") — no claims about specific people.

GEOGRAPHY TIERS: Tier 1 = San Diego County (Carlsbad, Encinitas, Oceanside, Vista, San Marcos, Escondido, Del Mar, Solana Beach, Rancho Bernardo, San Diego). Tier 2 = Orange County, Irvine, Newport Beach, Costa Mesa, Mission Viejo, Temecula, Murrieta, southern LA County, other practical SoCal. Tier 3 = national.

OUTPUT: For each company capture: name, website, hq_city, hq_state, socal_offices, segment, approx_revenue (string), revenue_source_url, employee_band, target_customers, services, geographic_presence, sales_org_notes (what you can see about how they sell: inside sales, field AEs, channel, named roles), sales_strength_indicators (growth awards, fast-growth lists, hiring of sales roles, press), relevant_sales_roles (titles seen on the site, job posts or LinkedIn snippets), why_attractive_for_their_sellers, people_seen, source_urls, geo_tier, confidence. Before calling StructuredOutput, use the Write tool to save the identical JSON to the file path given below. Also include queries_run (query + productive true/false + note) and observations (which sources worked best).`

const CO_SCHEMA = {
  type: 'object',
  properties: {
    segment_label: { type: 'string' },
    companies: { type: 'array', items: { type: 'object', properties: {
      name: { type: 'string' }, website: { type: 'string' }, hq_city: { type: 'string' }, hq_state: { type: 'string' },
      socal_offices: { type: 'string' },
      segment: { type: 'string', enum: ['MSP', 'MSSP', 'MSP_PLATFORM', 'CYBER_SERVICES', 'CLOUD_MS_AWS_PARTNER', 'VAR_SOLUTION_PROVIDER', 'UCAAS_TELECOM', 'SECURITY_SAAS', 'CONSULTING', 'OTHER'] },
      approx_revenue: { type: 'string' }, revenue_source_url: { type: 'string' }, employee_band: { type: 'string' },
      target_customers: { type: 'string' }, services: { type: 'string' }, geographic_presence: { type: 'string' },
      sales_org_notes: { type: 'string' }, sales_strength_indicators: { type: 'string' }, relevant_sales_roles: { type: 'string' },
      why_attractive_for_their_sellers: { type: 'string' },
      people_seen: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, title: { type: 'string' }, source_url: { type: 'string' } }, required: ['name', 'title', 'source_url'] } },
      source_urls: { type: 'array', items: { type: 'string' } },
      geo_tier: { type: 'string', enum: ['1', '2', '3'] },
      confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    }, required: ['name', 'website', 'segment', 'source_urls', 'geo_tier', 'confidence', 'hq_city', 'hq_state', 'approx_revenue', 'services', 'sales_org_notes', 'why_attractive_for_their_sellers', 'people_seen'] } },
    queries_run: { type: 'array', items: { type: 'object', properties: { query: { type: 'string' }, productive: { type: 'boolean' }, note: { type: 'string' } }, required: ['query', 'productive'] } },
    observations: { type: 'string' },
  },
  required: ['segment_label', 'companies', 'queries_run', 'observations'],
}

const SEGMENTS = [
  { key: 'sd_msps', title: 'San Diego County MSPs and MSSPs (Tier 1)', brief: `Find 15-25 managed IT / managed security providers headquartered or with real offices in San Diego County (Carlsbad, Oceanside, Vista, San Marcos, Escondido, Encinitas, Del Mar, Sorrento Valley, Rancho Bernardo, San Diego). Prioritize firms that look like $5M-$30M revenue (use Channel Futures MSP 501 entries, CRN MSP 500, Inc 5000, San Diego Business Journal fastest-growing lists, Clutch/Cloudtango/UpCity San Diego MSP lists, Microsoft/AWS partner directories). Examples to verify (do not assume): Managed Solution, Datalink Networks, Nexus IT? , C3SD, AdVran, Technijian (OC), CMIT Carlsbad, Agile IT, Boyett? etc. Search queries like: "MSP 501" San Diego; "managed service provider" San Diego "Inc. 5000"; "San Diego" MSP cybersecurity "fastest growing"; Clutch "San Diego" managed IT; "Carlsbad" managed IT services company; "North County" San Diego IT services company; "MSSP" "San Diego".` },
  { key: 'oc_socal_msps', title: 'Orange County / Temecula / Inland Empire / South LA MSPs (Tier 2)', brief: `Find 15-25 managed IT / managed security providers headquartered in Orange County (Irvine, Newport Beach, Costa Mesa, Mission Viejo, Anaheim, Santa Ana, Lake Forest), Temecula/Murrieta, Inland Empire (Riverside, Ontario, Corona), and southern LA County (Torrance, Long Beach, El Segundo). Prioritize $5M-$30M revenue firms with growth signals (MSP 501, CRN, Inc 5000, OC Business Journal fastest-growing). Examples to verify: Technijian, Alvaka Networks, TechMD, Dynamic Computing, Jackson Thornton? , Enterprise Networking Solutions?, Accent Computer Solutions (Rancho Cucamonga), SugarShot, Be Structured (LA), Kaizen? etc. Search creatively, verify each.` },
  { key: 'national_platforms', title: 'National PE-backed MSP platforms with SoCal presence (Tier 3 with local offices)', brief: `Find 15-20 national or multi-regional MSP/MSSP platforms (often private-equity backed roll-ups) that have offices or acquired companies in Southern California, or large remote sales orgs. Examples to verify: Thrive, Ntiva, Magna5, Dataprise, Coretelligent, Integris, Meriplex, Evolve IP, Omega Systems, Cyber Advisors, ITS (Intelligent Technical Solutions), Logically, Abacus Group, Netsurit, Marco, IT Partners+, Evergreen Services Group companies, New Charter Technologies, Sourcepass, Compass MSP, Entara, Framework IT, Inverselogic, CyberStreams, Executech, Atlantic Data Security? , Vertical Computers? , Impact Networking (has Irvine/SoCal offices), Corsica Technologies, LeadingIT?, Dataprise. Record which have SoCal offices and what sales roles are visible (job posts for Account Executive, Business Development, etc.).` },
  { key: 'mssp_cyber', title: 'MSSPs and cybersecurity services firms (SoCal + national sales teams)', brief: `Find 12-20 managed security service providers and cybersecurity consulting/services firms with sales teams in Southern California or selling to SMB/mid-market nationally: e.g. Arctic Wolf (has large sales orgs; verify SoCal presence), Critical Start, CISO Global, Netsurion, Cyderes, Deepwatch, Blackpoint Cyber (sells via MSPs), Huntress (vendor), Secureworks, Proficio (Carlsbad-based MSSP! verify), Cyber Defense Group, Silent Sector?, Packetlabs?, Alpine Security?, Cerberus?, Lumifi, Ingalls, GreyCastle, LMG Security, Kroll? Focus on firms where sellers sell recurring managed security to mid-market buyers. Note Proficio in Carlsbad specifically if real.` },
  { key: 'cloud_partners', title: 'Microsoft Solutions Partners, AWS consulting partners, managed cloud providers in SoCal', brief: `Find 12-20 Microsoft Solutions Partners / Azure consultancies, AWS consulting partners, and managed cloud providers with sales presence in San Diego / Orange County / LA: e.g. Managed Solution (San Diego, Microsoft), Mission Cloud (LA, AWS), Onica/Rackspace, Six Nines IT, Effectual, Agile IT (San Diego), Planet Technologies, Catapult, Core BTS, Insight, Perficient, Nerdio? , Quisitive, Synoptek (Irvine! verify), TierPoint, Flexential, Evolve IP, RapidScale (Raleigh but SoCal sales?), CloudHesive?, Logicalis. Verify each and note sales roles.` },
  { key: 'vars_solution_providers', title: 'VARs and IT infrastructure solution providers with SoCal sales teams', brief: `Find 12-15 value-added resellers / solution providers with sales offices in San Diego or Orange County: e.g. Trace3 (Irvine HQ), Sayers, SHI, CDW, Insight, Presidio, ePlus, Zones, Connection, WWT, Converge Technology Solutions, Datalink/Insight, Sirius (now CDW), Optiv (security VAR), GuidePoint Security, Set Solutions?, Sidepath (Irvine), Novacoast (Santa Barbara), NetWize?, Comm-Works? Record evidence of SoCal offices and the kinds of AE roles (enterprise vs mid-market).` },
  { key: 'ucaas_b2b', title: 'UCaaS / telecom / B2B technology services firms with strong SoCal sales organizations', brief: `Find 10-15 unified communications, telecom and adjacent B2B tech services firms with notable SoCal sales organizations: e.g. TPx Communications (LA-based managed services + UCaaS), RingCentral, 8x8, Intermedia, Nextiva, Vonage, Cox Business, Spectrum Enterprise, Lumen, Crexendo, Intelisys/ScanSource agent community, AppDirect/AppSmart advisors, Telarus partners, DataSite?, Bluewave Technology Group, plus San Diego B2B services with top-producer cultures (e.g. Sentinel?, Nuvola?). Note which sell recurring services to SMB/mid-market owners and where their SoCal teams are.` },
]

phase('Companies')
const results = await parallel(SEGMENTS.map(seg => () => agent(
  `${PREAMBLE}\n\nSEGMENT: ${seg.title}\n\nBRIEF: ${seg.brief}\n\nSave JSON to: ${OUT_DIR}/${seg.key}.json (segment_label = "${seg.key}").`,
  { label: `companies:${seg.key}`, phase: 'Companies', schema: CO_SCHEMA }
)))

const ok = results.filter(Boolean)
log(`Company segments completed: ${ok.length}/${SEGMENTS.length}`)
const all = ok.flatMap(r => r.companies.map(c => ({ ...c, segment_label: r.segment_label })))
const seen = new Map()
for (const c of all) {
  const k = (c.name || '').toLowerCase().replace(/[^a-z0-9]/g, '')
  if (!k) continue
  if (!seen.has(k)) seen.set(k, c)
  else { const e = seen.get(k); e.source_urls = Array.from(new Set([...(e.source_urls||[]), ...(c.source_urls||[])])); e.people_seen = [...(e.people_seen||[]), ...(c.people_seen||[])] }
}
const deduped = Array.from(seen.values())
log(`Unique companies: ${deduped.length} (from ${all.length} raw)`)
return { run_date: RUN_DATE, segments_completed: ok.map(r => r.segment_label), companies: deduped, observations: ok.map(r => ({ segment: r.segment_label, observations: r.observations, queries_run: r.queries_run })) }
