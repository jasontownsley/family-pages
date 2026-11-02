"""Spread pins through the day so they don't all appear at 07:00 and 15:00 (looks more human).

Each new pin gets a "release" time (UK local, "YYYY-MM-DDTHH:MM") inside its run's window; the board feeds
only include pins whose release time has passed. tools/feeds.py rewrites the feeds every hour on the server.
"""
import random
from datetime import date as Date, datetime, time, timedelta

WINDOWS = {"a": (time(8, 0), time(13, 50)),     # 07:00 run -> released through the morning and early afternoon
           "b": (time(14, 40), time(21, 30))}   # 15:00 run -> released through the afternoon and evening


def release(day, slot, seed):
    if isinstance(day, str):
        day = Date.fromisoformat(day)
    start, end = WINDOWS.get(slot, WINDOWS["a"])
    t0 = datetime.combine(day, start)
    span = (datetime.combine(day, end) - t0).total_seconds()
    t = t0 + timedelta(seconds=random.Random(f"{day}{slot}{seed}").random() * span)
    return t.strftime("%Y-%m-%dT%H:%M")


def released(item, now=None):
    r = item.get("release")
    return not r or r <= (now or datetime.now()).strftime("%Y-%m-%dT%H:%M")


def pub_date(item, fallback):
    """Datetime (with the local timezone) for the feed's pubDate."""
    r = item.get("release")
    return datetime.strptime(r, "%Y-%m-%dT%H:%M").astimezone() if r else fallback


PRICE_STEPS = (5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150)


def under(price):
    """ "Under £15" style hook for pin titles, or "" for missing / very high prices."""
    for step in PRICE_STEPS:
        if price and price <= step:
            return f"Under £{step}"
    return ""
