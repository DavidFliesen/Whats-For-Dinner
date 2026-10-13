"""Grow the recipe library with original, healthier home-cooking recipes from every cuisine.

Run daily by .github/workflows/grow-recipes.yml. Needs ANTHROPIC_API_KEY (FDC_API_KEY optional).

For each new recipe:
  1. Claude writes an original recipe for the cuisine with the fewest recipes so far, using only foods from
     pipeline/nutrients.json (or naming a new food, which is looked up in USDA FoodData Central);
  2. code computes calories, protein, fat, carbs, fiber and sodium per serving from the gram amounts, and the
     vegetarian / vegan / gluten-free / dairy-free flags from the ingredients — never from the AI;
  3. a second Claude pass reviews it (authentic, safe temperatures, amounts match steps) and anything doubtful is dropped.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai import AI, MODEL  # noqa: E402
from common import DATA, ROOT, Http, log, norm, read_json, today, write_json  # noqa: E402

HERE = Path(__file__).resolve().parent
NUTRIENTS = HERE / "nutrients.json"
CUISINES = HERE / "cuisines.json"
INDEX = DATA / "recipes" / "index.json"
AUTO_ID = "w4d-auto"
PHOTOS = ["salmon", "bowl", "chicken", "fish", "grill", "stirfry", "tacos", "plated", "fishplate", "soup", "vegbowl", "breakfast",
          "salad", "asiandish", "vegsoup", "pasta", "curry", "bbq", "sandwich", "steak", "ramen", "pancakes"]
MAX_FILE_BYTES = 1_500_000


def load_all_recipes() -> tuple[dict, list[dict]]:
    idx = read_json(INDEX, {"version": 1, "collections": []})
    allr = []
    for c in idx.get("collections", []):
        d = read_json(ROOT / c["file"], {}) or {}
        allr += d.get("recipes", []) if isinstance(d, dict) else d
    # the app's built-in recipes
    html = (ROOT / "index.html").read_text(encoding="utf-8") if (ROOT / "index.html").exists() else ""
    for m in re.finditer(r'"title": "([^"]+)"[^{}]*?"cuisine": "([^"]*)"', html):
        allr.append({"title": m.group(1), "cuisine": m.group(2)})
    return idx, allr


def pick_cuisines(allr: list[dict], n: int) -> list[dict]:
    cz = read_json(CUISINES, {})["cuisines"]

    def count(label):
        rx = re.compile(r"^" + re.escape(label) + r"\b", re.I)
        return sum(1 for r in allr if rx.search(r.get("cuisine", "") or ""))

    salt = today()
    ranked = sorted(cz, key=lambda c: (count(c["label"]), hashlib.md5((salt + c["label"]).encode()).hexdigest()))
    return ranked[:n]


def fdc_lookup(http: Http, query: str) -> list[float] | None:
    key = os.environ.get("FDC_API_KEY", "")
    if not key:
        return None
    url = ("https://api.nal.usda.gov/fdc/v1/foods/search?pageSize=3&dataType=Foundation,SR%20Legacy&api_key="
           + urllib.parse.quote(key) + "&query=" + urllib.parse.quote(query[:80]))
    try:
        foods = http.get(url, gap=1.0).json().get("foods", [])
    except Exception:  # noqa: BLE001
        return None
    for f in foods:
        v = {}
        for nut in f.get("foodNutrients", []):
            num = str(nut.get("nutrientNumber", ""))
            v[num] = nut.get("value")
        p, fat, c = v.get("203"), v.get("204"), v.get("205")
        if p is None or fat is None or c is None:
            continue
        kcal = v.get("208") or v.get("957") or v.get("958") or (4 * p + 4 * c + 9 * fat)
        return [round(float(kcal), 1), float(p), float(fat), float(c), float(v.get("291") or 0), float(v.get("307") or 0)]
    return None


def compute(recipe: dict, foods: dict) -> dict | None:
    tot = [0.0] * 6
    flags = set()
    for ing in recipe["ingredients"]:
        f = foods.get(ing["food"])
        if not f:
            return None
        g = float(ing.get("grams") or 0)
        if g < 0 or g > 3000:
            return None
        for k in range(6):
            tot[k] += f["per100"][k] * g / 100
        if g > 0:
            flags |= set(f.get("flags", ""))
    s = max(1, int(recipe.get("servings") or 2))
    per = [x / s for x in tot]
    veg = not (flags & {"m", "f"})
    return {"calories": round(per[0] / 5) * 5, "protein": round(per[1]), "fat": round(per[2], 1), "satFat": None,
            "carbs": round(per[3]), "fiber": round(per[4]), "sodium": round(per[5] / 5) * 5,
            "vegetarian": veg, "vegan": veg and not (flags & {"d", "e", "h"}), "glutenFree": "g" not in flags, "dairyFree": "d" not in flags}


def slug(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", norm(s))).strip("-")[:48]


def write_recipe(ai: AI, http: Http, cz: dict, nutr: dict, titles: set[str], same_cuisine: list[str]) -> dict | None:
    foods = nutr["foods"]
    food_list = "\n".join(f"{k}: {v['name']}" for k, v in foods.items())
    system = (
        "You are a recipe developer for a free, health-focused dinner app used worldwide. Write ONE original dinner recipe "
        "(your own words; not copied from any book or website) that people really cook at home in the given cuisine, "
        "made a little lighter without losing its character: lean proteins, plenty of vegetables, measured oil, little added salt. "
        "Serves 2. Give each ingredient TWICE: US measures ('us') and metric ('metric'), plus its weight in grams for 2 servings "
        "('grams') and a 'food' key chosen from the FOOD LIST that best matches it nutritionally. Use food 'none' for herbs, "
        "dried spices, water and other things with negligible nutrition. If nothing in the list fits a significant ingredient, use "
        "'new:<plain USDA-style description>' and add 'flags' (letters: m meat, f fish/seafood, d dairy, e egg, g gluten, h honey). "
        "Write oven and food-safety temperatures in °F (e.g. 'until it reaches 165°F'). Steps: 3 to 7, short and clear. "
        f"Pick 'photo' from: {', '.join(PHOTOS)}. 'course' is main, side or light. "
        'Reply with JSON only: {"title","desc","cuisine","course","minutes","servings":2,"servingSize",'
        '"ingredients":[{"us","metric","grams","food","flags"}],"steps":[...],"photo"}')
    avoid = "; ".join(same_cuisine[:40]) or "none yet"
    content = (f"Cuisine: {cz['label']} ({cz['hint']}). Use exactly \"{cz['label']}\" as the cuisine.\n"
               f"Already in the app for this cuisine (write something different): {avoid}\n\nFOOD LIST (key: food):\n{food_list}")
    r = ai.ask_json("recipe", content, system, model=MODEL, max_tokens=3000)
    if not r or not isinstance(r.get("ingredients"), list) or not isinstance(r.get("steps"), list):
        return None
    title = str(r.get("title", "")).strip()[:120]
    if not title or norm(title) in titles:
        log("recipe skipped (duplicate or untitled):", title)
        return None
    if not (3 <= len(r["ingredients"]) <= 22 and 2 <= len(r["steps"]) <= 10):
        return None
    for ing in r["ingredients"]:
        f = str(ing.get("food", "")).strip()
        if f.startswith("new:"):
            desc = f[4:].strip()
            key = "fdc-" + slug(desc)[:30]
            if key not in foods:
                vals = fdc_lookup(http, desc)
                if not vals:
                    log("recipe skipped: unknown food", desc)
                    return None
                foods[key] = {"name": desc, "per100": vals, "flags": re.sub(r"[^mfdegh]", "", str(ing.get("flags", ""))), "src": "fdc"}
                nutr["_dirty"] = True
            ing["food"] = key
        elif f not in foods:
            log("recipe skipped: food key not in list", f)
            return None
    rec = {"servings": 2, "ingredients": r["ingredients"]}
    nut = compute(rec, foods)
    if not nut or not (120 <= nut["calories"] <= 1100):
        log("recipe skipped: implausible nutrition", title, nut and nut["calories"])
        return None
    photo = r.get("photo") if r.get("photo") in PHOTOS else "plated"
    recipe = {
        "id": "w4d-auto-" + slug(title), "title": title, "desc": str(r.get("desc", ""))[:240], "cuisine": cz["label"],
        "course": r.get("course") if r.get("course") in ("main", "side", "light") else "main",
        "minutes": int(r.get("minutes") or 30), "servings": 2, "servingSize": str(r.get("servingSize", ""))[:80], **nut, "fried": False,
        "ingredients": [str(i.get("us", ""))[:160] for i in r["ingredients"]],
        "ingredientsMetric": [str(i.get("metric", ""))[:160] for i in r["ingredients"]],
        "steps": [str(s)[:400] for s in r["steps"]], "photo": photo,
        "source": {"name": "What's 4 Dinner? kitchen"}, "added": today(),
        "_grams": [[i["food"], i.get("grams")] for i in r["ingredients"]],
    }
    if re.search(r"\b(deep[- ]fr|deep fry|fried)\b", " ".join(recipe["steps"]) + " " + title, re.I):
        recipe["fried"] = True
    # Second opinion.
    review_sys = ("You are a strict recipe editor. Check this recipe for a dinner app. Reply with JSON only: "
                  '{"ok": true|false, "problems": ["..."]}. Mark ok=false if ANY of these: it is not a real home-cooking dish of the stated '
                  "cuisine; amounts don't match the steps or don't serve 2; a step is unsafe (e.g. poultry or pork not cooked to a safe "
                  "temperature, raw kidney beans not boiled); ingredients are missing from the steps or vice versa; the gram weights are "
                  "far off the US/metric amounts.")
    rv = ai.ask_json("review", str({k: recipe[k] for k in ("title", "cuisine", "ingredients", "ingredientsMetric", "steps", "_grams")}),
                     review_sys, model=MODEL, max_tokens=600)
    if not rv or rv.get("ok") is not True:
        log("recipe rejected by review:", title, (rv or {}).get("problems"))
        return None
    del recipe["_grams"]
    return recipe


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=int(os.environ.get("W4D_RECIPES_PER_RUN") or 4))
    a = ap.parse_args(argv)
    ai, http = AI(max_calls=a.count * 3), Http()
    if not ai.on:
        print("No ANTHROPIC_API_KEY set, so no new recipes this time. Add it under Settings → Secrets → Actions.")
        return 0
    nutr = read_json(NUTRIENTS)
    idx, allr = load_all_recipes()
    titles = {norm(r.get("title", "")) for r in allr}
    # Find (or start) the current auto collection file.
    autos = [c for c in idx["collections"] if c["id"].startswith(AUTO_ID)]
    cur = autos[-1] if autos else None
    if not cur or (ROOT / cur["file"]).exists() and (ROOT / cur["file"]).stat().st_size > MAX_FILE_BYTES:
        n = len(autos) + 1
        cid = AUTO_ID if n == 1 else f"{AUTO_ID}-{n}"
        cur = {"id": cid, "name": "What's 4 Dinner? World Kitchen (growing)", "file": f"data/recipes/{cid}.json",
               "credit": "What's 4 Dinner? kitchen", "publishedNutrition": False}
        idx["collections"].append(cur)
    data = read_json(ROOT / cur["file"], {"collection": cur["id"], "recipes": []})
    added = []
    for cz in pick_cuisines(allr, a.count):
        same = [r["title"] for r in allr + data["recipes"] if re.match(re.escape(cz["label"]) + r"\b", r.get("cuisine", ""), re.I)]
        rec = write_recipe(ai, http, cz, nutr, titles, same)
        if rec:
            ids = {r["id"] for r in data["recipes"]}
            while rec["id"] in ids:
                rec["id"] += "-2"
            data["recipes"].append(rec)
            titles.add(norm(rec["title"]))
            added.append(f"{rec['title']} ({rec['cuisine']}, {rec['calories']} kcal)")
    if added:
        data["generated"] = today()
        data["note"] = "Original recipes written by AI and checked by a second AI pass; nutrition computed from USDA values by code."
        write_json(ROOT / cur["file"], data)
        idx["updated"] = today()
        write_json(INDEX, idx)
    if nutr.pop("_dirty", False):
        write_json(NUTRIENTS, nutr)
    msg = "### New recipes\n" + ("\n".join(f"- {x}" for x in added) if added else "- none passed review this time")
    print(msg)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
