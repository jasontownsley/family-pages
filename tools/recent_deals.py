"""Summary the deals job reads before picking a theme: recent themes and
titles, plus every ASIN already used (so it never repeats one).

  python tools/recent_deals.py        last 14 days
  python tools/recent_deals.py 30     last 30 days
"""
import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "deals" / "data"

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    files = sorted(DATA.glob("????-??-??.json"))[-days:]
    print(f"RECENT ROUNDUPS (last {len(files)}):")
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        names = ", ".join(p.get("short_name") or p["name"] for p in d.get("products", []))
        print(f"{d['date']} | {d['theme']} | {d['pin_title']} | {names}")
    exclude = DATA / "exclude.txt"
    used = exclude.read_text(encoding="utf-8").split() if exclude.exists() else []
    print(f"\nASINS ALREADY USED ({len(used)}) - never reuse these:")
    print(" ".join(used))
