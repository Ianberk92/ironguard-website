# Discovery modalities (standard briefs)

Each modality is a distinct way of finding people so that no single search angle dominates. Round-1 briefs are in the
workflow scripts under research/workflows/. Keep each agent to a fixed search budget (10–14 searches) because the
environment caps web searches per turn (200 shared by all agents).

| Key | Angle | Highest-yield query patterns observed |
|---|---|---|
| geo_san_diego / geo_orange_county | search-indexed profiles by city + title | `"<Employer>" "account executive"` and `"<Employer>" "President's Club"` (aggregator snippets name sales staff); plain `site:linkedin.com/in` operators were ignored by the engine |
| awards_presidents_club | attainment announcements | `"President's Club" "<Employer>" "<city>"` in extended mode returned LinkedIn snippets with locations |
| awards_vendor_channel | CRN Next-Gen / Women of the Channel / vendor awards | employer press releases naming honorees; filter to sales titles |
| press_socal_hires / press_national_hires | appointments | `"appointed" OR "names" "vice president of sales" "managed services" <region> <year>` |
| conferences_* | speakers | event name + "speaker" + sales title |
| podcasts_msp_sales / interviews_case_studies | interviews | show name + "guest" + "sales" |
| entrepreneurs_exits_socal / builders_scaled_msps | exits and scale stories | `"acquires" "<city>" managed services provider <year>`; `"grew" "from $" "to $" MSP "VP of Sales"` |
| mssp_cyber_sellers / cloud_partner_sellers / var_vendor_sellers / ucaas_b2b_top_producers | adjacent pools | employer + title + award |
| by_company | sweep inside mapped companies | 2–3 searches per company: leadership/team page, "account executive", "President's Club" |
| company_people_seen | names noticed during company mapping | no searches (derived) |
