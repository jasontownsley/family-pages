"""Merchant health: pause merchants that are offline or behind on paying, resume them when they recover.

Runs on the server before each 07:00 build (deals_post.ps1):
  - Awin API: each joined merchant's link status (online/offline) and programme status.
  - ClaudeJobs\\merchant_exposure.json: Awin payment "Exposure Level" per merchant. The API doesn't expose it,
    so the weekly Monday check reads it in the Awin website and saves it here.
A merchant is PAUSED (no new pins or picks) if its links are offline, it is not active, or its Exposure Level is 4.
Writes ClaudeJobs\\merchant_health.json and prints any change since the last run.

  python tools/merchant_health.py
  python tools/merchant_health.py --is-paused 13560      (exit code 0 = paused)
"""
import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import awin_status as aw

JOBS = Path(r"C:\Users\User\ClaudeJobs")
HEALTH = JOBS / "merchant_health.json"
EXPOSURE = JOBS / "merchant_exposure.json"
BAD_LEVEL = 4

# merchants we chose not to apply to because of payment risk; reported when they recover
WATCHLIST = {24593: "Chelsea Peers NYC", 122718: "PLUSH", 125742: "Threadbare UK", 1969: "Interflora",
             34627: "Lindt UK", 82077: "PartyLite UK", 20680: "Imagine Experiences"}


def details(adv):
    url = f"https://api.awin.com/publishers/{aw.PUBLISHER}/programmedetails?advertiserId={adv}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {aw.token()}", "User-Agent": "DailyDealsUK/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def paused_ids():
    """Merchant ids currently paused (used by the pin pickers)."""
    if not HEALTH.exists():
        return set()
    return {int(k) for k, v in json.loads(HEALTH.read_text(encoding="utf-8"))["merchants"].items() if v.get("paused")}


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8")
    if len(argv) == 3 and argv[1] == "--is-paused":
        return 0 if int(argv[2]) in paused_ids() else 1
    exposure = json.loads(EXPOSURE.read_text(encoding="utf-8")) if EXPOSURE.exists() else {}
    levels = exposure.get("levels", {})
    old = json.loads(HEALTH.read_text(encoding="utf-8"))["merchants"] if HEALTH.exists() else {}
    out = {}
    for p in aw.programmes("joined"):
        adv = p["id"]
        try:
            info = details(adv)["programmeInfo"]
            link = info.get("linkStatus", "unknown")
        except Exception as e:
            link = f"unknown ({str(e)[:40]})"
        level = levels.get(str(adv))
        reasons = []
        if p.get("status") not in (None, "Active"):
            reasons.append(f"programme {p.get('status')}")
        if link == "offline":
            reasons.append("tracking links offline")
        if level is not None and int(level) >= BAD_LEVEL:
            reasons.append(f"payment Exposure Level {level}")
        out[str(adv)] = {"name": p["name"], "link": link, "level": level, "paused": bool(reasons), "reasons": reasons}
        time.sleep(3.1)                                   # Awin API rate limit
    HEALTH.write_text(json.dumps({"checked": datetime.now().strftime("%Y-%m-%dT%H:%M"),
                                  "exposure_checked": exposure.get("checked"), "merchants": out}, indent=1), encoding="utf-8")
    changes = []
    for k, v in out.items():
        was = old.get(k, {}).get("paused")
        if was is not None and was != v["paused"]:
            changes.append(f"{v['name']}: {'PAUSED (' + ', '.join(v['reasons']) + ')' if v['paused'] else 'RESUMED'}")
    paused = [f"{v['name']} ({', '.join(v['reasons'])})" for v in out.values() if v["paused"]]
    print(f"Merchant health: {len(out)} joined, {len(paused)} paused" + (": " + "; ".join(paused) if paused else "")
          + f". Exposure levels from {exposure.get('checked', 'never')}.")
    if changes:
        print("MERCHANT CHANGES: " + "; ".join(changes))
    good = [f"{n} (now level {levels[str(i)]})" for i, n in WATCHLIST.items() if str(i) in levels and int(levels[str(i)]) <= 2]
    if good:
        print("WATCHLIST RECOVERED, consider applying: " + "; ".join(good))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
