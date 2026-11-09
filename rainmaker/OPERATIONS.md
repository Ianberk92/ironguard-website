# Operations Manual — continuing, maintaining and expanding the search

## 1. Daily / weekly operating loop

1. **Discover**: run a research round (Claude Code agents, or a human researcher) that writes
   `data/raw/r<N>/<modality>.json` files in the discovery schema (README.md).
2. **Ingest**: `python3 scripts/ingest.py --run-id r<N>` (deduplicates by normalized name + company; flags
   same-name/different-company records for review in `possible_duplicate_of`).
3. **Triage**: open `data/exports/candidates.csv`; set `research_status` for weak leads to `rejected`
   (SQL below) and pick the next batch to verify.
4. **Verify**: for each candidate chosen, produce a verification record in `data/raw/verify/` (schema in
   README). The verification prompt in `research/prompts/verify_candidate.md` is the standard brief.
5. **Score and publish**: `./scripts/run_pipeline.sh` (ingest → score → export → dashboard → qa).
6. **Decide**: review `reports/06_rankings.md` and the dashboard; update `recruiting_priority`,
   `outreach_approval_status`, `contact_status`, `interview_status` as decisions are made.

Useful SQL (`sqlite3 data/rainmaker.db`):
```sql
UPDATE candidates SET research_status='rejected', next_action='none' WHERE id IN (12, 15);
UPDATE candidates SET outreach_approval_status='approved', contact_status='queued' WHERE id=3;
SELECT id, full_name, current_company, rank_overall, evidence_confidence FROM candidates ORDER BY rank_overall LIMIT 20;
```
Every status change you want tracked can be logged with
`INSERT INTO status_log(candidate_id, field, old_value, new_value, changed_at, changed_by) VALUES (...)`.

## 2. Research freshness

- `last_verified` is stamped on ingest/verification; records older than `freshness_days` (90) are flagged
  `stale_flag=1` on every ingest and surface on the dashboard under "needing further diligence".
- Titles, employers and locations should be re-validated before any outreach, because public profiles lag.

## 3. Continuous improvement

- `search_log` records every query, modality and whether it was productive. `SELECT modality, SUM(productive), COUNT(*) FROM search_log GROUP BY modality` shows which patterns pay off.
- `sources.candidates_yielded` ranks source URLs by how many candidates they produced.
- After each batch, update `config/settings.json → search.weekly_query_templates` with the patterns that worked
  and retire the dead ends (research/02_methodology_lessons.md keeps the running notes).
- The ingest step merges repeated discoveries of the same person instead of creating new work; a candidate is
  re-researched only when a verification run is explicitly requested.

## 4. Recurring discovery (what exists vs. what is configured)

**Delivered and tested locally:**
- `python3 scripts/weekly_discovery.py --plan` builds the week's query plan (new-candidate discovery, award
  watch, role-change watch at Tier 1–2 target companies, re-validation of the top 20 and stale records) and a
  ready-to-run research prompt in `checkpoints/weekly_prompt_<date>.md`.
- `python3 scripts/weekly_discovery.py --report` builds `reports/weekly_intel_<date>.md` from database deltas
  (new candidates, status changes, awards, new companies, current top 10, stale records).

**Not configured (requires the CEO's approval because it consumes Claude usage / runs unattended):**
- A scheduled Claude Code task (Claude.ai → scheduled tasks, or `claude -p` under cron) that executes the
  weekly prompt. Proposed definition in `config/schedule.json`. To enable: run the prompt interactively once,
  confirm the output quality, then create the scheduled task with the cron expression in that file.
- No paid data APIs are integrated. `research/03_optional_integrations.md` lists options, pricing and
  expected benefit; nothing has been purchased.

Honest statement: nothing runs after this session ends unless a scheduled task is created.

## 5. Expanding the search

- Add a modality: append a key to `config/settings.json → search.modalities`, write the brief in
  `research/prompts/discovery_modalities.md`, run it, drop the JSON in the next `data/raw/r<N>/`.
- Add a geography: extend `geography.tier1/tier2` in settings; `ingest.py` re-tiers on the next run.
- Change weights: edit `weights` and `sensitivity_scenarios`; `score.py` recomputes everything and `qa.py`
  checks consistency.

## 6. Repository hygiene (public repo)

`rainmaker/.gitignore` excludes `data/`, `candidates/`, `reports/`, `outreach/`, `dashboard/*.html`, `logs/`,
`checkpoints/` and `sources/`. Before any commit run `git status --porcelain rainmaker/` and confirm no file
naming a real candidate is staged. Preferred fix: move `rainmaker/` to a private repository.

## 7. Backup

The whole working state is `data/rainmaker.db` plus `data/raw/`. Zip and store those two in a private
location after each session; everything else is regenerable with `scripts/run_pipeline.sh`.
