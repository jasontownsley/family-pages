"""Homepage (deals/index.html) and category pages (deals/c/<slug>/index.html).

Built by build_deals.py on every run from the day files, deals/data/gifts.json and
deals/data/candles.json, so it updates itself each morning and afternoon.
"""
import html
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEALS = ROOT / "deals"
DATA = DEALS / "data"
SITE = "https://dailydealsuk.co.uk/deals"
PINTEREST = "https://uk.pinterest.com/thedailydealsuk/"
DISCLOSURE = ("We earn a small commission if you buy through our links (#ad), at no extra cost to you. "
              "As an Amazon Associate I earn from qualifying purchases.")

# slug, chip label, regex on a roundup's theme + titles, which shop collection to show with it
CATEGORIES = [
    ("christmas", "&#127876; Christmas", r"christmas|xmas|stocking|santa|advent|festive", "gifts"),
    ("halloween", "&#127875; Halloween", r"halloween|spooky|pumpkin", None),
    ("kitchen", "Kitchen", r"kitchen|baking|cook|bakers", None),
    ("cleaning", "Cleaning", r"clean|laundry", None),
    ("beauty", "Beauty", r"beauty|self-care|spa\b|skincare", None),
    ("home", "Home", r"home|organis|storage|cosy|entryway|hallway", None),
    ("gifts", "Gifts", r"gift", "gifts"),
    ("candles", "Candles", r"candle", "candles"),
    ("under-20", "Under &pound;20", r"under £(5|10|15|20)\b", None),
]

e = lambda s: html.escape(str(s), quote=True)


def key(d):
    return d["date"] + (f"-{d['slot']}" if d.get("slot") else "")


def pretty(iso):
    dt = datetime.strptime(iso[:10], "%Y-%m-%d")
    return f"{dt.day} {dt:%B}"


def first_sentence(text, limit=110):
    s = re.split(r"(?<=[.!?…])\s", text or "")[0].strip()
    return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def load(name):
    p = DATA / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


