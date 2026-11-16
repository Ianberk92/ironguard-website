# Optional external integrations (NOT purchased, NOT configured)

The system currently uses only permitted public web research. The following services would materially
improve discovery or verification. Prices are list prices as generally published and must be re-checked;
none has been bought or integrated. Approval required before any spend.

| Service | What it adds | Indicative cost | Expected benefit | Risk / notes |
|---|---|---|---|---|
| LinkedIn Recruiter Lite / Recruiter | Structured search by title, company, geography, tenure; InMail | ~$170/mo (Lite) to ~$10K+/yr (Recruiter) | Highest-yield source for current title/location; removes most "unknown" fields | Terms prohibit scraping; use the UI manually; still verify claims |
| ZoomInfo / Apollo.io / Lusha | Company org charts, title history, verified work emails | Apollo from ~$49/user/mo; ZoomInfo custom (typically $15K+/yr) | Faster role-change detection at target companies | Only collect work emails after outreach is approved; respect CCPA |
| Crunchbase / PitchBook | Acquisition history (who sold their MSP, when) | Crunchbase Pro ~$49/mo; PitchBook enterprise pricing | Better "founder exit" modality | Marginal for this niche |
| Channel Futures MSP 501 / CRN data | Verified revenue bands for MSPs | Free lists; data packs vary | Better target-company revenue sizing | Self-reported data |
| Google Programmable Search / Bing Web Search API | Programmatic query execution for the weekly runner | Google: 100 free queries/day then $5 per 1,000; Bing: tiered from ~$7 per 1,000 | Lets `weekly_discovery.py` run searches without Claude in the loop | Needs an API key stored outside the repo (.env) |
| Reference-check / background services (e.g., Checkr) | Employment verification after offer stage | Per-report pricing (~$30-$80) | Validates tenure claims before hire | Only with candidate consent; FCRA compliance |

Recommended first step if budget is approved: LinkedIn Recruiter Lite for the CEO (manual use), which
addresses the single largest evidence gap (current title and location) at the lowest cost.
