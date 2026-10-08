"""Summary the deals job reads before picking a theme: recent themes and
titles, plus every ASIN already used (so it never repeats one).

  python tools/recent_deals.py        last 14 days
  python tools/recent_deals.py 30     last 30 days
"""
import json
import sys
from pathlib import Path

import own_photos

DATA = Path(__file__).resolve().parent.parent / "deals" / "data"

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    # morning (<date>.json) and afternoon (<date>-b.json) roundups
    files = sorted(f for f in DATA.glob("????-??-??*.json") if f.stem[:10].count("-") == 2)[-2 * days:]
    print(f"RECENT ROUNDUPS (last {len(files)}):")
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        names = ", ".join(p.get("short_name") or p["name"] for p in d.get("products", []))
        slot = " (afternoon)" if d.get("slot") else ""
        alt = f" / {d['pin_title_alt']}" if d.get("pin_title_alt") else ""
        print(f"{d['date']}{slot} | {d['theme']} | {d['pin_title']}{alt} | {names}")
    exclude = DATA / "exclude.txt"
    used = exclude.read_text(encoding="utf-8").split() if exclude.exists() else []
    print(f"\nASINS ALREADY USED ({len(used)}) - never reuse these:")
    print(" ".join(used))
    fam = own_photos.available()
    print(f"\nFAMILY PHOTOS AVAILABLE ({len(fam)}) - products we own, photographed by us:")
    print("\n".join(fam) if fam else "(none)")
