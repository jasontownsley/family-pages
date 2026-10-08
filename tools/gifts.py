"""Christmas gift picks from our Awin merchants -> photo pins for the "Christmas Gift Ideas UK" board.

Same design and flow as candles.py (whose pin, page and feed helpers this reuses), but for
several merchants. Each run picks one new product per merchant, writing:
  deals/gifts/<id>/photo.jpg, pin.jpg, index.html
and appends to deals/data/gifts.json; the board's RSS feed is deals/gifts/feed.xml.

Dean Morris Cards is joined but not featured: its range is mostly crude novelty items and its
feed images 404.

Usage:
  python tools/gifts.py --pick [YYYY-MM-DD]
  python tools/gifts.py --render ID
"""
import csv
import gzip
import html
import io
import json
import random
import re
import sys
from datetime import date as Date, datetime, timezone
from email.utils import format_datetime
from pathlib import Path

from PIL import Image

import candles

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "deals" / "gifts"
MANIFEST = ROOT / "deals" / "data" / "gifts.json"
SITE = "https://dailydealsuk.co.uk/deals/gifts"

XMAS = re.compile(r"christmas|xmas|festive|santa|advent|stocking|snow|winter|fir\b|firelight|reindeer|elf\b", re.I)
RUDE = re.compile(r"\b(fuck\w*|cunt\w*|shit\w*|knobs?|arse\w*|bums?|gusset|twat\w*|wank\w*|dicks?|cocks?|tits|bollock\w*|piss\w*|sex\w*)\b", re.I)


def clean(text):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"^[A-Z][\w &'-]{2,30}:\s*", "", text.strip())    # "CHRISTMAS GIFT: Send a..." -> "Send a..."
    return re.sub(r"\s+", " ", text).strip()


def price_of(v):
    try:
        return float(str(v).split()[0])
    except (ValueError, IndexError):
        return 0.0


# ---------------------------------------------------------------- merchants

def cadbury(r):
    name, cat = r["product_name"].strip(), r.get("merchant_category", "")
    text = f"{name} {cat}"
    if r.get("in_stock") != "1" or not re.search(r"christmas|hamper|basket|gift box|selection|advent|stocking", text, re.I):
        return None
    if re.search(r"box of \d+|bulk|corporate|easter|valentine|pack of \d+|\(\d+ ?x|^gift box$|sleeve|personalis|your name|message", text, re.I):
        return None
    if price_of(r["search_price"]) < 4:
        return None
    kind = ("Chocolate Hamper" if re.search(r"hamper|basket", text, re.I) else
            "Advent Calendar" if re.search(r"advent", text, re.I) else
            "Selection Box" if re.search(r"selection", text, re.I) else "Christmas Chocolate Gift")
    brand = "Maynards Bassetts" if name.lower().startswith("maynards") else "Cadbury"
    short = re.sub(r"^(Cadbury|Maynards Bassetts)\s+", "", name)
    short = re.sub(r"\s*\([^)]*$", "", short).rstrip(". ")                # drop a cut-off "(Bundle..."
    return {"brand": brand, "name": short, "kind": kind, "price": price_of(r["search_price"]),
            "image": r.get("merchant_image_url") or r.get("large_image"), "url": r["aw_deep_link"],
            "blurb": clean(r.get("description")), "id": f"cgd-{r['aw_product_id']}",
            "xmas": bool(re.search(r"christmas", cat, re.I))}


def barekind(r):
    full = r["product_name"].split("|")[0].strip()
    if r.get("in_stock") == "0" or re.search(r"gift card|voucher", full, re.I):
        return None
    if not re.search(r"gift|box|set|pack|bundle|christmas", full, re.I):
        return None
    name = re.sub(r"\s*Bamboo Socks?\b", "", full).replace("Sock Set", "Set").strip()
    name = re.sub(r"\s+Set$", "", name)
    return {"brand": "Bare Kind", "name": name, "kind": "Bamboo Sock Gift Set", "price": price_of(r["search_price"]),
            "image": r.get("merchant_image_url") or r.get("large_image"), "url": r["aw_deep_link"],
            "blurb": clean(r.get("description")), "id": f"bk-{r['aw_product_id']}", "dedupe": full.lower()}


def scottish_fine_soaps(r):
    title = r["title"].strip()
    if r.get("availability") != "in_stock" or not re.search(r"gift|set|collection|hamper|box", title, re.I):
        return None
    if price_of(r["price"]) < 15:
        return None
    name = re.sub(r"\s+-\s+(Various|\d+\s*(ml|g))$", "", title, flags=re.I).replace("  ", " ")
    kind = "Diffuser Gift Set" if "diffuser" in name.lower() else "Bath & Body Gift Set"
    return {"brand": "Scottish Fine Soaps", "name": name, "kind": kind, "price": price_of(r["price"]),
            "image": r["image_link"], "url": r["aw_deep_link"], "blurb": clean(r.get("description")),
            "id": f"sfs-{r['id']}"}


MERCHANTS = [
    # (advertiser id, feed format in the Awin feed list, shop name shown on the pin, parser)
    ("736", "Awin", "Cadbury Gifts Direct", cadbury),
    ("30533", "Awin", "Bare Kind", barekind),
    ("101517", "Google", "Scottish Fine Soaps", scottish_fine_soaps),
]


