# What’s 4 Dinner? — Version 3.1.0
An ARTEZIQ app.

## What’s new in 3.1.0
- **24 new recipes in a World Kitchen collection** (`data/recipes/w4d-world.json`), each for 2 servings with US and metric amounts:
  - **Northern Irish & Irish (12):** lean Irish stew, beef and Guinness stew, chicken and leek filo pie, baked salmon with champ and kale, pork tenderloin with colcannon and Bramley apple, lighter seafood chowder, mussels in Armagh cider, lighter Ulster fry, chicken-sausage coddle, boxty with smoked salmon, hake with crushed potatoes and peas, and vegetable and pearl barley broth.
  - **Around the world (12):** Japanese miso salmon, Korean bibimbap, Greek cod plaki, Spanish shrimp and chickpea stew, Turkish red lentil soup, Lebanese chicken shawarma bowl, Mexican fish Veracruz, Peruvian chicken with salsa criolla, Jamaican jerk chicken with rice and peas, Ethiopian misir wot, Chinese steamed fish with ginger and scallion, and Indian chana masala.
  - Nutrition is estimated per serving from USDA FoodData Central values, and the recipe page says so.
- **North Coast and Derry~Londonderry restaurants researched** (`data/areas/north-coast-derry-researched.json`). 41 places across Portstewart, Coleraine, Portrush, Bushmills, Portballintrae, Ballintoy, Ballycastle, Limavady and Derry~Londonderry:
  - 38 have real photos from their official tourism listings (Visit Causeway Coast and Glens, Visit Derry, Discover Northern Ireland), credited with a link.
  - 11 have healthier picks taken from their own menus or reviews.
  - All have addresses, and most have websites.
- **Smarter matching.** Researched places now match map listings whose names differ a little (e.g. “1894” or “Harry’s Shack Portstewart”). A match needs a shared distinctive word within about 250 m, and town names don’t count. Researched addresses and websites fill gaps in the map data.
- More UK food names (beef mince, cornflour, plain flour, swede, pak choi, tinned, semi-skimmed milk, back bacon).

## Fixes in 3.0.1
- **GPS names your town, not a tiny map locality.** “Use my current location” now names the nearest city or town (e.g. Summerville, SC) instead of a small named place like “Pinehill” that OpenStreetMap has outside town limits. Falls back to the county if no town is found.
- Asks the device for its precise location (instead of accepting a 5-minute-old, rough one), and if the device only gives an approximate fix (common on Wi-Fi-only iPads), says how far off it may be and suggests typing the town.

## What’s new in 3.0.0
- **Growing data library.** Recipes and restaurant research now live in data files under `data/` (see `data/README.md`), so new collections can be added without changing the app.
- **27 NIH heart-healthy recipes** (`data/recipes/nhlbi.json`) with NIH’s published per-serving nutrition, cuisine, servings and a link to each original — including Southern, Creole, Cajun, Latino, Filipino, Vietnamese, Hawaiian and Native American dishes. Eat In now has 48 recipes.
- Recipe details show servings and serving size, credit the source, and add **More recipes like this** links to Food Network, Allrecipes and BBC Good Food (links only; nothing copied).
- Missing nutrients are hidden and ignored by filters instead of showing as zero.
- **Researched restaurants** (`data/areas/researched.json`): a first set of Charleston-area Gullah Geechee and soul food restaurants with healthier picks and cited sources. Hand-researched entries match restaurants by name, and several data files can cover the same area (notebook + research combine).
- “How we check these” lists the recipe sources.

## Changes in 2.9.3
- Shopping list has a third button, **Clear all**, next to Share list and Clear checked. It asks for a second tap (“Tap to confirm”, within 3 seconds) so a list isn’t wiped by accident.
- **Clear checked** is greyed out until at least one item is checked.

## Fixes in 2.9.2
- The **Save / Saved** button in recipe and dish details now shows a filled orange heart (with a light orange button) when saved, matching the heart on the cards. Tapping it again unsaves and returns it to an outline.

## Fixes in 2.9.1
- **Location suggestions**: typing “Summerville, SC” now puts the town of Summerville, South Carolina first. Typed state abbreviations are understood, towns rank above neighbourhoods, and neighbourhoods show their town (e.g. “Pinehill, Summerville, SC”). Pressing Enter only takes the top suggestion when it matches what you typed; otherwise it looks up exactly what you typed.
- **“Couldn’t reach the restaurant map”**: restaurant search now uses a lighter query and tries three public OpenStreetMap servers (overpass-api.de, overpass.private.coffee, maps.mail.ru), twice, before giving up. The error message now says whether you’re offline or the map is busy. The retired overpass.kumi.systems server was removed.
- The notebook uses the same servers and retries.

