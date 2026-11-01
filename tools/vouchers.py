"""Voucher codes and offers from our joined Awin merchants (Awin promotions API), for the site.

Runs before each build (07:00 and 15:00) and writes deals/data/vouchers.json:
  [{id, merchant, merchant_id, type ("voucher" has a code, "promotion" doesn't), title, description,
    code, terms, start, end, url (tracked affiliate link)}]
Skips merchants paused by merchant_health, offers not valid in the UK, and anything already ended.
Without the Awin API token (e.g. on the laptop) it leaves the existing file alone.

It also makes a Pinterest pin for each gift-shop offer (deals/vouchers/pins/<id>.jpg) and adds them to the
Christmas Gift Ideas board feed (deals/gifts/feed.xml). Breeze (travel eSIM) offers aren't pinned there.

  python tools/vouchers.py
  python tools/vouchers.py --pins-only     redraw missing pins and the feed from the saved list (no API call)
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
PINS = ROOT / "deals" / "vouchers" / "pins"
PAGE = "https://dailydealsuk.co.uk/deals/vouchers/"
NOT_GIFTS = ("breeze",)          # merchants whose offers don't belong on the Christmas gifts board


def pinnable(v):
    return not v["merchant"].lower().startswith(NOT_GIFTS)


GENERIC = {"off", "save", "christmas", "gift", "gifts", "candle", "candles", "more", "with", "code", "your",
           "free", "delivery", "selected", "sale", "orders", "order", "over", "when", "spend", "items", "range"}


def merchant_photo(v):
    """A product photo we already have that matches the offer (e.g. a WoodWick candle for "20% off WoodWick"),
    or None: an unrelated product from the same shop would mislead people."""
    import home
    words = {w for w in re.findall(r"[a-z]{4,}", v["title"].lower()) if w not in GENERIC}
    if not words:
        return None
    for name, folder in (("candles.json", "candles"), ("gifts.json", "gifts")):
        items = [m for m in home.load(name) if (m.get("shop") or "Candles Direct").lower().startswith(v["merchant"].lower()[:8])]
        for m in sorted(items, key=lambda m: m["date"], reverse=True):
            text = f"{m.get('brand', '')} {m.get('name', '')}".lower()
            ph = ROOT / "deals" / folder / str(m["id"]) / "photo.jpg"
            if ph.exists() and all(w in text for w in words):
                return ph
    return None


def end_date(v):
    """Fixed date for the pin ("Ends 5 Nov"): pins stay up for months, so never "in 4 days"."""
    if not v.get("end"):
        return "While stocks last"
    d = datetime.fromisoformat(v["end"])
    return f"Ends {d.day} {d:%b}"


def make_pin(v, out):
    """Offer pin in the site's blue style: shop + offer headline, product photo, code ticket, end date."""
    from PIL import Image, ImageDraw, ImageOps
    import build_deals as bd
    W, H, M = 1000, 1500, 60
    img = Image.new("RGB", (W, H), bd.BLUE)
    dr = ImageDraw.Draw(img)
    bd.pill(dr, M, 60, ("VOUCHER CODE" if v.get("code") else "OFFER") + " · " + v["merchant"].upper())
    f_title, lines = bd.fit(dr, v["title"], bd.FONT_HEAVY, W - 2 * M, 4, 84, 52)
    y = 160
    for ln in lines:
        dr.text((M, y), ln, font=f_title, fill="white")
        y += int(f_title.size * 1.1)
    y += 30
    photo = merchant_photo(v)
    ticket_h = 300
    ph_bottom = H - 180 - ticket_h - 40
    if ph_bottom - y > 220:
        dr.rounded_rectangle([M, y, W - M, ph_bottom], radius=28, fill="white")
        if photo:
            pic = Image.open(photo).convert("RGB")
            pic.thumbnail((W - 2 * M - 40, ph_bottom - y - 40))
            img.paste(pic, ((W - pic.width) // 2, y + (ph_bottom - y - pic.height) // 2))
        else:
            # no matching product photo: a big saving badge instead
            pct = re.search(r"\d+\s?%", v["title"])
            big = f"SAVE {pct.group(0).replace(' ', '')}" if pct else ("CODE" if v.get("code") else "OFFER")
            cy = (y + ph_bottom) // 2
            f_big, _ = bd.fit(dr, big, bd.FONT_HEAVY, W - 2 * M - 120, 1, 170, 80)
            dr.text((W // 2, cy - 30), big, font=f_big, fill=bd.RED, anchor="mm")
            dr.text((W // 2, cy + f_big.size // 2 + 20), "at " + v["merchant"], font=bd.font(bd.FONT_BOLD, 46),
                    fill=bd.INK_BLUE, anchor="mm")
    # the "ticket" with the code (or "no code needed") and the end date
    t0 = H - 180 - ticket_h
    dr.rounded_rectangle([M, t0, W - M, t0 + ticket_h], radius=28, fill="white")
    for x in range(M + 30, W - M - 30, 28):                    # dashed tear line
        dr.line([x, t0 + 190, x + 14, t0 + 190], fill=bd.SOFT, width=4)
    if v.get("code"):
        dr.text((W // 2, t0 + 52), "USE CODE", font=bd.font(bd.FONT_BOLD, 32), fill=bd.INK_BLUE, anchor="mm")
        f_code, _ = bd.fit(dr, v["code"], bd.FONT_HEAVY, W - 2 * M - 80, 1, 92, 48)
        dr.text((W // 2, t0 + 122), v["code"], font=f_code, fill=bd.RED, anchor="mm")
    else:
        dr.text((W // 2, t0 + 95), "No code needed", font=bd.font(bd.FONT_HEAVY, 64), fill=bd.INK_BLUE, anchor="mm")
    dr.text((W // 2, t0 + 245), end_date(v) + " · at " + v["merchant"], font=bd.font(bd.FONT_BOLD, 38),
            fill=bd.RED, anchor="mm")
    bd.footer(dr, W, H, M, "Tap for the offer")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=88, optimize=True)


def pins(items):
    made = 0
    for v in items:
        out = PINS / f"{v['id']}.jpg"
        if pinnable(v) and not out.exists():
            make_pin(v, out)
            made += 1
    import gifts
    gifts.write_feed(gifts.load_manifest())
    return made


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


def main(argv=()):
    sys.stdout.reconfigure(encoding="utf-8")
    if "--pins-only" in argv:
        items = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
        print(f"Voucher pins: {pins(items)} new")
        return 0
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
                    "url": p.get("urlTracking") or p.get("url"), "added": p.get("dateAdded") or p.get("startDate")})
    # codes first, then offers ending soonest
    out.sort(key=lambda v: (v["type"] != "voucher", v["end"] or "9999"))
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Vouchers: {len(out)} live ({sum(v['type'] == 'voucher' for v in out)} with codes) from "
          f"{len({v['merchant'] for v in out})} merchant(s); {pins(out)} new pin(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
