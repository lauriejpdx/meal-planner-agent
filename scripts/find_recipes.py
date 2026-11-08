#!/usr/bin/env python3
"""Score every saved recipe in the local index and print a compact shortlist.

Usage:
  find_recipes.py --have "chicken thigh,ground beef,acorn squash" \
                  --want "soup,stew,chili,bake,roast" [--limit 30] [--older-share 0.5]
                  [--index data/recipe-index/pinterest.json ...]

Code narrows thousands of saves to ~30 candidates; Claude makes the picks.
- --have: what's in the freezer, fridge, and pantry (each match +3)
- --want: dish types that suit the weather (each match +2)
- Desserts, drinks, snacks, and breakfast sections and titles are skipped.
- --older-share of the slots go to saves more than a year old, so forgotten
  recipes come back around, not just the newest pins.
"""
import argparse
import json
import re
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INDEX = [ROOT / "data" / "recipe-index" / "pinterest.json"]
SKIP_SECTIONS = {"desserts", "drinks", "snacks", "breakfast"}
SKIP_TITLE = re.compile(
    r"\b(cookies?|cakes?|cheesecake|brownies?|muffins?|smoothies?|cocktails?|mocktails?|"
    r"latte|fudge|cupcakes?|pudding|vinaigrette|dressing|frosting|granola|pancakes?|waffles?)\b",
    re.I)


def terms(csv):
    return [t.strip().lower() for t in (csv or "").split(",") if t.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", nargs="*", type=Path, default=DEFAULT_INDEX)
    ap.add_argument("--have", default="")
    ap.add_argument("--want", default="")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--older-share", type=float, default=0.5)
    args = ap.parse_args()

    have, want = terms(args.have), terms(args.want)
    year_ago = (date.today() - timedelta(days=365)).isoformat()
    rows = []
    for path in args.index:
        for r in json.loads(path.read_text()):
            title, text = r.get("title") or "", r.get("text") or ""
            if not (title or text) or not r.get("link"):
                continue
            if (r.get("section") or "").lower() in SKIP_SECTIONS or SKIP_TITLE.search(title):
                continue
            blob = f"{title} {text}".lower()
            h = [t for t in have if t in blob]
            w = [t for t in want if t in blob]
            score = 3 * len(h) + 2 * len(w)
            if score == 0:
                continue
            rows.append((score, r, h + w))

    rows.sort(key=lambda x: (-x[0], x[1].get("saved") or ""))
    n_old = round(args.limit * args.older_share)
    older = [x for x in rows if (x[1].get("saved") or "") < year_ago][:n_old]
    rest = [x for x in rows if x not in older][: args.limit - len(older)]
    picked = sorted(older + rest, key=lambda x: -x[0])

    print(f"# {len(rows)} matching saves; showing {len(picked)} ({len(older)} saved over a year ago)")
    for score, r, hits in picked:
        name = (r.get("title") or r.get("text"))[:80]
        old = " 🕰" if (r.get("saved") or "") < year_ago else ""
        print(f"{score:>2} | {r.get('saved') or '?'}{old} | {r.get('section') or '-'} | {name} | "
              f"{r['link']} | {', '.join(hits)}")


if __name__ == "__main__":
    main()
