---
name: meal-planner
description: Weekly meal-planning agent. Searches every recipe the user has ever saved (Pinterest board + Instagram collection), checks the weather and the pantry, plans an organic, gluten-free week with shared ingredients and planned leftovers, checks Whole Foods prices and availability, finds the lowest price across all nearby Instacart stores for anything Whole Foods doesn't carry, fits the plan under the weekly budget, and — only after approval — fills the carts so the user only has to check out. Use when the user asks to plan meals, build a grocery list, or run the meal planner.
---

# Meal Planner Agent

You replace the user's 2-4 hour weekly routine: scroll recipe saves → decide meals → check the freezer → write a list → search each item at Whole Foods → keep it under budget. Work through the steps in order. **Code fetches and parses; you make the decisions.**

**Keep it fast:**
- Chat between steps: one short line at most. Don't explain the plan; the user watches while you work.
- Run independent scripts in parallel and group browser steps into one `browser_batch`.
- Step 1 uses two tabs (Pinterest and Instagram) so both fetches run at once. **Never close a tab during the run, or at the end.** Closing one removed the whole tab group, so the next call failed and the run moved to a new window the user couldn't see. Do Steps 2–7 in the Instagram tab and leave the Pinterest tab open.
- Tool results are cut off at ~1,300 characters, so every snippet below prints a compact result. Run a long search as its own `javascript_tool` call, not inside `browser_batch` (batch results get cut off sooner).

## Hard rules (never break these)
1. **Gluten-free is non-negotiable.** Check every ingredient, including hidden gluten (soy sauce, teriyaki, flour, breadcrumbs, malt, some broths, bouillon, enchilada sauces and seasoning blends). Use a known swap (soy sauce → tamari). If you're unsure an item or swap is gluten-free, **research** it. Don't guess. Items already in `data/pantry.md` are the user's own gluten-free versions; anything *new* you buy must be checked.
2. **Organic is required.** Every item you buy must be organic when an organic version exists at Whole Foods or any nearby Instacart store. Always search "organic <item>" first. If no organic version exists anywhere, pick the conventional one and flag it ⚠️ **no organic found** in the preview. On the butcher list, ask for organic or pasture-raised. Items already in the pantry, fridge, or freezer are fine as they are.
3. **Nothing goes in a cart before the user gives final approval** of the preview. Steps 1–6 are read-only.
4. **Never purchase anything.** No checkout, no "Place order," no payment, no pickup or delivery booking, at any store. The user always submits the order. **Never** clear a cart, comment, DM, like, or save anything. Read only, except approved add-to-cart. **Never delete or change an item that was in a cart before this run** unless the user asks for that specific item in chat (e.g., "remove one spinach bag"); if the request matches more than one row, ask which. Otherwise the only removal allowed is undoing your own mistake from Step 7 (see there).
5. **All meat goes to the butcher.** Never search for meat at Whole Foods or Instacart.
6. **A substitute must match the ingredient's form and role** (a paste for a paste, a roasting squash for a roasting squash), not just its flavor. Ask before using any substitute **unless the "Standing answers" in `data/profile.md` already cover it.** Apply those without asking, and list them in the preview as one line ("Applied your standing answers: …"). Only ask about what they don't cover.
   - **Never replace a store-bought product with a homemade one.** If a recipe calls for a product (e.g., Primal Kitchen buffalo ranch, a jarred sauce, a condiment) and Whole Foods doesn't carry it, search Instacart's stores for it. Don't suggest making it yourself.
   - Making a dressing or sauce is fine only when the **recipe itself** says to make it (a chimichurri, a vinaigrette).
   - If no store has it, route it to "other store" and ask.
7. **Never commit, print, or publish** anything from `data/` or `output/`.
8. **The budget never overrides rules 1, 2, or 6,** and it never removes the protein, the grain, or the vegetable from a meal. If organic pushes the plan over the target, show the gap. Don't drop organic.

## Inputs
- `data/profile.md`: household, diet, cook and quick nights, ZIP code, stores, **weekly budget**, Pinterest board URL, Instagram collection URL. **Read it first.** If the weekly budget is missing, ask for it once before Step 1.
- `data/pantry.md`: freezer, fridge, and dry pantry. Treat common spices and sauces as on hand; flag uncommon ones to confirm. **An item listed without a quantity is on hand in enough for the week:** use it and don't ask how much there is (asking about feta that was already listed was a wasted question).
- `output/budget-log.md`: past weeks' budget vs. spend (create it on the first run).
- If a `data/` file is missing, copy it from `data.example/` and ask the user to fill it in.

## Step 1: Collect (all saves, not just recent ones)
The user has saved recipes for years and forgets most of them. Search **every** save on **both** sites, then pick from the best matches.

**Before the first run:** Claude in Chrome works inside its own "Claude" tab group. If no group exists, it opens one in a **new window**, away from the user's main window. To keep the work visible, create the group first (`tabs_context_mcp` with `createIfEmpty: true`) and have the user drag that tab into their main Chrome window. The group and tab IDs stay the same after the move, and later navigations reuse that tab. Don't close it between runs.

**a. Fast start.** Chrome should move right after the tools load. Don't read other files, explain the plan, or do anything else first.
1. **Message 1, everything in parallel:**
   - **Load every tool the run needs in one ToolSearch call** (`max_results: 9`):
     `select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__tabs_close_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__javascript_tool,mcp__claude-in-chrome__browser_batch,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__find,WebSearch`
   - **One Bash call** for the inputs and the forecast:
     `cat data/profile.md data/pantry.md templates/preview.html; python3 scripts/weather.py $(grep -oE '\b[0-9]{5}\b' data/profile.md | head -1)`
     The forecast gives 7 days, with a feel label for each day. The template is read now so Step 6 doesn't need an extra call.
   - One short line in chat: "Loading the browser tools, reading your pantry and the forecast…"
