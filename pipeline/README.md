# What's 4 Dinner? — self-growing world data

This folder holds the robots that grow the app's data on their own, with no one needing to do anything.
They run free on GitHub Actions.

| Workflow | When | What it does |
|---|---|---|
| **Grow world data** (`grow-world.yml`) | Every 2 hours | Builds the next map squares of the world, refreshes old ones, reads restaurant websites and menus |
| **Add an area** (`add-area.yml`) | When someone asks | Builds one town right away (from the app's “Ask us to do this town next” link, or the Actions tab) |
| **Grow recipes** (`grow-recipes.yml`) | Daily | Writes and checks a few new original recipes, cuisine by cuisine |

## How the world fills in

1. The world is cut into squares of 0.25° (about 28 km tall). Each square becomes one small file,
   `data/world/tiles/{row}/{col}.json`, which the app loads only when someone searches there.
2. The order comes from GeoNames: every town and city with 1,000+ people, biggest first
   (`pipeline/state/queue.txt`, built on the first run). Places in `pipeline/state/priority.txt` go first.
3. For each square the robot:
   - downloads every restaurant, fast-food place and food pub from **OpenStreetMap**;
   - adds places only **Overture Maps** knows about (confidence 0.6+, not marked closed) and fills in missing websites, phones and addresses;
   - finds photos: OpenStreetMap photo tags, then the place's **Wikidata** photo, then **Wikimedia Commons** photos
     taken within 100 m that name the place, then the chain's logo.
4. With the rest of each run it visits restaurants' **own websites** (respecting robots.txt) for their main photo and menu link.
   With an AI key, Claude also:
   - checks each website photo and drops ones that aren't food, the dining room or the building;
   - reads the menu and picks up to 6 lighter dishes. Code keeps a pick only if its name is on the menu word-for-word.
5. Every square is rebuilt every 180 days, so closures and new openings show up.
6. Before anything is saved, `validate.py` checks every changed file. If anything is wrong, nothing is committed.

At 12 runs a day it should reach every town in the world within a few months, then keep refreshing. Each run's summary shows the real progress (squares done out of the total).
The live map search in the app always comes first; the world data adds places, photos and menus, and stands in when the
live map is busy.

## Recipes

`recipes.py` picks the cuisines with the fewest recipes (87 cuisines in `cuisines.json`, from Irish to Ethiopian to Peruvian)
and asks Claude for an original, lighter home-cooking recipe. Then:

- **Nutrition is computed by code** from gram weights and USDA values in `nutrients.json`, not by the AI.
  New foods are looked up in USDA FoodData Central when `FDC_API_KEY` is set.
- **Vegetarian, vegan, gluten-free and dairy-free flags are computed by code** from the ingredients.
- **A second Claude pass reviews each recipe**: it must be a real dish of that cuisine, with safe cooking temperatures and amounts that match the steps.

Anything doubtful is dropped. Recipes go to `data/recipes/w4d-auto.json`, which is registered in `index.json`.

## One-time setup (5 minutes)

1. **Upload these files** to the repo, keeping the folders (including `.github/` and `.gitignore`).
2. **Allow the robots to save:** Settings → Actions → General → *Workflow permissions* → **Read and write permissions** → Save.
3. **Optional but recommended — AI steps:** Settings → Secrets and variables → Actions → *New repository secret*
   - `ANTHROPIC_API_KEY`: your Claude API key from console.anthropic.com. Set a monthly spend limit there.
     Without it, the map data, photos and websites still grow, but menu picks, photo checks and new recipes don't.
   - `FDC_API_KEY`: a free key from api.data.gov, used for foods not in `nutrients.json`.
4. **Optional:** create an issue label named `add-area` (Issues → Labels). Requests work without it too.
5. **Start it:** Actions → *Grow world data* → **Run workflow**. After that it runs by itself.

## Settings (Settings → Secrets and variables → Actions → Variables)

| Variable | Default | Meaning |
|---|---|---|
| `W4D_AI_CALLS_PER_RUN` | 60 | Max Claude calls per world run, which caps cost (about 12 runs a day) |
| `W4D_AI_FAST_MODEL` | claude-haiku-5-5 | Model for menus and photo checks |
| `W4D_AI_MODEL` | claude-sonnet-5-5 | Model for writing and reviewing recipes |
| `W4D_RECIPES_PER_DAY` | 4 | Recipes attempted per day |
| `W4D_SITES_PER_RUN` | 400 | Restaurant websites read per run |
| `W4D_REFRESH_DAYS` | 180 | Rebuild a square after this many days |
| `W4D_BUDGET_MB` | 900 | Stop adding new squares past this size. GitHub Pages sites are limited to 1 GB |

## When the world outgrows the repo

The whole world is likely bigger than one GitHub Pages site allows (1 GB). The robot fills the most-populated places
first and pauses new squares at `W4D_BUDGET_MB`, and its run summary says so. To keep growing, make a second repo
(e.g. `Whats-For-Dinner-data`) with Pages on, move `data/world/tiles` there, and change `"base"` in
`data/world/manifest.json` to that site's address. The app reads tiles from whatever `base` says.

## Running it yourself

```bash
pip install -r pipeline/requirements.txt
python pipeline/grow.py --place "Portstewart, Northern Ireland" --minutes 10
python pipeline/recipes.py --count 1          # needs ANTHROPIC_API_KEY
python pipeline/validate.py
python pipeline/tests/test_offline.py         # full offline test with canned data, no network
```

Sources and licenses: see `data/world/LICENSE.md`.