CSS = """
:root{--blue:#0678FF;--deep:#0A3FA8;--dark:#0052CC;--red:#D0021B;--soft:#CFE3FF;--bg:#F3F6FC;--surface:#fff;--text:#14213D;--dim:#5B6178;--border:#DCE4F2}
@media (prefers-color-scheme:dark){:root{--bg:#0B1220;--surface:#131C2E;--text:#EAF0FA;--dim:#9AA6BC;--border:#26324A}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:Poppins,system-ui,sans-serif;line-height:1.55}
a{color:inherit}.wrap{max-width:1120px;margin:0 auto;padding:0 16px}
header.top{background:linear-gradient(180deg,var(--deep),var(--blue));color:#fff;position:relative;overflow:hidden}
header.top:before{content:"";position:absolute;inset:0;background:radial-gradient(circle at 8% 30%,rgba(255,214,140,.35) 0 22px,transparent 23px),radial-gradient(circle at 92% 20%,rgba(255,214,140,.28) 0 30px,transparent 31px),radial-gradient(circle at 85% 75%,rgba(255,214,140,.22) 0 18px,transparent 19px),radial-gradient(circle at 15% 85%,rgba(255,214,140,.2) 0 26px,transparent 27px);filter:blur(6px)}
nav{display:flex;align-items:center;justify-content:space-between;padding:18px 0;position:relative}
.logo{font-family:'Archivo Black',sans-serif;font-size:22px;letter-spacing:.02em;text-decoration:none}
.pin{background:var(--red);color:#fff;text-decoration:none;font-weight:600;padding:9px 16px;border-radius:99px;font-size:14px;white-space:nowrap}
.hero{padding:36px 0 56px;position:relative;max-width:720px}.hero.small{padding:10px 0 48px}
.hero h1{font-family:Georgia,serif;font-size:clamp(34px,6vw,58px);line-height:1.05;margin:0 0 14px}
.hero.small h1{font-size:clamp(30px,5vw,46px)}
.hero p{color:var(--soft);font-size:18px;margin:0 0 22px}
.cta{display:flex;gap:12px;flex-wrap:wrap}.cta a{text-decoration:none;font-weight:600;padding:12px 20px;border-radius:12px}
.cta .a1{background:#fff;color:var(--deep)}.cta .a2{border:2px solid rgba(255,255,255,.6);color:#fff}
.disc{font-size:13px;color:var(--dim);background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:10px 14px;margin:-26px 0 0;position:relative}
.chips{display:flex;gap:8px;overflow-x:auto;padding:22px 0 4px;scrollbar-width:none}
.chips a{flex:none;text-decoration:none;background:var(--surface);border:1px solid var(--border);padding:8px 14px;border-radius:99px;font-weight:500;font-size:14px}
.chips a.on{background:var(--blue);border-color:var(--blue);color:#fff}
section{padding:34px 0 8px}
.sh{display:flex;align-items:flex-end;justify-content:space-between;gap:12px;margin-bottom:16px}
.sh h2{font-family:Georgia,serif;font-size:clamp(24px,4vw,32px);margin:0}.sh p{margin:4px 0 0;color:var(--dim)}
.sh a{color:var(--blue);font-weight:600;text-decoration:none;white-space:nowrap}
.grid{display:grid;gap:18px;grid-template-columns:repeat(auto-fill,minmax(250px,1fr))}
.pcard{background:var(--surface);border:1px solid var(--border);border-radius:18px;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 6px 20px rgba(10,63,168,.06)}
.ph{background:#fff;aspect-ratio:1;position:relative;display:grid;place-items:center;padding:18px}
.ph img{max-width:100%;max-height:100%;object-fit:contain}
.tag{position:absolute;left:12px;top:12px;background:var(--red);color:#fff;font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;padding:4px 10px;border-radius:99px}
.pb{padding:16px 18px 18px;display:flex;flex-direction:column;flex:1}
.brand{font-size:12px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--blue)}
.pb h3{font-family:Georgia,serif;font-size:21px;line-height:1.2;margin:4px 0 2px}.kind{color:var(--dim);font-size:14px;margin:0 0 8px}
.quote{font-family:Georgia,serif;font-style:italic;color:var(--dim);font-size:15px;margin:0 0 14px;flex:1}
.btn{display:inline-block;align-self:flex-start;background:var(--blue);color:#fff;text-decoration:none;font-weight:600;font-size:14px;padding:10px 16px;border-radius:10px}
.band{background:linear-gradient(135deg,var(--deep),var(--blue));color:#fff;border-radius:22px;padding:24px;margin-top:8px}
.band .sh p{color:var(--soft)}.band .sh a{color:#fff}
.rgrid{display:grid;gap:18px;grid-template-columns:repeat(auto-fill,minmax(440px,1fr))}
.rcard{background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:18px;overflow:hidden;display:grid;grid-template-columns:200px 1fr;align-items:start}
.rimg{display:block;padding:12px}.rimg img{width:100%;aspect-ratio:2/3;object-fit:contain;display:block;border-radius:10px}
.rb{padding:16px}.pill{background:var(--red);color:#fff;font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;padding:4px 10px;border-radius:99px}
.rb h3{font-size:17px;line-height:1.3;margin:10px 0 6px}.rb h3 a{text-decoration:none}.rb ol{margin:0 0 12px;padding-left:20px;color:var(--dim);font-size:14px}
.row{display:flex;align-items:center;justify-content:space-between;gap:8px}.date{font-size:13px;color:var(--dim)}
.sgrid{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(190px,1fr))}
.scard{text-decoration:none;background:var(--surface);border:1px solid var(--border);border-radius:16px;overflow:hidden;display:flex;flex-direction:column}
.simg{aspect-ratio:4/5;overflow:hidden;display:block}.simg img{width:100%;height:100%;object-fit:cover}
.scard .cat{font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--red);padding:10px 12px 0}
.scard strong{padding:2px 12px 0;font-size:15px}.scard small{padding:0 12px 12px;color:var(--dim)}
.follow{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;background:var(--surface);border:1px solid var(--border);border-radius:18px;padding:22px;margin:34px 0}
.follow h2{font-family:Georgia,serif;margin:0 0 4px}.follow p{margin:0;color:var(--dim)}
.empty{color:var(--dim)}
footer{background:var(--dark);color:var(--soft);padding:28px 0 40px;margin-top:20px;font-size:14px}footer strong{color:#fff;font-family:'Archivo Black',sans-serif;font-size:18px}
footer a{color:#fff}
@media (max-width:560px){.rgrid{grid-template-columns:1fr}.rcard{grid-template-columns:130px 1fr}.hero p{font-size:16px}.pin span{display:none}}
"""


