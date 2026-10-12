# What's 4 Dinner? data files

The app loads everything in this folder at startup, so the recipe library and restaurant
research can keep growing without changing the app itself. All files are optional.

## Recipes: `data/recipes/`

`index.json` lists the collections the app should load:

```json
{ "version": 1, "collections": [
  { "id": "nhlbi", "name": "NIH Heart-Healthy Recipes", "file": "data/recipes/nhlbi.json",
    "url": "https://…", "credit": "NIH National Heart, Lung, and Blood Institute", "publishedNutrition": true }
]}
```

Each collection file holds `{ "recipes": [ … ] }`. One recipe:

| Field | Notes |
|---|---|
| `id` | Unique, prefixed by collection (`nhlbi-…`) |
| `title`, `desc`, `cuisine` | Shown on the card |
| `course` | `main` (default), `side` or `light` |
| `minutes`, `servings`, `servingSize` | |
| `calories`, `protein`, `fat`, `satFat`, `carbs`, `fiber`, `sodium` | Per serving. Use `null` when the source doesn't publish a value — the app hides it and the filters ignore it |
| `vegetarian`, `vegan`, `glutenFree`, `dairyFree`, `fried` | `true`/`false` |
| `ingredients` | As published |
| `ingredientsMetric` | Optional metric version |
| `steps` | Short summary in our own words |
| `photo` | A stock-photo key from the app (`chicken`, `salmon`, `fish`, `fishplate`, `soup`, `vegsoup`, `bowl`, `vegbowl`, `salad`, `pasta`, `pasta2`, `plated`, `burger`, `asiandish`, `curry`, `tacos` …) or `image` with an https URL |
| `source` | `{ "name", "book", "url" }` — always link the original |

Health flags (low calorie, low sodium, GLP-1, high protein, Healthier) are always calculated by
the app from the numbers; never store them.

## Restaurants: `data/areas/`

- `index.json` — areas built by `area_builder.ipynb` (entries keyed by OpenStreetMap id).
- `researched.json` — areas researched by hand. Entries are matched by restaurant **name**
  (plus `aliases`, and optional `lat`/`lon` within 0.5 mi).

Both list areas as `{ id, name, center: [lat, lon], radius_mi, file }`. Every area file covering a
location applies, so notebook and hand research combine.

One restaurant entry:

```json
"berthas-kitchen": {
  "name": "Bertha's Kitchen", "aliases": ["Berthas Kitchen"], "address": "…",
  "cuisines": ["gullah", "soul"],
  "picks": [ { "dish": "Okra soup", "note": "…", "fits": ["lowCal"] } ],
  "photo": "https://… (optional)", "website": "https://…", "menuUrl": "https://…",
  "sourceName": "Charleston City Paper", "sourceUrl": "https://…", "checked": "2026-10-12"
}
```

`fits` may use: `lowCal`, `lowSodium`, `glp1`, `highProtein`, `vegetarian`, `glutenFree`, `dairyFree`.
Cuisine keys include `gullah`, `lowcountry`, `southern`, `soul`, `bbq`, `cajun`, `creole`,
`seafood`, `irish`, `pub`, plus any OpenStreetMap cuisine value.

## Sources and rules

- Use only sources that allow reuse (U.S. government recipes such as NIH/NHLBI, open data such as
  OpenStreetMap, Overture Maps and Foursquare Open Source Places) or facts with a link back.
- Never copy recipe text, photos or menus from commercial sites (Food Network, Allrecipes, etc.).
  The app links out to them with "More recipes like this" instead.
- Respect `robots.txt`. MyPlate Kitchen currently blocks automated reading, so it isn't included.
