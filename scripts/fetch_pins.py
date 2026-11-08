#!/usr/bin/env python3
"""Fetch EVERY pin on a public Pinterest board (main feed + all sections) and cache it.

Usage: fetch_pins.py <board_url> [--refresh] [--max-age-days N] [--cache PATH]
Output: a short JSON summary (count, sections, date range). The pins themselves
go to the cache file, which find_recipes.py reads. Nothing is printed per pin,
because a board can hold thousands.

Uses the same JSON endpoints the Pinterest website uses for a public board, so no
login and no API approval are needed. Each pin includes the recipe-site link,
which means pins no longer have to be opened in the browser.
The cache is reused for --max-age-days (default 7) unless --refresh is passed.
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept": "application/json",
           "X-Pinterest-PWS-Handler": "www/[username]/[slug].js"}
DEFAULT_CACHE = Path(__file__).resolve().parent.parent / "data" / "recipe-index" / "pinterest.json"


def get(resource, options):
    query = urllib.parse.urlencode({"data": json.dumps({"options": options, "context": {}})})
    url = f"https://www.pinterest.com/resource/{resource}/get/?{query}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp).get("resource_response") or {}


def get_all(resource, options, page_size):
    """Follow Pinterest's bookmark pagination until the end."""
    out, bookmark = [], None
    for _ in range(200):
        opts = dict(options, page_size=page_size)
        if bookmark:
            opts["bookmarks"] = [bookmark]
        # Logged-out pages sometimes come back empty mid-board; a short retry fixes it.
        for attempt in range(4):
            resp = get(resource, opts)
            data = resp.get("data")
            if data or resp.get("bookmark") in (None, "-end-"):
                break
            time.sleep(2 * (attempt + 1))
        out.extend(data if isinstance(data, list) else [])
        bookmark = resp.get("bookmark")
        if not bookmark or bookmark == "-end-":
            break
        time.sleep(0.3)
    return out


def to_date(value):
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError):
        return None


def slim(pin, section=None):
    return {
        "id": pin.get("id"),
        "source": "pinterest",
        "title": (pin.get("title") or pin.get("grid_title") or "").strip(),
        "text": (pin.get("description") or "").strip()[:300],
        "link": pin.get("link"),
        "saved": to_date(pin.get("created_at")),
        "section": section,
    }


def fetch(board_url):
    parts = [p for p in urllib.parse.urlparse(board_url).path.split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"Not a board URL: {board_url}")
    username, slug = parts[0], parts[1]
    board = get("BoardResource", {"username": username, "slug": slug}).get("data") or {}
    board_id = board.get("id")
    if not board_id:
        raise RuntimeError("Board not found or not public")

    pins = {}
    total = board.get("pin_count") or 0
    # Page size 250 works for the main feed; section endpoints return nothing above ~25.
    # Logged out, a flaky page can look like the end of the board, so walk the feed
    # again (and merge) until the count matches the board's own pin count.
    for _ in range(4):
        for p in get_all("BoardFeedResource", {"board_id": board_id}, 250):
            if p.get("type") == "pin" and p.get("id"):
                pins.setdefault(p["id"], slim(p))
        if len(pins) >= total * 0.97:
            break
    sections = {}
    for s in get_all("BoardSectionsResource", {"board_id": board_id}, 25):
        sec_pins = get_all("BoardSectionPinsResource", {"section_id": s["id"]}, 25)
        sections[s.get("title")] = s.get("pin_count")
        for p in sec_pins:
            if p.get("type") == "pin" and p.get("id"):
                pins[p["id"]] = slim(p, s.get("title"))
    return board.get("pin_count"), sections, list(pins.values())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("board_url")
    ap.add_argument("--refresh", action="store_true", help="ignore the cache")
    ap.add_argument("--max-age-days", type=float, default=7)
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    args = ap.parse_args()

    cache = args.cache
    fresh = cache.exists() and (time.time() - cache.stat().st_mtime) < args.max_age_days * 86400
    if fresh and not args.refresh:
        pins = json.loads(cache.read_text())
        source, board_count, sections = "cache", None, None
    else:
        try:
            board_count, sections, pins = fetch(args.board_url)
        except Exception as exc:  # undocumented endpoints: fail loudly so the agent falls back
            if cache.exists():
                pins, source = json.loads(cache.read_text()), f"stale cache (fetch failed: {exc})"
                board_count = sections = None
            else:
                json.dump({"error": f"Pinterest fetch failed: {exc}"}, sys.stdout)
                sys.exit(1)
        else:
            source = "fetched"
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(pins, ensure_ascii=False))

    dates = sorted(p["saved"] for p in pins if p.get("saved"))
    summary = {
        "source": source,
        "cache": str(cache),
        "pins": len(pins),
        "board_pin_count": board_count,
        "with_link": sum(1 for p in pins if p.get("link")),
        "no_text": sum(1 for p in pins if not (p.get("title") or p.get("text"))),
        "oldest": dates[0] if dates else None,
        "newest": dates[-1] if dates else None,
        "sections": sections,
        "as_of": datetime.now(timezone.utc).date().isoformat(),
    }
    json.dump(summary, sys.stdout, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
