"""Collage pins: "9 Stocking Fillers Under £10 UK"-style roundups of our Awin products (gifts + candles).

The kind of pin that wins Pinterest search in the run-up to Christmas: a big number headline, a festive
background and a grid of products with prices. Each run (07:00 and 15:00) makes one, rotating through
THEMES so the same theme doesn't come back within a few days. Each collage gets:
  deals/lists/<id>/pin.jpg      the pin (1000 x 1500)
  deals/lists/<id>/index.html   the landing page listing the products (each links to its product page)
and goes into deals/data/collages.json; gifts.write_feed adds it to the Christmas Gift Ideas board feed.

  python tools/collages.py --make [YYYY-MM-DD] [--afternoon]
"""
import json
import random
import re
import sys
from datetime import date as Date, datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import candles as cd
import home

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "deals" / "lists"
MANIFEST = ROOT / "deals" / "data" / "collages.json"
SITE = "https://dailydealsuk.co.uk/deals/lists"
YEAR = 2026

# festive palette (Nov-Dec): deep red to berry, gold accents, cream text, evergreen footer
RED_TOP, RED_BOTTOM, GOLD, CREAM, GREEN = "#9B1C24", "#5C0B16", "#F5D27A", "#FFF6E8", "#0F3D2E"
TAG_RED = "#D0021B"


def _txt(p):
    return f"{p['brand']} {p['name']} {p['kind']} {p.get('blurb', '')[:200]}".lower()


# slug, headline (without the number), subline, filter(product, price) -> bool, keywords for the pin description
THEMES = [
    ("stocking-fillers-under-10", "Stocking Fillers Under £10", "Little extras they'll love",
     lambda p, pr: pr <= 10, "#stockingfillers #stockingfillersuk #christmasgifts"),
    ("secret-santa-under-15", "Secret Santa Gifts Under £15", "Office & family gift swaps",
     lambda p, pr: pr <= 15, "#secretsanta #secretsantagifts #christmasgifts"),
    ("christmas-gifts-under-20", "Christmas Gifts Under £20", "Budget-friendly gift ideas",
     lambda p, pr: 8 <= pr <= 20, "#christmasgiftideas #giftsunder20 #budgetgifts"),
    ("christmas-gifts-for-her", "Christmas Gifts For Her", "Cosy, pampering & sweet treats",
     lambda p, pr: not re.search(r"\bkid|child|boy|\bmen\b|\bhim\b|dad|beard", f"{p['name']} {p['kind']}", re.I) and (
         p["_folder"] == "candles" or p["shop"] in ("Scottish Fine Soaps", "Bare Kind")
         or re.search(r"hamper|basket|selection|truffle", _txt(p))), "#giftsforher #christmasgiftsforher #giftideas"),
    ("christmas-gifts-for-him", "Christmas Gifts For Him", "For dads, brothers & boyfriends",
     lambda p, pr: re.search(r"\bmen|for him|dad|grooming|vetiver|sandalwood|shav|beard|game|puzzle|whisk|beer|gin|"
                             r"football|golf|socks", _txt(p)) and p["_folder"] != "candles",
     "#giftsforhim #christmasgiftsforhim #giftsformen"),
    ("chocolate-christmas-gifts", "Chocolate Christmas Gifts", "Hampers, selection boxes & more",
     lambda p, pr: p["_folder"] == "gifts" and (p["shop"] == "Cadbury Gifts Direct"
                                                  or re.search(r"chocolat|truffle|fudge", f"{p['name']} {p['kind']}", re.I)),
     "#chocolategifts #christmaschocolate #cadbury"),
    ("christmas-candle-gifts", "Christmas Candle Gift Ideas", "Yankee Candle, WoodWick & more",
     lambda p, pr: p["_folder"] == "candles", "#christmascandles #yankeecandle #candlegifts"),
    ("cosy-christmas-gifts", "Cosy Christmas Gifts", "For snug nights in",
     lambda p, pr: p["_folder"] == "candles" or re.search(r"sock|cosy|hot choc|blanket|bath|soak|candle|light", _txt(p)),
     "#cosygifts #hygge #christmasgifts"),
    ("pamper-gift-sets", "Pamper Gift Sets", "Bath, body & home fragrance",
     lambda p, pr: p["shop"] == "Scottish Fine Soaps" or re.search(r"bath|body|hand care|diffuser|spa", _txt(p)),
     "#pampergifts #giftsets #selfcaregifts"),
    ("kids-christmas-crafts", "Christmas Crafts For Kids", "Easy festive makes & stocking fillers",
     lambda p, pr: p["shop"] == "Baker Ross", "#christmascrafts #kidscrafts #christmasactivities"),
    ("fun-gifts", "Fun & Quirky Christmas Gifts", "Games, novelty lights & treats",
     lambda p, pr: p["shop"] == "Scribbler", "#funnygifts #quirkygifts #secretsanta"),
]
THEME_GAP_DAYS = 4          # a theme isn't reused within this many days
NOT_XMAS = re.compile(r"birthday|valentine|easter|mother'?s day|father'?s day|wedding|anniversar|baby|new home|get well", re.I)


