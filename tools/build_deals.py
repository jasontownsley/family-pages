"""Build the Daily Deals UK site from deals/data/*.json.

For each day's data file this renders:
  deals/<date>/index.html   roundup page with affiliate links
  deals/<date>/pin.jpg      1000x1500 Pinterest pin image
  deals/<date>/pin2.jpg     second roundup pin (top 3) when the data has pin_title_alt
  deals/<date>/spot/<ASIN>.jpg  single-product photo pins for the first few
                            products with a photo_query (photo from Pexels, see
                            photos.py; no photo means no single pin)
and then deals/index.html (archive), deals/feed.xml (RSS for Pinterest
auto-publish) and deals/data/exclude.txt (ASINs already used).

Usage:
  python tools/build_deals.py               build everything
  python tools/build_deals.py --check FILE  validate one data file only
"""
import html
import json
import re
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

import home
import own_photos
import photos

SITE_URL = "https://dailydealsuk.co.uk/deals"
BRAND = "Daily Deals UK"
TAG = "dailydeal07d1-21"
DISCLOSURE = "As an Amazon Associate I earn from qualifying purchases."
FEED_ITEMS = 60      # roundup + single-product pins, newest first
SPOTLIGHTS = 5      # single-product pins per day
# Paused 2026-09-25: stock photos rarely look like the product (e.g. a bedroom for a
# lamp). Days that already have photos keep their pins; no new photos are fetched
# until real product images are available (Awin feeds).
# Stock photos are only used when the deals job has LOOKED at the candidates and
# approved one (photo_id); unchecked photo_query matches are never used.
FETCH_NEW_PHOTOS = True

ROOT = Path(__file__).resolve().parent.parent
DEALS = ROOT / "deals"
DATA = DEALS / "data"
LEGACY_PAGE = ROOT / "pinterest" / "index.html"

GREEN, GREEN_DARK = "#146C43", "#0E4F31"
ORANGE, GOLD = "#E8562F", "#E6C77E"
INK, PAPER = "#17251C", "#F7F5EF"
# pin style from 2026-10-09: bright blue (green above kept for the older product pins)
BLUE, BLUE_DARK = "#0678FF", "#0052CC"
RED, INK_BLUE, SOFT = "#D0021B", "#14213D", "#CFE3FF"

FONT_DIR = Path("C:/Windows/Fonts")
FONT_HEAVY = FONT_DIR / "ariblk.ttf"
FONT_BOLD = FONT_DIR / "segoeuib.ttf"
FONT_SEMI = FONT_DIR / "seguisb.ttf"

