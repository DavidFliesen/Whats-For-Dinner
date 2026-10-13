"""Grow the world restaurant data, a few hundred square kilometres at a time.

Run by .github/workflows/grow-world.yml every two hours, and by add-area.yml when someone asks for a place.
Each run:
  1. builds tiles: requested ones first, then ones due for a refresh, then the next ones in the world queue
     (every town and city on Earth with 1,000+ people, biggest first);
  2. spends the rest of its time on enrichment: reading restaurants' own websites for a photo and menu link,
     and (with an API key) having Claude check photos and pick lighter dishes from published menus.

    python pipeline/grow.py --minutes 50
    python pipeline/grow.py --place "Portstewart, Northern Ireland" --minutes 25
    python pipeline/grow.py --tiles 580/695,580/696
"""
from __future__ import annotations

import argparse
import io
import math
import os
import re
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai import AI  # noqa: E402
from common import (CACHE_DIR, FIXTURES, STATE_DIR, TILES, WORLD, Http, km, log, read_json,  # noqa: E402
                    tile_bbox, tile_key, tile_of, tile_path, tiles_around, today, write_json, now_iso)
from photos import commons_near, match_commons, menu_text, read_site, wikidata_images  # noqa: E402
from sources import merge, osm_places, overture_places  # noqa: E402

QUEUE_FILE = STATE_DIR / "queue.txt"
STATE_FILE = STATE_DIR / "state.json"
GEONAMES_URL = "https://download.geonames.org/export/dump/cities1000.zip"

REFRESH_DAYS = int(os.environ.get("W4D_REFRESH_DAYS") or 180)
BUDGET_MB = float(os.environ.get("W4D_BUDGET_MB") or 900)
SITES_PER_RUN = int(os.environ.get("W4D_SITES_PER_RUN") or 400)
TILE_SHARE = float(os.environ.get("W4D_TILE_SHARE") or 0.6)        # share of the run spent building tiles
OUT_KEYS = ["o", "id", "n", "la", "lo", "am", "c", "b", "w", "a", "p", "h", "dt", "dl", "tk",
            "img", "imgs", "imgf", "imgk", "imgv", "pk", "mu", "chk", "wc"]
CARRY = ["img", "imgs", "imgf", "imgk", "imgv", "pk", "mu", "chk", "wc"]


# ---------------------------------------------------------------- world queue
def build_queue(http: Http) -> list[str]:
    """Every populated place with 1,000+ people (GeoNames, CC BY 4.0), biggest first, as tiles."""
    rows = []
    if FIXTURES:
        text = (Path(FIXTURES) / "cities.txt").read_text(encoding="utf-8")
    else:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        z = CACHE_DIR / "cities1000.zip"
        if not z.exists():
            log("downloading GeoNames cities1000")
            r = http.get(GEONAMES_URL, timeout=300)
            r.raise_for_status()
            z.write_bytes(r.content)
        with zipfile.ZipFile(z) as zf:
            text = zf.read("cities1000.txt").decode("utf-8")
    for line in io.StringIO(text):
        c = line.rstrip("\n").split("\t")
        if len(c) < 15:
            continue
        try:
            rows.append((int(c[14] or 0), float(c[4]), float(c[5])))
        except ValueError:
            continue
    rows.sort(key=lambda r: -r[0])
    seen, order = set(), []
    for pop, lat, lon in rows:
        radius = min(35.0, max(4.0, 3 + math.sqrt(max(pop, 0)) / 45))
        for i, j in tiles_around(lat, lon, radius):
            k = tile_key(i, j)
            if k not in seen:
                seen.add(k)
                order.append(k)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text("# World build order: tiles around every place with 1,000+ people (GeoNames), biggest first.\n"
                          + "\n".join(order) + "\n", encoding="utf-8")
    log(f"queue built: {len(order)} tiles from {len(rows)} places")
    return order


