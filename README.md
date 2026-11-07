# Weekly Meal Planner Agent

An AI agent that replaces a 1–2 hour weekly routine: scrolling saved recipes, checking the freezer, writing a grocery list, and searching for each item at Whole Foods.

It reads recent recipe saves from **Pinterest** and **Instagram**, checks the **weather** and the **pantry**, and proposes a **gluten-free** plan for the week (cook nights plus quick nights covered by leftovers). It also builds a shopping list grouped by store. **After you approve it**, the agent adds the items to your **Whole Foods** cart and checks **Safeway on Instacart** for anything Whole Foods doesn't carry.

## How it works

| Step | What happens | Done by |
|---|---|---|
| 1. Collect | Pinterest board RSS, Instagram collection, 7-day weather | Python + Claude in Chrome |
| 2. Get ingredients | Opens each pin's recipe site and parses its structured recipe data (schema.org JSON-LD) | Chrome + Python |
| 3. Plan | Picks meals for the weather, uses the freezer first, shares ingredients, enforces gluten-free | Claude |
| 4. Preview | Shows the plan and the list by store, then **stops for approval** | Claude |
| 5. Cart | Reads the cart, matches products, adds them to the Whole Foods cart, falls back to Instacart | Claude in Chrome |
| 6. Summary | What was added, the butcher list, what's left to do | Claude |

**Design:** code fetches and parses; Claude makes the decisions. Guardrails: nothing is added without approval, the agent never checks out or deletes anything, all meat goes to the butcher, and it asks when a gluten-free swap is uncertain.

The agent's instructions are in [`.claude/skills/meal-planner/SKILL.md`](.claude/skills/meal-planner/SKILL.md). The build prompts are in [`prompts/`](prompts/).

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
- The Pinterest RSS feed exposes only ~25 pins. The Pinterest API (pending approval) will replace it.
- Instagram has no API for saved posts, so the agent reads them in the browser.
- Whole Foods and Instacart have no public cart APIs, so the agent uses the browser in the user's own logged-in session.

- [Privacy Policy](PRIVACY.md)
