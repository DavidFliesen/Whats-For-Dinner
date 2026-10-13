"""Checks every data file before a run's changes are committed. Exits 1 (and nothing is committed) on any problem."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, ROOT, TILE, TILES, WORLD, tile_bbox  # noqa: E402

FITS = {"lowCal", "lowSodium", "glp1", "highProtein", "vegetarian", "glutenFree", "dairyFree"}
AMENITY = {"restaurant", "fast_food", "pub"}
errors: list[str] = []


def err(where, msg):
    if len(errors) < 200:
        errors.append(f"{where}: {msg}")


def https(u):
    return isinstance(u, str) and re.match(r"^https://\S+$", u) is not None


def check_tile(path: Path):
    try:
        t = json.loads(path.read_text(encoding="utf-8"))
    except Exception as ex:  # noqa: BLE001
        return err(path, f"not valid JSON ({ex})")
    if path.stat().st_size > 8_000_000:
        err(path, "tile over 8 MB")
    i, j = int(path.parent.name), int(path.stem)
    w, s, e, n = tile_bbox(i, j)
    if t.get("v") != 1 or not re.match(r"^\d{4}-\d\d-\d\d$", str(t.get("built", ""))):
        err(path, "bad header")
    places = t.get("places")
    if not isinstance(places, list) or t.get("n") != len(places):
        return err(path, "places missing or count wrong")
    for k, p in enumerate(places):
        where = f"{path}#{k}"
        if not isinstance(p.get("n"), str) or not p["n"].strip():
            err(where, "no name")
        if not (p.get("o") or p.get("id")):
            err(where, "no id")
        la, lo = p.get("la"), p.get("lo")
        if not isinstance(la, (int, float)) or not isinstance(lo, (int, float)) or not (s - 0.01 <= la <= n + 0.01 and w - 0.01 <= lo <= e + 0.01):
            err(where, f"coordinates outside the tile ({la}, {lo})")
        if p.get("am") not in AMENITY:
            err(where, f"bad amenity {p.get('am')}")
        for key in ("img", "imgs"):
            if p.get(key) and not https(p[key]):
                err(where, f"{key} must be https")
        if p.get("w") and not re.match(r"^https?://\S+$", p["w"]):
            err(where, "bad website")
        for pk in p.get("pk", []) or []:
            if not isinstance(pk.get("d"), str) or not pk["d"] or len(pk["d"]) > 120 or not set(pk.get("f", [])) <= FITS:
                err(where, "bad menu pick")


def check_recipes():
    idx = json.loads((DATA / "recipes" / "index.json").read_text(encoding="utf-8"))
    ids = set()
    for c in idx.get("collections", []):
        f = ROOT / c["file"]
        if not f.exists():
            err(f, "listed in index.json but missing")
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        for r in d.get("recipes", []):
            where = f"{f.name}:{r.get('id')}"
            if not r.get("id") or r["id"] in ids:
                err(where, "missing or duplicate id")
            ids.add(r.get("id"))
            for k in ("title", "ingredients", "steps"):
                if not r.get(k):
                    err(where, f"missing {k}")
            if r.get("ingredientsMetric") and len(r["ingredientsMetric"]) != len(r["ingredients"]):
                err(where, "metric and US ingredient lists differ in length")
            cal = r.get("calories")
            if cal is not None and not (50 <= cal <= 1500):
                err(where, f"calories {cal} out of range")


def changed_tiles() -> list[Path]:
    """Tiles added or modified in this run (git working tree), so big worlds validate quickly."""
    import subprocess
    out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", str(TILES)],
                         cwd=ROOT, capture_output=True, text=True).stdout
    files = []
    for line in out.splitlines():
        path = line[3:].strip().strip('"')
        p = ROOT / path
        if p.suffix == ".json" and p.exists():
            files.append(p)
    return files


def main() -> int:
    n = 0
    only_changed = "--changed" in sys.argv
    if TILES.exists():
        for f in (changed_tiles() if only_changed else TILES.glob("*/*.json")):
            check_tile(f)
            n += 1
    m = WORLD / "manifest.json"
    if m.exists():
        try:
            json.loads(m.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            err(m, "bad JSON")
    check_recipes()
    print(f"checked {n} tiles{' changed in this run' if only_changed else ''} and the recipe library; tile size {TILE}°")
    if errors:
        print("PROBLEMS:\n" + "\n".join(errors))
        return 1
    print("all good")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
