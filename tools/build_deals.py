"""Build the Daily Deals UK site from deals/data/*.json.

For each day's data file this renders:
  deals/<date>/index.html   roundup page with affiliate links
  deals/<date>/pin.jpg      1000x1500 Pinterest pin image
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

from PIL import Image, ImageDraw, ImageFont

SITE_URL = "https://jasontownsley.github.io/family-pages/deals"
BRAND = "Daily Deals UK"
TAG = "dailydeal07d1-21"
DISCLOSURE = "As an Amazon Associate I earn from qualifying purchases."
FEED_ITEMS = 30

ROOT = Path(__file__).resolve().parent.parent
DEALS = ROOT / "deals"
DATA = DEALS / "data"
LEGACY_PAGE = ROOT / "pinterest" / "index.html"

GREEN, GREEN_DARK = "#146C43", "#0E4F31"
ORANGE, GOLD = "#E8562F", "#E6C77E"
INK, PAPER = "#17251C", "#F7F5EF"

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
    if len(d["pin_title"]) > 100:
        errs.append(f"{name}: pin_title over 100 chars")
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
        seen.add(a)
    return errs


def load_days():
    days = []
    for f in sorted(DATA.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        errs = validate(d, f.name)
        if errs:
            raise SystemExit("Invalid data:\n  " + "\n  ".join(errs))
        days.append(d)
    return sorted(days, key=lambda d: d["date"], reverse=True)


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


def make_pin(d, out):
    W, H, M = 1000, 1500, 70
    img = Image.new("RGB", (W, H), PAPER)
    dr = ImageDraw.Draw(img)

    # header block sized to fit the title and hook
    f_title, lines = fit(dr, d["pin_title"], FONT_HEAVY, W - 2 * M, 4, 92, 56)
    lh = int(f_title.size * 1.12)
    f_hook = font(FONT_SEMI, 36)
    hook = wrap(dr, d["pin_hook"], f_hook, W - 2 * M)[:2] if d.get("pin_hook") else []
    header_h = 187 + lh * len(lines) + 52 * len(hook) + 45
    dr.rectangle([0, 0, W, header_h], fill=GREEN)

    f_kick = font(FONT_BOLD, 34)
    kicker = d["theme"].upper()
    kw = dr.textlength(kicker, font=f_kick)
    dr.rounded_rectangle([M, 70, M + kw + 44, 70 + 58], radius=29, fill=ORANGE)
    dr.text((M + 22, 99), kicker, font=f_kick, fill="white", anchor="lm")

    y = 170
    for ln in lines:
        dr.text((M, y), ln, font=f_title, fill="white")
        y += lh
    y += 12
    for ln in hook:
        y += 8
        dr.text((M, y), ln, font=f_hook, fill=GOLD)
        y += 44

    # numbered product list
    prods = d["products"][:8]
    top, bottom = header_h + 40, H - 190
    step = (bottom - top) / len(prods)
    r = int(min(32, step * 0.4))
    f_num = font(FONT_HEAVY, int(r * 1.2))
    f_item = font(FONT_BOLD, min(44, int(step * 0.5)))
    for i, p in enumerate(prods, 1):
        cy = int(top + step * (i - 0.5))
        dr.ellipse([M, cy - r, M + 2 * r, cy + r], fill=ORANGE)
        dr.text((M + r, cy), str(i), font=f_num, fill="white", anchor="mm")
        label = p.get("short_name") or p["name"]
        ln = wrap(dr, label, f_item, W - 2 * M - 100)
        text = ln[0] if len(ln) == 1 else ln[0].rstrip(",;:-") + "…"
        dr.text((M + 96, cy), text, font=f_item, fill=INK, anchor="lm")
    more = len(d["products"]) - len(prods)

    # footer
    dr.rectangle([0, H - 150, W, H], fill=GREEN_DARK)
    f_foot = font(FONT_HEAVY, 46)
    f_cta = font(FONT_SEMI, 32)
    dr.text((M, H - 95), BRAND.upper(), font=f_foot, fill=GOLD, anchor="lm")
    cta = f"+{more} more inside · tap to see" if more else "Tap for the full list"
    dr.text((W - M, H - 95), cta, font=f_cta, fill="white", anchor="rm")

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=88, optimize=True)


# ---------------------------------------------------------------- HTML

CSS = """
:root{--bg:#F2F3F9;--surface:#fff;--text:#17251C;--dim:#5B6178;--brand:#146C43;
--brand-soft:#E1EFE7;--accent:#E8562F;--border:#DBDEEC}
@media (prefers-color-scheme:dark){:root{--bg:#0E1410;--surface:#16201A;--text:#EDF3EE;
--dim:#9AAA9F;--brand:#3FAE7C;--brand-soft:#1B3327;--accent:#F0805A;--border:#2A3A30}}
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


def day_page(d):
    url = f"{SITE_URL}/{d['date']}/"
    out = [HEAD.format(title=e(d["pin_title"]), desc=e(d["pin_description"]),
                       image=f"{url}pin.jpg", url=url, brand=e(BRAND), site=SITE_URL, css=CSS)]
    out.append(f'<header><a href="{SITE_URL}/">&larr; {e(BRAND)}</a></header>')
    out.append(f'<span class="theme">{e(d["theme"])}</span>')
    out.append(f'<h1>{e(d["pin_title"])}</h1>')
    out.append(f'<p class="intro">{e(d.get("intro") or d["pin_description"])}</p>')
    out.append(f'<p class="disc">{e(DISCLOSURE)} Links below are affiliate links (#ad).</p>')
    for i, p in enumerate(d["products"], 1):
        out.append(
            f'<div class="item"><div class="num">{i}</div>'
            f'<span class="cat">{e(p["category"])}</span>'
            f'<h2>{e(p["headline"])}</h2><p class="name">{e(p["name"])}</p>'
            f'<p>{e(p["why"])}</p>'
            f'<a class="btn" href="{aff(p["asin"])}" rel="sponsored nofollow noopener" target="_blank">'
            f'Check today\'s price on Amazon</a></div>')
    out.append(f'<p class="intro">Published {pretty_date(d["date"])}.</p>')
    out.append(FOOT.format(disc=e(DISCLOSURE), year=d["date"][:4], brand=e(BRAND)))
    return "".join(out)


def index_page(days):
    latest = days[0] if days else None
    desc = "Hand-picked, well-reviewed UK finds for home, kitchen, cleaning and gifts - a new list every day."
    out = [HEAD.format(title=e(f"{BRAND} - daily finds"), desc=e(desc),
                       image=f"{SITE_URL}/{latest['date']}/pin.jpg" if latest else "",
                       url=f"{SITE_URL}/", brand=e(BRAND), site=SITE_URL, css=CSS)]
    out.append(f"<h1>{e(BRAND)}</h1><p class=\"intro\">{e(desc)}</p>")
    out.append(f'<p class="disc">{e(DISCLOSURE)}</p><div class="grid">')
    for d in days:
        out.append(f'<a href="{SITE_URL}/{d["date"]}/"><img src="{SITE_URL}/{d["date"]}/pin.jpg" '
                   f'alt="{e(d["pin_title"])}" loading="lazy"><span>{e(d["pin_title"])}</span>'
                   f'<small>{pretty_date(d["date"])}</small></a>')
    out.append("</div>")
    out.append(FOOT.format(disc=e(DISCLOSURE), year=datetime.now().year, brand=e(BRAND)))
    return "".join(out)


def feed(days):
    items = []
    for d in days[:FEED_ITEMS]:
        url = f"{SITE_URL}/{d['date']}/"
        img = f"{url}pin.jpg"
        size = (DEALS / d["date"] / "pin.jpg").stat().st_size
        pub = format_datetime(datetime.strptime(d["date"], "%Y-%m-%d").replace(hour=8, tzinfo=timezone.utc))
        items.append(
            f"<item><title>{e(d['pin_title'])}</title><link>{url}</link><guid isPermaLink=\"true\">{url}</guid>"
            f"<pubDate>{pub}</pubDate><description>{e(d['pin_description'])}</description>"
            f"<enclosure url=\"{img}\" length=\"{size}\" type=\"image/jpeg\"/>"
            f"<media:content url=\"{img}\" medium=\"image\" type=\"image/jpeg\" width=\"1000\" height=\"1500\"/>"
            f"</item>")
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
    for d in days:
        folder = DEALS / d["date"]
        pin = folder / "pin.jpg"
        src = DATA / f"{d['date']}.json"
        if not pin.exists() or pin.stat().st_mtime < src.stat().st_mtime:
            make_pin(d, pin)
        (folder / "index.html").write_text(day_page(d), encoding="utf-8")
    (DEALS / "index.html").write_text(index_page(days), encoding="utf-8")
    (DEALS / "feed.xml").write_text(feed(days), encoding="utf-8")
    (DATA / "exclude.txt").write_text(exclude_list(days), encoding="utf-8")
    print(f"Built {len(days)} day(s); latest {days[0]['date'] if days else 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
