"""Lifestyle photos for the single-product pins, from Pexels.

Amazon's licence forbids storing its product images, so pins use a free
Pexels photo of the setting (a tidy kitchen, a Halloween window) instead.
Pexels photos are free for commercial use and may be cropped and edited.

The API key is read from the PEXELS_API_KEY environment variable or from
ClaudeJobs\\pexels_key.txt on the server (kept out of the repo). With no key,
fetch() returns None and the build simply makes no single-product pins.
"""
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

KEY_FILE = Path("C:/Users/User/ClaudeJobs/pexels_key.txt")
API = "https://api.pexels.com/v1/search?"


def api_key():
    if os.environ.get("PEXELS_API_KEY"):
        return os.environ["PEXELS_API_KEY"].strip()
    if KEY_FILE.exists():
        return KEY_FILE.read_text(encoding="utf-8").strip() or None
    return None


def _get(url, key=None, timeout=25):
    headers = {"User-Agent": "DailyDealsUK/1.0"}
    if key:
        headers["Authorization"] = key
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout).read()


def _credit(ph, query=""):
    return {"id": ph["id"], "photographer": " ".join(ph["photographer"].split()), "page": ph["url"],
            "query": query, "alt": ph.get("alt", "")}


def candidates(query, n, used_ids):
    """Up to n unused portrait/square results for query, as Pexels photo dicts."""
    key = api_key()
    if not key or not query:
        return []
    url = API + urllib.parse.urlencode({"query": query, "per_page": 30, "locale": "en-GB"})
    try:
        results = json.loads(_get(url, key)).get("photos", [])
    except Exception as ex:
        print(f"Pexels search failed for '{query}': {ex}")
        return []
    keep = [ph for ph in results if ph["id"] not in used_ids and ph["height"] >= ph["width"] * 0.8]
    return keep[:n]


def fetch_id(photo_id, dest, query=""):
    """Download one specific Pexels photo (already checked by eye) to dest; return its credit or None."""
    key = api_key()
    if not key:
        return None
    try:
        ph = json.loads(_get(f"https://api.pexels.com/v1/photos/{int(photo_id)}", key))
        src = ph["src"]["original"] + "?auto=compress&cs=tinysrgb&fit=crop&w=1000&h=1000"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(_get(src, timeout=30))
    except Exception as ex:
        print(f"  Pexels download failed for photo {photo_id}: {ex}")
        return None
    return _credit(ph, query)


def fetch(query, dest, used_ids):
    """Download a portrait photo for query to dest; return its credit dict or None.

    used_ids: Pexels photo ids already used on earlier pins, so photos don't repeat.
    """
    key = api_key()
    if not key or not query:
        return None
    url = API + urllib.parse.urlencode({"query": query, "orientation": "portrait",
                                         "per_page": 30, "locale": "en-GB"})
    try:
        req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": "DailyDealsUK/1.0"})
        results = json.load(urllib.request.urlopen(req, timeout=20)).get("photos", [])
    except Exception as ex:
        print(f"  Pexels search failed for '{query}': {ex}")
        return None
    for ph in results:
        if ph["id"] in used_ids:
            continue
        src = ph["src"]["original"] + "?auto=compress&cs=tinysrgb&fit=crop&w=1000&h=1000"
        try:
            req = urllib.request.Request(src, headers={"User-Agent": "DailyDealsUK/1.0"})
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(urllib.request.urlopen(req, timeout=30).read())
        except Exception as ex:
            print(f"  Pexels download failed for photo {ph['id']}: {ex}")
            return None
        return {"id": ph["id"], "photographer": " ".join(ph["photographer"].split()), "page": ph["url"],
                "query": query}
    return None
