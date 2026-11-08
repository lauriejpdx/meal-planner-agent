# Prompt Evolution

How the agent's prompt changed from the first spec to the current skill, [`.claude/skills/meal-planner/SKILL.md`](.claude/skills/meal-planner/SKILL.md). Each version came from running the agent end to end and fixing what broke.

## v0: Build spec
[`prompts/01-build-spec.txt`](prompts/01-build-spec.txt): read the newest Pinterest pins (RSS) and Instagram saves, shortlist about 8 recipes, plan 4 dinners, preview, then add to the Whole Foods cart and check Safeway on Instacart for anything missing.

Discovery changed the stack before any code was written. The Instagram API has no saved-posts endpoint, Pinterest's API needed a review period, and the Instacart and Whole Foods options needed business accounts. So **Claude in Chrome** does that work in my own logged-in browser, and small Python scripts handle only the fixed logic.

## v1: First working agent
- **Judge every match.** A search for "acorn squash" at Whole Foods returned butternut and delicata, and Amazon never says "no results." → The agent judges each result itself.
- **Substitutes must match the ingredient's form and role,** not just its flavor (it once offered chili crunch for chili paste).
- **Cart safety:** read the cart first and subtract what's already there; never touch Delete or "Clear cart."
- **Weather by ZIP:** Open-Meteo's geocoder didn't handle ZIP codes → Zippopotam converts ZIP → coordinates.
- **Prices before approval.** Whole Foods is searched before the preview, so the preview shows real prices, and each product's ASIN is recorded. After approval, the agent adds exactly those products, then re-reads the cart and compares it to a before snapshot.
- **Overlap and leftovers:** shared perishables across meals, every extra portion assigned to a quick night, and a protein, a grain, and a vegetable in every meal.
- **Weekly budget:** a target and a ceiling, a fixed order for revising when over, savings counted from real prices only, and a week-over-week log.
- **An HTML preview page** to review the plan, instead of a long chat message.
- The agent may undo its own wrong add, but never changes items that were already in my cart.

## v2: My corrections after full run
- **Every save, not the newest 25.** The RSS feed only showed 25 of my 2,131 pins. Now every Pinterest and Instagram save is indexed, cached in the browser, and scored in code against my freezer, pantry, and the weather. Half the shortlist goes to saves more than a year old.
- **Organic became a hard rule** next to gluten-free. The budget can't override it.
- **Instacart: lowest price across all nearby stores,** not just Safeway, with each store's order minimum checked before the preview.
- **No homemade swaps for store-bought products** (it once suggested mayo and Tabasco in place of buffalo sauce).
- **Standing answers in my profile** (herbs, cheeses, a pepper's color, and so on), so approval takes one round of questions, not three.

## v3: Fast and reliable enough to use every week
- **A 4-recipe shortlist,** one per cook night, and a fast start: every tool loads in one call, and Chrome starts moving right away.
- **A live counter on screen** while saves are searched, and each recipe is read visibly in Chrome.
- **One add-to-cart script,** stored once in the browser and called with one line per item. It sets the quantity (or the weight for loose produce), clicks only once per page load, and flags any quantity that comes in too high.
- **Never close a tab.** Closing one removed Chrome's whole tab group and broke the run.
- **Smaller fixes:** the Instacart outcome is always stated, a pantry item listed without an amount counts as enough, and the agent may remove an item that was already in my cart only when I name it in chat.