def pool():
    """Every in-stock product we've pinned, newest first, with its current price and photo."""
    pr = home.prices()
    seen, out = set(), []
    for name, folder in (("gifts.json", "gifts"), ("candles.json", "candles")):
        for m in sorted(home.load(name), key=lambda m: m["date"], reverse=True):
            rid = home.raw_id(m["id"])
            v = pr.get(rid, {})
            photo = ROOT / "deals" / folder / str(m["id"]) / "photo.jpg"
            key = (m.get("shop", "Candles Direct"), m["name"].lower())
            if key in seen or not photo.exists() or not v.get("in_stock", True) or NOT_XMAS.search(m["name"]):
                continue
            seen.add(key)
            out.append({**m, "shop": m.get("shop", "Candles Direct"), "_folder": folder, "_photo": photo,
                        "_price": v.get("price") or m.get("price") or 0, "_save": v.get("save", 0)})
    return out


def choose(day, slot, items, manifest):
    """(theme, products): the theme least recently used that has at least 6 products."""
    rnd = random.Random(f"{day}{slot}")
    recent = {m["theme"]: m["date"] for m in manifest}
    order = sorted(THEMES, key=lambda t: (recent.get(t[0], ""), rnd.random()))
    for t in order:
        if t[0] in recent and (day - Date.fromisoformat(recent[t[0]])).days < THEME_GAP_DAYS:
            continue
        prods = [p for p in items if p["_price"] and t[3](p, p["_price"])]
        if len(prods) < 6:
            continue
        # mix of shops, products on offer first, then a random spread (not always the newest)
        rnd.shuffle(prods)
        prods.sort(key=lambda p: -(p["_save"] >= 5))
        picked, per_shop = [], {}
        cap = 3 if len({p["shop"] for p in prods}) > 2 else 6
        for p in prods:
            if per_shop.get(p["shop"], 0) < cap:
                picked.append(p)
                per_shop[p["shop"]] = per_shop.get(p["shop"], 0) + 1
            if len(picked) == 9:
                break
        if len(picked) >= 6:
            return t, picked[:9] if len(picked) >= 9 else picked[:6]
    return None, []


# ---------------------------------------------------------------- pin

def bokeh(img, seed, n=34):
    """Soft gold fairy-light dots in the background."""
    rnd = random.Random(seed)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(n):
        x, y, r = rnd.randint(0, img.width), rnd.randint(0, img.height), rnd.randint(8, 34)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(245, 210, 122, rnd.randint(40, 110)))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(9)))


