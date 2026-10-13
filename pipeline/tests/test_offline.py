"""Offline end-to-end test: runs the pipeline against canned responses in tests/fixtures.

    python pipeline/tests/test_offline.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIPE = HERE.parent
REPO = PIPE.parent


def run(args, env):
    r = subprocess.run([sys.executable, *args], env=env, capture_output=True, text=True)
    print(r.stdout[-3000:], r.stderr[-3000:])
    assert r.returncode == 0, f"{args} failed"
    return r.stdout


def main():
    tmp = Path(tempfile.mkdtemp(prefix="w4d-test-"))
    shutil.copytree(REPO / "data" / "recipes", tmp / "data" / "recipes")
    shutil.copy(REPO / "index.html", tmp / "index.html")
    (tmp / "pipeline").mkdir()
    snap = (PIPE / "nutrients.json").read_text()
    env = dict(os.environ, W4D_ROOT=str(tmp), W4D_FIXTURES=str(HERE / "fixtures"), ANTHROPIC_API_KEY="test", PYTHONDONTWRITEBYTECODE="1")
    try:
        run([str(PIPE / "grow.py"), "--minutes", "1"], env)
        run([str(PIPE / "grow.py"), "--place", "Portstewart", "--minutes", "1"], env)
        run([str(PIPE / "recipes.py"), "--count", "1"], env)
        run([str(PIPE / "validate.py")], env)
    finally:
        (PIPE / "nutrients.json").write_text(snap)
    tiles = list((tmp / "data" / "world" / "tiles").glob("*/*.json"))
    assert tiles, "no tiles written"
    t = json.loads((tmp / "data/world/tiles/580/693.json").read_text())
    by = {p["n"]: p for p in t["places"]}
    print(json.dumps(t, indent=1)[:4000])
    assert "Drinks Only Pub" not in by and "Outside This Tile" not in by and "Morelli's" not in by
    assert "Low Confidence Diner" not in by and "Closed Grill" not in by
    hs = by["Harry's Shack"]
    assert hs["o"] == "n101" and hs["p"].startswith("+44") and "Strand" in hs["a"]
    assert hs["img"].endswith("/img/shack-dinner.jpg") and hs["imgf"] == "site" and hs["imgv"] == "food"
    assert [x["d"] for x in hs["pk"]] == ["Grilled hake, crushed potatoes, sea herbs", "Roast cauliflower, lentils, salsa verde"]
    assert "madeUpTag" not in hs["pk"][0]["f"]
    assert by["Ramore Wine Bar"]["imgf"] == "wikidata" and by["Ramore Wine Bar"]["dt"] == "v"
    assert by["Portrush Fish Bar"]["imgf"] == "commons"
    assert by["McDonald's"]["imgf"] == "brand" and by["McDonald's"]["imgk"] == "logo"
    assert by["Shenanigans Thai Kitchen"]["c"] == ["thai"] and "w" not in by["Shenanigans Thai Kitchen"]
    man = json.loads((tmp / "data/world/manifest.json").read_text())
    assert man["tiles"] >= 1 and man["places"] >= 5
    auto = json.loads((tmp / "data/recipes/w4d-auto.json").read_text())
    r = auto["recipes"][0]
    assert r["cuisine"] and r["glutenFree"] is False and r["vegetarian"] is False and r["calories"] > 100
    idx = json.loads((tmp / "data/recipes/index.json").read_text())
    assert any(c["id"] == "w4d-auto" for c in idx["collections"])
    assert (tmp / "pipeline/cache/request_result.md").exists()
    print("\nRESULT:", (tmp / "pipeline/cache/request_result.md").read_text())
    print("ALL OFFLINE TESTS PASSED", tmp)


if __name__ == "__main__":
    main()