ASIN_RE = re.compile(r"^B0[A-Z0-9]{8}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------- validation

def validate(d, name="data"):
    """Return a list of problems with one day's data (empty list = OK)."""
    errs = []
    req = {"date": str, "theme": str, "pin_title": str, "pin_description": str, "products": list}
    for k, t in req.items():
        if not isinstance(d.get(k), t):
            errs.append(f"{name}: '{k}' missing or not a {t.__name__}")
    if errs:
        return errs
    if not DATE_RE.match(d["date"]):
        errs.append(f"{name}: date must be YYYY-MM-DD")
    if d.get("slot") not in (None, "b"):
        errs.append(f"{name}: slot must be \"b\" (afternoon run) or left out")
    if len(d["pin_title"]) > 100:
        errs.append(f"{name}: pin_title over 100 chars")
    alt = d.get("pin_title_alt")
    if alt is not None and (not isinstance(alt, str) or not 10 <= len(alt) <= 100 or alt == d["pin_title"]):
        errs.append(f"{name}: pin_title_alt must be a different title of 10-100 chars")
    if len(d["pin_description"]) > 500:
        errs.append(f"{name}: pin_description over 500 chars")
    prods = d["products"]
    if not 3 <= len(prods) <= 10:
        errs.append(f"{name}: need 3-10 products, got {len(prods)}")
    seen = set()
    for i, p in enumerate(prods, 1):
        for k in ("asin", "name", "headline", "why", "category"):
            if not isinstance(p.get(k), str) or not p[k].strip():
                errs.append(f"{name}: product {i} missing '{k}'")
        a = p.get("asin", "")
        if not ASIN_RE.match(a):
            errs.append(f"{name}: product {i} ASIN '{a}' looks wrong")
        if a in seen:
            errs.append(f"{name}: product {i} ASIN {a} repeated")
        q = p.get("photo_query")
        if q is not None and (not isinstance(q, str) or len(q) > 80):
            errs.append(f"{name}: product {i} photo_query must be a short string")
        pid = p.get("photo_id")
        if pid is not None and not (isinstance(pid, int) or (isinstance(pid, str) and pid.isdigit())):
            errs.append(f"{name}: product {i} photo_id must be a Pexels photo number")
        op = p.get("own_photo")
        if op is not None and (not isinstance(op, str) or not op.strip()):
            errs.append(f"{name}: product {i} own_photo must be a filename")
        seen.add(a)
    return errs


def load_days():
    days = []
    for f in sorted(DATA.glob("????-??-??*.json")):   # day files only (not candles.json)
        d = json.loads(f.read_text(encoding="utf-8"))
        errs = validate(d, f.name)
        if errs:
            raise SystemExit("Invalid data:\n  " + "\n  ".join(errs))
        days.append(d)
    return sorted(days, key=key, reverse=True)


def key(d):
    """Folder / URL / data-file name: the date, plus "-b" for the afternoon roundup."""
    return d["date"] + (f"-{d['slot']}" if d.get("slot") else "")


def aff(asin):
    return f"https://www.amazon.co.uk/dp/{asin}?tag={TAG}"


# ---------------------------------------------------------------- pin image

def font(path, size):
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default(size)


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=fnt) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def fit(draw, text, path, width, max_lines, start, smallest):
    """Largest font size (stepping down) at which text fits in max_lines."""
    for size in range(start, smallest - 1, -4):
        f = font(path, size)
        lines = wrap(draw, text, f, width)
        if len(lines) <= max_lines:
            return f, lines
    f = font(path, smallest)
    return f, wrap(draw, text, f, width)[:max_lines]


def pill(dr, x, y, text, size=34):
    f = font(FONT_BOLD, size)
    w = dr.textlength(text, font=f)
    dr.rounded_rectangle([x, y, x + w + 44, y + 58], radius=29, fill=RED)
    dr.text((x + 22, y + 29), text, font=f, fill="white", anchor="lm")


def footer(dr, W, H, M, cta):
    dr.rectangle([0, H - 150, W, H], fill=BLUE_DARK)
    dr.text((M, H - 95), BRAND.upper(), font=font(FONT_HEAVY, 46), fill="white", anchor="lm")
    dr.text((W - M, H - 95), cta, font=font(FONT_SEMI, 32), fill=SOFT, anchor="rm")


def photo_card(img, src, box, num=None):
    """Photo inside a white rounded frame, with an optional red number badge."""
    x0, y0, x1, y1 = box
    dr = ImageDraw.Draw(img)
    dr.rounded_rectangle(box, radius=28, fill="white")
    pad = 14
    ph = ImageOps.fit(Image.open(src).convert("RGB"), (x1 - x0 - 2 * pad, y1 - y0 - 2 * pad), method=Image.LANCZOS)
    mask = Image.new("L", ph.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, *ph.size], radius=18, fill=255)
    img.paste(ph, (x0 + pad, y0 + pad), mask)
    if num is not None:
        r = 30
        dr.ellipse([x0 + 26, y0 + 26, x0 + 26 + 2 * r, y0 + 26 + 2 * r], fill=RED)
        dr.text((x0 + 26 + r, y0 + 26 + r), str(num), font=font(FONT_HEAVY, 34), fill="white", anchor="mm")


