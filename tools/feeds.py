"""Rewrite the Pinterest board feeds (gifts, candles) so pins whose release time has passed appear.

Run hourly on the server by ClaudeJobs\run_feeds.ps1 (no Claude, no network calls), which commits and
pushes only when a feed actually changed.

  python tools/feeds.py
"""
import sys

import candles
import gifts


def main():
    candles.write_feed(candles.load_manifest())
    gifts.write_feed(gifts.load_manifest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
