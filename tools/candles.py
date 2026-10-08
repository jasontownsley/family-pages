"""Candles Direct picks (Awin product feed) -> single-product photo pins.

Each run picks up to N in-stock candles we haven't featured, favouring the season's
scents, and for each one writes:
  deals/candles/<id>/photo.jpg   merchant product photo (Awin feed image, allowed for promotion)
  deals/candles/<id>/pin.jpg     1000x1500 Pinterest pin
  deals/candles/<id>/index.html  landing page with the Awin tracking link
and appends it to deals/data/candles.json, which build_deals.py adds to feed.xml.

The Awin key is NOT in the repo: env AWIN_KEY or C:\\Users\\User\\ClaudeJobs\\awin_key.txt.

Usage:
  python tools/candles.py --pick [YYYY-MM-DD] [N]   add today's picks (default 3)
  python tools/candles.py --render ID              re-render one pin (design changes)
Feed for its own Pinterest board: deals/candles/feed.xml
"""
import csv
import gzip
import html
import io
import json
import os
import random
import re
import sys
import urllib.request
from datetime import date as Date, datetime, timezone
from email.utils import format_datetime
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "deals" / "candles"
MANIFEST = ROOT / "deals" / "data" / "candles.json"
SITE = "https://dailydealsuk.co.uk/deals/candles"
PUBLISHER, MERCHANT = "3105665", "13560"
KEY_FILE = Path(r"C:\Users\User\ClaudeJobs\awin_key.txt")
UA = {"User-Agent": "Mozilla/5.0 DailyDealsUK/1.0"}

BLUE, BLUE_DEEP, BLUE_DARK = "#0678FF", "#0A3FA8", "#0052CC"
RED, SOFT, GOLD = "#D0021B", "#CFE3FF", "#F5D27A"
FONTS = Path("C:/Windows/Fonts")
SERIF_B, SERIF_I = FONTS / "georgiab.ttf", FONTS / "georgiai.ttf"
HEAVY, BOLD, SEMI = FONTS / "ariblk.ttf", FONTS / "segoeuib.ttf", FONTS / "seguisb.ttf"

# season -> scent words to favour (checked against name + description)
CHRISTMAS = ("Christmas scent", r"christmas|santa|snow|cookie|gingerbread|candy cane|peppermint|cranberry|fir|"
                                 r"pine|balsam|spruce|festive|wonderland|nutmeg|clove|mistletoe|winter|sleigh")
AUTUMN = ("Autumn scent", r"pumpkin|apple|cinnamon|spice|chai|maple|harvest|cosy|cozy|caramel|leaves|fireside|hearth|bonfire")
# date range -> scent families to favour, in order (the label follows the scent that matched)
SEASONS = [
    ((11, 1), (12, 31), [CHRISTMAS, AUTUMN]),
    ((10, 1), (10, 31), [AUTUMN, CHRISTMAS]),
]
TYPES = re.compile(r"jar candle|reed diffuser|gift set|candle$", re.I)


def font(path, size):
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default(size)