def make_pin(d, out):
    """Roundup pin: blue header, up to 2 approved photos, numbered list in a white card."""
    W, H, M = 1000, 1500, 60
    img = Image.new("RGB", (W, H), BLUE)
    dr = ImageDraw.Draw(img)
    pill(dr, M, 60, d["theme"].upper())
    # keep the title to 3 lines where possible so the list has room; 4 only if needed
    f_title, lines = fit(dr, d["pin_title"], FONT_HEAVY, W - 2 * M, 3, 76, 60)
    if len(wrap(dr, d["pin_title"], f_title, W - 2 * M)) > 3:
        f_title, lines = fit(dr, d["pin_title"], FONT_HEAVY, W - 2 * M, 4, 60, 48)
    y = 150
    for ln in lines:
        dr.text((M, y), ln, font=f_title, fill="white")
        y += int(f_title.size * 1.1)
    if d.get("pin_hook"):
        f_hook = font(FONT_SEMI, 36)
        y += 10
        for ln in wrap(dr, d["pin_hook"], f_hook, W - 2 * M)[:2]:
            dr.text((M, y), ln, font=f_hook, fill=SOFT)
            y += 48
    y += 25

    # photo row: only photos already approved for this day (own or checked Pexels)
    prods = d["products"]
    photos_dir = out.parent / "photos"
    shots = [(i, photos_dir / f"{p['asin']}.jpg") for i, p in enumerate(prods, 1)
             if (photos_dir / f"{p['asin']}.jpg").exists()][:2]
    if shots:
        gap, ph_h = 24, 300
        cw = (W - 2 * M - gap * (len(shots) - 1)) // len(shots)
        for k, (num, src) in enumerate(shots):
            x = M + k * (cw + gap)
            photo_card(img, src, (x, y, x + cw, y + ph_h), num)
        y += ph_h + 24

    # numbered list in a white card
    top, bottom = y, H - 180
    dr.rounded_rectangle([M, top, W - M, bottom], radius=28, fill="white")
    items = prods[:8]
    step = (bottom - top - 30) / len(items)
    r = int(min(26, step * 0.36))
    f_num, f_item = font(FONT_HEAVY, int(r * 1.2)), font(FONT_BOLD, min(40, int(step * 0.48)))
    for i, p in enumerate(items, 1):
        cy = int(top + 15 + step * (i - 0.5))
        dr.ellipse([M + 30, cy - r, M + 30 + 2 * r, cy + r], fill=RED)
        dr.text((M + 30 + r, cy), str(i), font=f_num, fill="white", anchor="mm")
        ln = wrap(dr, p.get("short_name") or p["name"], f_item, W - 2 * M - 130)
        text = ln[0] if len(ln) == 1 else ln[0].rstrip(",;:-") + "…"
        dr.text((M + 56 + 2 * r, cy), text, font=f_item, fill=INK_BLUE, anchor="lm")
    more = len(prods) - len(items)
    footer(dr, W, H, M, f"+{more} more inside · tap to see" if more else "Tap for the full list")

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=88, optimize=True)


