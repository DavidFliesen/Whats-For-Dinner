# World restaurant data — sources and licenses

The tiles in `data/world/tiles/` are built automatically by `pipeline/grow.py`. They combine:

| Source | What we use | License / terms |
|---|---|---|
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | Restaurant names, locations, cuisine, diet tags, websites, opening hours, photo tags | © OpenStreetMap contributors, [ODbL 1.0](https://opendatacommons.org/licenses/odbl/). The tiles are a derived database and are offered under the ODbL. |
| [Overture Maps Places](https://docs.overturemaps.org/attribution/) | Extra restaurants, categories, websites, phones, addresses | [CDLA Permissive 2.0](https://cdla.dev/permissive-2-0/), © Overture Maps Foundation and its contributors |
| [Wikidata](https://www.wikidata.org) | Links to photos and logos | CC0 |
| [Wikimedia Commons](https://commons.wikimedia.org) | Photos and logos (linked, not copied) | Each file's own free license, shown on its Commons page (linked from the app) |
| [GeoNames](https://www.geonames.org) | Town and city list used to order the work | CC BY 4.0 |
| Restaurants' own websites | The main image (linked, not copied), a link to the menu, and dish names copied word-for-word from the published menu | Facts with a link back to the restaurant. robots.txt is respected. |

Menu picks are chosen by an AI (Claude) and kept only if each dish name appears word-for-word in the menu that was read.