def wrap(dr, text, f, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if dr.textlength(trial, font=f) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + ([line] if line else [])


# ---------------------------------------------------------------- feed

def awin_key():
    k = os.environ.get("AWIN_KEY") or (KEY_FILE.read_text().strip() if KEY_FILE.exists() else "")
    if not k:
        raise SystemExit("No Awin key (set AWIN_KEY or create ClaudeJobs\\awin_key.txt)")
    return k


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def feed_rows():
    base = f"https://ui.awin.com/productdata-darwin-download/publisher/{PUBLISHER}/{awin_key()}/1"
    listing = csv.DictReader(io.StringIO(fetch(f"{base}/feedList").decode("utf-8-sig")))
    url = next(r["URL"] for r in listing
               if r["Advertiser ID"] == MERCHANT and r["Datafeed Format"] == "Google")
    text = gzip.decompress(fetch(url)).decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def parse(row):
    """Feed row -> pick dict, or None if it isn't something we'd feature."""
    if row.get("availability") != "in_stock" or not row.get("image_link"):
        return None
    desc = re.sub(r"\s+", " ", row.get("description", ""))
    m = re.search(r"About This Fragrance\s*(.+?)\s*(?:Fragrance Notes|Scent Profile)", desc)
    blurb = m.group(1).strip() if m else ""
    m = (re.search(r"Fragrance Notes:?\s*(.+?)\s*About ", desc)
         or re.search(r"Scent Profile:?\s*(.+?)\s*About ", desc))
    notes = m.group(1) if m else ""
    notes = re.sub(r"(Top|Mid|Heart|Base):\s*", ", ", notes)
    notes = re.sub(r"([a-z])([A-Z])", r"\1, \2", notes)          # "Black CherryBlack" -> split
    notes = [n.strip(" .") for n in notes.split(",") if n.strip(" .")]
    m = re.search(r"About (?:Signature )?([A-Z][A-Za-z ]+?(?:Jar Candles?|Diffusers?|Gift Sets?|Candles?))\b", desc[desc.find("About", 10):])
    kind = (m.group(1) if m else "").strip()
    kind = re.sub(r"s$", "", kind)
    price = float(row["price"].split()[0]) if row.get("price") else 0
    if not blurb or not TYPES.search(kind) or price < 7:
        return None
    return {"id": row["id"], "brand": row["brand"], "name": row["title"].strip(), "kind": kind,
            "blurb": blurb, "notes": notes[:5], "image": row["image_link"],
            "url": row["aw_deep_link"], "price": price}


def first_sentence(text, limit=150):
    s = re.split(r"(?<=[.!?…])\s", text)[0].strip()
    if len(s) > limit:
        s = s[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return s


# ---------------------------------------------------------------- pin

def product_cutout(photo, size):
    """Product photo (white background) fitted into a size x size square."""
    im = Image.open(photo).convert("RGB")
    # trim the white margin so the product fills the card
    bg = Image.new("RGB", im.size, (255, 255, 255))
    box = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 18 else 0).getbbox()
    if box:
        im = im.crop(box)
    im.thumbnail((size, size), Image.LANCZOS)
    return im


def sparkles(img, seed, area, n=18):
    """Soft out-of-focus lights in the background."""
    rnd = random.Random(seed)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = area
    for _ in range(n):
        r = rnd.randint(10, 34)
        x = rnd.choice([rnd.randint(x0, x0 + 260), rnd.randint(x1 - 260, x1)])   # keep to the sides
        y = rnd.randint(y0, y1)
        a = rnd.randint(30, 70)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 214, 140, a))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(9)))


