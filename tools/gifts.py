"""Christmas gift picks from our Awin merchants -> photo pins for the "Christmas Gift Ideas UK" board.

Same design and flow as candles.py (whose pin, page and feed helpers this reuses), but for
several merchants. Each run picks one new product per merchant, writing:
  deals/gifts/<id>/photo.jpg, pin.jpg, index.html
and appends to deals/data/gifts.json; the board's RSS feed is deals/gifts/feed.xml.

Scribbler is mostly greeting cards (many rude), so only its gift products are used.
Dean Morris Cards is joined but not featured: its range is mostly crude novelty items and its
feed images 404.

Usage:
  python tools/gifts.py --pick [YYYY-MM-DD] [--afternoon]
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
YEAR_TAG = 2026

XMAS = re.compile(r"christmas|xmas|festive|santa|advent|stocking|snow|winter|fir\b|firelight|reindeer|elf\b", re.I)
RUDE = re.compile(r"\b(fuck\w*|cunt\w*|shit\w*|knobs?|arse\w*|bums?|gusset|twat\w*|wank\w*|dicks?|cocks?|tits|bollock\w*|piss\w*|sex\w*)\b", re.I)


CLOTHING = re.compile(r"\b(jumper|sweater|hoodie|t-?shirt|socks?|hat|beanie|scarf|gloves|pyjamas?|apron|tea towel)\b", re.I)
SIZED = re.compile(r"[-–]\s*(xs|s|sml|m|med|l|lrg|xl|xxl)\s*$", re.I)   # clothing size codes: "Jumper-S", "Socks - Med"


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
    # skip clothing and merch: each size is a separate feed item ("Santa Jumper-S", "-MED", "-LRG"), and
    # Cadbury's strength is chocolate gifts
    if CLOTHING.search(name) or SIZED.search(name):
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


def scribbler(r):
    # most of the feed is greeting cards (many rude); only the "Gift Giving" products are gifts
    title = r["title"].strip()
    if r.get("availability") != "in_stock" or r.get("google_product_category") != "Arts & Entertainment > Party & Celebration > Gift Giving":
        return None
    if re.search(r"\bcard\b|gift bag|wrap|\btags?\b|badge|ribbon|tissue|voucher|personalis|photo upload|balloon|insult", title, re.I):
        return None
    if price_of(r["price"]) < 8:
        return None
    text = f"{title} {r.get('description', '')}"
    kind = ("Game" if re.search(r"\bgame\b|dobble|puzzle", text, re.I) else
            "Soft Toy" if re.search(r"jellycat|plush|soft toy", title, re.I) else
            "Chocolate Gift" if re.search(r"chocolate|chocolonely|sweets", text, re.I) else
            "Novelty Light" if re.search(r"\blight\b|lamp", text, re.I) else
            "Mug" if re.search(r"\bmug\b", title, re.I) else "Gift Idea")
    brand = re.sub(r"\s+(Ltd|DS)$", "", (r.get("brand") or "").strip()) or "Scribbler"
    name = re.sub(rf"^{re.escape(brand)}\s+", "", title, flags=re.I) if brand != "Scribbler" else title
    return {"brand": brand, "name": name, "kind": kind, "price": price_of(r["price"]), "image": r["image_link"],
            "url": r["aw_deep_link"], "blurb": clean(r.get("description")), "id": f"scr-{r['id']}"}


BR_XMAS = re.compile(r"christmas|xmas|festive|santa|reindeer|\belf\b|elves|snowm[ae]n|gingerbread|advent|nativity|"
                     r"bauble|stocking|nutcracker|robin|penguin|polar bear|snowflake|christmas tree|winter wonderland", re.I)
BR_NOT = re.compile(r"mother'?s day|father'?s day|easter|valentine|halloween|autumn|birthday|bulk|class pack|"
                    r"value pack|teacher|school", re.I)


def baker_ross(r):
    # kids' Christmas crafts and stocking fillers; the feed carries a "was" price (product_price_old)
    name, cat = r["product_name"].strip(), r.get("merchant_category", "")
    if re.search(r"\((Pack|Box) of|\(Per kit\)", name):             # "... (Pack of 6) Christmas Crafts, All In One Kit" -> "... (Pack of 6)"
        name = re.sub(r"\)\s.*$", ")", name)
    # Christmas words in the product's own name (not just the shop's category or a "Christmas Crafts" suffix),
    # and only kits, decorations and toys - not plain craft supplies like card packs or glue dots
    if r.get("in_stock") != "1" or price_of(r["search_price"]) < 2.5 or not BR_XMAS.search(name):
        return None
    if not (cat.startswith(("Craft Kits", "Toys")) or "Decoration" in cat) or BR_NOT.search(name):
        return None
    kind = ("Kids' Christmas Craft Kit" if cat.startswith("Craft Kits") else
            "Christmas Stocking Filler" if cat.startswith("Toys") else "Christmas Craft Supplies")
    return {"brand": "Baker Ross", "name": name, "kind": kind, "price": price_of(r["search_price"]),
            "image": r.get("merchant_image_url") or r.get("aw_image_url"), "url": r["aw_deep_link"],
            "blurb": clean(r.get("description")), "id": f"br-{r['aw_product_id']}", "xmas": True}


MERCHANTS = [
    # (advertiser id, feed format in the Awin feed list, shop name shown on the pin, parser)
    ("736", "Awin", "Cadbury Gifts Direct", cadbury),
    ("30533", "Awin", "Bare Kind", barekind),
    ("101517", "Google", "Scottish Fine Soaps", scottish_fine_soaps),
    ("3965", "Google", "Scribbler", scribbler),
    ("1902", "Awin", "Baker Ross", baker_ross),
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
    import drip
    import home
    e = lambda s: html.escape(str(s), quote=True)
    items, dates = [], []
    pr = home.prices()
    live = [m for m in manifest if drip.released(m)]          # pins come out through the day (drip.py)
    for n, m in enumerate(sorted(live, key=lambda m: (m["date"], m.get("release", ""), m["id"]), reverse=True)[:100]):
        url = f"{SITE}/{m['id']}/"
        pin = OUT / m["id"] / "pin.jpg"
        when = drip.pub_date(m, datetime.fromisoformat(m["date"]).replace(hour=10 + 3 * (n % 4), tzinfo=timezone.utc))
        dates.append(when)
        price = (pr.get(home.raw_id(m["id"])) or {}).get("price") or m.get("price")
        hook = drip.under(price)
        # keyword-first titles, like the pins that rank in Pinterest search
        title = f"{m['name']} | {m['kind']} UK" + (f" {hook}" if hook else "")
        if len(title) > 100:
            title = f"{m['name'][:60]} | {m['kind']}"[:100]
        tag = "#" + re.sub(r"\W", "", m["brand"]).lower()
        desc = (f"{m['kind']} from {m['brand']}" + (f", {hook.lower()}" if hook else "") + ". "
                f"{candles.first_sentence(m['blurb'], 260)} A {m['label'].lower()} idea from {m['shop']}. "
                f"#ad #christmasgifts #giftideas #christmasgiftideasuk #stockingfillers {tag}")[:500]
        items.append(f"<item><title>{e(title)}</title><link>{url}</link><guid isPermaLink=\"true\">{url}</guid>"
                     f"<pubDate>{format_datetime(when)}</pubDate><description>{e(desc)}</description>"
                     f"<enclosure url=\"{url}pin.jpg\" length=\"{pin.stat().st_size if pin.exists() else 0}\" type=\"image/jpeg\"/>"
                     f"<media:content url=\"{url}pin.jpg\" medium=\"image\" type=\"image/jpeg\" width=\"1000\" height=\"1500\"/></item>")
    # collage roundup pins (collages.py), released through the day like the product pins
    cfile = MANIFEST.parent / "collages.json"
    for c in sorted((json.loads(cfile.read_text(encoding="utf-8")) if cfile.exists() else []),
                    key=lambda c: c.get("release", c["date"]), reverse=True)[:40]:
        pin = OUT.parent / "lists" / c["id"] / "pin.jpg"
        if not pin.exists() or not drip.released(c):
            continue
        url = f"https://dailydealsuk.co.uk/deals/lists/{c['id']}/"
        when = drip.pub_date(c, datetime.fromisoformat(c["date"]).replace(hour=12, tzinfo=timezone.utc))
        dates.append(when)
        desc = (f"{c['title']}: {c['sub'].lower()}. Hand-picked Christmas gift ideas from UK shops, with prices. "
                f"#ad {c['tags']} #christmasgiftideasuk #giftguide")[:500]
        items.append(f"<item><title>{e(c['title'] + ' ' + str(YEAR_TAG))}</title><link>{url}</link><guid isPermaLink=\"true\">{url}</guid>"
                     f"<pubDate>{format_datetime(when)}</pubDate><description>{e(desc)}</description>"
                     f"<enclosure url=\"{url}pin.jpg\" length=\"{pin.stat().st_size}\" type=\"image/jpeg\"/>"
                     f"<media:content url=\"{url}pin.jpg\" medium=\"image\" type=\"image/jpeg\" width=\"1000\" height=\"1500\"/></item>")
    # voucher-code / offer pins from the same gift shops (made by vouchers.py), while they're still live
    vfile = MANIFEST.parent / "vouchers.json"
    now = datetime.now(timezone.utc)
    for v in (json.loads(vfile.read_text(encoding="utf-8")) if vfile.exists() else []):
        pin = OUT.parent / "vouchers" / "pins" / f"{v['id']}.jpg"
        if not pin.exists() or (v.get("end") and datetime.fromisoformat(v["end"]) < now):
            continue
        url = f"https://dailydealsuk.co.uk/deals/vouchers/?v={v['id']}#v{v['id']}"
        img = f"https://dailydealsuk.co.uk/deals/vouchers/pins/{v['id']}.jpg"
        when = datetime.fromisoformat(v.get("added") or v.get("start") or now.isoformat())
        dates.append(when)
        title = (f"{v['merchant']} voucher code: {v['title']}" if v.get("code") else f"{v['merchant']} offer: {v['title']}")[:100]
        desc = (f"{v['title']}. " + (f"Use code {v['code']} at {v['merchant']}. " if v.get("code") else f"No code needed at {v['merchant']}. ")
                + "Check the end date and terms before you buy. #ad #vouchercodes #christmasdeals #giftideas")[:500]
        items.append(f"<item><title>{e(title)}</title><link>{url}</link><guid isPermaLink=\"true\">{url}</guid>"
                     f"<pubDate>{format_datetime(when)}</pubDate><description>{e(desc)}</description>"
                     f"<enclosure url=\"{img}\" length=\"{pin.stat().st_size}\" type=\"image/jpeg\"/>"
                     f"<media:content url=\"{img}\" medium=\"image\" type=\"image/jpeg\" width=\"1000\" height=\"1500\"/></item>")
    (OUT / "feed.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel>'
        f"<title>Daily Deals UK - Christmas Gift Ideas</title><link>{SITE}/</link><description>Christmas gift picks.</description>"
        # lastBuildDate = newest pin, so the hourly feed refresh only changes the file when a pin is released
        f"<language>en-gb</language><lastBuildDate>{format_datetime(max(dates) if dates else datetime.now(timezone.utc))}</lastBuildDate>"
        + "".join(items) + "</channel></rss>\n", encoding="utf-8")


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else []


# pins per shop per day, split over the 07:00 run (slot "a", the larger half) and the 15:00 run (slot "b")
DAILY = {"Cadbury Gifts Direct": 3, "Bare Kind": 2, "Scottish Fine Soaps": 1, "Scribbler": 2, "Baker Ross": 2}
REPEAT_AFTER_DAYS = 21       # a product can be pinned again (as a fresh pin) once its last pin is this old


def per_run(shop, slot):
    n = DAILY.get(shop, 1)
    return (n + 1) // 2 if slot == "a" else n // 2


def pick(day, slot="a"):
    manifest = load_manifest()
    if any(m["date"] == day.isoformat() and m.get("slot", "a") == slot for m in manifest):
        print(f"Gifts already picked for {day} ({'afternoon' if slot == 'b' else 'morning'})")
        return 0
    last, times = {}, {}
    for m in manifest:
        k = (m["shop"], m["dedupe"])
        last[k] = max(last.get(k, ""), m["date"])
        times[k] = times.get(k, 0) + 1
    listing = feed_list()
    rnd = random.Random(day.isoformat() + slot)
    picks = []
    import merchant_health
    paused = merchant_health.paused_ids()
    for adv, fmt, shop, parse in MERCHANTS:
        want = per_run(shop, slot)
        if not want:
            continue
        if int(adv) in paused:
            print(f"  {shop}: paused (merchant health), skipped")
            continue
        cands = []
        for p in merchant_products(listing, adv, fmt, shop, parse):
            k = (shop, p["dedupe"])
            if k in last and (day - Date.fromisoformat(last[k])).days < REPEAT_AFTER_DAYS:
                continue
            if k in times:                                  # a repeat: new id, so it's a fresh pin and page
                p["id"] = f"{p['id']}-r{times[k] + 1}"
            p["_repeat"] = k in times
            cands.append(p)
        rnd.shuffle(cands)
        # never-pinned products first, then Christmas ones first, then the longest since their last pin
        cands.sort(key=lambda p: (p["_repeat"], 0 if p.get("xmas") or XMAS.search(p["name"] + " " + p["blurb"]) else 1,
                                  last.get((shop, p["dedupe"]), "")))
        picks += cands[:want]
    for p in picks:
        p.pop("_repeat", None)
        p["label"] = label_for(p)
        publish(p)
        import drip
        manifest.append({**p, "date": day.isoformat(), "slot": slot, "release": drip.release(day, slot, p["id"])})
    MANIFEST.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    write_feed(manifest)
    print(f"Gifts: {len(picks)} pick(s) for {day} {'afternoon' if slot == 'b' else 'morning'}: "
          + "; ".join(f"{p['shop']}: {p['name']}" for p in picks))
    return 0


def main(argv):
    if len(argv) >= 2 and argv[1] == "--pick":
        args = [a for a in argv[2:] if a != "--afternoon"]
        return pick(Date.fromisoformat(args[0]) if args else Date.today(), "b" if "--afternoon" in argv else "a")
    if len(argv) == 3 and argv[1] == "--render":
        publish(next(m for m in load_manifest() if m["id"] == argv[2]))
        write_feed(load_manifest())
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
