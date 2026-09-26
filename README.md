# What’s 4 Dinner? — Version 2.0.0
A mobile-first PWA that helps you decide dinner: **Eat in** (home recipes) or **Dine out** (real restaurants near you), with optional filters.

## What’s new in 2.0.0
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