def make_top3_pin(d, out):
    """Second roundup pin: the top 3 picks as big cards (photo where approved), alternative title."""
    W, H, M = 1000, 1500, 60
    img = Image.new("RGB", (W, H), BLUE)
    dr = ImageDraw.Draw(img)
    pill(dr, M, 60, "TOP 3 · " + d["theme"].upper())
    f_title, lines = fit(dr, d["pin_title_alt"], FONT_HEAVY, W - 2 * M, 3, 76, 52)
    y = 150
    for ln in lines:
        dr.text((M, y), ln, font=f_title, fill="white")
        y += int(f_title.size * 1.1)
    y += 30
    photos_dir = out.parent / "photos"
    top, bottom, gap = y, H - 180, 22
    ch = (bottom - top - 2 * gap) // 3
    f_name, f_head = font(FONT_HEAVY, 40), font(FONT_SEMI, 32)
    for i, p in enumerate(d["products"][:3], 1):
        y0 = top + (i - 1) * (ch + gap)
        src = photos_dir / f"{p['asin']}.jpg"
        tx = M + 40
        if src.exists():
            photo_card(img, src, (M, y0, M + ch, y0 + ch), i)
            dr.rounded_rectangle([M + ch + 16, y0, W - M, y0 + ch], radius=28, fill="white")
            tx = M + ch + 46
        else:
            dr.rounded_rectangle([M, y0, W - M, y0 + ch], radius=28, fill="white")
            r = 34
            dr.ellipse([M + 30, y0 + ch // 2 - r, M + 30 + 2 * r, y0 + ch // 2 + r], fill=RED)
            dr.text((M + 30 + r, y0 + ch // 2), str(i), font=font(FONT_HEAVY, 40), fill="white", anchor="mm")
            tx = M + 130
        tw = W - M - 30 - tx
        name = wrap(dr, p.get("short_name") or p["name"], f_name, tw)[:2]
        head = wrap(dr, p["headline"], f_head, tw)[:2]
        block = 48 * len(name) + 10 + 40 * len(head)
        ty = y0 + (ch - block) // 2
        for ln in name:
            dr.text((tx, ty), ln, font=f_name, fill=INK_BLUE)
            ty += 48
        ty += 10
        for ln in head:
            dr.text((tx, ty), ln, font=f_head, fill="#4A5578")
            ty += 40
    more = len(d["products"]) - 3
    footer(dr, W, H, M, f"+{more} more picks · tap to see" if more > 0 else "Tap for the full list")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=88, optimize=True)


def make_spot_pin(p, photo, credit, out):
    """Single-product pin: framed photo on top, hook and product name below."""
    W, H, M, PH = 1000, 1500, 60, 860
    img = Image.new("RGB", (W, H), BLUE)
    photo_card(img, photo, (M, 50, W - M, PH))
    dr = ImageDraw.Draw(img)
    pill(dr, M + 30, 80, p["category"].upper(), 30)

    f_credit = font(FONT_SEMI, 20)
    ctext = "Our own photo" if credit.get("own") else f"Photo: {credit['photographer']} / Pexels"
    cw = dr.textlength(ctext, font=f_credit)
    dr.rounded_rectangle([W - M - cw - 40, PH - 56, W - M - 14, PH - 22], radius=10, fill=(0, 0, 0))
    dr.text((W - M - cw - 27, PH - 39), ctext, font=f_credit, fill="white", anchor="lm")

    # hook + product name, centred in the blue panel
    f_head, lines = fit(dr, p["headline"], FONT_HEAVY, W - 2 * M, 3, 72, 50)
    lh = int(f_head.size * 1.12)
    f_name = font(FONT_BOLD, 40)
    y = PH + (H - 150 - PH - (lh * len(lines) + 74)) // 2
    for ln in lines:
        dr.text((M, y), ln, font=f_head, fill="white")
        y += lh
    dr.text((M, y + 24), wrap(dr, p.get("short_name") or p["name"], f_name, W - 2 * M)[0], font=f_name, fill=SOFT)
    footer(dr, W, H, M, "Tap for details")

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=88, optimize=True)


def used_photo_ids():
    ids = set()
    for f in DEALS.glob("*/photos.json"):
        ids |= {c["id"] for c in json.loads(f.read_text(encoding="utf-8")).values() if not c.get("own")}
    return ids


def spotlights(d):
    """[(product, credit)] for this day's single-product pins, fetching photos as needed."""
    folder = DEALS / key(d)
    cfile = folder / "photos.json"
    credits = json.loads(cfile.read_text(encoding="utf-8")) if cfile.exists() else {}
    # family photos first (always allowed), then Pexels photos if enabled
    picks = [p for p in d["products"] if p.get("own_photo")]
    picks += [p for p in d["products"] if p.get("photo_id") and not p.get("own_photo")]
    picks = picks[:SPOTLIGHTS]
    changed = False
    for p in picks:
        photo = folder / "photos" / f"{p['asin']}.jpg"
        if p["asin"] in credits and photo.exists():
            continue
        if p.get("own_photo"):
            credit = own_photos.prepare(p["own_photo"], photo, p["asin"])
        elif FETCH_NEW_PHOTOS:
            credit = photos.fetch_id(p["photo_id"], photo, p.get("photo_query", ""))
        else:
            continue
        if credit:
            credits[p["asin"]] = credit
            changed = True
    if changed:
        cfile.write_text(json.dumps(credits, indent=1), encoding="utf-8")
    return [(p, credits[p["asin"]]) for p in picks if p["asin"] in credits]


def spot_title(p):
    return f"{p.get('short_name') or p['name']}: {p['headline']}"[:100]


def spot_description(d, p):
    tags = [t for t in re.findall(r"#\w+", d["pin_description"]) if t != "#ad"][:4]
    return f"{p['headline']}. {p['why']} One of today's {d['theme']} picks. #ad {' '.join(tags)}"[:500]


# ---------------------------------------------------------------- HTML

CSS = """
:root{--bg:#F3F6FC;--surface:#fff;--text:#14213D;--dim:#5B6178;--brand:#0678FF;
--brand-soft:#E3EEFF;--accent:#D0021B;--border:#DCE4F2}
@media (prefers-color-scheme:dark){:root{--bg:#0B1220;--surface:#131C2E;--text:#EAF0FA;
--dim:#9AA6BC;--brand:#4C9BFF;--brand-soft:#16264A;--accent:#FF4D5E;--border:#26324A}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font-family:'Poppins',system-ui,sans-serif;line-height:1.55}
.wrap{max-width:760px;margin:0 auto;padding:24px 16px 64px}
header a{color:var(--brand);font-weight:600;text-decoration:none}
h1{font-family:'Archivo Black',sans-serif;font-size:clamp(28px,6vw,42px);line-height:1.1;margin:12px 0}
.theme{display:inline-block;background:var(--accent);color:#fff;border-radius:99px;padding:3px 14px;
font-size:13px;font-weight:600;letter-spacing:.04em;text-transform:uppercase}
.intro{color:var(--dim)}.disc{font-size:13px;color:var(--dim);border-left:3px solid var(--accent);padding-left:10px}
.item{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:18px 20px;margin:16px 0;
display:grid;grid-template-columns:44px 1fr;gap:4px 14px}
.num{grid-row:span 4;width:40px;height:40px;border-radius:50%;background:var(--accent);color:#fff;
font-family:'Archivo Black',sans-serif;display:grid;place-items:center}
.item h2{font-size:19px;margin:0}.name{color:var(--dim);font-size:14px;margin:0}.item p{margin:4px 0}
.item:target{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent)}
.cat{font-size:12px;font-weight:600;color:var(--brand);text-transform:uppercase;letter-spacing:.05em}
.btn{justify-self:start;background:var(--brand);color:#fff;text-decoration:none;font-weight:600;
padding:9px 16px;border-radius:10px;margin-top:6px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px}
.grid a{color:inherit;text-decoration:none}.grid img{width:100%;border-radius:12px;display:block}
.grid span{display:block;font-weight:600;margin-top:6px}.grid small{color:var(--dim)}
footer{margin-top:40px;font-size:13px;color:var(--dim)}
"""

HEAD = """<!doctype html><html lang="en-GB"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><meta name="description" content="{desc}">
<meta property="og:type" content="article"><meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}"><meta property="og:image" content="{image}">
<meta property="og:url" content="{url}"><meta name="pinterest-rich-pin" content="true">
<link rel="alternate" type="application/rss+xml" title="{brand}" href="{site}/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Poppins:wght@400;600&display=swap" rel="stylesheet">
<style>{css}</style></head><body><div class="wrap">"""

FOOT = """<footer><p>{disc}</p><p>Products are picked from well-reviewed UK listings.
Prices and availability change often, so always check the current price on Amazon before buying.</p>
<p>&copy; {year} {brand}</p></footer></div></body></html>"""


def e(s):
    return html.escape(str(s), quote=True)


def pretty_date(iso):
    dt = datetime.strptime(iso, "%Y-%m-%d")
    return f"{dt.day} {dt:%B %Y}"


def day_page(d, spots=()):
    url = f"{SITE_URL}/{key(d)}/"
    out = [HEAD.format(title=e(d["pin_title"]), desc=e(d["pin_description"]),
                       image=f"{url}pin.jpg", url=url, brand=e(BRAND), site=SITE_URL, css=CSS)]
    out.append(f'<header><a href="{SITE_URL}/">&larr; {e(BRAND)}</a></header>')
    out.append(f'<span class="theme">{e(d["theme"])}</span>')
    out.append(f'<h1>{e(d["pin_title"])}</h1>')
    out.append(f'<p class="intro">{e(d.get("intro") or d["pin_description"])}</p>')
    out.append(f'<p class="disc">{e(DISCLOSURE)} Links below are affiliate links (#ad).</p>')
    for i, p in enumerate(d["products"], 1):
        out.append(
            f'<div class="item" id="{e(p["asin"])}"><div class="num">{i}</div>'
            f'<span class="cat">{e(p["category"])}</span>'
            f'<h2>{e(p["headline"])}</h2><p class="name">{e(p["name"])}</p>'
            f'<p>{e(p["why"])}</p>'
            f'<a class="btn" href="{aff(p["asin"])}" rel="sponsored nofollow noopener" target="_blank">'
            f'Check today\'s price on Amazon</a></div>')
    out.append(f'<p class="intro">Published {pretty_date(d["date"])}.</p>')
    pex = [c for _, c in spots if not c.get("own")]
    if pex:
        cred = ", ".join(f'<a href="{e(c["page"])}">{e(c["photographer"])}</a>' for c in pex)
        out.append(f'<p class="intro">Pin photos from Pexels: {cred}.</p>')
    out.append(FOOT.format(disc=e(DISCLOSURE), year=d["date"][:4], brand=e(BRAND)))
    return "".join(out)


def index_page(days):
    latest = days[0] if days else None
    desc = "Hand-picked, well-reviewed UK finds for home, kitchen, cleaning and gifts - a new list every day."
    out = [HEAD.format(title=e(f"{BRAND} - daily finds"), desc=e(desc),
                       image=f"{SITE_URL}/{key(latest)}/pin.jpg" if latest else "",
                       url=f"{SITE_URL}/", brand=e(BRAND), site=SITE_URL, css=CSS)]
    out.append(f"<h1>{e(BRAND)}</h1><p class=\"intro\">{e(desc)}</p>")
    out.append(f'<p class="disc">{e(DISCLOSURE)}</p><div class="grid">')
    for d in days:
        out.append(f'<a href="{SITE_URL}/{key(d)}/"><img src="{SITE_URL}/{key(d)}/pin.jpg" '
                   f'alt="{e(d["pin_title"])}" loading="lazy"><span>{e(d["pin_title"])}</span>'
                   f'<small>{pretty_date(d["date"])}</small></a>')
    out.append("</div>")
    out.append(FOOT.format(disc=e(DISCLOSURE), year=datetime.now().year, brand=e(BRAND)))
    return "".join(out)


def feed_item(title, link, desc, img_url, img_path, when):
    return (f"<item><title>{e(title)}</title><link>{link}</link><guid isPermaLink=\"true\">{link}</guid>"
            f"<pubDate>{format_datetime(when)}</pubDate><description>{e(desc)}</description>"
            f"<enclosure url=\"{img_url}\" length=\"{img_path.stat().st_size}\" type=\"image/jpeg\"/>"
            f"<media:content url=\"{img_url}\" medium=\"image\" type=\"image/jpeg\" width=\"1000\" height=\"1500\"/>"
            f"</item>")


def feed(days, spots_by_date):
    items = []
    for d in days:
        k = key(d)
        url = f"{SITE_URL}/{k}/"
        day = datetime.strptime(d["date"], "%Y-%m-%d").replace(hour=14 if d.get("slot") else 8, tzinfo=timezone.utc)
        spots = list(enumerate(spots_by_date.get(k, []), 1))
        for n, (p, _) in reversed(spots):
            items.append(feed_item(spot_title(p), f"{url}#{p['asin']}", spot_description(d, p),
                                   f"{url}spot/{p['asin']}.jpg", DEALS / k / "spot" / f"{p['asin']}.jpg",
                                   day.replace(hour=day.hour + 1 + n)))
        if d.get("pin_title_alt") and (DEALS / k / "pin2.jpg").exists():
            items.append(feed_item(d["pin_title_alt"], f"{url}#top3", d["pin_description"], f"{url}pin2.jpg",
                                   DEALS / k / "pin2.jpg", day.replace(hour=day.hour + 6 if day.hour < 12 else 21)))
        items.append(feed_item(d["pin_title"], url, d["pin_description"], f"{url}pin.jpg",
                               DEALS / k / "pin.jpg", day))
    items = items[:FEED_ITEMS]
    now = format_datetime(datetime.now(timezone.utc))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel>'
            f"<title>{e(BRAND)}</title><link>{SITE_URL}/</link>"
            f"<description>Hand-picked UK finds, a new list every day.</description>"
            f"<language>en-gb</language><lastBuildDate>{now}</lastBuildDate>"
            + "".join(items) + "</channel></rss>\n")


def exclude_list(days):
    used = {p["asin"] for d in days for p in d["products"]}
    if LEGACY_PAGE.exists():
        used |= set(re.findall(r"B0[A-Z0-9]{8}", LEGACY_PAGE.read_text(encoding="utf-8")))
    return "\n".join(sorted(used)) + "\n"


# ---------------------------------------------------------------- main

def main(argv):
    if len(argv) == 3 and argv[1] == "--check":
        errs = validate(json.loads(Path(argv[2]).read_text(encoding="utf-8")), Path(argv[2]).name)
        print("\n".join(errs) or "OK")
        return 1 if errs else 0

    DATA.mkdir(parents=True, exist_ok=True)
    days = load_days()
    spots_by_date = {}
    for d in days:
        folder = DEALS / key(d)
        pin = folder / "pin.jpg"
        src = DATA / f"{key(d)}.json"
        spots = spots_by_date[key(d)] = spotlights(d)   # first, so the roundups can show the photos
        if not pin.exists() or pin.stat().st_mtime < src.stat().st_mtime:
            make_pin(d, pin)
        pin2 = folder / "pin2.jpg"
        if d.get("pin_title_alt") and (not pin2.exists() or pin2.stat().st_mtime < src.stat().st_mtime):
            make_top3_pin(d, pin2)
        for p, credit in spots:
            out = folder / "spot" / f"{p['asin']}.jpg"
            if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
                make_spot_pin(p, folder / "photos" / f"{p['asin']}.jpg", credit, out)
        (folder / "index.html").write_text(day_page(d, spots), encoding="utf-8")
    home.build(days, spots_by_date)          # homepage + category pages
    (DEALS / "feed.xml").write_text(feed(days, spots_by_date), encoding="utf-8")
    (DATA / "exclude.txt").write_text(exclude_list(days), encoding="utf-8")
    nspots = sum(len(v) for v in spots_by_date.values())
    print(f"Built {len(days)} day(s), {nspots} single-product pin(s); latest {days[0]['date'] if days else 'none'}"
          + ("" if photos.api_key() else " [no Pexels key: single-product pins off]"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