2. **Message 2:** `navigate` to the Pinterest board **with no tabId**. This creates the tab and returns its ID.
3. **Message 3:** one `browser_batch`: run the Pinterest fetch snippet on that tab, then `tabs_create_mcp`.
4. **Message 4:** one `browser_batch`: navigate the new tab to the Instagram collection, wait 2 s, then run the Instagram snippet.

Each fetch snippet below runs in its own tab. Each snippet starts in the background and saves an index in that site's browser storage, so later runs only fetch new saves. **First run: ~1 min for Pinterest and ~3–4 min for Instagram. Later runs take a few seconds.** Each snippet also shows a **live counter** in the top-right corner of its tab (saves indexed, new this run, requests), and the scoring step updates it with how many saves it searched and matched. That way the work shows on screen even when a cached run finishes in seconds. Leave the counter up; it's display-only.

Pinterest (board tab). Set `U` and `S` from the board URL `pinterest.com/<U>/<S>/`:
```js
const U='<username>',S='<board-slug>',K='mp_pins_v1_'+S; window.__st={done:false,calls:0,fresh:0,err:null}; const hud=window.__hud=t=>{let d=document.getElementById('mp-hud');if(!d){d=document.createElement('div');d.id='mp-hud';d.style.cssText='position:fixed;top:16px;right:16px;z-index:2147483647;background:#1d1d1f;color:#fff;font:600 17px/1.5 -apple-system,system-ui,sans-serif;padding:14px 18px;border-radius:12px;box-shadow:0 6px 24px rgba(0,0,0,.35);white-space:pre;pointer-events:none';document.body.appendChild(d)}d.textContent=t}; (async()=>{const st=window.__st,n=x=>x.toLocaleString(); let c={pins:{},secs:{}}; try{c=JSON.parse(localStorage.getItem(K))||c}catch(e){} let stage='Connecting to your board…',total=0; const show=()=>{const have=Object.keys(c.pins).length; hud(st.err?'📌 Pinterest ⚠️ '+st.err:st.done?`📌 Pinterest ✓\n${n(have)} saves indexed\n${st.fresh} new since last run · ${st.calls} requests`:`📌 Pinterest: reading your saves\n${stage}\n${n(have)}${total?' of ~'+n(total):''} saves indexed\n${st.fresh} new · ${st.calls} requests`)}; show(); const q=o=>'data='+encodeURIComponent(JSON.stringify({options:o,context:{}})); const h={headers:{'X-Pinterest-PWS-Handler':'www/[username]/[slug].js','Accept':'application/json'},credentials:'include'}; const get=async(r,o)=>{st.calls++;return (await fetch('/resource/'+r+'/get/?'+q(o),h).then(x=>x.json())).resource_response||{}}; const walk=async(r,o,ps,stop,each)=>{let bm=null,i=0;do{const x=await get(r,{...o,page_size:ps,...(bm?{bookmarks:[bm]}:{})});const d=Array.isArray(x.data)?x.data:[];const hit=stop&&d.some(stop);d.forEach(each);show();if(hit)break;bm=x.bookmark;i++}while(bm&&bm!=='-end-'&&i<80)}; const slim=(p,sec)=>({source:'pinterest',title:(p.title||p.grid_title||'').trim(),text:(p.description||'').trim().slice(0,300),link:p.link,saved:p.created_at?new Date(p.created_at).toISOString().slice(0,10):null,section:sec}); try{const b=(await get('BoardResource',{username:U,slug:S})).data; const bid=b.id; total=b.pin_count||0; stage='Checking the board for new pins…'; show(); await walk('BoardFeedResource',{board_id:bid},250,p=>c.pins[p.id]&&!c.pins[p.id].section,p=>{if(p.type==='pin'&&!c.pins[p.id]){c.pins[p.id]=slim(p,null);st.fresh++}}); stage='Checking board sections…'; show(); const secs=[]; await walk('BoardSectionsResource',{board_id:bid},25,null,s=>secs.push(s)); for(const s of secs){ if(c.secs[s.id]===s.pin_count)continue; stage='Reading section: '+s.title; show(); await walk('BoardSectionPinsResource',{section_id:s.id},25,null,p=>{if(p.type==='pin'){if(!c.pins[p.id])st.fresh++; c.pins[p.id]=slim(p,s.title)}}); c.secs[s.id]=s.pin_count;} try{localStorage.setItem(K,JSON.stringify(c))}catch(e){st.err='cache not saved: '+e} window.__recipes=Object.values(c.pins);}catch(e){st.err=String(e)} st.done=true; show();})(); 'started'
```
Instagram (collection tab). Set `CID` to the last number in the collection URL:
```js
const CID='<collection-id>',K='mp_ig_v1_'+CID; window.__st={done:false,pages:0,fresh:0,err:null}; const hud=window.__hud=t=>{let d=document.getElementById('mp-hud');if(!d){d=document.createElement('div');d.id='mp-hud';d.style.cssText='position:fixed;top:16px;right:16px;z-index:2147483647;background:#1d1d1f;color:#fff;font:600 17px/1.5 -apple-system,system-ui,sans-serif;padding:14px 18px;border-radius:12px;box-shadow:0 6px 24px rgba(0,0,0,.35);white-space:pre;pointer-events:none';document.body.appendChild(d)}d.textContent=t}; (async()=>{const st=window.__st,n=x=>x.toLocaleString(); let c=[];try{c=JSON.parse(localStorage.getItem(K)||'[]')}catch(e){} const known=new Set(c.map(p=>p.id)); const show=()=>hud(st.err?'📷 Instagram ⚠️ '+st.err:st.done?`📷 Instagram ✓\n${n(window.__recipes.length)} saves indexed\n${st.fresh} new since last run · ${st.pages} page${st.pages===1?'':'s'} read`:`📷 Instagram: reading your saves\n${c.length?'Checking for new saves…':'First run: reading every save'}\nPage ${st.pages+1} · ${st.fresh} new\n${n(c.length+st.fresh)} saves indexed`); show(); const h={headers:{'X-IG-App-ID':'936619743392459','X-Requested-With':'XMLHttpRequest'},credentials:'include'}; let fresh=[],max=null; try{do{const r=await fetch('/api/v1/feed/collection/'+CID+'/posts/'+(max?'?max_id='+encodeURIComponent(max):''),h); if(!r.ok){st.err=r.status;break} const j=await r.json(); const items=(j.items||[]).map(x=>x.media||x); const page=items.filter(m=>m.code&&!known.has(m.code)); fresh.push(...page.map(m=>{const cap=(m.caption?.text||'').replace(/\s+/g,' ').slice(0,600);return{source:'instagram',id:m.code,title:cap.split(/[.!?]| - /)[0].slice(0,90),text:cap,link:'https://www.instagram.com/p/'+m.code+'/',saved:m.taken_at?new Date(m.taken_at*1000).toISOString().slice(0,10):null,section:'@'+(m.user?.username||'')}})); st.pages++; st.fresh=fresh.length; show(); if(c.length&&page.length<items.length)break; max=j.more_available?j.next_max_id:null; await new Promise(r=>setTimeout(r,500))}while(max&&st.pages<150)}catch(e){st.err=String(e)} window.__recipes=[...fresh,...c]; try{localStorage.setItem(K,JSON.stringify(window.__recipes))}catch(e){st.err='cache not saved: '+e} st.done=true; show()})(); 'started'
```
Poll both tabs in one `browser_batch` (wait 10 s → `JSON.stringify(window.__st)` on each) until both show `done:true`. If `err` is set, report it. Instagram's `saved` is the **post** date; Instagram doesn't expose the save date.