def load_queue(http: Http) -> list[str]:
    if QUEUE_FILE.exists():
        return [ln.strip() for ln in QUEUE_FILE.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    return build_queue(http)


# ---------------------------------------------------------------- tiles on disk
def scan_tiles() -> dict[str, tuple[str, int, int]]:
    """{key: (built, places, bytes)} read from each tile's header."""
    out = {}
    if not TILES.exists():
        return out
    for d in TILES.iterdir():
        if not d.is_dir():
            continue
        for f in d.glob("*.json"):
            try:
                head = f.open("r", encoding="utf-8").read(120)
            except OSError:
                continue
            b = re.search(r'"built":"([0-9-]{10})', head)
            n = re.search(r'"n":(\d+)', head)
            out[f"{d.name}/{f.stem}"] = (b.group(1) if b else "", int(n.group(1)) if n else 0, f.stat().st_size)
    return out


def compact(p: dict) -> dict:
    return {k: p[k] for k in OUT_KEYS if p.get(k) not in (None, "", [], {})}


def save_tile(i: int, j: int, places: list[dict], sources: list[str], built: str | None = None) -> int:
    places = sorted((compact(p) for p in places), key=lambda p: p.get("o") or ("~" + p.get("id", "")))
    return write_json(tile_path(i, j), {"v": 1, "built": built or today(), "n": len(places), "src": sources,
                                       "tile": tile_key(i, j), "places": places}, compact=True)


def build_tile(http: Http, i: int, j: int, stats: dict) -> bool:
    bbox = tile_bbox(i, j)
    osm = osm_places(http, bbox)
    if osm is None:
        log(f"tile {i}/{j}: map servers unavailable, will retry")
        return False
    ov = overture_places(bbox)
    sources = ["osm"] + (["overture"] if ov is not None else [])
    places = merge(osm, ov or [])
    # Keep what earlier runs found (photos, menu picks, website checks).
    old = read_json(tile_path(i, j), {}) or {}
    old_by = {(p.get("o") or p.get("id")): p for p in old.get("places", [])}
    for p in places:
        q = old_by.get(p.get("o") or p.get("id"))
        if q:
            for k in CARRY:
                if not p.get(k) and q.get(k):
                    p[k] = q[k]
    # Photos: OpenStreetMap tags (done in sources) > the place's Wikidata entry > Commons photos taken there > brand.
    need = [p for p in places if not p.get("img")]
    qids = [p["wd"] for p in need if p.get("wd")] + [p["bwd"] for p in need if p.get("bwd")]
    wd = wikidata_images(http, qids) if qids else {}
    for p in need:
        if p.get("wd") in wd and wd[p["wd"]]["imgk"] == "photo":
            p.update(wd[p["wd"]], imgf="wikidata")
    need = [p for p in places if not p.get("img")]
    if need:
        cells = sorted({(round(p["la"], 1), round(p["lo"], 1)) for p in need})[:9]
        match_commons(need, commons_near(http, cells))
    for p in places:
        if not p.get("img") and p.get("bwd") in wd:
            p.update(wd[p["bwd"]], imgf="brand")
    size = save_tile(i, j, places, sources)
    stats["tiles"] += 1
    stats["places"] += len(places)
    stats["new_photos"] += sum(1 for p in places if p.get("img"))
    log(f"tile {i}/{j}: {len(osm)} OSM + {len(places) - len(osm)} Overture-only, "
        f"{sum(1 for p in places if p.get('img'))} with photos, {size // 1024} KB")
    return True


# ---------------------------------------------------------------- enrichment (websites, photos, menus)
def enrich_tile(http: Http, ai: AI, i: int, j: int, deadline: float, stats: dict) -> bool:
    """Returns True when every place in the tile has been looked at."""
    path = tile_path(i, j)
    t = read_json(path)
    if not t:
        return True
    places = t.get("places", [])

    def todo(p):
        return p.get("w") and (not p.get("wc") or (ai.on and not p.get("chk") and p.get("am") != "fast_food"))

    cands = sorted([p for p in places if todo(p)], key=lambda p: (bool(p.get("b")), bool(p.get("img")) and p.get("imgf") != "brand"))
    changed = False
    finished = True
    for p in cands:
        if time.time() > deadline or stats["sites"] >= SITES_PER_RUN:
            finished = False
            break
        if not p.get("wc"):
            stats["sites"] += 1
            info = read_site(http, p)
            p["wc"] = info["wc"]
            changed = True
            cand = info.get("img_candidate")
            if cand and (not p.get("img") or p.get("imgf") == "brand" or p.get("imgk") == "logo"):
                kind = ai.check_photo(cand, p["n"]) if ai.on else None
                if kind != "other":
                    p.update({"img": cand, "imgs": p["w"], "imgf": "site",
                              "imgk": "logo" if (kind == "logo" or (kind is None and info.get("imgk") == "logo")) else "photo"})
                    if kind:
                        p["imgv"] = kind
                    stats["site_photos"] += 1
            if info.get("c") and not p.get("c"):
                p["c"] = [c for c in info["c"] if c][:3]
            if info.get("mu"):
                p["mu"] = info["mu"]
            home_text = info.get("_home_text", "")
        else:
            home_text = ""
        if ai.on and not p.get("chk") and p.get("am") != "fast_food":
            text = menu_text(http, p["mu"]) if p.get("mu") else ""
            if len(text) < 300 and len(re.findall(r"\d+[.,]\d{2}\b|[£$€]\s?\d", home_text)) >= 5:
                text = home_text                       # the home page itself is the menu
            picks = ai.menu_picks(p["n"], " ".join(p.get("c", [])), text) if text else []
            p["chk"] = today()
            changed = True
            if picks:
                p["pk"] = picks
                p["mu"] = p.get("mu") or p["w"]
                stats["menus"] += 1
    if changed:
        save_tile(i, j, places, t.get("src", ["osm"]), built=t.get("built"))
    return finished


# ---------------------------------------------------------------- requests
def geocode(http: Http, text: str):
    m = re.search(r"(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)", text)
    if m:
        lat, lon = float(m.group(1)), float(m.group(2))
        if -85 < lat < 85 and -180 <= lon <= 180:
            label = re.sub(r"\(?\s*-?\d{1,2}\.\d+\s*,\s*-?\d{1,3}\.\d+\s*\)?", "", text).strip(" ,") or f"{lat:.3f}, {lon:.3f}"
            return lat, lon, label
    q = re.sub(r"\s+", " ", text).strip()[:120]
    if not q:
        return None
    import urllib.parse
    r = http.get("https://nominatim.openstreetmap.org/search?format=json&limit=1&q=" + urllib.parse.quote(q), gap=1.5)
    try:
        hits = r.json() if r.status_code == 200 else []
    except ValueError:
        hits = []
    if not hits:
        return None
    return float(hits[0]["lat"]), float(hits[0]["lon"]), hits[0].get("display_name", q)[:120]


def place_from_issue(body: str, title: str) -> str:
    m = re.search(r"###\s*Town or city\s*\n+(.+?)(\n###|\Z)", body or "", re.S | re.I)
    text = (m.group(1) if m else "") or re.sub(r"^\s*Add area:\s*", "", title or "", flags=re.I)
    text = re.sub(r"_No response_", "", text).strip()
    return text.splitlines()[0].strip()[:160] if text else ""


# ---------------------------------------------------------------- main
def world_bytes(scan) -> int:
    return sum(v[2] for v in scan.values())


def write_manifest(scan, queue_len, cursor):
    places = sum(v[1] for v in scan.values())
    write_json(WORLD / "manifest.json", {
        "v": 1, "base": "data/world/tiles/", "tile_degrees": 0.25, "updated": now_iso(),
        "tiles": len(scan), "places": places, "queue_total": queue_len, "queue_done": min(cursor, queue_len),
        "sources": ["OpenStreetMap (ODbL)", "Overture Maps Places (CDLA Permissive 2.0)", "Wikidata (CC0)",
                    "Wikimedia Commons (various free licenses)", "GeoNames (CC BY 4.0)", "restaurants' own websites"],
        "license": "data/world/LICENSE.md"})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=50)
    ap.add_argument("--tiles", default="", help="comma-separated i/j tiles to build first")
    ap.add_argument("--place", default="", help="a town or 'lat, lon' to build first")
    ap.add_argument("--issue", action="store_true", help="read the place from ISSUE_TITLE / ISSUE_BODY env vars")
    ap.add_argument("--max-new", type=int, default=10_000)
    a = ap.parse_args(argv)

    start = time.time()
    deadline = start + a.minutes * 60
    tile_deadline = start + a.minutes * 60 * TILE_SHARE
    http, ai = Http(), AI()
    state = read_json(STATE_FILE, {}) or {}
    state.setdefault("cursor", 0)
    state.setdefault("enrich_cursor", 0)
    state.setdefault("retry", [])
    queue = load_queue(http)
    scan = scan_tiles()
    stats = {"tiles": 0, "places": 0, "new_photos": 0, "sites": 0, "site_photos": 0, "menus": 0}
    report: list[str] = []

    first: list[str] = []
    place_text = a.place
    if a.issue:
        place_text = place_from_issue(os.environ.get("ISSUE_BODY", ""), os.environ.get("ISSUE_TITLE", ""))
    if place_text:
        g = geocode(http, place_text)
        if not g:
            report.append(f"Couldn't find “{place_text}” on the map. Please add the country or the coordinates (lat, lon).")
            Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
            (CACHE_DIR / "request_result.md").write_text("\n".join(report), encoding="utf-8")
            (CACHE_DIR / "request_ok").write_text("0")
            log(report[-1])
            return 0
        lat, lon, label = g
        near = sorted(tiles_around(lat, lon, 12), key=lambda t: km(lat, lon, *_tile_mid(*t)))[:9]
        first += [tile_key(*t) for t in near]
        report.append(f"Area: {label} ({lat:.4f}, {lon:.4f}) — {len(near)} map squares.")
    if a.tiles:
        first += [t.strip() for t in a.tiles.split(",") if re.match(r"^\d+/\d+$", t.strip())]

    def run_tile(k) -> bool:
        i, j = map(int, k.split("/"))
        ok = build_tile(http, i, j, stats)
        if ok:
            scan[k] = (today(), 0, tile_path(i, j).stat().st_size)
        return ok

    # Priority places (pipeline/state/priority.txt, one "lat, lon  # name" per line) jump the queue until built.
    pri = STATE_DIR / "priority.txt"
    if pri.exists():
        for line in pri.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)", line)
            if not m:
                continue
            for t in tiles_around(float(m.group(1)), float(m.group(2)), 12):
                k = tile_key(*t)
                if k not in scan and k not in first:
                    first.append(k)
    # 1) requested tiles (always rebuilt)
    for k in first:
        if time.time() > tile_deadline + (deadline - tile_deadline) * 0.5:
            break
        if not run_tile(k) and k not in state["retry"]:
            state["retry"].append(k)
    # 2) retries, 3) refreshes due, 4) the world queue
    for k in list(state["retry"])[:20]:
        if time.time() > tile_deadline:
            break
        if run_tile(k):
            state["retry"].remove(k)
    due_before = time.strftime("%Y-%m-%d", time.gmtime(time.time() - REFRESH_DAYS * 86400))
    due = sorted((v[0], k) for k, v in scan.items() if v[0] and v[0] < due_before)
    for _, k in due[: max(3, stats["tiles"] // 3 + 5)]:
        if time.time() > tile_deadline:
            break
        run_tile(k)
    new = 0
    over_budget = world_bytes(scan) > BUDGET_MB * 1e6
    if over_budget:
        report.append(f"Size budget reached ({BUDGET_MB:.0f} MB); new areas paused. Raise W4D_BUDGET_MB or move tiles to a data repo.")
    while not over_budget and state["cursor"] < len(queue) and time.time() < tile_deadline and new < a.max_new:
        k = queue[state["cursor"]]
        if k in scan and scan[k][0]:
            state["cursor"] += 1
            continue
        if run_tile(k):
            state["cursor"] += 1
            new += 1
        else:
            if k not in state["retry"]:
                state["retry"].append(k)
            state["cursor"] += 1
            if len(state["retry"]) > 50:
                break                                   # the map servers are struggling; stop for this run
        over_budget = world_bytes(scan) > BUDGET_MB * 1e6
    state["retry"] = state["retry"][-500:]

    # Enrichment: requested tiles first, then walk the queue.
    for k in first:
        if time.time() < deadline and k in scan:
            enrich_tile(http, ai, *map(int, k.split("/")), deadline, stats)
    while time.time() < deadline and stats["sites"] < SITES_PER_RUN and state["enrich_cursor"] < len(queue):
        k = queue[state["enrich_cursor"]]
        if k not in scan:
            if state["enrich_cursor"] >= state["cursor"]:
                break                                   # caught up with the build front
            state["enrich_cursor"] += 1
            continue
        if enrich_tile(http, ai, *map(int, k.split("/")), deadline, stats):
            state["enrich_cursor"] += 1

    scan = scan_tiles()
    write_manifest(scan, len(queue), state["cursor"])
    state["last_run"] = {"at": now_iso(), "minutes": round((time.time() - start) / 60, 1), **stats,
                         "ai_calls": ai.calls, "http_requests": http.count}
    write_json(STATE_FILE, state)

    pct = 100 * min(state["cursor"], len(queue)) / max(1, len(queue))
    lines = [f"### World data run {today()}",
             f"- Built {stats['tiles']} map squares ({stats['places']} restaurants), {stats['new_photos']} with photos.",
             f"- Read {stats['sites']} restaurant websites: {stats['site_photos']} new photos, {stats['menus']} menus with lighter picks.",
             f"- AI calls: {ai.calls}{'' if ai.client or FIXTURES else ' (no ANTHROPIC_API_KEY, AI steps off)'}.",
             f"- World progress: {min(state['cursor'], len(queue))} of {len(queue)} squares ({pct:.1f}%); "
             f"{len(scan)} squares, {sum(v[1] for v in scan.values())} restaurants, {world_bytes(scan) / 1e6:.1f} MB stored."]
    lines += [f"- {r}" for r in report]
    summary = "\n".join(lines)
    print(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(summary + "\n")
    if place_text:
        req = [tile_path(*map(int, k.split("/"))) for k in first]
        got = [read_json(p, {}) for p in req if p.exists()]
        n = sum(len(t.get("places", [])) for t in got)
        ph = sum(1 for t in got for p in t.get("places", []) if p.get("img"))
        pk = sum(1 for t in got for p in t.get("places", []) if p.get("pk"))
        msg = (f"Done! {report[0]}\n\nThe app now has **{n} restaurants** there, **{ph} with photos** and **{pk} with lighter menu picks**. "
               "It can take a few minutes to appear on the site. More photos and menus are added on later runs.")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / "request_result.md").write_text(msg, encoding="utf-8")
        (CACHE_DIR / "request_ok").write_text("1")
    return 0


def _tile_mid(i, j):
    w, s, e, n = tile_bbox(i, j)
    return (s + n) / 2, (w + e) / 2


if __name__ == "__main__":
    raise SystemExit(main())
