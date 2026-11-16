"""SQLite schema and connection helpers for the candidate database.

Usage:
  python scripts/db.py init     # create tables (idempotent)
  python scripts/db.py stats    # print table counts and funnel
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, ensure_dirs, get_logger, load_settings, now_iso, path  # noqa: E402

log = get_logger("db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  name_norm TEXT NOT NULL UNIQUE,
  website TEXT, hq_city TEXT, hq_state TEXT, socal_offices TEXT,
  segment TEXT, segment_label TEXT,
  approx_revenue TEXT, revenue_source_url TEXT, employee_band TEXT,
  target_customers TEXT, services TEXT, geographic_presence TEXT,
  sales_org_notes TEXT, sales_strength_indicators TEXT, relevant_sales_roles TEXT,
  why_attractive TEXT, geo_tier TEXT, confidence TEXT,
  source_urls TEXT, people_seen TEXT,
  research_status TEXT DEFAULT 'mapped',
  first_seen TEXT, last_verified TEXT, notes TEXT
);

CREATE TABLE IF NOT EXISTS candidates (
  id INTEGER PRIMARY KEY,
  full_name TEXT NOT NULL,
  name_norm TEXT NOT NULL,
  current_title TEXT, current_company TEXT, company_norm TEXT,
  previous_employers TEXT, location_public TEXT, location_source_url TEXT, geo_tier TEXT,
  years_experience TEXT, what_they_sell TEXT, msp_mssp_experience TEXT, net_new_evidence TEXT,
  segment_experience TEXT, leadership_evidence TEXT, entrepreneurial_evidence TEXT,
  archetype TEXT, public_profile_url TEXT, key_quote TEXT, concerns TEXT,
  discovery_modalities TEXT, confidence_discovery TEXT, notes TEXT,
  research_status TEXT DEFAULT 'discovered',
  recruiting_priority TEXT DEFAULT 'unranked',
  contact_status TEXT DEFAULT 'not_contacted',
  outreach_approval_status TEXT DEFAULT 'not_requested',
  interview_status TEXT DEFAULT 'none',
  next_action TEXT,
  first_seen TEXT, last_verified TEXT, stale_flag INTEGER DEFAULT 0,
  possible_duplicate_of INTEGER,
  verification TEXT,            -- JSON blob from verification stage
  scores TEXT,                  -- JSON: dimension -> 0-10 or null
  score_total REAL, score_low REAL, score_high REAL,
  evidence_confidence REAL, recruitability REAL,
  producer_score REAL, executive_score REAL, overall_score REAL,
  rank_producer INTEGER, rank_executive INTEGER, rank_overall INTEGER,
  UNIQUE(name_norm, company_norm)
);
CREATE INDEX IF NOT EXISTS idx_candidates_name ON candidates(name_norm);

CREATE TABLE IF NOT EXISTS evidence (
  id INTEGER PRIMARY KEY,
  candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  claim TEXT NOT NULL, classification TEXT NOT NULL,
  source_url TEXT, quote TEXT, checked_at TEXT, checked_by TEXT,
  UNIQUE(candidate_id, claim, source_url)
);

CREATE TABLE IF NOT EXISTS awards (
  id INTEGER PRIMARY KEY,
  candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  award TEXT NOT NULL, year TEXT, source_url TEXT,
  UNIQUE(candidate_id, award, source_url)
);

CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY,
  url TEXT NOT NULL UNIQUE,
  source_type TEXT, first_seen TEXT, last_checked TEXT,
  candidates_yielded INTEGER DEFAULT 0, notes TEXT
);

CREATE TABLE IF NOT EXISTS candidate_sources (
  candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  PRIMARY KEY (candidate_id, source_id)
);

CREATE TABLE IF NOT EXISTS search_log (
  id INTEGER PRIMARY KEY,
  run_id TEXT, modality TEXT, query TEXT, productive INTEGER, note TEXT, run_at TEXT,
  UNIQUE(run_id, modality, query)
);

CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY,
  run_id TEXT UNIQUE, started_at TEXT, finished_at TEXT, phase TEXT, stats TEXT
);

CREATE TABLE IF NOT EXISTS status_log (
  id INTEGER PRIMARY KEY,
  candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
  field TEXT, old_value TEXT, new_value TEXT, changed_at TEXT, changed_by TEXT
);
"""


def connect() -> sqlite3.Connection:
    ensure_dirs()
    db_path = path("db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db() -> None:
    conn = connect()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    log.info("database initialized at %s", path("db"))


def stats() -> dict:
    conn = connect()
    out = {}
    for t in ("companies", "candidates", "evidence", "awards", "sources", "search_log", "runs"):
        out[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    out["funnel"] = {
        r["research_status"]: r["n"]
        for r in conn.execute("SELECT research_status, COUNT(*) n FROM candidates GROUP BY research_status")
    }
    out["priority"] = {
        r["recruiting_priority"]: r["n"]
        for r in conn.execute("SELECT recruiting_priority, COUNT(*) n FROM candidates GROUP BY recruiting_priority")
    }
    out["geo_tier"] = {
        str(r["geo_tier"]): r["n"] for r in conn.execute("SELECT geo_tier, COUNT(*) n FROM candidates GROUP BY geo_tier")
    }
    out["stale"] = conn.execute("SELECT COUNT(*) FROM candidates WHERE stale_flag=1").fetchone()[0]
    conn.close()
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "init"
    if cmd == "init":
        init_db()
    elif cmd == "stats":
        init_db()
        print(json.dumps(stats(), indent=2))
    else:
        print(__doc__)
