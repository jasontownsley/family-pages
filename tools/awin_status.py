"""Awin programme statuses via the Awin API (no browser, no password).

Token: C:\\Users\\User\\ClaudeJobs\\awin_api_token.txt (or env AWIN_API_TOKEN) - never in the repo.
Remembers the last result in ClaudeJobs\\awin_programmes.json and reports what changed.

  python tools/awin_status.py          print joined / pending / rejected and any changes
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

PUBLISHER = "3105665"
JOBS = Path(r"C:\Users\User\ClaudeJobs")
TOKEN_FILE = JOBS / "awin_api_token.txt"
STATE = JOBS / "awin_programmes.json"
RELATIONSHIPS = ("joined", "pending", "rejected", "suspended", "notjoined_invited")


def token():
    t = os.environ.get("AWIN_API_TOKEN") or (TOKEN_FILE.read_text(encoding="utf-8-sig").strip() if TOKEN_FILE.exists() else "")
    if not t:
        raise SystemExit(f"No Awin API token (create {TOKEN_FILE})")
    return t


def programmes(relationship):
    url = f"https://api.awin.com/publishers/{PUBLISHER}/programmes?relationship={relationship}&countryCode=GB"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token()}", "User-Agent": "DailyDealsUK/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Awin API {relationship}: HTTP {e.code} {e.read()[:200]!r}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    now = {}
    for rel in RELATIONSHIPS:
        try:
            for p in programmes(rel):
                now[str(p["id"])] = {"name": p.get("name", "?"), "status": rel}
        except SystemExit as e:
            if rel in ("joined", "pending"):
                raise
            print(f"({e})")
    before = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    for rel in ("joined", "pending", "rejected", "suspended"):
        names = sorted(v["name"] for v in now.values() if v["status"] == rel)
        print(f"{rel.upper()} ({len(names)}): {', '.join(names) or '-'}")
    changes = [f"{v['name']}: {before[k]['status']} -> {v['status']}" for k, v in now.items()
               if k in before and before[k]["status"] != v["status"]]
    if before:
        print("CHANGES SINCE LAST CHECK: " + ("; ".join(changes) if changes else "none"))
    STATE.write_text(json.dumps(now, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