def make_pin(p, photo, out, label):
    W, H, M = 1000, 1500, 64
    # vertical gradient: deep blue at the top to brand blue at the bottom
    grad = Image.linear_gradient("L").resize((W, H))
    img = Image.composite(Image.new("RGBA", (W, H), BLUE), Image.new("RGBA", (W, H), BLUE_DEEP), grad)
    sparkles(img, p["id"], (0, 0, W, 1100))
    dr = ImageDraw.Draw(img)

    # label pill + brand
    f_pill = font(BOLD, 30)
    pw = dr.textlength(label.upper(), font=f_pill)
    dr.rounded_rectangle([M, 56, M + pw + 44, 110], radius=27, fill=RED)
    dr.text((M + 22, 83), label.upper(), font=f_pill, fill="white", anchor="lm")
    f_brand = font(BOLD, 30)
    brand = " ".join(p["brand"].upper())
    dr.text((W - M, 83), brand, font=f_brand, fill=GOLD, anchor="rm")

    # product name (serif) + type
    size = 92
    while size > 56:
        f_name = font(SERIF_B, size)
        lines = wrap(dr, p["name"], f_name, W - 2 * M)
        if len(lines) <= 2:
            break
        size -= 6
    y = 150
    for ln in lines:
        dr.text((M, y), ln, font=f_name, fill="white")
        y += int(size * 1.08)
    dr.text((M, y + 6), p["kind"], font=font(SEMI, 36), fill=SOFT)
    dr.line([M, y + 66, M + 120, y + 66], fill=GOLD, width=4)
    y += 80

    # product on a white card with a soft shadow
    card_top = max(y + 20, 330)
    card_bottom = 1080
    card = (M, card_top, W - M, card_bottom)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([card[0] + 6, card[1] + 22, card[2] - 6, card[3] + 22],
                                             radius=36, fill=(0, 20, 60, 120))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(22)))
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle(card, radius=36, fill="white")
    inner = min(card[2] - card[0], card[3] - card[1]) - 70
    prod = product_cutout(photo, inner)
    img.paste(prod, ((W - prod.width) // 2, card[1] + (card[3] - card[1] - prod.height) // 2))

    # scent description (italic serif) + notes
    f_quote = font(SERIF_I, 38)
    quote = wrap(dr, f"\u201C{first_sentence(p['blurb'], 125)}\u201D", f_quote, W - 2 * M)[:3]
    y = card_bottom + 44
    for ln in quote:
        dr.text((M, y), ln, font=f_quote, fill="white")
        y += 50
    if p["notes"]:
        f_notes = font(SEMI, 28)
        ns = [n.lower() for n in p["notes"][:4]]
        while len(ns) > 1 and dr.textlength("Notes: " + " · ".join(ns), font=f_notes) > W - 2 * M:
            ns.pop()
        dr.text((M, y + 14), "Notes: " + " · ".join(ns), font=f_notes, fill=GOLD)

    # footer
    dr.rectangle([0, H - 130, W, H], fill=BLUE_DARK)
    dr.text((M, H - 65), "DAILY DEALS UK", font=font(HEAVY, 42), fill="white", anchor="lm")
    dr.text((W - M, H - 65), f"Shop at {p.get('shop', 'Candles Direct')} \u203A", font=font(SEMI, 30), fill=SOFT, anchor="rm")

    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out, "JPEG", quality=90, optimize=True)


# ---------------------------------------------------------------- page

def page(p, site=SITE, price=""):
    e = lambda s: html.escape(str(s), quote=True)
    url = f"{site}/{p['id']}/"
    shop = p.get("shop", "Candles Direct")
    title = f"{p['brand']} {p['name']} {p['kind']}"
    notes = ", ".join(p["notes"])
    return f"""<!doctype html><html lang="en-GB"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)} | Daily Deals UK</title>
<meta name="description" content="{e(p['blurb'][:300])}"><meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(p['blurb'][:300])}"><meta property="og:image" content="{url}pin.jpg">
<meta property="og:url" content="{url}"><meta name="pinterest-rich-pin" content="true">
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Poppins:wght@400;600&display=swap" rel="stylesheet">
<style>:root{{--bg:#F2F5FB;--surface:#fff;--text:#14213D;--dim:#5B6178;--brand:#0678FF;--accent:#D0021B;--border:#DBE3F0}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0B1220;--surface:#131C2E;--text:#EAF0FA;--dim:#9AA6BC;--brand:#4C9BFF;--accent:#FF4D5E;--border:#26324A}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:Poppins,system-ui,sans-serif;line-height:1.6}}
.wrap{{max-width:720px;margin:0 auto;padding:24px 16px 64px}}a.home{{color:var(--brand);font-weight:600;text-decoration:none}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:18px;padding:24px;margin-top:16px}}
.card img{{width:100%;max-width:420px;display:block;margin:0 auto 12px;border-radius:12px;background:#fff}}
.brand{{color:var(--accent);font-weight:600;letter-spacing:.08em;text-transform:uppercase;font-size:13px}}
h1{{font-family:'Archivo Black',sans-serif;font-size:clamp(26px,6vw,38px);line-height:1.15;margin:6px 0}}
.kind{{color:var(--dim);margin:0 0 12px}}.notes{{color:var(--dim);font-size:15px}}
.btn{{display:inline-block;background:var(--brand);color:#fff;text-decoration:none;font-weight:600;padding:12px 22px;border-radius:12px;margin-top:10px}}
.disc{{font-size:13px;color:var(--dim);margin-top:28px}}
.price{{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;margin:0 0 4px}}.price strong{{font-size:24px}}.price s{{color:var(--dim)}}.save{{background:var(--accent);color:#fff;font-weight:700;font-size:13px;padding:2px 8px;border-radius:6px}}.oos{{color:var(--accent);font-weight:600}}.pchk{{font-size:12px;color:var(--dim);margin:0 0 12px}}</style></head><body><div class="wrap">
<a class="home" href="https://dailydealsuk.co.uk/deals/">&larr; Daily Deals UK</a>
<div class="card"><img src="photo.jpg" alt="{e(title)}"><span class="brand">{e(p['brand'])}</span>
<h1>{e(p['name'])}</h1><p class="kind">{e(p['kind'])}</p>{price}<p>{e(p['blurb'])}</p>
{f'<p class="notes"><strong>Fragrance notes:</strong> {e(notes)}</p>' if notes else ''}
<a class="btn" href="{e(p['url'])}" rel="sponsored nofollow noopener" target="_blank">See it at {e(shop)}</a></div>
<p class="disc">This is an affiliate link (#ad): we may earn a small commission if you buy, at no extra cost to you.
Prices and stock change often, so check the current price on {e(shop)}.</p></div></body></html>"""


# ---------------------------------------------------------------- RSS (own Pinterest board)

def write_feed(manifest):
    e = lambda s: html.escape(str(s), quote=True)
    items = []
    for n, m in enumerate(sorted(manifest, key=lambda m: m["date"], reverse=True)[:60]):
        url = f"{SITE}/{m['id']}/"
        pin = OUT / m["id"] / "pin.jpg"
        hour = 11 + 4 * (n % 3)                       # spread the day's picks out
        when = datetime.fromisoformat(m["date"]).replace(hour=hour, tzinfo=timezone.utc)
        title = f"{m['brand']} {m['name']} {m['kind']}"[:100]
        tags = "#candles #homefragrance #" + re.sub(r"\W", "", m["brand"]).lower() + (
            " #christmascandles" if "Christmas" in m["label"] else " #autumnvibes" if "Autumn" in m["label"] else "")
        desc = f"{first_sentence(m['blurb'], 300)} Fragrance notes: {', '.join(m['notes'][:4]).lower()}. #ad {tags}"[:500]
        items.append(f"<item><title>{e(title)}</title><link>{url}</link><guid isPermaLink=\"true\">{url}</guid>"
                     f"<pubDate>{format_datetime(when)}</pubDate><description>{e(desc)}</description>"
                     f"<enclosure url=\"{url}pin.jpg\" length=\"{pin.stat().st_size if pin.exists() else 0}\" type=\"image/jpeg\"/>"
                     f"<media:content url=\"{url}pin.jpg\" medium=\"image\" type=\"image/jpeg\" width=\"1000\" height=\"1500\"/></item>")
    (OUT / "feed.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel>'
        f"<title>Daily Deals UK - Candles</title><link>{SITE}/</link><description>Candle and home fragrance picks.</description>"
        f"<language>en-gb</language><lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>"
        + "".join(items) + "</channel></rss>\n", encoding="utf-8")


# ---------------------------------------------------------------- main

def season_for(day):
    for (m0, d0), (m1, d1), fams in SEASONS:
        if (m0, d0) <= (day.month, day.day) <= (m1, d1):
            return [(label, re.compile(words, re.I)) for label, words in fams]
    return []


def label_for(p, fams):
    """(rank, label): which seasonal family the scent belongs to, best first."""
    for i, (label, rx) in enumerate(fams):
        if rx.search(p["name"]) or rx.search(p["blurb"]):
            return i, label
    return len(fams), "Candle of the day"


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else []


def publish(p, label):
    folder = OUT / p["id"]
    folder.mkdir(parents=True, exist_ok=True)
    photo = folder / "photo.jpg"
    if not photo.exists():
        Image.open(io.BytesIO(fetch(p["image"]))).convert("RGB").save(photo, "JPEG", quality=90)
    make_pin(p, photo, folder / "pin.jpg", label)
    (folder / "index.html").write_text(page(p), encoding="utf-8")


def pick(day, n):
    manifest = load_manifest()
    if any(m["date"] == day.isoformat() for m in manifest):
        print(f"Candles already picked for {day}")
        return 0
    used = {(m["brand"], m["name"].lower()) for m in manifest}
    fams = season_for(day)
    cands = [p for p in map(parse, feed_rows()) if p and (p["brand"], p["name"].lower()) not in used]
    seen, uniq = set(), []
    for p in sorted(cands, key=lambda p: -p["price"]):        # one size per scent (largest)
        if (p["brand"], p["name"].lower()) not in seen:
            seen.add((p["brand"], p["name"].lower()))
            uniq.append(p)
    rnd = random.Random(day.isoformat())
    rnd.shuffle(uniq)
    uniq.sort(key=lambda p: label_for(p, fams)[0])
    picks, brands = [], set()
    for p in uniq:                                             # different brands where possible
        if len(picks) < n and (p["brand"] not in brands or len(uniq) < 3 * n):
            picks.append(p)
            brands.add(p["brand"])
    for p in picks:
        label = label_for(p, fams)[1]
        publish(p, label)
        manifest.append({**p, "date": day.isoformat(), "label": label})
    MANIFEST.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    write_feed(manifest)
    print(f"Candles: {len(picks)} pick(s) for {day}: " + "; ".join(f"{p['brand']} {p['name']}" for p in picks))
    return 0


def main(argv):
    if len(argv) >= 2 and argv[1] == "--pick":
        day = Date.fromisoformat(argv[2]) if len(argv) > 2 else Date.today()
        return pick(day, int(argv[3]) if len(argv) > 3 else 3)
    if len(argv) == 3 and argv[1] == "--render":
        p = next(m for m in load_manifest() if m["id"] == argv[2])
        publish(p, p.get("label", "Candle of the day"))
        write_feed(load_manifest())
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