def feed_list():
    base = f"https://ui.awin.com/productdata-darwin-download/publisher/{candles.PUBLISHER}/{candles.awin_key()}/1"
    return list(csv.DictReader(io.StringIO(candles.fetch(f"{base}/feedList").decode("utf-8-sig"))))


def merchant_products(listing, adv, fmt, shop, parse):
    url = next((r["URL"] for r in listing if r["Advertiser ID"] == adv and r["Datafeed Format"] == fmt
                and r["Membership Status"] == "active"), None)
    if not url:
        print(f"  {shop}: no active feed")
        return []
    rows = csv.DictReader(io.StringIO(gzip.decompress(candles.fetch(url)).decode("utf-8-sig")))
    out, seen = [], set()
    for r in rows:
        p = parse(r)
        if (not p or not p["image"] or len(p["blurb"]) < 40 or p["blurb"].lower().startswith(p["name"].lower())
                or RUDE.search(p["name"] + " " + p["blurb"])):
            continue
        key = p.pop("dedupe", p["name"].lower())
        if key in seen:
            continue
        seen.add(key)
        p["shop"], p["notes"], p["dedupe"] = shop, [], key
        out.append(p)
    return out


# ---------------------------------------------------------------- pins, pages, feed

def label_for(p):
    if p["kind"] == "Chocolate Hamper":
        return "Christmas hamper"
    if p["price"] < 10 or re.search(r"stocking", p["name"] + p["blurb"], re.I):
        return "Stocking filler"
    return "Christmas gift"


def publish(p):
    folder = OUT / p["id"]
    folder.mkdir(parents=True, exist_ok=True)
    photo = folder / "photo.jpg"
    if not photo.exists():
        Image.open(io.BytesIO(candles.fetch(p["image"]))).convert("RGB").save(photo, "JPEG", quality=90)
    candles.make_pin(p, photo, folder / "pin.jpg", p["label"])
    (folder / "index.html").write_text(candles.page(p, SITE), encoding="utf-8")


def write_feed(manifest):
    e = lambda s: html.escape(str(s), quote=True)
    items = []
    for n, m in enumerate(sorted(manifest, key=lambda m: (m["date"], m["id"]), reverse=True)[:80]):
        url = f"{SITE}/{m['id']}/"
        pin = OUT / m["id"] / "pin.jpg"
        when = datetime.fromisoformat(m["date"]).replace(hour=10 + 3 * (n % 4), tzinfo=timezone.utc)
        title = f"{m['brand']} {m['name']} - {m['kind']}"[:100]
        tag = "#" + re.sub(r"\W", "", m["brand"]).lower()
        desc = (f"{candles.first_sentence(m['blurb'], 300)} A {m['label'].lower()} idea from {m['shop']}. "
                f"#ad #christmasgifts #giftideas #stockingfillers {tag}")[:500]
        items.append(f"<item><title>{e(title)}</title><link>{url}</link><guid isPermaLink=\"true\">{url}</guid>"
                     f"<pubDate>{format_datetime(when)}</pubDate><description>{e(desc)}</description>"
                     f"<enclosure url=\"{url}pin.jpg\" length=\"{pin.stat().st_size if pin.exists() else 0}\" type=\"image/jpeg\"/>"
                     f"<media:content url=\"{url}pin.jpg\" medium=\"image\" type=\"image/jpeg\" width=\"1000\" height=\"1500\"/></item>")
    (OUT / "feed.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel>'
        f"<title>Daily Deals UK - Christmas Gift Ideas</title><link>{SITE}/</link><description>Christmas gift picks.</description>"
        f"<language>en-gb</language><lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>"
        + "".join(items) + "</channel></rss>\n", encoding="utf-8")


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else []


def pick(day):
    manifest = load_manifest()
    if any(m["date"] == day.isoformat() for m in manifest):
        print(f"Gifts already picked for {day}")
        return 0
    used = {(m["shop"], m["dedupe"]) for m in manifest}
    listing = feed_list()
    rnd = random.Random(day.isoformat())
    picks = []
    for adv, fmt, shop, parse in MERCHANTS:
        cands = [p for p in merchant_products(listing, adv, fmt, shop, parse) if (shop, p["dedupe"]) not in used]
        rnd.shuffle(cands)
        cands.sort(key=lambda p: 0 if p.get("xmas") or XMAS.search(p["name"] + " " + p["blurb"]) else 1)   # Christmas first
        if cands:
            picks.append(cands[0])
    for p in picks:
        p["label"] = label_for(p)
        publish(p)
        manifest.append({**p, "date": day.isoformat()})
    MANIFEST.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    write_feed(manifest)
    print(f"Gifts: {len(picks)} pick(s) for {day}: " + "; ".join(f"{p['shop']}: {p['name']}" for p in picks))
    return 0


def main(argv):
    if len(argv) >= 2 and argv[1] == "--pick":
        return pick(Date.fromisoformat(argv[2]) if len(argv) > 2 else Date.today())
    if len(argv) == 3 and argv[1] == "--render":
        publish(next(m for m in load_manifest() if m["id"] == argv[2]))
        write_feed(load_manifest())
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