def make_pin(title, n, sub, prods, out, seed):
    W, H, M = 1000, 1500, 52
    grad = Image.linear_gradient("L").resize((W, H))
    img = Image.composite(Image.new("RGBA", (W, H), RED_BOTTOM), Image.new("RGBA", (W, H), RED_TOP), grad)
    bokeh(img, seed)
    dr = ImageDraw.Draw(img)
    f = cd.font
    # pill + headline: the number in gold, the rest in cream
    pill = f"UK GIFT IDEAS · {YEAR}"
    fp = f(cd.BOLD, 28)
    pw = dr.textlength(pill, font=fp)
    dr.rounded_rectangle([M, 44, M + pw + 40, 94], radius=25, fill=GOLD)
    dr.text((M + 20, 69), pill, font=fp, fill=RED_BOTTOM, anchor="lm")
    size = 92
    while True:
        fh = f(cd.HEAVY, size)
        lines = cd.wrap(dr, f"{n} {title}", fh, W - 2 * M)
        if len(lines) <= 2 or size <= 60:
            break
        size -= 4
    y = 116
    for i, ln in enumerate(lines[:3]):
        x = M
        if i == 0 and ln.startswith(f"{n} "):
            dr.text((x, y), str(n), font=fh, fill=GOLD)
            x += dr.textlength(f"{n} ", font=fh)
            ln = ln[len(str(n)) + 1:]
        dr.text((x, y), ln, font=fh, fill=CREAM)
        y += int(size * 1.08)
    dr.text((M, y + 6), sub, font=f(cd.SEMI, 36), fill=GOLD)
    top = y + 70
    # product grid: 3 x 3 (or 3 x 2) white tiles with a price tag
    cols, rows = (3, 3) if len(prods) >= 9 else (2, 3)      # 6 products: bigger tiles
    gap, bottom = 16, H - 150
    tw = (W - 2 * M - gap * (cols - 1)) // cols
    th = min(tw, (bottom - top - gap * (rows - 1)) // rows)
    gy = top + (bottom - top - (th * rows + gap * (rows - 1))) // 2
    for i, p in enumerate(prods[:cols * rows]):
        x0 = M + (i % cols) * (tw + gap)
        y0 = gy + (i // cols) * (th + gap)
        dr.rounded_rectangle([x0, y0, x0 + tw, y0 + th], radius=22, fill="white")
        pic = cd.product_cutout(p["_photo"], min(tw, th) - 30)
        img.paste(pic, (x0 + (tw - pic.width) // 2, y0 + (th - pic.height) // 2))
        dr = ImageDraw.Draw(img)
        price = f"£{p['_price']:.0f}" if p["_price"] >= 10 or float(p["_price"]).is_integer() else f"£{p['_price']:.2f}"
        ft = f(cd.HEAVY, 30)
        pw = dr.textlength(price, font=ft)
        dr.rounded_rectangle([x0 + 10, y0 + th - 54, x0 + 30 + pw, y0 + th - 10], radius=16, fill=TAG_RED)
        dr.text((x0 + 20, y0 + th - 32), price, font=ft, fill="white", anchor="lm")
    dr.rectangle([0, H - 120, W, H], fill=GREEN)
    dr.text((M, H - 60), "DAILY DEALS UK", font=f(cd.HEAVY, 42), fill=CREAM, anchor="lm")
    dr.text((W - M, H - 60), f"Tap to see all {n} ›", font=f(cd.SEMI, 32), fill=GOLD, anchor="rm")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out, "JPEG", quality=88, optimize=True)


# ---------------------------------------------------------------- landing page

def page(c, prods):
    url = f"{SITE}/{c['id']}/"
    hero = (f'<div class="hero small"><h1>{home.e(c["title"])}</h1><p>{home.e(c["sub"])} - hand-picked from UK shops we '
            f'trust, with prices checked twice a day.</p><div class="cta"><a class="a1" href="{home.SITE}/guides/christmas-gift-guide/">'
            f'&#127876; Full Christmas gift guide</a></div></div>')
    cards = "".join(home.product_card(p, p["_folder"]) for p in prods)
    return "".join([home.head(f"{c['title']} | Daily Deals UK", f"{c['title']}: {c['sub'].lower()}. Hand-picked UK gift ideas "
                              f"with live prices.", url, f"{url}pin.jpg"),
                    home.topbar(hero), home.chips(""), f'<section><div class="grid">{cards}</div></section>',
                    home.vouchers_section(home.vouchers(exclude={"Breeze eSim"}), n=3), home.footer()])


def refresh_pages():
    """Rebuild every list page so prices and stock stay current (called by build_deals via home.build)."""
    items = {(p["_folder"], str(p["id"])): p for p in pool()}
    for c in load_manifest():
        prods = [items[(f, i)] for f, i in c["products"] if (f, i) in items]
        folder = OUT / c["id"]
        if prods and folder.exists():
            (folder / "index.html").write_text(page(c, prods), encoding="utf-8")


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else []


def make(day, slot="a"):
    manifest = load_manifest()
    if any(m["date"] == day.isoformat() and m.get("slot", "a") == slot for m in manifest):
        print(f"Collage already made for {day} ({'afternoon' if slot == 'b' else 'morning'})")
        return 0
    theme, prods = choose(day, slot, pool(), manifest)
    if not prods:
        print("Collage: not enough products for any theme")
        return 0
    slug, head, sub, _, tags = theme
    n = len(prods)
    cid = f"{day.isoformat()}{'-b' if slot == 'b' else ''}-{slug}"
    c = {"id": cid, "theme": slug, "title": f"{n} {head} UK", "sub": sub, "tags": tags, "date": day.isoformat(),
         "slot": slot, "products": [(p["_folder"], str(p["id"])) for p in prods],
         "release": home_release(day, slot)}
    make_pin(head, n, sub, prods, OUT / cid / "pin.jpg", cid)
    (OUT / cid / "index.html").write_text(page(c, prods), encoding="utf-8")
    manifest.append(c)
    MANIFEST.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    import gifts
    gifts.write_feed(gifts.load_manifest())
    print(f"Collage: {c['title']} ({', '.join(p['name'][:24] for p in prods)})")
    return 0


def home_release(day, slot):
    import drip
    return drip.release(day, slot, f"collage{slot}")


def main(argv):
    if len(argv) >= 2 and argv[1] == "--make":
        args = [a for a in argv[2:] if not a.startswith("--")]
        return make(Date.fromisoformat(args[0]) if args else Date.today(), "b" if "--afternoon" in argv else "a")
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
