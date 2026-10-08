"""Price and stock check for every Awin product we feature (runs before each build, 07:00 and 15:00).

Current price and stock come from the Awin product feeds. For Shopify shops (Candles Direct, Scottish Fine
Soaps, Bare Kind) the shop's public product data (<product url>.js) also gives the "was" price
(compare_at_price), so we can show genuine savings. Cadbury Gifts Direct has no "was" price in its feed,
so its items show the current price only.

Writes deals/data/prices.json: {raw product id: {price, was, save, in_stock, shop, checked}}.
Amazon products are never priced here (Amazon only allows prices from its own API).

  python tools/prices.py
"""
import csv
import gzip
import io
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import candles

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "deals" / "data"
OUT = DATA / "prices.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DailyDealsUK/1.0"}

# advertiser id, feed format, shop, is Shopify (has <url>.js with compare_at_price)
FEEDS = [("13560", "Google", "Candles Direct", True), ("101517", "Google", "Scottish Fine Soaps", True),
         ("30533", "Awin", "Bare Kind", True), ("736", "Awin", "Cadbury Gifts Direct", False)]


def featured_ids():
    """Raw feed ids of every Awin product shown on the site."""
    ids = set()
    for m in json.loads((DATA / "candles.json").read_text(encoding="utf-8")) if (DATA / "candles.json").exists() else []:
        ids.add(str(m["id"]))
    for m in json.loads((DATA / "gifts.json").read_text(encoding="utf-8")) if (DATA / "gifts.json").exists() else []:
        ids.add(str(m["id"]).split("-", 1)[1])
    g = DATA / "guide-christmas.json"
    if g.exists():
        for s in json.loads(g.read_text(encoding="utf-8"))["sections"]:
            ids |= {it["key"][3:] for it in s["items"] if it["src"] == "awin"}
    return ids


def feed_index(wanted):
    base = f"https://ui.awin.com/productdata-darwin-download/publisher/{candles.PUBLISHER}/{candles.awin_key()}/1"
    listing = list(csv.DictReader(io.StringIO(candles.fetch(f"{base}/feedList").decode("utf-8-sig"))))
    found = {}
    for adv, fmt, shop, shopify in FEEDS:
        url = next((r["URL"] for r in listing if r["Advertiser ID"] == adv and r["Datafeed Format"] == fmt), None)
        if not url:
            print(f"  {shop}: no feed")
            continue
        for r in csv.DictReader(io.StringIO(gzip.decompress(candles.fetch(url)).decode("utf-8-sig"))):
            rid = r.get("id") or r.get("aw_product_id")
            if rid not in wanted:
                continue
            if fmt == "Google":
                found[rid] = {"shop": shop, "shopify": shopify, "link": r["link"], "variant": rid,
                              "price": float(r["price"].split()[0]), "in_stock": r["availability"] == "in_stock"}
            else:
                link = r.get("merchant_deep_link", "")
                var = urllib.parse.parse_qs(urllib.parse.urlparse(link).query).get("variant", [""])[0]
                found[rid] = {"shop": shop, "shopify": shopify, "link": link, "variant": var,
                              "price": float(r["search_price"] or 0), "in_stock": r.get("in_stock") != "0"}
    return found


def shopify_price(link, variant):
    """(price, was, available) for one variant from the shop's public product data."""
    u = urllib.parse.urlparse(link)
    # ask for pounds explicitly: some shops (e.g. Bare Kind) default to another currency for automated requests
    js = f"{u.scheme}://{u.netloc}{u.path.rstrip('/')}.js?currency=GBP"
    headers = {**UA, "Cookie": "localization=GB; cart_currency=GBP"}
    with urllib.request.urlopen(urllib.request.Request(js, headers=headers), timeout=30) as r:
        data = json.load(r)
    vs = data.get("variants", [])
    v = next((x for x in vs if str(x.get("id")) == str(variant)), vs[0] if len(vs) == 1 else None)
    if not v:
        return None
    was = (v.get("compare_at_price") or 0) / 100
    return v["price"] / 100, was, bool(v.get("available"))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    wanted = featured_ids()
    idx = feed_index(wanted)
    checked = datetime.now().strftime("%Y-%m-%dT%H:%M")
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    out, offers, missing = {}, 0, 0
    for rid in sorted(wanted):
        f = idx.get(rid)
        if not f:                      # gone from the feed: treat as out of stock
            out[rid] = {**old.get(rid, {}), "in_stock": False, "checked": checked}
            missing += 1
            continue
        price, was, stock = f["price"], None, f["in_stock"]
        if f["shopify"] and f["link"]:
            try:
                sp = shopify_price(f["link"], f["variant"])
                if sp:
                    price, w, stock = sp[0], sp[1], sp[2] and stock
                    was = w if w > price else None
            except Exception as e:     # shop data unavailable: fall back to the feed price
                print(f"  {f['shop']} {rid}: {str(e)[:60]}")
            time.sleep(0.3)
        save = round((was - price) / was * 100) if was else 0
        offers += save >= 5 and stock
        out[rid] = {"price": round(price, 2), "was": was, "save": save, "in_stock": stock, "shop": f["shop"], "checked": checked}
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"Prices: {len(out)} products checked, {offers} on offer, "
          f"{sum(not v.get('in_stock') for v in out.values())} out of stock ({missing} no longer in feeds)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
