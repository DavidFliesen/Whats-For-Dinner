# What's 4 Dinner? data files

The app loads everything in this folder at startup, so the recipe library and restaurant
research can keep growing without changing the app itself. All files are optional.

## Recipes: `data/recipes/`

`index.json` lists the collections the app should load:

```json
{ "version": 1, "collections": [
  { "id": "nhlbi", "name": "NIH Heart-Healthy Recipes", "file": "data/recipes/nhlbi.json",
    "url": "https://…", "credit": "NIH National Heart, Lung, and Blood Institute", "publishedNutrition": true },
  { "id": "w4d-world", "name": "What's 4 Dinner? World Kitchen", "file": "data/recipes/w4d-world.json",
    "credit": "What's 4 Dinner? kitchen", "publishedNutrition": false }
]}
```

`publishedNutrition: true` means the numbers are the source's own. `false` means they're our estimates,
computed per serving from USDA FoodData Central values for the amounts listed, and the app labels
them that way.

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
- `researched.json` — areas researched by hand: `charleston-researched.json` and
  `north-coast-derry-researched.json` (Portstewart, Portrush, Coleraine, Bushmills, Ballycastle,
  Limavady, Derry~Londonderry). Entries match a map listing in either of two ways:
  - by restaurant **name** or one of its `aliases`, within 0.5 mi when `lat`/`lon` are given;
  - by location, when `lat`/`lon` are within about 250 m and the names share a distinctive word.
    Generic words and town names don't count.

Both list areas as `{ id, name, center: [lat, lon], radius_mi, file }`. Every area file covering a
location applies, so notebook and hand research combine.

One restaurant entry:

```json
"berthas-kitchen": {
  "name": "Bertha's Kitchen", "aliases": ["Berthas Kitchen"], "address": "…",
  "cuisines": ["gullah", "soul"],
  "picks": [ { "dish": "Okra soup", "note": "…", "fits": ["lowCal"] } ],
  "lat": 32.81, "lon": -79.97,
  "photo": "https://… (optional)", "photoSource": "https://… (page the photo came from)",
  "photoCreditName": "Visit Derry (optional; credits a tourism listing instead of the restaurant's own site)",
  "website": "https://…", "menuUrl": "https://…",
  "sourceName": "Charleston City Paper", "sourceUrl": "https://…", "checked": "2026-10-12"
}
```

A researched `address` or `website` is used when the map listing lacks one.

`fits` may use: `lowCal`, `lowSodium`, `glp1`, `highProtein`, `vegetarian`, `glutenFree`, `dairyFree`.
Cuisine keys include `gullah`, `lowcountry`, `southern`, `soul`, `bbq`, `cajun`, `creole`,
`seafood`, `irish`, `pub`, plus any OpenStreetMap cuisine value.

## World data: `data/world/`

Built automatically by `pipeline/grow.py` (see `pipeline/README.md`); don't edit by hand.
`manifest.json` says where the tiles are (`base`) and how far the world build has got.
Each tile `tiles/{row}/{col}.json` covers 0.25° × 0.25° (row = floor((lat+90)×4), col = floor((lon+180)×4)):

```json
{"v":1,"built":"2026-10-13","n":2,"src":["osm","overture"],"tile":"580/693","places":[
 {"o":"n101","n":"Harry's Shack","la":55.17066,"lo":-6.7276,"am":"restaurant","c":["seafood"],
  "w":"https://…","a":"118 Strand Road, Portstewart","img":"https://…","imgs":"https://… (credit page)",
  "imgf":"site","imgk":"photo","imgv":"food","pk":[{"d":"Grilled hake…","t":"note","f":["glp1"]}],
  "mu":"https://… (menu)","chk":"2026-10-13","wc":"2026-10-13"},
 {"id":"95d57e1379","n":"Shenanigans Thai Kitchen","la":55.184,"lo":-6.71,"am":"restaurant","c":["thai"]}]}
```

`o` = OpenStreetMap id (matches the app's live search); `id` = places only Overture knows about.
`imgf` = where the photo came from (`osm`, `wikidata`, `commons`, `site`, `brand`); `imgv` = what the AI photo check saw.
Licenses: `data/world/LICENSE.md`.

## Sources and rules

- Use only sources that allow reuse (U.S. government recipes such as NIH/NHLBI, open data such as
  OpenStreetMap, Overture Maps and Foursquare Open Source Places) or facts with a link back.
- Never copy recipe text, photos or menus from commercial sites (Food Network, Allrecipes, etc.).
  The app links out to them with "More recipes like this" instead.
- Respect `robots.txt`. MyPlate Kitchen currently blocks automated reading, so it isn't included.
- `data/recipes/w4d-auto*.json` is written by `pipeline/recipes.py`: original recipes, nutrition computed by code.
