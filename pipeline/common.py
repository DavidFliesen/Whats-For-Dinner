"""Shared helpers for the What's 4 Dinner? data pipeline.

Everything here is plain Python so it runs the same on GitHub Actions and on a laptop.
"""
from __future__ import annotations

import json
import math
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.robotparser
from datetime import date, datetime, timezone
from pathlib import Path

import requests

ROOT = Path(os.environ.get("W4D_ROOT") or Path(__file__).resolve().parent.parent)   # repo root (tests point this at a copy)
DATA = ROOT / "data"
WORLD = DATA / "world"
TILES = WORLD / "tiles"
STATE_DIR = ROOT / "pipeline" / "state"
CACHE_DIR = ROOT / "pipeline" / "cache"                 # not committed (see .gitignore); kept by actions/cache

TILE = 0.25                                             # degrees; must match index.html
USER_AGENT = os.environ.get(
    "W4D_USER_AGENT",
    "Whats4DinnerDataBot/1.0 (+https://github.com/DavidFliesen/Whats-For-Dinner; open data for a free dinner app)")

FIXTURES = os.environ.get("W4D_FIXTURES", "")           # offline test mode: read canned responses from this folder


def today() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- tiles
def tile_of(lat: float, lon: float) -> tuple[int, int]:
    i = int(math.floor((lat + 90) / TILE))
    j = int(math.floor((lon + 180) / TILE)) % int(360 / TILE)
    return i, j


def tile_bbox(i: int, j: int) -> tuple[float, float, float, float]:
    """(west, south, east, north)"""
    s = i * TILE - 90
    w = j * TILE - 180
    return (w, s, w + TILE, s + TILE)


def tile_key(i: int, j: int) -> str:
    return f"{i}/{j}"


def tile_path(i: int, j: int) -> Path:
    return TILES / str(i) / f"{j}.json"


def tiles_around(lat: float, lon: float, radius_km: float) -> list[tuple[int, int]]:
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * max(0.15, math.cos(math.radians(lat))))
    i0, j0 = tile_of(lat - dlat, lon - dlon)
    i1, j1 = tile_of(lat + dlat, lon + dlon)
    out = []
    n = int(360 / TILE)
    jj = range(j0, j1 + 1) if j1 >= j0 else list(range(j0, n)) + list(range(0, j1 + 1))
    for i in range(max(0, i0), min(int(180 / TILE) - 1, i1) + 1):
        for j in jj:
            out.append((i, j))
    return out


def km(a_lat, a_lon, b_lat, b_lon) -> float:
    r = 6371.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1, math.sqrt(h)))


# ---------------------------------------------------------------- names
GENERIC = set("""the and restaurant restaurants hotel bar bars bistro kitchen cafe café grill house inn room pub eatery
lounge tavern wine food street city coast harbour harbor golf country club fish chips seafood pizza chinese indian
takeaway take away de la le el los las da di del du und co ltd llc""".split())


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    s = re.sub(r"['’`]", "", s.lower())
    s = re.sub(r"&", " and ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def sig_words(s: str) -> set[str]:
    return {w for w in norm(s).split() if len(w) >= 4 and w not in GENERIC}


def same_place_name(a: str, b: str) -> bool:
    x, y = norm(a), norm(b)
    if not x or not y:
        return False
    if x == y or x in y or y in x:
        return True
    sa, sb = sig_words(a), sig_words(b)
    return bool(sa and sb and len(sa & sb) / min(len(sa), len(sb)) >= 0.5)


# ---------------------------------------------------------------- json
def read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, obj, compact=False) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
    else:
        text = json.dumps(obj, ensure_ascii=False, indent=1)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text + "\n", encoding="utf-8")
    tmp.replace(path)
    return len(text.encode("utf-8")) + 1


def clean_url(u: str, allow_http=False) -> str:
    u = str(u or "").strip()
    if re.match(r"^https://[^\s\"'<>]+$", u, re.I):
        return u[:500]
    if allow_http and re.match(r"^http://[^\s\"'<>]+$", u, re.I):
        return u[:500]
    return ""


# ---------------------------------------------------------------- polite HTTP
class Http:
    """One shared session with a clear User-Agent, per-host pacing, robots.txt checks and a request budget."""

    def __init__(self, min_gap=1.0):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = USER_AGENT
        self.s.headers["Accept-Language"] = "en"
        self.last: dict[str, float] = {}
        self.robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self.min_gap = min_gap
        self.count = 0

    def _pace(self, host, gap):
        t = self.last.get(host, 0)
        wait = gap - (time.time() - t)
        if wait > 0:
            time.sleep(wait)
        self.last[host] = time.time()

    def allowed(self, url: str) -> bool:
        """Respect robots.txt for websites we read (restaurant sites, menus)."""
        if FIXTURES:
            return True
        p = urllib.parse.urlsplit(url)
        base = f"{p.scheme}://{p.netloc}"
        if base not in self.robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self.s.get(base + "/robots.txt", timeout=10)
                if r.status_code >= 400:
                    rp = None                      # no robots.txt: allowed
                else:
                    rp.parse(r.text.splitlines())
            except requests.RequestException:
                rp = None
            self.robots[base] = rp
        rp = self.robots[base]
        return True if rp is None else rp.can_fetch(USER_AGENT, url)

    def get(self, url, gap=None, timeout=30, **kw):
        if FIXTURES:
            return _fixture_response(url)
        host = urllib.parse.urlsplit(url).netloc
        self._pace(host, self.min_gap if gap is None else gap)
        self.count += 1
        return self.s.get(url, timeout=timeout, **kw)

    def post(self, url, gap=None, timeout=120, **kw):
        if FIXTURES:
            return _fixture_response(url, kw.get("data"))
        host = urllib.parse.urlsplit(url).netloc
        self._pace(host, self.min_gap if gap is None else gap)
        self.count += 1
        return self.s.post(url, timeout=timeout, **kw)


class _FakeResp:
    def __init__(self, status, text, ctype="application/json", url=""):
        self.status_code, self.text, self.url = status, text, url
        self.headers = {"content-type": ctype}
        self.content = text.encode("utf-8") if isinstance(text, str) else text

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


def _fixture_response(url, data=None):
    """Offline test mode: map a URL to a canned file in W4D_FIXTURES (see pipeline/tests)."""
    folder = Path(FIXTURES)
    table = read_json(folder / "routes.json", {})
    for pattern, fname in table.items():
        if re.search(pattern, url):
            f = folder / fname
            ctype = "text/html" if fname.endswith(".html") else "application/json"
            return _FakeResp(200, f.read_text(encoding="utf-8"), ctype, url)
    return _FakeResp(404, "not found", "text/plain", url)


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)
