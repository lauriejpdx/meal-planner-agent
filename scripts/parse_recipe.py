#!/usr/bin/env python3
"""Extract structured recipe data (schema.org Recipe JSON-LD) from recipe pages.

Usage: parse_recipe.py <url> [<url> ...]
Output: JSON list, one entry per URL, with a status of:
  ok                 - ingredients found
  site_unavailable   - site down or blocked (report the URL to the user)
  no_recipe_data     - page loaded but has no structured recipe (try reading it in Chrome)
"""
import json
import re
import sys
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


def find_recipes(node):
    """Walk JSON-LD (which may be nested in @graph or lists) and yield Recipe objects."""
    if isinstance(node, dict):
        types = node.get("@type")
        types = types if isinstance(types, list) else [types]
        if "Recipe" in types:
            yield node
        for value in node.values():
            yield from find_recipes(value)
    elif isinstance(node, list):
        for value in node:
            yield from find_recipes(value)


def parse(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            page = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as exc:
        return {"url": url, "status": "site_unavailable", "detail": f"HTTP {exc.code}"}
    except Exception as exc:
        return {"url": url, "status": "site_unavailable", "detail": str(exc)}

    blocks = re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', page, re.S)
    for block in blocks:
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        for recipe in find_recipes(data):
            return {
                "url": url,
                "status": "ok",
                "name": recipe.get("name"),
                "yield": recipe.get("recipeYield"),
                "total_time": recipe.get("totalTime"),
                "ingredients": recipe.get("recipeIngredient", []),
            }
    return {"url": url, "status": "no_recipe_data"}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    json.dump([parse(u) for u in sys.argv[1:]], sys.stdout, indent=2, ensure_ascii=False)
