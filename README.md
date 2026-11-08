# Weekly Meal Planner Agent

An AI agent that replaces a 1–2 hour weekly routine: scrolling saved recipes, checking the freezer, writing a grocery list, and searching for each item at Whole Foods.

**The agent:** [`.claude/skills/meal-planner/SKILL.md`](.claude/skills/meal-planner/SKILL.md), a Claude Code skill run with `/meal-planner`. How the prompt evolved: [`PROMPT_EVOLUTION.md`](PROMPT_EVOLUTION.md).

It searches **every** recipe saved on **Pinterest** and **Instagram** (not just recent ones), checks the **weather** and the **pantry**, and plans an **organic, gluten-free** week as a whole: cook nights share ingredients, and every leftover portion is assigned to a quick night. It checks **Whole Foods** prices and availability (with the **lowest price across nearby Instacart stores** as the fallback) and fits the plan under a **weekly budget**. **After you approve it**, the agent fills your Whole Foods and Instacart carts. You only check out.

## How it works

| Step | What happens | Done by |
|---|---|---|
| 1. Collect | Every Pinterest pin and Instagram save (cached in the browser), scored in code against the pantry and weather; 7-day weather | Claude in Chrome + Python (weather) |
| 2. Get ingredients | Opens each shortlisted recipe page or reel and reads its structured recipe data (schema.org JSON-LD) or caption | Claude in Chrome (Python fallback) |
| 3. Plan | Plans the week as a whole: shared ingredients, a leftover for every quick night, a protein, a grain, and a vegetable in every meal, freezer first, gluten-free enforced | Claude |
| 4. Check | Reads the cart, searches each item at Whole Foods, picks the product, falls back to the cheapest nearby Instacart store (read-only) | Claude in Chrome |
| 5. Budget | Totals real prices against the weekly budget, revises if over, itemizes what planning saved | Claude |
| 6. Preview | Opens an HTML page with the budget, the meal plan, any questions, and the list by store, then **stops for approval** | Claude |
| 7. Cart | Adds the approved products to the Whole Foods and Instacart carts with a small in-browser script, then re-reads each cart to verify (never checks out) | Claude in Chrome |
| 8. Summary | What was added, the butcher list, budget vs. spend logged week over week | Claude |

**Design:** code fetches and parses; Claude makes the decisions. Guardrails: nothing is added without approval, the agent never checks out, never touches items already in your cart unless you ask (otherwise it can only undo its own mistakes), all meat goes to the butcher, and it asks when a gluten-free swap is uncertain.

The agent's instructions are in [`.claude/skills/meal-planner/SKILL.md`](.claude/skills/meal-planner/SKILL.md). The preview page layout is in [`templates/`](templates/). The starting build prompt is in [`prompts/`](prompts/), and every version since is summarized in [`PROMPT_EVOLUTION.md`](PROMPT_EVOLUTION.md).

## Setup

1. Install [Claude Code](https://claude.com/claude-code) and the **Claude in Chrome** extension (paid Claude plan).
2. In Chrome, log into Amazon (with your Whole Foods store selected), Instagram, Pinterest, and Instacart.
3. Copy the templates and fill them in:
   ```
   cp -r data.example data
   ```
4. From this folder, run `claude --chrome`, then type `/meal-planner`.

Python 3.9+, standard library only. No API keys: weather comes from Open-Meteo and Zippopotam.

## Known limitations (POC)
- Pinterest and Instagram saves are read through the sites' own web endpoints in the logged-in browser, which are undocumented and could change. `scripts/fetch_pins.py` is a logged-out fallback that may miss pins.
- Instagram has no API for saved posts, so the agent reads them in the browser.
- Whole Foods and Instacart have no public cart APIs, so the agent uses the browser in the user's own logged-in session.

- [Privacy Policy](PRIVACY.md)