## What’s new in 2.9.0
- **Cuisine picker in Dine Out**, right under the location: pick one or more cuisines (with counts), or “Any”. Built from the restaurants actually nearby, so it works in every country and picks up local styles automatically (e.g. Roman in Rome, Sichuan in China).
- **Local favorites** shown first where they’re a regional specialty: Gullah Geechee (NC–FL coastal corridor), Lowcountry (SC/GA coast), Southern, Soul food and Carolina barbecue (Carolinas), Cajun & Creole (LA/MS), Tex-Mex (TX/NM/AZ), seafood (coasts), Irish and pub food (Ireland & Northern Ireland), plus the national cuisine elsewhere.
- Regional ordering tips in each restaurant’s details (e.g. Gullah Geechee, Lowcountry, Southern, Soul food, Cajun, Creole, barbecue, Irish, pub).
- Pubs that serve food are now included (important in the UK and Ireland).
- `area_builder.ipynb` now tags local cuisines from words on each restaurant’s own website (e.g. red rice, okra soup, shrimp and grits, Ulster fry, champ), so places the map doesn’t label still show up under Gullah Geechee, Lowcountry, Irish, etc.
- Cuisine choice is remembered, and resets when you pick a new location.

## 2.8.0
- **Researched areas**: Summerville & Charleston, SC and Portstewart & Londonderry, Northern Ireland. Run `area_builder.ipynb` in Google Colab (free T4 GPU, no API keys) and upload the `data/areas/` files it produces. The app then loads them automatically when your location is in one of those areas:
  - **Real photos** from each restaurant’s own website (tagged “Real photo”).
  - **Menu picks**: up to 6 healthier dishes copied word-for-word from the restaurant’s online menu and tagged with the app’s filters. These also count when filtering. Every pick is checked against the downloaded menu text; anything not on the menu is discarded.
  - Chains are skipped (the app handles them) and sites whose robots.txt disallows bots are respected.
- **Import JSON** moved from the header into **How we check these**; it accepts a meals file or an area file (for checking before publishing).
- **How we check these** link now shows in Dine Out too.
- Service worker always fetches the newest area data, with an offline fallback.
- Replaces `agent_pipeline.ipynb` / `agent_pipeline_oss.ipynb` (safe to delete).

## 2.7.0
- **Healthier** filter, on by default. Dine Out hides burger, pizza and fried-chicken fast food, dessert/ice-cream/doughnut shops and chips shops (with a one-tap “Turn off Healthier” link showing how many are hidden). Eat In and restaurant dishes require ≤ 500 cal, ≤ 15 g fat and < 800 mg sodium.
- **Filters now narrow restaurants in every country**: low calorie, low sodium, GLP-1, high protein, vegetarian, gluten-free and dairy-free match places by cuisine, sit-down vs fast food, and OpenStreetMap diet tags (e.g. diet:vegan, diet:gluten_free). Cards show which of your filters each place suits.
- **Dishes with published nutrition** show the chain’s real logo (from Wikidata) or a clean name tile — no more mismatched stock food photos.
- **Remembers your last settings**, including the city (blank only on the very first visit), mode, filters, radius, measurements and cuisine.

## 2.6.0
- **Photos & reviews buttons that match the country**: Google Maps and Tripadvisor everywhere, plus Yelp (US/Canada), Tabelog (Japan), Naver Map (Korea), Dianping (China), Zomato (India) and TheFork (much of Europe).
- **Get it delivered**: the main delivery apps for 70+ countries (e.g. DoorDash/Uber Eats/Grubhub in the US; Deliveroo/Just Eat/Uber Eats in the UK and Ireland; Wolt, Glovo, Swiggy, Zomato, GrabFood, Rappi, iFood, talabat and more elsewhere), plus “Order direct” when the restaurant has a website and “Other apps” as a catch-all. Buttons open a search for that restaurant — no APIs, no keys.
- **Delivers / Takeout (Takeaway) badges and filters** from OpenStreetMap tags. Coverage is partial, so untagged places may still deliver.
- Dishes with published nutrition also get the review and delivery buttons.

