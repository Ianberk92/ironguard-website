# Growably (Tech Tribe CRM) setup specification — pre-sale system of record

Decision (acting head of sales, 2026-11-11): Growably is the CRM and marketing-automation system for everything
before signature. HaloPSA stays the system of record after signature (quotes, agreements, onboarding, support).
Growably is included in the Tech Tribe membership, is MSP-specific, and runs on the HighLevel platform (pipelines,
workflows, email and SMS sequences, calendars, forms, API). Revisit at the 90-day checkpoint only if two-way email
logging or reporting proves inadequate; HubSpot Starter is the fallback.

## 1. Pipeline (one pipeline, seven stages)

| Stage | Entry rule | Exit rule | Owner |
|---|---|---|---|
| 1 Target | Account on the ICP list with a trigger note | First meeting booked | CEO / coordinator |
| 2 First meeting | Meeting held (discovery) | Qualified or disqualified | CEO |
| 3 Qualified | Pain + authority + timing confirmed; next step dated | Review sold or environment review scheduled | CEO |
| 4 Insurance Readiness Review / environment review | Fixed-fee Review paid, or review scheduled | Findings presented | CEO + senior engineer |
| 5 Proposal | Written scope and price delivered | Signed / lost | CEO |
| 6 Signed | Agreement signed, onboarding deposit paid | Handed to HaloPSA onboarding | CEO → ops |
| 7 Onboarded | First MRR invoice issued | — | ops |

Lost reasons (required field): price, timing, incumbent stayed, no fit (<25 users), no response, other.

## 2. Contact and opportunity fields (custom)

- Company: users (number), sites (number), platform (Microsoft 365 / Google Workspace / other), industry
  (construction, engineering, technology, professional services, life sciences, other), insurance renewal month,
  incumbent MSP (if known), trigger (renewal, new site, IT person left, MSP complaint, growth, referral), source
  (referral, broker, CPA, Scorecard, website, event, outbound, alumni/network), ICP fit (A/B/C).
- Opportunity: estimated users, estimated MRR (users × $165), Review sold (yes/no), next step, next step date,
  senior engineer assigned, proposal sent date, close date.
- Contact: role (CEO/owner, COO, CFO, IT lead, office manager), decision role (decider, influencer, champion).

## 3. Sequences (email, with one SMS only after a reply or a meeting)

1. **Insurance-renewal sequence** (5 touches over 3 weeks) to every Scorecard taker and past inquiry: the Review
   offer, one underwriter-questions example, one "what is not included" sheet, one case study, one direct ask.
2. **New-site / growth trigger sequence** (4 touches) for target accounts with a site or hiring trigger.
3. **Referral-intro sequence** (2 touches) for people introduced by clients, brokers or CPAs.
4. **Post-meeting follow-up** (manual send, drafted from the Fireflies transcript).
5. **Quiet-period nurture** (monthly, one insight article) for qualified-but-not-now accounts.

Copy rules: short, specific, no stock phrases; always a single ask; always the published pricing link.

## 4. Forms, calendar, automations

- Scorecard and executive-checklist forms post into Growably as contacts with source = Scorecard / lead magnet,
  and trigger sequence 1 automatically.
- Calendar: a 30-minute "working session" booking page (no sales language), synced to the CEO's Microsoft 365
  calendar.
- Automations: new lead → task for CEO within 1 business day; stage change to Qualified → task "schedule Review";
  no activity 14 days on a qualified opportunity → reminder; signed → create HaloPSA onboarding task (manual until
  the integration is proven).

## 5. Reporting (weekly, one page)

Accounts worked, first meetings held, qualified opportunities created, Reviews proposed / sold, proposals sent,
signatures, pipeline value (estimated MRR × 12), against the 30/60/90-day gates in H2. Exported weekly to the
rainmaker system (CSV) until the API sync is configured.

## 6. Integration with the AI chief of staff

Growably exposes the LeadConnector V2 REST API (per Tech Tribe member documentation; confirm in the account).
Phase 1 (now): weekly CSV export from Growably into `data/crm/` and the weekly report script. Phase 2 (after the
90-day checkpoint): API key stored outside the repo (.env), scripts to log Fireflies call notes, create tasks and
update stages automatically. No credentials are ever committed.

## 7. Setup checklist (about two hours, once)

1. Create the pipeline and stages above; delete sample stages.
2. Add the custom fields in section 2.
3. Build the five sequences from the copy in `assessment/sales_sequences.md` (next file to produce).
4. Connect the Scorecard and checklist forms; set source values.
5. Create the booking page; connect the Microsoft 365 calendar.
6. Import the first 100 ICP accounts (CSV from the rainmaker system once Apollo data is attached).
7. Turn on the three automations in section 4.
8. Run the weekly report once with test data; delete the test data.