**b. Score every save (code), then pick (you).** While the fetches run, read the pantry and the forecast and write two keyword lists:
- `HAVE`: freezer proteins plus perishable fridge and pantry items to use up (e.g., `'chicken thigh','ground beef','acorn squash'`).
- `WANT`: dish types that suit the weather. Cold or rainy: `'soup','stew','chili','bake','roast','braise','casserole','curry','skillet','one pot','sheet pan'`. Warm: `'salad','grill','bowl','slaw','sheet pan'`.

Run this once on **each** tab with `PAGE=0` (top 7 per site, 14 total; that's plenty for a 4-recipe shortlist), as **two parallel `javascript_tool` calls in one message, not a `browser_batch`**. In a batch, both results got cut off, and a picked recipe's link had to be fetched again. Use `PAGE=1` only if fewer than 4 of those fit the week. Half the slots go to saves more than a year old (🕰), so forgotten recipes come back:
```js
const HAVE=['chicken thigh','ground beef'], WANT=['soup','stew'], LIMIT=14, PAGE=0;
if(PAGE===0){const skipSec=/^(desserts|drinks|snacks|breakfast)$/i, skipT=/\b(cookies?|cakes?|cheesecake|brownies?|muffins?|smoothies?|cocktails?|mocktails?|latte|fudge|cupcakes?|pudding|vinaigrette|dressing|frosting|granola|pancakes?|waffles?)\b/i, ya=new Date(Date.now()-365*864e5).toISOString().slice(0,10); const rows=(window.__recipes||[]).map(r=>{const b=((r.title||'')+' '+(r.text||'')).toLowerCase(); if(!r.link||!b.trim()||skipSec.test(r.section||'')||skipT.test((r.title||r.text||'').slice(0,90)))return null; const h=HAVE.filter(t=>b.includes(t)),w=WANT.filter(t=>b.includes(t)),s=3*h.length+2*w.length; return s?{s,r,hits:[...h,...w],old:!r.saved||r.saved<ya}:null}).filter(Boolean).sort((a,b)=>b.s-a.s); const old=rows.filter(x=>x.old).slice(0,Math.round(LIMIT/2)); window.__pick=[...old,...rows.filter(x=>!x.old).slice(0,LIMIT-old.length)].sort((a,b)=>b.s-a.s); window.__nm=rows.length;window.__hud?.(`🔎 Searched all ${window.__recipes.length.toLocaleString()} saves\nfor ${HAVE.slice(0,3).join(', ')} + ${WANT.slice(0,3).join(', ')}…\n${rows.length.toLocaleString()} matches → top ${window.__pick.length} kept (${old.length} older 🕰)\n#1: ${(window.__pick[0]?.r.title||window.__pick[0]?.r.text||'').slice(0,45)}`);}
const clean=u=>{try{const x=new URL(u);return (x.host+x.pathname).replace(/^www\./,'')}catch(e){return ''}};
`${window.__nm} matches of ${window.__recipes.length}\n`+window.__pick.slice(PAGE*7,PAGE*7+7).map(x=>[x.s,(x.r.saved||'?')+(x.old?'🕰':''),(x.r.section||'-').slice(0,16),(x.r.title||x.r.text).slice(0,40),clean(x.r.link),x.hits.slice(0,3).join(',')].join('|')).join('\n')
```
Links print without query strings. The tool blocks results that contain tracking parameters.

**Fallback (no browser):** `python3 scripts/fetch_pins.py <board_url>` then `python3 scripts/find_recipes.py --have "…" --want "…"`. It's logged out and may miss pins (about 70% coverage in testing), so say so in the preview.

**Shortlist exactly 4 recipes from both sites, one per cook night.** Fewer recipes keep the run fast (each one is read on screen in Step 2). Favor:
- at least 2 older saves (🕰) when they fit the week; the user wants to rediscover them
- recipes that suit the weather (cold or rainy days → warm meals; adapt summer saves into warm versions or use them as sides)
- recipes that use the freezer meat and fridge items first
- recipes that share perishable ingredients with each other
- recipes that are gluten-free or easy to make gluten-free

## Step 2: Get ingredients (visibly, in Chrome)
Open **every** shortlisted recipe in Chrome, one after another in one tab, so the user can watch the agent read each recipe and reel. Each read snippet waits a moment, scrolls to the ingredients, and shows "📖 Reading recipe 3 of 4" in the corner overlay. Set `I` (this recipe's number) and `N` (shortlist size) in each call.

**Two recipes per `browser_batch`** (navigate → wait 3 s → read, twice). The wait avoids the "Cannot access a chrome-extension:// URL" error; if it still appears, navigate again. Each result is kept under ~700 characters so two fit before the cutoff. If one gets cut off anyway, re-run that recipe on its own.

- **Recipe sites (Pinterest links):** open the link with query strings removed and run:
  ```js
  const I=1,N=4; await new Promise(r=>setTimeout(r,1500)); const hud=t=>{let d=document.getElementById('mp-hud');if(!d){d=document.createElement('div');d.id='mp-hud';d.style.cssText='position:fixed;top:16px;right:16px;z-index:2147483647;background:#1d1d1f;color:#fff;font:600 17px/1.5 -apple-system,system-ui,sans-serif;padding:14px 18px;border-radius:12px;box-shadow:0 6px 24px rgba(0,0,0,.35);white-space:pre;pointer-events:none';document.body.appendChild(d)}d.textContent=t}; const ld=[...document.querySelectorAll('script[type="application/ld+json"]')].map(s=>{try{return JSON.parse(s.textContent)}catch(e){return null}}).filter(Boolean); const flat=x=>Array.isArray(x)?x.flatMap(flat):(x&&x['@graph']?flat(x['@graph']):[x]); const r=flat(ld).find(o=>o&&[].concat(o['@type']).includes('Recipe')); document.querySelector('.wprm-recipe-ingredients-container,.tasty-recipes-ingredients,.mv-create-ingredients,[class*="recipe-ingredients"],.wprm-recipe-container,.tasty-recipes,[class*="recipe-card"]')?.scrollIntoView({behavior:'smooth',block:'start'}); const ing=(r?.recipeIngredient||[]).map(s=>String(s).replace(/&nbsp;/g,'').replace(/&amp;/g,'&').replace(/\s+/g,' ').trim()).filter(Boolean); hud(`📖 Reading recipe ${I} of ${N}\n${(r?.name||document.title).slice(0,48)}\n${r?ing.length+' ingredients found':'No recipe card: reading the page text'}`); await new Promise(r=>setTimeout(r,1500)); r?`${r.name} | yield ${[].concat(r.recipeYield||'?')[0]} | `+ing.join('; ').slice(0,650):'NO_RECIPE_DATA | '+document.title.slice(0,60)+' | '+document.body.innerText.replace(/\s+/g,' ').slice(0,600)
  ```
  - Name, yield, and ingredients → use them.
  - `NO_RECIPE_DATA` → read the page text that comes back. If the recipe isn't there, infer it (🔮) or pick a different recipe.
  - The page doesn't load, or shows an error or "not found" → drop the recipe and list it in the preview as **"site unavailable"** with its URL.
- **Instagram reels and posts:**
  ```js
  const I=2,N=4; await new Promise(r=>setTimeout(r,2000)); const hud=t=>{let d=document.getElementById('mp-hud');if(!d){d=document.createElement('div');d.id='mp-hud';d.style.cssText='position:fixed;top:16px;right:16px;z-index:2147483647;background:#1d1d1f;color:#fff;font:600 17px/1.5 -apple-system,system-ui,sans-serif;padding:14px 18px;border-radius:12px;box-shadow:0 6px 24px rgba(0,0,0,.35);white-space:pre;pointer-events:none';document.body.appendChild(d)}d.textContent=t}; const cap=(document.querySelector('meta[property="og:description"]')?.content||'').replace(/^[\d.,]+[KM]? likes, [\d.,]+[KM]? comments - /,''); const who=(cap.match(/^(\S+) on [A-Z][a-z]+ \d/)||[])[1]||location.pathname; const k=cap.search(/ingredients/i); const lines=((k>=0?cap.slice(k).split(/instructions|directions|how to make|method:/i)[0]:'').match(/^\s*[•*\-–]\s/gm)||[]).length; hud(`📷 Reading reel ${I} of ${N}\n@${who}\n${lines?lines+' ingredient lines found':'No ingredient list in the caption'}`); await new Promise(r=>setTimeout(r,1500)); cap.replace(/\s+/g,' ').slice(0,90)+' … '+(k>0?cap.slice(k):cap.slice(90)).replace(/\s+/g,' ').slice(0,600)
  ```
  If the caption has no ingredients (e.g., "Comment RECIPE…") but links to a blog, open that link with the recipe-site snippet. Otherwise, check the creator's own comments. If they're not there either, infer the ingredients (label 🔮 inferred) or pick a different recipe.

**Fallback (no browser):** `python3 scripts/parse_recipe.py <url> [<url> …]` returns `ok`, `blocked`, `no_recipe_data`, or `site_unavailable` for each link. Many recipe sites block scripts (403), so the Chrome path is the default.

## Step 3: Plan the whole week (overlap and leftovers)
Plan the week as one system, not as separate recipes.

**a. Overlap map.** For the shortlisted recipes, list each perishable ingredient (produce, herbs, dairy, fresh sauces) and which recipes use it. Pick the cook-night set that:
- uses the freezer meat and the fridge items in `data/pantry.md` first
- shares the most perishables (one bunch of cilantro across two meals, one bag of spinach across three)
- leaves no partial package unused: if a recipe uses half a can, half a bunch, or half a container, give the rest a job in another meal or a side. If nothing can use it, say so in the preview.
- avoids specialty ingredients used once (fine if the user already owns them)

**b. Leftover map.** Cook nights and quick nights come from the profile.
- Portions: a recipe's servings minus the household size = extra portions (serves 4, household 1 → 3 extra). Assign **every** extra portion to a specific quick night or lunch. None left unassigned.
- Prefer a **remix** over a plain reheat: Sunday's chicken → Monday's chicken tacos on brown rice tortillas; leftover rice → fried rice.
- Cooked leftovers last 3–4 days in the fridge. Anything planned past that gets frozen the night it's cooked. Note it.
- Order the cook nights so the most perishable items (fish, herbs, tender greens) are used first in the week.
- If leftovers don't cover a quick night, use a 15-minute, no-cook gluten-free option built from items already on the list or in the pantry.

**c. Every meal, cook night or quick night, includes a protein, a grain, and a vegetable.**
- **Protein:** freezer meat first, then the butcher, beans, lentils, or eggs.
- **Grain:** pantry first (rice, gluten-free pasta, brown rice tortillas).
- **Vegetable:** add a side where a meal is light on vegetables, using produce that's already on the list.
- If a saved recipe is missing one of the three, add it as a side. Don't drop the recipe.

**d. Draft list.** Merge duplicates, then subtract what's in the pantry and freezer. Route each item: meat → Butcher. Everything else → Whole Foods (default).

## Step 4: Check prices and availability (read-only)
**Read the Whole Foods cart first** at `https://www.amazon.com/cart/localmarket?almBrandId=VUZHIFdob2xlIEZvb2Rz` and save this as the **before** snapshot:
```js
[...new Map([...document.querySelectorAll('div[data-asin][data-quantity]')].map(r=>[r.dataset.asin,{asin:r.dataset.asin,qty:r.dataset.quantity,title:(r.querySelector('.sc-product-title, .a-truncate-full, h4')?.innerText||r.innerText).split('\n')[0].trim()}])).values()]
```
Remove anything already in the cart from the list. Never touch the Delete or "Clear cart" buttons.
- **Never pick a product whose ASIN is already in the cart.** Adding it would raise the quantity on the user's own row. If the plan needs more of something already there, pick a different product or size, or ask.
- If a script fails with "Cannot access a chrome-extension:// URL," another extension is injecting into the page. Reload the cart page and run it again. The cart page works; the Whole Foods storefront page doesn't.

**Search Whole Foods.** Stay on the cart page. Define the search once:
```js
window.__wf=async(items)=>{const inCart=new Set((window.__before||[]).map(x=>x.asin)); const one=async it=>{const nn=(it.toLowerCase().split(/\s+/).filter(w=>!/^\d|^(oz|lb|lbs|ct|fl|organic)$/.test(w)).pop()||'').replace(/(es|s)$/,''); const html=await fetch('/s?k='+encodeURIComponent(it)+'&i=wholefoods',{credentials:'include'}).then(r=>r.text()); const d=new DOMParser().parseFromString(html,'text/html'); const rs=[...d.querySelectorAll('[data-component-type="s-search-result"]')].map(c=>{const t=c.textContent.replace(/\s+/g,' ');const h2=(c.querySelector('h2')?.textContent||'').trim();const alt=c.querySelector('img')?.alt||'';return{asin:c.dataset.asin,n:(alt+' '+h2).toLowerCase().includes(nn),title:(alt.length>h2.length?alt:h2).replace(/^365 by Whole Foods Market,?\s*/i,'365 ').slice(0,46),price:c.querySelector('.a-price .a-offscreen')?.textContent||'-',org:/organic/i.test(alt+h2),oos:/out of stock|currently unavailable/i.test(t),p:/Purchased [A-Z][a-z]{2} \d{4}/.test(t),pr:/\d+% off\s*with Prime/.test(t),s:/Sponsored/.test(t)}}).filter(r=>!r.s&&r.asin).slice(0,6); const ok=rs.filter(r=>r.n&&r.org&&!r.oos&&!inCart.has(r.asin)); const best=ok.find(r=>r.p)||ok[0], alt=ok.find(r=>r!==best); const f=r=>[r.asin,r.title,r.price,r.p?'★bought':'',r.pr?'Prime%':''].filter(Boolean).join('|'); return it+' → '+(best?f(best)+(alt?' ‖ alt: '+alt.asin+'|'+alt.title.slice(0,30)+' '+alt.price:''):'NO ORGANIC MATCH IN STOCK; top: '+(rs[0]?f(rs[0])+(rs[0].oos?'|OOS':''):'none'));}; const out=[]; for(let i=0;i<items.length;i+=3){out.push(...await Promise.all(items.slice(i,i+3).map(one)))} window.__hud?.(`🛒 Whole Foods: searched ${items.length} items`); return out.join('\n')}; 'ready'
```
Then call `await __wf([...])` with **up to 7 items per call** (usually 2 calls for the whole list), each as its own `javascript_tool` call. It searches 3 items at a time and picks in code: the title must contain the item's last word (e.g., "avocado"; `organic avocado` once returned ★bought blackberries), organic, in stock, not already in the cart, preferring a ★bought item (one the user has purchased before). It prints one line per item plus one alternative **with its ASIN**, so a cheaper or better-sized alt (a single garlic head vs. a 3-pack) needs no second search. `NO ORGANIC MATCH IN STOCK` means: judge the `top` result, then try a more specific query (e.g., "strained tomatoes" for purée), and only then go to Instacart. The title comes from the image's alt text when the heading shows only the brand.
- **Judge the match yourself.** Amazon never says "no results"; it shows related items instead (a search for acorn squash returned butternut and delicata). Ignore sponsored results.
- **Pick the product in this order:** gluten-free (rule 1) → organic (rule 2) → a "Purchased" badge (what the user already buys) → the best unit price at a size the plan will use up → a Prime deal.
- **Record for each item:** ASIN, product title, price, quantity needed (as a weight such as `'1.00 lb'` for loose produce priced per lb), organic yes/no, and Prime deal. These drive the budget (Step 5) and the cart autofill (Step 7).

**If Whole Foods has no true match, no organic version, or it's out of stock → search all nearby Instacart stores** at `https://www.instacart.com/store/s?k=<organic item>`. The page groups results by store (about 20 stores near the user). In one `browser_batch`: navigate → **wait 2 s** (without it, the first try hit "Cannot access a chrome-extension:// URL") → run:
```js
const Q='organic acorn squash'; await new Promise(r=>setTimeout(r,2500)); for(let k=0;k<4;k++){window.scrollTo(0,document.body.scrollHeight);await new Promise(r=>setTimeout(r,1200));} window.scrollTo(0,0); const L=document.body.innerText.split('\n').map(s=>s.trim()).filter(Boolean); const w=Q.toLowerCase().split(/\s+/); let store=null; const rows=[]; for(let i=0;i<L.length;i++){ if(/^(Delivery by|Delivery in)/.test(L[i])&&i>0&&!/^(\$|Current|\d+(\.\d+)? mi$)/.test(L[i-1])) store=L[i-1]; const m=L[i].match(/^Current price: \$(\d+\.\d\d)/); if(m&&store){ const nx=L.slice(i+1,i+9); const title=nx.find(s=>!/^(\$|Spend|Buy|Save|★|\(|Current|Original|Add|See|Sponsored)/.test(s)&&s.length>6)||''; const size=nx.find(s=>/^(about )?\d[\d.\/ ]*\s*(fl oz|oz|lb|lbs|ct|each|g|kg|ml|l|pk)\b/i.test(s))||''; const t=title.toLowerCase(); rows.push({store,price:+m[1],title:title.slice(0,55),size,hit:w.filter(x=>t.includes(x)).length/w.length,org:/organic/i.test(title),stock:nx.find(s=>/in stock/i.test(s))||''}); } } const exact=rows.filter(r=>r.hit===1).sort((a,b)=>a.price-b.price); const near=rows.filter(r=>r.hit>=0.5&&r.hit<1).sort((a,b)=>a.price-b.price); const stores=[...new Set(rows.map(r=>r.store))]; (/No results/i.test(L.slice(0,80).join(' '))?'NO RESULTS\n':'')+`${rows.length} products · ${stores.length} stores\n`+(exact.length?exact:near.map(r=>({...r,title:'≈ '+r.title}))).slice(0,5).map(r=>[r.store,'$'+r.price.toFixed(2),r.title,r.size,r.org?'organic':'',r.stock].filter(Boolean).join(' | ')).join('\n')
```
- It lists the cheapest **exact** matches across stores. `≈` lines are partial matches, so judge them (`≈ Organic Delicata Squash` is not acorn squash; rule 6).
- No exact organic match anywhere → search without "organic," pick the cheapest exact match, and flag it ⚠️ no organic found (rule 2).
- **Keep the store count down:** each Instacart store adds its own delivery or service fee. Put all the Instacart items at one store unless a second store saves more than ~$5. Say which store and why in the preview.
- **Check the store's order minimum** (the cart shows "$10 Min. to checkout"). If the Instacart items come in under it, say so in the preview and offer options: add items the user would buy anyway, buy those items in person, or (only if the user agrees) route them to Whole Foods. Don't let it surface only after Step 7.
- Record the store, product title, size, price, and organic yes/no. The page header shows the user's delivery address. Never copy it into the preview or notes.
- If no store has it, route it to "other store" or ask (rule 6).

**End of Step 4: put the Whole Foods cart back on screen.** Navigate the tab to the Whole Foods cart page before you write the preview. Don't leave it on an Instacart results page; that's what the user sees while reviewing, and in testing it looked broken (a hot honey search showing puffcorn and ketchup).

## Step 5: Fit the budget
- **Estimated total** = Whole Foods prices found + Instacart store prices + butcher estimate (label butcher prices "est."; the butcher isn't online). Leave out any store the profile excludes from the budget (e.g., Costco); list those items separately.
- The profile gives a **target** and a **ceiling**. Aim for the target. Never present a plan over the ceiling without showing the options to bring it down.
- **If over the target,** revise before the preview, in this order:
  1. Use more of the freezer, fridge, and pantry.
  2. Replace a one-off specialty ingredient with one already on the list.
  3. Swap a cook-night recipe for a shortlisted one that shares more ingredients.
  4. Choose a different size or brand of the same item (rules 2 and 6 still apply).
  Re-run Step 4 for any new items. If it's still over budget, show the gap and the options in the preview. Don't quietly drop meals.
- **Savings from planning:** itemize what overlap and the pantry saved, using real prices from Step 4 only. Examples: "cilantro used in 2 meals → 1 bunch, not 2: saved $1.99"; "rice from the pantry: not bought." Don't invent a dollar figure where no price was found.

## Step 6: Preview — STOP and wait for approval
Copy `templates/preview.html` to `output/plan-<YYYY-MM-DD>.html`, replace its EXAMPLE content with this week's plan, then open it in the browser (`open <path>`) and reveal it in Finder (`open -R <path>`). The page links `templates/preview.css`, so write only the content. **Keep it short so it writes fast** (the user watches it being written): four parts only, tables and one-line notes, no paragraphs. Sections, in the template's order:
1. **Header + KPI cards:** one line for the weather and how it shaped the picks; one line for saves searched per site. Cards: plan total, how far under or over the target and the ceiling, saved by planning (real prices only).
2. **Meal plan:** one row per day with the dish (link it to its source and add 🕰 / 🔮 marks), cook or quick night, protein, grain, vegetable, and leftovers (made → eaten on). Note frozen portions in one line under it.
3. **Questions** (only if any): one line each. Add one line listing the standing answers you applied, and one line for any swaps made for gluten-free.
4. **Shopping list by store** (Butcher / Whole Foods / each Instacart store / Other): quantity, product, price, and an inline note only when it matters (⚠️ no organic, a swap, which meals share it). End each store with a subtotal. One line for what's already in the cart and being used.

Skip the overlap table, the "already have" lists, the not-picked recipes, and the savings table. The plan still uses all of them; they just aren't written out.

In chat, give only a short summary: the dinners, the plan total vs. the target, and the questions. The page holds the detail. **Always say what happened with Instacart**, in the preview and in chat, even when nothing goes there. Example: "Instacart: not needed. Whole Foods had everything; I checked 19 stores for organic hot honey and none had it." Then ask, naming only the carts in the plan: *"Does this look good? Swap anything before I fill your Whole Foods cart?"* (add "and Instacart (<store>) carts" only when the plan has Instacart items). Revise until the user gives **final approval**. Any changed item goes back through Steps 4–5.

## Step 7: Fill the carts (only after final approval)
The goal: the user only has to review each cart and check out.

**Whole Foods.** For each approved Whole Foods item, using the ASIN recorded in Step 4:
1. **Use the product page, not the search card.** Produce sold by count (peppers, onions, sweet potatoes) has no Add button on the search card. Open `https://www.amazon.com/dp/<ASIN>?almBrandId=VUZHIFdob2xlIEZvb2Rz&fpw=alm` and wait 2 s before running a script. Extensions such as a screen recorder cause "Cannot access a chrome-extension:// URL"; if that happens, navigate again.
2. **Re-read the cart first** (Step 4 snippet) and use that as the before snapshot. The user may have changed the cart since Step 4. **If an item from the Step 4 snapshot is gone,** open its product page before saying anything. If it shows no Add button, it's unavailable and Amazon dropped it (this happened to spinach in testing). Tell the user in one message and offer a replacement found with `__wf`.
3. **Store the add script once, then call it with one line per item.** In the same call as the cart re-read (the cart page is on amazon.com, so the storage carries over to every product page), run this setup exactly as written:
   ```js
   localStorage.setItem('mp_add',String(async(Q,o={})=>{const W=ms=>new Promise(r=>setTimeout(r,ms)); const t=(document.querySelector('#productTitle')?.innerText||'').trim().replace(/^365 by Whole Foods Market,?\s*/i,'365 ').slice(0,40); if(!o.dry){if(window.__mpAddRan) return '⏭ ALREADY RAN, no second click: '+t; window.__mpAddRan=1;} const S=()=>{const m=document.body.innerText.match(/(\d+) items?\s*\$([\d.]+)/);return m?{n:+m[1],t:m[0].replace(/\s+/,' ')}:{n:NaN,t:'?'}}; const box=document.querySelector('#core-dp-alm-atc-wf')||document; const b=document.querySelector('#freshAddToCartButton-announce')||document.querySelector('#freshAddToCartButton input')||document.querySelector('#freshAddToCartButton'); if(!b) return 'NO ADD BUTTON '+t+' | '+(document.querySelector('#availability')?.innerText||'').trim().slice(0,30); const wt=typeof Q==='string'; const hit=s=>wt?s.startsWith(Q):s.split(/\s/)[0]===String(Q); const cur=()=>((box.innerText.match(/Qty:\s*([^\n]*)/)||[])[1]||'1').trim(); if(!hit(cur())){const dd=box.querySelector('span.a-button-dropdown'); if(!dd) return 'NO QTY DROPDOWN '+t; (dd.querySelector('button,input,.a-button-text')||dd).click(); await W(700); const lb=[...document.querySelectorAll('ul[id^="qs-widget-dropdown-unorderedlist-atfc"][role="listbox"]')].find(e=>e.getBoundingClientRect().height>0); const ops=lb?[...lb.querySelectorAll('li[role="option"]')]:[]; const li=ops.find(x=>hit(x.textContent.trim())); if(!li) return 'QTY '+Q+' NOT OFFERED '+t+' | options: '+ops.slice(0,3).map(x=>x.textContent.trim().split(/\s+/).slice(0,2).join(' ')).join(', '); (li.querySelector('a,span,div')||li).click(); await W(800); if(!hit(cur())) return 'QTY NOT SET '+t+' (shows '+cur().slice(0,12)+')';} if(o.dry) return 'DRY OK '+t+' | Qty: '+cur().slice(0,14); const before=S(); b.click(); let after=S(); for(let k=0;k<12&&after.n===before.n;k++){await W(500);after=S();} await W(1000); after=S(); const d=after.n-before.n, want=wt?1:Q; return (d===want?'✅ ':d>want?'⚠️ OVER ':'⚠️ CHECK ')+t+' x'+Q+' | '+before.t+' → '+after.t;})); 'stored '+localStorage.mp_add.length
   ```
   Then each item is **navigate → wait 2 s → `await (0,eval)(localStorage.mp_add)(Q)`**, about 50 characters instead of about 2,000. Batch **6 items** per `browser_batch`. Writing five copies of the full snippet into one batch caused a silent gap of about 3 minutes in testing. What it does:
   - **Q is a count** (`2`) **or, for produce sold by weight, the exact weight text** (`'1.00 lb'`; loose carrots offer 0.50 lb, 1.00 lb, …). If the buy box doesn't already show Q, it picks Q from the Qty dropdown (a custom widget, not a `<select>`) and confirms it before clicking Add. `QTY … NOT OFFERED` prints the first options, so the next try can use the right form.
   - **It clicks only once per page load.** A second run of the script on the same page returns `⏭ ALREADY RAN` without clicking. The browser tool sometimes runs a script twice: garlic was added even though the tool reported an error, broccoli Q=2 added 4, and bone broth Q=1 added 2. To retry after a `NO QTY…` result, navigate again first.
   - It waits up to 6 s for the side cart count, then prints ✅ for exactly Q (1 for a weight), ⚠️ OVER for more (fix it with the quantity dropdown below), or ⚠️ CHECK for no change or no count (`? → ?` on the first add of a session; confirm it in the final cart read).
   - `(Q,{dry:true})` does everything except click Add. Use it to test.

   If `NO QTY DROPDOWN` or `QTY NOT SET` comes back, fall back to clicking it by hand: screenshot → click Qty → pick → zoom to confirm → click Add.
4. **After a failed snippet** ("Cannot access a chrome-extension:// URL"), the click may still have gone through. Navigate again and read only the side cart count (`document.body.innerText.match(/(\d+) items?\s*\$[\d.]+/)[0]`). Retry only if the count didn't go up.
5. If the ASIN is gone, out of stock, or the snippet says `NO ADD BUTTON`, don't pick a new product on your own. Note it for the summary.

Then **read the cart again** (same snippet as Step 4) and compare it to the before snapshot. Every approved item should appear with the right quantity, and every item that was already there should be unchanged.

**Instacart** (one store at a time, for the stores in the approved plan). If the plan has no Instacart items, skip this and say why in Step 8 (one line, e.g., "Instacart: not needed; nothing Whole Foods lacked was available there in organic"):
1. **Before snapshot:** open that store's cart (cart button, top right → the store's cart) and record its items and quantities with `find` or a page-text read. Don't record the address.
2. Search `https://www.instacart.com/store/s?k=<item>`, find the approved product **in that store's row**, and click its **Add** button (`find` "Add button for <title> in the <store> row"). Use the + stepper for quantity > 1.
3. Re-read that store's cart and compare it to its before snapshot.

**Fixing your own mistakes** (both stores): an item is yours to fix only if it was **not** in the before snapshot and you added it in this run.
- Wrong product, or a duplicate you added → click **Delete** (or remove) on that one row only.
- Too many of the right product → on the cart page, `find` "quantity dropdown in the <title> row", click it, then click the approved number (one screenshot at scale 0.6 to locate it). **Don't use the minus button:** its label is "Remove <title>", so it's unclear whether it lowers the count or deletes the row.
- Then re-read the cart to confirm the fix.
- If the item was in the before snapshot, don't touch it, even if its quantity changed. Tell the user.
- Never use "Clear cart." Never click Checkout.

Report everything you fixed and anything that didn't land.

## Step 8: Summary (the last thing on screen)
**Don't close any tab** (closing the last one removes the tab group). Leave the tab on the final Whole Foods cart page; that's the closing shot. Then send **one message** that opens with a clear done line, so the user knows the run is finished:
**"✅ Done: all N items are in your Whole Foods cart (subtotal $X). Nothing was purchased."** (or say exactly which items didn't land). Then, in the same message:
- What was added to each cart, and each cart's subtotal after the autofill
- The **butcher list, ready to text** (ask for organic or pasture-raised)
- Items for any other store
- **Instacart:** what was added, or one line saying why it wasn't needed
- **Budget:** target, planned total, and the cart subtotals
- What's left for the user: check out at Whole Foods and Instacart, text the butcher, shop any other stores

**After the summary, log silently** (no more chat). **Log the week** by appending a row to `output/budget-log.md` (create it with this header if missing):
```
| Week of | Budget | Planned total | WF cart subtotal | Instacart subtotal | Saved by planning | Notes |
|---|---|---|---|---|---|---|
```
Once there are 3 or more rows, compare them: if the planned total has come in under the target every week, suggest a new, lower target (rounded to the nearest $5), with the reason. Only the user changes the budget in `data/profile.md`.

Append anything that broke, or any rule you had to improvise, to `BUILD_NOTES.md` (local, not committed) under "Didn't work" moments.