## 2.5.0
- **Location starts blank** with a prompt to type a town/city/postcode or use GPS. Locations aren’t remembered between visits.
- **Real restaurant photos where free sources have them**: a photo mapped to the restaurant in OpenStreetMap, or from Wikidata/Wikimedia Commons (the place itself, else its chain — photo first, then logo). Cards are tagged “Real photo”, “Chain photo” or “Logo”, with credit/license links in the popup.
- Restaurants without a real photo get a varied cuisine photo (picked per restaurant) so neighbours rarely look identical.
- New **See photos & reviews** button opens the restaurant on Google Maps; **Directions** is separate.
- Credited to **ARTEZIQ**.

## 2.4.0
- **Location suggestions as you type** (after 3 letters), worldwide — e.g. “Portste” offers Portstewart, Northern Ireland. Uses Photon (OpenStreetMap data, no API key). Arrow keys + Enter work; Enter picks the top suggestion.
- **Dine Out fits on screen**: the hero shrinks to a slim Eat In / Dine Out bar in Dine Out, the empty chain section is hidden, and the page scrolls to the results after every search.
- **International recipes**: 6 new dishes (Indian chicken tikka, Moroccan tagine, Thai larb, Irish cod with champ, Vietnamese pho-style soup, Italian turkey meatballs) — 21 total — with a cuisine filter.
- **Measurements**: US (cups, oz, °F), UK & Ireland (metric + UK food names like courgette, prawns, spring onions, coriander), or Metric. Picked automatically from the device language; change it anytime next to the recipe count.

## 2.3.0
- **Dine Out works worldwide.** Location search is no longer limited to the US — try “Portstewart, Northern Ireland” or “London, England”. GPS works anywhere too.
- Locations outside the US show as “Town, Region” (e.g. “London, England”).
- Chain dishes with published nutrition (Chipotle, Chick-fil-A) only appear for US locations, since those numbers are for US menus.

## 2.2.0
- **Surprise Me wheel**: the header button (and floating button on phones) opens a spinning wheel built from the meals or restaurants that match your current mode, filters and search. Up to 12 random picks per wheel; the pointer lands on the winner, which you can open or spin again.

## 2.1.0

- Restored the original look: white page, navy hero card with Eat In / Dine Out switch, colored filter pills, Plus Jakarta Sans.
- Every recipe, restaurant dish and restaurant has a food photo. Tapping the photo, title or button opens the detail popup (photo header, pinned close button).
- Photos have automatic backups: if one fails to load, a similar photo is swapped in.
- “Decide For Me” and “Import JSON” are back in the header; “Decide for me” also floats on phones.
- Service worker caches photos you’ve viewed so they work offline.

A mobile-first PWA that helps you decide dinner: **Eat in** (home recipes) or **Dine out** (real restaurants near you), with optional filters.

## 2.0.0
- **Filters are user choices again**: Low calorie (≤ 450), Low sodium (< 500 mg), GLP-1 friendly, High protein (30 g+), plus Vegetarian, Gluten-free, Dairy-free, Under 25 min and Saved.
- **Flags are calculated from the numbers**, never trusted from a data file. GLP-1 friendly = ≥ 25 g protein, ≤ 15 g fat, ≤ 500 cal, not fried.
- **No invented restaurants.** Dine Out finds real places within 5/10/20 mi using OpenStreetMap (no API key). Typed city/ZIP and GPS both work.
- Restaurants without published nutrition get cuisine-specific ordering tips that adapt to your active filters. Chains that publish nutrition (Chipotle, Chick-fil-A) show dishes with real numbers when one is in your radius.
- 15 home recipes with nutrition estimated from USDA FoodData Central values for the listed amounts.
- Shopping list, saved meals, and “Decide for me” (now visible on phones).
- Real offline support: service worker caches the app shell; the last restaurant search is saved on the device.
- Official logo and new app icons (including maskable).
- Imported JSON is validated and escaped, and persists on the device.

## Files
index.html · manifest.json · sw.js · assets/logo.png · icons/*

## Import format (for the upcoming research notebook)
A JSON array of meals. Required: `title`, `type` (`"eat-in"` or `"dine-out"`).
Optional: `desc, venue, address, lat, lon, calories, protein, sodium, fat, carbs, fiber, minutes, fried, vegetarian, vegan, glutenFree, dairyFree, source ("published"|"estimated"), sourceUrl, order, ingredients[], steps[]`.

Not medical advice.
