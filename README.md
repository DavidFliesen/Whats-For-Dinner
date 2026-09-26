# What’s 4 Dinner? — Version 2.8.0
An ARTEZIQ app.

## What’s new in 2.8.0
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
