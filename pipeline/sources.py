"""Restaurant sources: OpenStreetMap (Overpass) and Overture Maps Places, merged into one list per tile."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.parse

from common import FIXTURES, Http, clean_url, km, log, read_json, same_place_name

OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
MIN_OVERTURE_CONFIDENCE = float(os.environ.get("W4D_MIN_CONFIDENCE", "0.6"))


# ---------------------------------------------------------------- OpenStreetMap
def commons_file_url(name: str) -> tuple[str, str]:
    f = re.sub(r"^File:", "", str(name), flags=re.I).strip().replace(" ", "_")
    q = urllib.parse.quote(f)
    return (f"https://commons.wikimedia.org/wiki/Special:FilePath/{q}?width=800",
            f"https://commons.wikimedia.org/wiki/File:{q}")


def photo_from_tags(t: dict) -> dict:
    c = t.get("wikimedia_commons", "")
    if re.match(r"^File:", c, re.I):
        img, page = commons_file_url(c)
        return {"img": img, "imgs": page, "imgf": "commons"}
    im = t.get("image", "")
    m = re.search(r"commons\.wikimedia\.org/wiki/(File:[^?#]+)", im, re.I)
    if m:
        img, page = commons_file_url(urllib.parse.unquote(m.group(1)))
        return {"img": img, "imgs": page, "imgf": "commons"}
    if re.match(r"^https://\S+\.(jpe?g|png|webp)(\?.*)?$", im, re.I):
        return {"img": im, "imgs": "", "imgf": "osm"}
    return {}


def _diet(t: dict) -> str:
    out = []
    for key, code in (("diet:vegetarian", "v"), ("diet:vegan", "vg"), ("diet:gluten_free", "gf"), ("diet:dairy_free", "df"), ("diet:lactose_free", "df")):
        if re.match(r"^(yes|only)$", t.get(key, ""), re.I) and code not in out:
            out.append(code)
    return ",".join(out)


def osm_places(http: Http, bbox) -> list[dict] | None:
    """All named restaurants, fast-food places and food-serving pubs in the box. None if every server failed."""
    w, s, e, n = bbox
    q = (f'[out:json][timeout:180];nwr["amenity"~"^(restaurant|fast_food|pub)$"]["name"]'
         f"({s:.5f},{w:.5f},{n:.5f},{e:.5f});out center tags;")
    data = None
    for attempt in range(2):
        for ep in OVERPASS:
            try:
                r = http.post(ep, data={"data": q}, gap=2.0, timeout=200)
                if r.status_code == 200:
                    d = r.json()
                    remark = d.get("remark", "") or ""
                    if isinstance(d.get("elements"), list) and not re.search(r"timed out|out of memory|runtime error", remark, re.I):
                        data = d
                        break
                    log("overpass remark:", remark[:120])
                else:
                    log("overpass", ep.split("/")[2], r.status_code)
            except Exception as ex:  # noqa: BLE001 - network errors of any kind mean "try the next server"
                log("overpass error", ep.split("/")[2], str(ex)[:120])
        if data:
            break
        time.sleep(20 if not FIXTURES else 0)
    if data is None:
        return None
    out = []
    for el in data["elements"]:
        t = el.get("tags") or {}
        lat = el.get("lat", (el.get("center") or {}).get("lat"))
        lon = el.get("lon", (el.get("center") or {}).get("lon"))
        if lat is None or not t.get("name"):
            continue
        if not (s <= float(lat) < n and w <= float(lon) < e):
            continue                                   # each place belongs to exactly one tile
        am = t.get("amenity")
        if am == "pub" and not re.match(r"^(yes|only)$", t.get("food", ""), re.I) and not t.get("cuisine"):
            continue
        cuisine = [c.strip().lower() for c in re.split(r"[;,]", t.get("cuisine", "")) if c.strip()]
        street = " ".join(x for x in (t.get("addr:housenumber", ""), t.get("addr:street", "")) if x)
        addr = ", ".join(x for x in (street, t.get("addr:city", ""), t.get("addr:postcode", "")) if x)
        web = t.get("website") or t.get("contact:website") or ""
        rec = {
            "o": el["type"][0] + str(el["id"]), "n": t["name"][:120], "la": round(float(lat), 5), "lo": round(float(lon), 5),
            "am": am, "c": cuisine[:4], "b": t.get("brand", "")[:60], "bwd": t.get("brand:wikidata", ""), "wd": t.get("wikidata", ""),
            "w": clean_url(web, allow_http=True), "a": addr[:160], "p": (t.get("phone") or t.get("contact:phone") or "")[:40],
            "h": t.get("opening_hours", "")[:120], "dt": _diet(t),
            "dl": "yes" if re.match(r"^(yes|only)$", t.get("delivery", ""), re.I) else ("no" if t.get("delivery") == "no" else ""),
            "tk": "yes" if re.match(r"^(yes|only)$", t.get("takeaway", ""), re.I) else ("no" if t.get("takeaway") == "no" else ""),
        }
        rec.update(photo_from_tags(t))
        out.append(rec)
    return out


# ---------------------------------------------------------------- Overture Maps
FAST_RE = re.compile(r"fast_food|burger|fried_chicken|hot_dog|chicken_wings|fish_and_chips|kebab|shawarma|food_truck|takeaway", re.I)
PUB_RE = re.compile(r"^(pub|gastropub|irish_pub|brewpub|beer_garden)$", re.I)
REST_RE = re.compile(r"restaurant|diner|steakhouse|bistro|brasserie|eatery|food_court|buffet|noodle|sushi|pizza|bbq|barbecue|"
                     r"creperie|tapas|ramen|dim_sum|izakaya|trattoria|taverna|chophouse|soul_food|cafeteria|canteen|poke|taqueria", re.I)
NOT_CUISINE = {"restaurant", "fast_food", "fast_food_restaurant", "family_style", "buffet", "diner", "eatery", "food_court",
               "gastropub", "pub", "brewpub", "bistro", "brasserie", "cafeteria", "canteen", "food_truck", "takeaway", "theme",
               "dinner_theater", "restaurant_and_bar", "bar_and_grill", "casual_dining", "fine_dining", "food", "eat_and_drink",
               "food_and_drink", "beverage", "bar", "hotel", "accommodation", "chicken_wings", "beer_garden", "irish_pub"}
CUISINE_ALIAS = {"barbecue": "bbq", "bbq": "bbq", "steakhouse": "steak_house", "cajun_creole": "cajun", "fish_and_chips": "fish_and_chips",
                 "breakfast_and_brunch": "breakfast", "burger": "burger", "pizza": "pizza", "sushi": "sushi", "seafood": "seafood",
                 "southern": "southern", "soul_food": "soul_food", "noodles": "noodle", "hot_dog": "hot_dog", "fried_chicken": "chicken",
                 "middle_eastern": "middle_eastern", "latin_american": "latin_american", "tex_mex": "tex-mex"}


def _cats(r: dict) -> tuple[list[str], list[str]]:
    """(main categories, all categories) across old and new Overture schemas."""
    cats = r.get("categories") or {}
    tax = r.get("taxonomy") or {}
    main = [c for c in (cats.get("primary"), r.get("basic_category"), tax.get("primary")) if c]
    allc = main + list(cats.get("alternate") or []) + list(tax.get("hierarchy") or [])
    return [str(c).lower() for c in main], [str(c).lower() for c in allc if c]


def classify_overture(r: dict) -> tuple[str, list[str]] | None:
    main, allc = _cats(r)
    if not main:
        return None
    m0 = main[0]
    if PUB_RE.match(m0):
        am = "pub"
    elif FAST_RE.search(m0):
        am = "fast_food"
    elif REST_RE.search(m0):
        am = "restaurant"
    else:
        return None                                 # cafes, bars, bakeries, shops and everything else
    cuisine = []
    for c in allc:
        base = re.sub(r"_(restaurant|shop|house|place|joint)$", "", c)
        base = CUISINE_ALIAS.get(base, base)
        if base in NOT_CUISINE or not re.match(r"^[a-z][a-z_-]{2,30}$", base) or base in cuisine:
            continue
        cuisine.append(base)
    if any(c in ("burger", "fish_and_chips", "hot_dog") for c in cuisine) and am == "restaurant" and FAST_RE.search(" ".join(main)):
        am = "fast_food"
    return am, cuisine[:4]


def overture_records(bbox) -> list[dict] | None:
    """Raw Overture place rows for the box (None on failure)."""
    if FIXTURES:
        rows = read_json(os.path.join(FIXTURES, "overture.json"), [])
        w, s, e, n = bbox
        return [r for r in rows if w <= (r["bbox"]["xmin"] + r["bbox"]["xmax"]) / 2 < e and s <= (r["bbox"]["ymin"] + r["bbox"]["ymax"]) / 2 < n]
    try:
        from overturemaps import core
        reader = core.record_batch_reader("place", bbox=tuple(bbox), stac=True)
        if reader is None:
            return None
        rows = []
        for batch in reader:
            rows.extend(batch.to_pylist())
        return rows
    except Exception as ex:  # noqa: BLE001
        log("overture error", str(ex)[:200])
        return None


def overture_places(bbox) -> list[dict] | None:
    rows = overture_records(bbox)
    if rows is None:
        return None
    out = []
    for r in rows:
        status = str(r.get("operating_status") or "").lower()
        if "closed" in status:
            continue
        cl = classify_overture(r)
        if not cl:
            continue
        name = ((r.get("names") or {}).get("primary") or "").strip()
        bb = r.get("bbox") or {}
        if not name or bb.get("xmin") is None:
            continue
        lat = (bb["ymin"] + bb["ymax"]) / 2
        lon = (bb["xmin"] + bb["xmax"]) / 2
        am, cuisine = cl
        brand = r.get("brand") or {}
        addrs = r.get("addresses") or []
        a0 = addrs[0] if addrs else {}
        addr = a0.get("freeform") or ""
        if addr and a0.get("locality") and a0["locality"].lower() not in addr.lower():
            addr = f'{addr}, {a0["locality"]}'
        webs = [clean_url(u, allow_http=True) for u in (r.get("websites") or [])]
        webs = [u for u in webs if u and not re.search(r"facebook\.com|instagram\.com|twitter\.com|x\.com|tiktok\.com|yelp\.|tripadvisor\.", u, re.I)]
        out.append({
            "ov": str(r.get("id") or ""), "n": name[:120], "la": round(lat, 5), "lo": round(lon, 5), "am": am, "c": cuisine,
            "b": ((brand.get("names") or {}).get("primary") or "")[:60], "bwd": brand.get("wikidata") or "",
            "w": webs[0] if webs else "", "a": addr[:160], "p": ((r.get("phones") or [""])[0] or "")[:40],
            "conf": float(r.get("confidence") or 0),
        })
    return out


# ---------------------------------------------------------------- merge
def short_id(ov: str) -> str:
    return hashlib.sha1(ov.encode()).hexdigest()[:10]


def merge(osm: list[dict], ov: list[dict]) -> list[dict]:
    """OSM is the base (it's what the app's live search uses). Overture fills gaps and adds places OSM lacks."""
    grid: dict[tuple[int, int], list[dict]] = {}
    for p in osm:
        grid.setdefault((int(p["la"] * 500), int(p["lo"] * 500)), []).append(p)

    def near(lat, lon):
        gi, gj = int(lat * 500), int(lon * 500)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                yield from grid.get((gi + di, gj + dj), [])

    added = []
    for v in ov:
        match = None
        best = 1e9
        for p in near(v["la"], v["lo"]):
            d = km(p["la"], p["lo"], v["la"], v["lo"])
            if d <= 0.12 and d < best and same_place_name(p["n"], v["n"]):
                match, best = p, d
        if match:
            for k in ("w", "a", "p", "b", "bwd"):
                if not match.get(k) and v.get(k):
                    match[k] = v[k]
            if not match.get("c") and v.get("c"):
                match["c"] = v["c"]
            match["ov"] = v["ov"]
            continue
        if v["conf"] < MIN_OVERTURE_CONFIDENCE:
            continue
        rec = {k: v[k] for k in ("n", "la", "lo", "am", "c", "b", "bwd", "w", "a", "p") if v.get(k)}
        rec["id"] = short_id(v["ov"])
        rec["ov"] = v["ov"]
        added.append(rec)
    # Overture sometimes lists one place twice; keep the first of each name within ~40 m.
    kept: list[dict] = []
    for a in added:
        if any(km(a["la"], a["lo"], k["la"], k["lo"]) < 0.04 and same_place_name(a["n"], k["n"]) for k in kept):
            continue
        kept.append(a)
    return osm + kept
