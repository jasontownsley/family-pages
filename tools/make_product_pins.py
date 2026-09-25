"""Single-product Pinterest pins (replacements for the old pins, which had
prices and star ratings baked into the image).

Reads pins/products.json and writes:
  pins/<ASIN>.jpg              1000x1500 text-only pin (no price, rating or Amazon photo)
  pins/pinterest_upload.csv    Pinterest bulk-create file, scheduled 2 pins a day

Usage: python tools/make_product_pins.py [first publish date YYYY-MM-DD]
"""
import csv
import json
import sys
from datetime import date, datetime, timedelta

from PIL import Image, ImageDraw

from build_deals import (BRAND, FONT_BOLD, FONT_HEAVY, FONT_SEMI, GOLD, GREEN, GREEN_DARK,
                         INK, ORANGE, PAPER, ROOT, aff, fit, font, wrap)

PINS = ROOT / "pins"
MEDIA_URL = "https://dailydealsuk.co.uk/pins/{}.jpg"
BOARD = "Amazon Finds UK"
PUBLISH_TIMES = ("10:00:00", "19:00:00")


def make_pin(p, out):
    W, H, M = 1000, 1500, 70
    img = Image.new("RGB", (W, H), GREEN)
    dr = ImageDraw.Draw(img)

    f_kick = font(FONT_BOLD, 34)
    kicker = p["category"].upper()
    kw = dr.textlength(kicker, font=f_kick)
    dr.rounded_rectangle([M, 90, M + kw + 44, 90 + 58], radius=29, fill=ORANGE)
    dr.text((M + 22, 119), kicker, font=f_kick, fill="white", anchor="lm")

    # measure the headline and product card, then centre them between badge and footer
    f_head, lines = fit(dr, p["headline"], FONT_HEAVY, W - 2 * M, 5, 112, 64)
    lh = int(f_head.size * 1.12)
    f_name, f_why = font(FONT_HEAVY, 56), font(FONT_SEMI, 42)
    names = wrap(dr, p["short_name"], f_name, W - 2 * M - 40)[:2]
    whys = wrap(dr, p["why"], f_why, W - 2 * M - 40)[:6]
    card_h = 50 + 70 * len(names) + 20 + 40 + 58 * len(whys) + 40
    gap = 80
    block = lh * len(lines) + gap + card_h
    y = 190 + max(0, (H - 150 - 60 - 190 - block) // 2)

    for ln in lines:
        dr.text((M, y), ln, font=f_head, fill="white")
        y += lh
    top = y + gap
    dr.rounded_rectangle([M - 20, top, W - M + 20, top + card_h], radius=28, fill=PAPER)
    y = top + 50
    for ln in names:
        dr.text((M + 20, y), ln, font=f_name, fill=INK)
        y += 70
    y += 20
    dr.line([M + 20, y, M + 160, y], fill=ORANGE, width=6)
    y += 40
    for ln in whys:
        dr.text((M + 20, y), ln, font=f_why, fill=INK)
        y += 58

    # footer
    dr.rectangle([0, H - 150, W, H], fill=GREEN_DARK)
    dr.text((M, H - 95), BRAND.upper(), font=font(FONT_HEAVY, 46), fill=GOLD, anchor="lm")
    dr.text((W - M, H - 95), "Tap to see it on Amazon", font=font(FONT_SEMI, 32), fill="white", anchor="rm")

    img.save(out, "JPEG", quality=88, optimize=True)


def main(argv):
    start = date.fromisoformat(argv[1]) if len(argv) > 1 else date.today() + timedelta(days=1)
    products = json.loads((PINS / "products.json").read_text(encoding="utf-8"))
    rows = []
    for i, p in enumerate(products):
        make_pin(p, PINS / f"{p['asin']}.jpg")
        when = datetime.fromisoformat(f"{start + timedelta(days=i // 2)}T{PUBLISH_TIMES[i % 2]}")
        title = f"{p['short_name']}: {p['headline']}"[:100]
        desc = f"{p['headline']}. {p['why']} Tap through for today's price on Amazon UK. #ad {p['tags']}"[:500]
        rows.append([title, MEDIA_URL.format(p["asin"]), BOARD, "", desc, aff(p["asin"]),
                     when.strftime("%Y-%m-%dT%H:%M:%S"), ""])
    with open(PINS / "pinterest_upload.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Title", "Media URL", "Pinterest board", "Thumbnail", "Description", "Link",
                    "Publish date", "Keywords"])
        w.writerows(rows)
    print(f"{len(rows)} pins, publishing {rows[0][6]} to {rows[-1][6]}")


if __name__ == "__main__":
    main(sys.argv)
