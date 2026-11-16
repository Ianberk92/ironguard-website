#!/usr/bin/env python3
"""Keep only one user's data from a Claude organization export (strict version).

Usage (on your Mac):
  python3 filter_claude_export.py <folder-with-zips> user@example.com

- Conversations/projects/artifacts: kept only if OWNED by the user
  (owner-type fields like account/creator/user/owner hold the user's ID).
- User lists and login history: trimmed to the user's own rows.
- Output: <folder>/only_<email>/ (old output is replaced). Originals untouched.
"""
import json, sys, zipfile, pathlib, re, shutil

src = pathlib.Path(sys.argv[1]).expanduser()
email = sys.argv[2].lower()
out = src / f"only_{email}"
if out.exists():
    shutil.rmtree(out)
out.mkdir()

UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
OWNER_KEYS = ("account", "account_uuid", "account_id", "owner_account", "creator", "created_by",
              "creator_uuid", "user", "user_uuid", "user_id", "owner", "owner_uuid")

def load_all():
    for z in sorted(src.glob("*.zip")):
        with zipfile.ZipFile(z) as zf:
            for n in zf.namelist():
                if n.lower().endswith((".json", ".jsonl")):
                    raw = zf.read(n).decode("utf-8", "replace")
                    try:
                        yield z.name, n, json.loads(raw)
                    except json.JSONDecodeError:
                        yield z.name, n, [json.loads(l) for l in raw.splitlines() if l.strip()]

files = list(load_all())

# 1) the user's ID(s): objects whose email field equals the address
ids = set()
def scan(o):
    if isinstance(o, dict):
        if any(isinstance(v, str) and v.lower() == email for v in o.values()):
            for k in ("uuid", "id", "account_uuid", "user_uuid"):
                if isinstance(o.get(k), str) and UUID.fullmatch(o[k]):
                    ids.add(o[k])
        for v in o.values(): scan(v)
    elif isinstance(o, list):
        for v in o: scan(v)
for *_, d in files: scan(d)
print("User IDs found for", email, ":", ids or "NONE")
if not ids:
    sys.exit("No account found with that email.")

def has_id(v):
    s = json.dumps(v).lower()
    return any(i in s for i in ids) or email in s

def owner_fields(rec):
    return {k: rec[k] for k in OWNER_KEYS if k in rec}

def keep_record(rec):
    """True only if this record belongs to the user."""
    if not isinstance(rec, dict):
        return False
    of = owner_fields(rec)
    if of:                                   # has an owner field: must be ours
        return has_id(of)
    if rec.get("uuid") in ids or str(rec.get("email", "")).lower() == email:
        return True                          # the user's own row (users.json etc.)
    return False

def filter_data(d, path_has_id):
    """Lists: keep only the user's records. Dicts: recurse into lists inside."""
    if isinstance(d, list):
        return [r for r in d if keep_record(r)]
    if isinstance(d, dict):
        if keep_record(d) or path_has_id:     # a single file that is the user's own
            return d
        res = {}
        for k, v in d.items():
            if isinstance(v, list):
                kept = [r for r in v if keep_record(r)]
                if kept: res[k] = kept
        return res or None
    return None

total = 0
for zname, member, data in files:
    path_has_id = any(i in member for i in ids)   # e.g. memories/<user-id>.json
    kept = filter_data(data, path_has_id)
    if kept:
        dest = out / zname.replace(".zip", "") / member
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(kept, indent=2, ensure_ascii=False))
        n = len(kept) if isinstance(kept, list) else 1
        total += n
        print(f"{zname}/{member}: kept {n}")
# 3) copy the full folder (every file, any type) of each artifact the user owns
owned = set()
for zname, member, data in files:
    m = re.match(r"artifacts/([0-9a-f-]{36})/artifact\.json$", member)
    if m and isinstance(data, dict) and keep_record(data):
        owned.add(m.group(1))
for z in sorted(src.glob("*.zip")):
    with zipfile.ZipFile(z) as zf:
        for n in zf.namelist():
            m = re.match(r"artifacts/([0-9a-f-]{36})/", n)
            if m and m.group(1) in owned and not n.endswith("/"):
                dest = out / z.name.replace(".zip", "") / n
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(n))
print(f"Artifacts owned by {email}: {len(owned)} (full folders copied)")
print(f"Done. {total} records saved in {out}")
