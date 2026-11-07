#!/usr/bin/env python3
"""Fetch recent pins from a public Pinterest board via its RSS feed.

Usage: fetch_pins.py <board_url> [--limit N]
Output: JSON list of pins, newest first.

Note: the RSS pin links don't open (obfuscated IDs), so the recipe-site URL
has to be resolved in the browser. See the meal-planner skill, step 2.
"""
import argparse
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


def to_date(value):
    """RSS pubDate -> YYYY-MM-DD, or None if missing or malformed."""
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError):
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("board_url")
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()

    feed = args.board_url.rstrip("/") + ".rss"
    req = urllib.request.Request(feed, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            root = ET.fromstring(resp.read())
    except Exception as exc:  # feed is undocumented; fail loudly so the agent falls back to Chrome
        json.dump({"error": f"RSS feed unavailable: {exc}", "feed": feed}, sys.stdout)
        sys.exit(1)

    pins = []
    for item in root.iter("item"):
        raw_desc = item.findtext("description") or ""
        img = re.search(r'<img src="([^"]+)"', raw_desc)
        text = html.unescape(re.sub(r"<[^>]+>", "", raw_desc)).strip()
        title = html.unescape((item.findtext("title") or "").strip())
        saved = item.findtext("pubDate")
        pins.append({
            "title": title or text[:140],
            "description": text,
            "saved": to_date(saved),
            "image": img.group(1) if img else None,
        })

    pins.sort(key=lambda p: p["saved"] or "", reverse=True)
    json.dump(pins[: args.limit], sys.stdout, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
