# Standard verification brief (one candidate)

You are verifying a sales candidate for Ironguard IT (Carlsbad, CA MSP). Budget: at most N web searches (default 4).

Goal: confirm or refute, with URLs and verbatim quotes, (1) current title and employer, (2) public location, (3) the
specific performance claims already captured, (4) any new third-party evidence of net-new production, awards,
territory building or leadership, (5) any disqualifier (not a sales role, junior, out of comp band, stale data).

Rules: real sources only; classify each item VERIFIED / INFERRED / UNKNOWN / UNVERIFIED CLAIM; never infer residence
from employer HQ; no personal contact data; never state the person is unhappy or looking. Score the seven dimensions
0–10 only where evidence supports it (else null); give evidence_confidence (0–1), recruitability (0–10), concerns,
biggest unknown, recommended next action. Output the verification JSON schema in README.md and save it to
data/raw/verify/<slug>.json with research_status "verified" (or "deep_dive" when 8+ sources were read, or "rejected").
