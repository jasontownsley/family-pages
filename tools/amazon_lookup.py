"""Look up Amazon UK products for the deals job.

Claude's WebFetch gets 503 / stripped pages from Amazon, but a plain request
with browser headers from the server works, so the job calls this instead.

  python tools/amazon_lookup.py B00004TZY8 B00EP2QYY0     check ASINs
  python tools/amazon_lookup.py --search "gifts under 20"  search Amazon UK

One line per product: ASIN | rating | ratings count | price | title
"""
import gzip
import html
import re
import sys
import time
import urllib.parse
import urllib.request

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "gzip",
}
ASIN_RE = re.compile(r"^B0[A-Z0-9]{8}$|^\d{9}[\dX]$")


def fetch(url):
    for attempt in range(2):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=25)
            body = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            page = body.decode("utf-8", "replace")
            if "captcha" not in page.lower()[:20000]:
                return page
        except Exception as e:
            err = e
        time.sleep(3)
    return None


def text(m):
    return html.unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else "?"


def lookup(asin):
    page = fetch(f"https://www.amazon.co.uk/dp/{asin}")
    if page is None:
        return f"{asin} | BLOCKED - could not load page, try again later"
    title = text(re.search(r'id="productTitle"[^>]*>(.*?)<', page, re.S))
    if title == "?":
        return f"{asin} | NOT FOUND - no product page on amazon.co.uk"
    rating = text(re.search(r"([\d.]+) out of 5 stars", page))
    count = text(re.search(r'id="acrCustomerReviewText"[^>]*>\(?([\d,]+)', page)).replace(",", "")
    price = text(re.search(r'class="a-offscreen">(£[\d,.]+)<', page))
    avail = re.search(r'id="availability"(.{0,800})', page, re.S)
    stock = "unavailable" if avail and "unavailable" in avail.group(1).lower() else "available"
    return f"{asin} | {rating} stars | {count} ratings | {price} | {stock} | {title[:110]}"


def search(query):
    page = fetch("https://www.amazon.co.uk/s?k=" + urllib.parse.quote_plus(query))
    if page is None:
        return ["BLOCKED - search could not load, try again later"]
    # Each result's div carries data-asin a little before the s-search-result marker,
    # so take the last data-asin in the tail of the preceding chunk
    chunks = page.split('data-component-type="s-search-result"')
    out = []
    for prev, block in zip(chunks, chunks[1:]):
        asins = re.findall(r'data-asin="([A-Z0-9]{10})"', prev[-1500:])
        if not asins:
            continue
        asin = asins[-1]
        if re.search(r">\s*Sponsored\s*<", block[:5000]):
            continue
        title = text(re.search(r"<h2[^>]*>.*?<span[^>]*>(.*?)</span>", block, re.S))
        rating = text(re.search(r"([\d.]+) out of 5 stars", block))
        count = text(re.search(r'aria-label="([\d,]+) ratings?"', block)).replace(",", "")
        price = text(re.search(r'class="a-offscreen">(£[\d,.]+)<', block))
        out.append(f"{asin} | {rating} stars | {count} ratings | {price} | {title[:110]}")
        if len(out) == 15:
            break
    return out or ["no results"]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if args[0] == "--search":
        print("\n".join(search(" ".join(args[1:]))))
    else:
        for i, a in enumerate(args[:12]):
            a = a.strip().upper()
            print(lookup(a) if ASIN_RE.match(a) else f"{a} | not an ASIN")
            if i < len(args) - 1:
                time.sleep(1.5)