def head(title, desc, url, image):
    return f"""<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="{image}"><meta property="og:url" content="{url}">
<link rel="alternate" type="application/rss+xml" title="Daily Deals UK" href="{SITE}/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Poppins:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>"""


def topbar(hero):
    return (f'<header class="top"><div class="wrap"><nav><a class="logo" href="{SITE}/">DAILY DEALS UK</a>'
            f'<a class="pin" href="{PINTEREST}" rel="noopener" target="_blank">&#9733; <span>Follow on </span>Pinterest</a></nav>'
            f'{hero}</div></header><main class="wrap"><p class="disc">{e(DISCLOSURE)}</p>')


def chips(active):
    out = [f'<a{" class=on" if active == "" else ""} href="{SITE}/">All</a>']
    for slug, label, _, _ in CATEGORIES:
        out.append(f'<a{" class=on" if active == slug else ""} href="{SITE}/c/{slug}/">{label}</a>')
    return '<div class="chips">' + "".join(out) + "</div>"


def footer():
    return (f'<div class="follow"><div><h2>Never miss a find</h2><p>Follow Daily Deals UK on Pinterest for 10+ new picks every day.</p></div>'
            f'<a class="pin" href="{PINTEREST}" rel="noopener" target="_blank">&#9733; Follow on Pinterest</a></div></main>'
            '<footer><div class="wrap"><strong>DAILY DEALS UK</strong><p>Hand-picked from well-reviewed UK listings. Prices and stock change '
            'often, so always check the current price before buying. Links are affiliate links (#ad): as an Amazon Associate I earn from '
            'qualifying purchases, and we may earn commission from other UK retailers.</p>'
            f'<p>&copy; {datetime.now().year} Daily Deals UK &middot; <a href="{SITE}/feed.xml">RSS</a></p></div></footer></body></html>')


def product_card(p, folder):
    url = f"{SITE}/{folder}/{p['id']}/"
    return (f'<article class="pcard"><a class="ph" href="{url}"><img src="{url}photo.jpg" alt="{e(p["brand"])} {e(p["name"])}" loading="lazy">'
            f'<span class="tag">{e(p["label"])}</span></a><div class="pb"><span class="brand">{e(p["brand"])}</span>'
            f'<h3>{e(p["name"])}</h3><p class="kind">{e(p["kind"])}</p><p class="quote">{e(first_sentence(p["blurb"]))}</p>'
            f'<a class="btn" href="{url}">See it at {e(p.get("shop", "Candles Direct"))} &rsaquo;</a></div></article>')


def roundup_card(d):
    url = f"{SITE}/{key(d)}/"
    items = "".join(f"<li>{e(p.get('short_name') or p['name'])}</li>" for p in d["products"][:7])
    return (f'<article class="rcard"><a class="rimg" href="{url}"><img src="{url}pin.jpg" alt="{e(d["pin_title"])}" loading="lazy"></a>'
            f'<div class="rb"><span class="pill">{e(d["theme"])}</span><h3><a href="{url}">{e(d["pin_title"])}</a></h3><ol>{items}</ol>'
            f'<div class="row"><a class="btn" href="{url}">See the full list &rsaquo;</a><span class="date">{pretty(d["date"])}</span></div></div></article>')


def spot_card(d, p):
    url = f"{SITE}/{key(d)}/"
    return (f'<a class="scard" href="{url}#{p["asin"]}"><span class="simg"><img src="{url}photos/{p["asin"]}.jpg" alt="" loading="lazy"></span>'
            f'<span class="cat">{e(p["category"])}</span><strong>{e(p.get("short_name") or p["name"])}</strong><small>{e(p["headline"])}</small></a>')


def latest(items, n):
    return sorted(items, key=lambda m: (m["date"], m["id"]), reverse=True)[:n]


def matches(d, rx):
    text = " ".join([d["theme"], d["pin_title"], d.get("pin_title_alt", ""), d.get("pin_description", "")])
    return re.search(rx, text, re.I)


