"""Price and stock check for every Awin product we feature (runs before each build, 07:00 and 15:00).

Current price and stock come from the Awin product feeds. For Shopify shops (Candles Direct, Scottish Fine
Soaps, Bare Kind) the shop's public product data (<product url>.js) also gives the "was" price
(compare_at_price), so we can show genuine savings. Cadbury Gifts Direct has no "was" price in its feed,
so its items show the current price only.

Writes deals/data/prices.json: {raw product id: {price, was, save, in_stock, shop, checked}}.
Amazon products are never priced here (Amazon only allows prices from its own API).

  python tools/prices.py            full check (07:00): asks each Shopify shop for its "was" price
  python tools/prices.py --quick    afternoon check: only asks the shop about products whose feed price changed
"""
import csv
import gzip
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import candles

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "deals" / "data"
OUT = DATA / "prices.json"
MAX_CALLS, MAX_CALLS_QUICK = 40, 15   # shop look-ups per run (07:00 full / 15:00 quick)
TIME_BUDGET = 12 * 60                 # seconds: stop asking shops after this, so a run never drags on for hours
STALE_DAYS = 3                        # re-ask a shop about an unchanged product after this many days
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DailyDealsUK/1.0"}

# advertiser id, feed format, shop, is Shopify (has <url>.js with compare_at_price)
FEEDS = [("13560", "Google", "Candles Direct", True), ("101517", "Google", "Scottish Fine Soaps", True),
         ("30533", "Awin", "Bare Kind", True), ("736", "Awin", "Cadbury Gifts Direct", False),
         ("3965", "Google", "Scribbler", True), ("1902", "Awin", "Baker Ross", False)]


def featured_ids():
    """Raw feed ids of every Awin product shown on the site."""
    ids = set()
    for m in json.loads((DATA / "candles.json").read_text(encoding="utf-8")) if (DATA / "candles.json").exists() else []:
        ids.add(re.sub(r"-r\d+$", "", str(m["id"])))      # repeat candle pins: "123-r2" -> "123"
    for m in json.loads((DATA / "gifts.json").read_text(encoding="utf-8")) if (DATA / "gifts.json").exists() else []:
        ids.add(re.sub(r"-r\d+$", "", str(m["id"])).split("-", 1)[1])     # "sfs-123-r2" -> "123"
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
                old_price = (r.get("product_price_old") or "").split()
                found[rid] = {"shop": shop, "shopify": shopify, "link": link, "variant": var,
                              "price": float(r["search_price"] or 0), "in_stock": r.get("in_stock") != "0",
                              # some feeds (e.g. Baker Ross) carry the shop's own "was" price
                              "was_feed": float(old_price[0]) if old_price and old_price[0].replace(".", "", 1).isdigit() else None}
    return found


def shopify_price(link, variant):
    """(price, was, available) for one variant from the shop's public product data."""
    u = urllib.parse.urlparse(link)
    # ask for pounds explicitly: some shops (e.g. Bare Kind) default to another currency for automated requests
    js = f"{u.scheme}://{u.netloc}{u.path.rstrip('/')}.js?currency=GBP"
    headers = {**UA, "Cookie": "localization=GB; cart_currency=GBP"}
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(js, headers=headers), timeout=30) as r:
                data = json.load(r)
            break
        except urllib.error.HTTPError as e:
            # the shop asked us to slow down: wait as long as it says (or a while), then try again
            if e.code != 429 or attempt == 2:
                raise
            wait = e.headers.get("Retry-After", "")
            time.sleep(min(int(wait), 60) if wait.isdigit() else 20 * (attempt + 1))
    vs = data.get("variants", [])
    v = next((x for x in vs if str(x.get("id")) == str(variant)), vs[0] if len(vs) == 1 else None)
    if not v:
        return None
    was = (v.get("compare_at_price") or 0) / 100
    return v["price"] / 100, was, bool(v.get("available"))


def main(argv=()):
    sys.stdout.reconfigure(encoding="utf-8")
    quick = "--quick" in argv
    wanted = featured_ids()
    idx = feed_index(wanted)
    checked = datetime.now().strftime("%Y-%m-%dT%H:%M")
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    out, offers, missing, kept, reused = {}, 0, 0, 0, 0
    # Asking the shops is slow (they rate-limit us), so each run asks about a limited number of products:
    # new ones and ones whose feed price moved first, then (full 07:00 run only) the ones checked longest ago.
    # Everything else keeps its last saving while its price is unchanged.
    stale_before = (datetime.now() - timedelta(days=STALE_DAYS)).strftime("%Y-%m-%dT%H:%M")
    def priority(rid):
        f, o = idx.get(rid), old.get(rid, {})
        if not f or not (f["shopify"] and f["link"]):
            return None
        if o.get("price") is None or abs(o["price"] - f["price"]) >= 0.01:
            return (0, "")                                   # new or price changed: always worth asking
        if not quick and o.get("shop_checked", "") < stale_before:
            return (1, o.get("shop_checked", ""))            # not asked for a while
        return None
    ask = sorted((r for r in wanted if priority(r)), key=priority)[:MAX_CALLS_QUICK if quick else MAX_CALLS]
    ask, deadline = set(ask), time.time() + TIME_BUDGET
    for rid in sorted(wanted):
        f = idx.get(rid)
        if not f:                      # gone from the feed: treat as out of stock
            out[rid] = {**old.get(rid, {}), "in_stock": False, "checked": checked}
            missing += 1
            continue
        price, was, stock = f["price"], None, f["in_stock"]
        o = old.get(rid, {})
        shop_checked = o.get("shop_checked", "")
        if rid in ask and time.time() < deadline:
            try:
                sp = shopify_price(f["link"], f["variant"])
                if sp:
                    price, w, stock = sp[0], sp[1], sp[2] and stock
                    was = w if w > price else None
                    shop_checked = checked
            except Exception as e:     # shop data unavailable: fall back to the feed price
                print(f"  {f['shop']} {rid}: {str(e)[:60]}")
                # keep the last known "was" price while the current price hasn't changed,
                # so a failed check doesn't wipe a genuine saving off the site
                if o.get("was") and abs(o.get("price", 0) - price) < 0.01:
                    was = o["was"]
                    kept += 1
            time.sleep(1.5)              # be gentle: shops rate-limit fast repeated requests
        elif o.get("price") is not None and abs(o["price"] - price) < 0.01:
            # price unchanged since the shop was last asked: its saving and stock still stand
            was, stock = o.get("was"), stock and o.get("in_stock", True)
            reused += 1
        if not f["shopify"] and f.get("was_feed") and f["was_feed"] > price:
            was = f["was_feed"]
        save = round((was - price) / was * 100) if was else 0
        offers += save >= 5 and stock
        out[rid] = {"price": round(price, 2), "was": was, "save": save, "in_stock": stock, "shop": f["shop"],
                    "checked": checked, "shop_checked": shop_checked}
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"Prices: {len(out)} products checked, {offers} on offer, "
          f"{sum(not v.get('in_stock') for v in out.values())} out of stock ({missing} no longer in feeds)"
          + (f", {kept} savings kept from the last check" if kept else "")
          + (f", {reused} unchanged (last saving kept)" if reused else "") + f", {len(ask)} asked the shop")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
