"""Voucher codes and offers from our joined Awin merchants (Awin promotions API), for the site.

Runs before each build (07:00 and 15:00) and writes deals/data/vouchers.json:
  [{id, merchant, merchant_id, type ("voucher" has a code, "promotion" doesn't), title, description,
    code, terms, start, end, url (tracked affiliate link)}]
Skips merchants paused by merchant_health, offers not valid in the UK, and anything already ended.
Without the Awin API token (e.g. on the laptop) it leaves the existing file alone.

  python tools/vouchers.py
"""
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import awin_status as aw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "deals" / "data" / "vouchers.json"


def fetch():
    items, page = [], 1
    while True:
        body = {"filters": {"membership": "joined", "status": "active", "type": "all"},
                "pagination": {"page": page, "pageSize": 200}}
        req = urllib.request.Request(f"https://api.awin.com/publisher/{aw.PUBLISHER}/promotions",
                                     data=json.dumps(body).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {aw.token()}", "Content-Type": "application/json",
                                              "User-Agent": "DailyDealsUK/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.load(r)
        items += d.get("data", [])
        pg = d.get("pagination", {})
        if page * pg.get("pageSize", 200) >= pg.get("total", 0):
            return items
        page += 1


def clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        raw = fetch()
    except SystemExit as e:              # no token on this machine
        print(f"Vouchers: skipped ({e})")
        return 0
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"Vouchers: Awin API unavailable ({str(e)[:80]}), keeping the last list")
        return 0
    try:
        import merchant_health
        paused = merchant_health.paused_ids()
    except Exception:
        paused = set()
    now = datetime.now(timezone.utc)
    out = []
    for p in raw:
        adv = p.get("advertiser", {})
        regions = p.get("regions", {})
        uk = regions.get("all") or any(r.get("countryCode") == "GB" for r in regions.get("list", []))
        end = p.get("endDate")
        if not uk or int(adv.get("id", 0)) in paused or (end and datetime.fromisoformat(end) < now):
            continue
        code = ((p.get("voucher") or {}).get("code") or "").strip()
        title, desc = clean(p.get("title")), clean(p.get("description"))
        out.append({"id": p["promotionId"], "merchant": adv.get("name", "").replace(" UK", ""), "merchant_id": adv.get("id"),
                    "type": "voucher" if code else "promotion", "title": title,
                    "description": "" if desc.lower() == title.lower() else desc, "code": code,
                    "terms": clean(p.get("terms")), "start": p.get("startDate"), "end": end,
                    "url": p.get("urlTracking") or p.get("url")})
    # codes first, then offers ending soonest
    out.sort(key=lambda v: (v["type"] != "voucher", v["end"] or "9999"))
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Vouchers: {len(out)} live ({sum(v['type'] == 'voucher' for v in out)} with codes) from "
          f"{len({v['merchant'] for v in out})} merchant(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
