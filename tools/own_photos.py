"""Family photos of products we actually own ("Family favourites").

Photos are dropped into a shared OneDrive folder, named after the product
(e.g. "tangle teezer.jpg"). The deals job may feature one a day; the build
then makes a real-photo pin for it. Only a cropped, re-encoded copy is ever
published (EXIF, including GPS, is dropped); the originals stay in OneDrive.

Folder: OWN_PHOTOS_DIR env var, else the server's synced work OneDrive folder
(JasonTownsley@BlueSkiesDigital, "OneDrive - Blue Skies Digital").
Used photos are recorded in ClaudeJobs/own_photos_used.json (outside the repo).
"""
import json
import os
from datetime import date
from pathlib import Path

from PIL import Image, ImageOps

try:  # iPhone photos are HEIC
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

OWN_DIR = Path(os.environ.get("OWN_PHOTOS_DIR", r"C:\Users\User\OneDrive - Blue Skies Digital\Daily Deals UK Photos"))
USED_FILE = Path(os.environ.get("OWN_PHOTOS_USED", r"C:\Users\User\ClaudeJobs\own_photos_used.json"))
EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}


def used():
    try:
        return json.loads(USED_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def available():
    """Photo filenames in the folder that haven't been featured yet."""
    if not OWN_DIR.is_dir():
        return []
    done = used()
    return sorted(f.name for f in OWN_DIR.iterdir()
                  if f.is_file() and f.suffix.lower() in EXTS and f.name not in done)


def prepare(filename, dest, asin):
    """Copy a family photo into the site as a clean JPEG; return its credit or None."""
    src = OWN_DIR / filename
    if not src.is_file():
        return None
    try:
        img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    except Exception as ex:
        print(f"  Could not open family photo '{filename}': {ex}")
        return None
    img.thumbnail((1400, 1400))
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "JPEG", quality=88, optimize=True)  # re-encoded: no EXIF/GPS carried over
    record = used()
    record[filename] = {"asin": asin, "date": date.today().isoformat()}
    try:
        USED_FILE.write_text(json.dumps(record, indent=1), encoding="utf-8")
    except OSError:
        pass
    return {"id": "own:" + filename, "photographer": "Daily Deals UK", "page": "", "own": True}
