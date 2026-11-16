"""Shared helpers for Operation Rainmaker scripts.

Pure standard library. Resolves paths relative to the rainmaker/ project root so every
script can be run from anywhere: `python rainmaker/scripts/<script>.py`.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # rainmaker/
SETTINGS_PATH = ROOT / "config" / "settings.json"


def load_settings() -> dict:
    with open(SETTINGS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def path(key: str) -> Path:
    """Resolve a configured path key (see config/settings.json -> paths)."""
    settings = load_settings()
    p = ROOT / settings["paths"][key]
    return p


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


_PUNCT = re.compile(r"[^a-z0-9 ]+")
_SUFFIX = re.compile(r"\b(jr|sr|ii|iii|iv|mba|cissp|pmp|cpa)\b")


def normalize_name(name: str) -> str:
    """Normalize a person name for deduplication.

    Lowercases, strips accents/punctuation, removes common suffixes and credentials,
    and collapses to first + last token (middle names/initials dropped) so that
    "J. Robert Smith, MBA" and "Robert Smith" still collide for manual review.
    """
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = s.lower().replace("’", "'")
    s = s.split(",")[0]  # drop ", MBA" style trailers
    s = _PUNCT.sub(" ", s)
    s = _SUFFIX.sub(" ", s)
    tokens = [t for t in s.split() if len(t) > 1]
    if len(tokens) >= 2:
        tokens = [tokens[0], tokens[-1]]
    return " ".join(tokens)


def normalize_company(name: str) -> str:
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(inc|llc|ltd|corp|corporation|co|company|group|technologies|technology|solutions|it|services)\b", " ", s)
    s = _PUNCT.sub(" ", s)
    return " ".join(s.split())


def get_logger(name: str) -> logging.Logger:
    logs_dir = ROOT / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    fh = logging.FileHandler(logs_dir / "rainmaker.log", encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def checkpoint(phase: str, **stats) -> None:
    """Write a recoverable progress checkpoint (checkpoints/status.json + history)."""
    cp_dir = ROOT / "checkpoints"
    cp_dir.mkdir(parents=True, exist_ok=True)
    status_path = cp_dir / "status.json"
    history_path = cp_dir / "history.jsonl"
    record = {"phase": phase, "at": now_iso(), **stats}
    existing = {}
    if status_path.exists():
        try:
            existing = json.loads(status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    existing.setdefault("phases", {})[phase] = record
    existing["last_update"] = record["at"]
    status_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    with open(history_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def read_json(p: Path):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def ensure_dirs() -> None:
    s = load_settings()
    for key, rel in s["paths"].items():
        p = ROOT / rel
        if key in ("db", "dashboard"):
            p.parent.mkdir(parents=True, exist_ok=True)
        else:
            p.mkdir(parents=True, exist_ok=True)