def build(days, spots_by_key):
    """days: newest first; spots_by_key: {key: [(product, credit), ...]}"""
    gifts, candles = load("gifts.json"), load("candles.json")
    spots = [(d, p) for d in days for p, _ in spots_by_key.get(key(d), [])
             if (DEALS / key(d) / "photos" / f"{p['asin']}.jpg").exists()][:10]
    latest_pin = f"{SITE}/{key(days[0])}/pin.jpg" if days else ""

    hero = ('<div class="hero"><h1>Hand-picked UK finds &amp; gift ideas, fresh every day</h1>'
            '<p>Well-reviewed home, kitchen, beauty and gift picks from UK shops, plus Christmas gift ideas from brands you love.</p>'
            '<div class="cta"><a class="a1" href="#gifts">&#127876; Christmas gift ideas</a><a class="a2" href="#today">Today\'s finds</a></div></div>')
    out = [head("Daily Deals UK - hand-picked UK finds and gift ideas",
                "Hand-picked, well-reviewed UK finds for home, kitchen, beauty and gifts, plus Christmas gift ideas - new picks every day.",
                f"{SITE}/", latest_pin), topbar(hero), chips("")]
    if gifts:
        out.append(f'<section id="gifts"><div class="sh"><div><h2>&#127876; Christmas Gift Ideas</h2><p>Real products from '
                   f'Cadbury Gifts Direct, Bare Kind, Scottish Fine Soaps and more. New picks daily.</p></div>'
                   f'<a href="{SITE}/c/christmas/">See all &rsaquo;</a></div><div class="grid">'
                   + "".join(product_card(p, "gifts") for p in latest(gifts, 8)) + "</div></section>")
    out.append(f'<section id="today"><div class="band"><div class="sh"><div><h2>Today\'s Amazon finds</h2><p>Two fresh roundups a day, '
               f'every product checked for great reviews.</p></div><a href="#archive">Archive &rsaquo;</a></div><div class="rgrid">'
               + "".join(roundup_card(d) for d in days[:4]) + "</div></div></section>")
    if spots:
        out.append('<section><div class="sh"><div><h2>Spotlight picks</h2><p>Single finds worth a closer look.</p></div></div>'
                   '<div class="sgrid">' + "".join(spot_card(d, p) for d, p in spots) + "</div></section>")
    if candles:
        out.append(f'<section id="candles"><div class="sh"><div><h2>&#128367;&#65039; Candles &amp; Home Fragrance</h2><p>Yankee Candle, '
                   f'WoodWick and P.F. Candle Co. scents for cosy nights and Christmas.</p></div><a href="{SITE}/c/candles/">See all &rsaquo;</a></div>'
                   '<div class="grid">' + "".join(product_card(p, "candles") for p in latest(candles, 8)) + "</div></section>")
    if len(days) > 4:
        out.append('<section id="archive"><div class="sh"><div><h2>More roundups</h2><p>Every list we\'ve published.</p></div></div>'
                   '<div class="rgrid">' + "".join(roundup_card(d) for d in days[4:]) + "</div></section>")
    out.append(footer())
    (DEALS / "index.html").write_text("".join(out), encoding="utf-8")

    for slug, label, rx, coll in CATEGORIES:
        name = re.sub(r"&#\d+;\s*", "", label).replace("&pound;", "£")
        rounds = [d for d in days if matches(d, rx)]
        prods = {"gifts": gifts, "candles": candles}.get(coll, [])
        hero = f'<div class="hero small"><h1>{e(name)} finds</h1><p>Hand-picked {e(name.lower())} picks from UK shops, updated daily.</p></div>'
        page = [head(f"{name} finds and gift ideas UK | Daily Deals UK",
                     f"Hand-picked {name.lower()} finds from well-reviewed UK listings, updated daily.",
                     f"{SITE}/c/{slug}/", latest_pin), topbar(hero), chips(slug)]
        if prods:
            page.append('<section><div class="grid">' + "".join(product_card(p, coll) for p in latest(prods, 60)) + "</div></section>")
        if rounds:
            page.append('<section><div class="sh"><div><h2>Amazon roundups</h2></div></div><div class="rgrid">'
                        + "".join(roundup_card(d) for d in rounds) + "</div></section>")
        if not prods and not rounds:
            page.append('<section><p class="empty">New picks for this category are on the way - check back soon.</p></section>')
        page.append(footer())
        out_file = DEALS / "c" / slug / "index.html"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text("".join(page), encoding="utf-8")
