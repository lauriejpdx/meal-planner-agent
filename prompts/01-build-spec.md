# Prompt 01 — Build Spec

Build me a weekly meal-planning agent that replaces my 1–2 hour Friday-night routine: scrolling my recipe saves, checking what's in my freezer, writing a grocery list, and searching for each item on Whole Foods.

**Context:** My profile (household, diet, cook nights, stores) is in `data/profile.md`, and my freezer and pantry are in `data/pantry.md`. Read both first. Gluten-free is non-negotiable.

**Stack:** Claude Code runs the workflow as a skill. Claude in Chrome handles every site that has no usable API, in my logged-in browser. Small Python scripts handle anything deterministic. Code fetches and parses; Claude makes the decisions.

**Workflow:**
1. **Collect:** Read my Pinterest board's RSS feed (`<board-url>.rss`) and my Instagram "Food Inspo" collection (in Chrome). Get the 7-day forecast for my ZIP code from Open-Meteo. Shortlist about 8 candidate recipes, favoring recent saves and recipes that suit the weather.
2. **Get ingredients:**
   - Pinterest: open each shortlisted pin from the board page in Chrome (the RSS pin links don't open) and take the "Visit site" URL without its query string. Parse the recipe's structured data (schema.org JSON-LD) in Python. If the site is down, skip the recipe and flag it in the preview as "site unavailable," with its URL so I can check it myself.
   - Instagram: check the caption, then the creator's own comments. If neither has the recipe, infer the ingredients and label them "inferred," or skip the post. Never comment or DM.
3. **Plan:** Pick 4 cook-night dinners (Sat, Sun, Tue, Thu) and cover the quick nights (Mon, Wed, Fri) with leftovers or 15-minute gluten-free meals.
   - Use my freezer meat first.
   - Share ingredients across meals.
   - Scale recipes for one person, with planned leftovers.
   - Add vegetable sides.
   - On cold or rainy days, favor warm meals.
   - Check every ingredient for gluten. If you're unsure of a swap, **ask me.**
4. **Preview (approval gate):** Show the recipes you pulled (with dead links flagged), the weather and how it shaped the picks, what I already have, the meal plan, and the shopping list grouped by store with an estimated cost. All meat goes to the butcher. Wait for my approval, and revise as I ask.
5. **Check and add to cart (only after final approval):**
   - Whole Foods: read my cart first. Search each item at `amazon.com/s?k=<item>&i=wholefoods` and judge whether each result actually matches the ingredient. Amazon shows unrelated items instead of "no results." Add matching items to the cart. Never remove my items, and never check out.
   - Anything not at Whole Foods: check Safeway on instacart.com. A substitute must match the ingredient's form and role (a paste for a paste). Otherwise, route the item to another store.
6. **Summary:** what was added where, what's left for me (checkout, the butcher text, other stores), and the estimated total.

**Build order:** steps 1–4 first, then step 5. Log every failure and every change to the agent prompt in `BUILD_NOTES.md`.
