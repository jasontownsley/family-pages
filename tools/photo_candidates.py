"""Stock-photo candidates for one product, for the deals job to LOOK AT before choosing.

  python tools/photo_candidates.py <ASIN> "<search words>"

Downloads up to 4 small preview images to deals/_candidates/ (git-ignored) and
prints, for each: Pexels photo id, file path, and the photo's own description.
The job then opens each file with Read and keeps one only if it clearly shows
the same kind of item as the product, by setting "photo_id": <id> on it.
"""
import sys
import time
from pathlib import Path

import photos
from build_deals import DEALS, used_photo_ids

CAND = DEALS / "_candidates"

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    asin, query = sys.argv[1].strip().upper(), " ".join(sys.argv[2:]).strip()
    CAND.mkdir(parents=True, exist_ok=True)
    for old in CAND.glob("*.jpg"):  # clear yesterday's previews
        if time.time() - old.stat().st_mtime > 12 * 3600:
            old.unlink()
    if not photos.api_key():
        sys.exit("No Pexels key - no photo candidates.")
    found = photos.candidates(query, 4, used_photo_ids())
    if not found:
        print(f"No usable photos for '{query}'. Try other words once, or leave this product without a photo.")
    for ph in found:
        path = CAND / f"{asin}_{ph['id']}.jpg"
        try:
            path.write_bytes(photos._get(ph["src"]["medium"], timeout=20))
        except Exception as ex:
            print(f"{ph['id']} | download failed: {ex}")
            continue
        print(f"photo_id {ph['id']} | deals/_candidates/{path.name} | {ph.get('alt') or 'no description'}")
