"""Free, credited photos for restaurants: Wikidata, Wikimedia Commons, and the restaurant's own website."""
from __future__ import annotations

import json
import re
import urllib.parse
from html.parser import HTMLParser

from common import Http, clean_url, km, log, sig_words, today
from sources import commons_file_url


# ---------------------------------------------------------------- Wikidata
def wikidata_images(http: Http, ids: list[str]) -> dict[str, dict]:
    """{Qid: {"img","imgs","imgk"}} using P18 (image), else P154 (logo)."""
    out: dict[str, dict] = {}
    ids = sorted({i for i in ids if re.match(r"^Q\d+$", i or "")})
    for k in range(0, len(ids), 50):
        chunk = ids[k:k + 50]
        url = ("https://www.wikidata.org/w/api.php?action=wbgetentities&props=claims&format=json&ids="
               + "|".join(chunk))
        try:
            r = http.get(url, gap=0.5)
            ents = r.json().get("entities", {}) if r.status_code == 200 else {}
        except Exception as ex:  # noqa: BLE001
            log("wikidata error", str(ex)[:120])
            continue
        for qid, ent in ents.items():
            claims = ent.get("claims", {}) or {}
            for prop, kind in (("P18", "photo"), ("P154", "logo")):
                try:
                    f = claims[prop][0]["mainsnak"]["datavalue"]["value"]
                except (KeyError, IndexError, TypeError):
                    continue
                img, page = commons_file_url(f)
                out[qid] = {"img": img, "imgs": page, "imgk": kind}
                break
    return out


# ---------------------------------------------------------------- Commons photos taken at the place
def commons_near(http: Http, points: list[tuple[float, float]]) -> list[dict]:
    files: dict[str, dict] = {}
    for lat, lon in points:
        url = ("https://commons.wikimedia.org/w/api.php?action=query&list=geosearch&gsnamespace=6&gslimit=500"
               f"&gsradius=10000&gscoord={lat:.5f}|{lon:.5f}&format=json")
        try:
            r = http.get(url, gap=0.5)
            for g in (r.json().get("query", {}) or {}).get("geosearch", []) if r.status_code == 200 else []:
                files[g["title"]] = {"title": g["title"], "lat": g["lat"], "lon": g["lon"]}
        except Exception as ex:  # noqa: BLE001
            log("commons error", str(ex)[:120])
    return list(files.values())


def match_commons(places: list[dict], files: list[dict]) -> int:
    """Give a place a Commons photo when a file within ~100 m names it (shares a distinctive word)."""
    if not files:
        return 0
    n = 0
    for p in places:
        if p.get("img"):
            continue
        words = sig_words(p["n"])
        if not words:
            continue
        best, bd = None, 1e9
        for f in files:
            d = km(p["la"], p["lo"], f["lat"], f["lon"])
            if d > 0.1 or d >= bd:
                continue
            title_words = sig_words(re.sub(r"\.(jpe?g|png|webp|tiff?)$", "", f["title"][5:], flags=re.I))
            if words & title_words and not re.search(r"\.(svg|pdf|ogg|webm|gif)$", f["title"], re.I):
                best, bd = f, d
        if best:
            img, page = commons_file_url(best["title"])
            p.update({"img": img, "imgs": page, "imgf": "commons", "imgk": "photo"})
            n += 1
    return n


# ---------------------------------------------------------------- the restaurant's own website
class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.links: list[tuple[str, str]] = []
        self.ld: list[str] = []
        self._in_ld = False
        self._a_href = None
        self._a_text: list[str] = []
        self.text: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            k = (a.get("property") or a.get("name") or "").lower()
            if k and a.get("content"):
                self.meta.setdefault(k, a["content"])
        elif tag == "script":
            self._in_ld = (a.get("type") or "").lower() == "application/ld+json"
            if not self._in_ld:
                self._skip += 1
        elif tag == "style":
            self._skip += 1
        elif tag == "a" and a.get("href"):
            self._a_href, self._a_text = a["href"], []

    def handle_endtag(self, tag):
        if tag == "script":
            if self._in_ld:
                self._in_ld = False
            else:
                self._skip = max(0, self._skip - 1)
        elif tag == "style":
            self._skip = max(0, self._skip - 1)
        elif tag == "a" and self._a_href is not None:
            self.links.append((self._a_href, " ".join(self._a_text).strip()))
            self._a_href = None

    def handle_data(self, data):
        if self._in_ld:
            self.ld.append(data)
            return
        if self._skip:
            return
        if self._a_href is not None:
            self._a_text.append(data.strip())
        t = data.strip()
        if t:
            self.text.append(t)


def _ld_objects(chunks: list[str]):
    for c in chunks:
        try:
            d = json.loads(c)
        except (json.JSONDecodeError, ValueError):
            continue
        stack = d if isinstance(d, list) else [d]
        while stack:
            o = stack.pop()
            if isinstance(o, dict):
                yield o
                for v in o.values():
                    if isinstance(v, (list, dict)):
                        stack.extend(v if isinstance(v, list) else [v])
            elif isinstance(o, list):
                stack.extend(o)


def fetch_page(http: Http, url: str, max_bytes=3_000_000):
    """(final_url, content_type, bytes) or None. Honors robots.txt."""
    if not url or not http.allowed(url):
        return None
    try:
        r = http.get(url, gap=2.0, timeout=25, stream=False, allow_redirects=True)
    except Exception as ex:  # noqa: BLE001
        log("site error", url[:80], str(ex)[:80])
        return None
    if r.status_code != 200:
        return None
    body = r.content[:max_bytes]
    return getattr(r, "url", url) or url, (r.headers.get("content-type") or "").lower(), body


def read_site(http: Http, place: dict) -> dict:
    """Look at the restaurant's home page for its main photo, cuisine and a menu link."""
    out = {"wc": today()}
    got = fetch_page(http, place.get("w", ""))
    if not got:
        return out
    final, ctype, body = got
    if "html" not in ctype and not body.lstrip()[:15].lower().startswith((b"<!doctype", b"<html")):
        return out
    pp = _PageParser()
    try:
        pp.feed(body.decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001 - malformed HTML; use what was parsed
        pass
    img = ""
    for o in _ld_objects(pp.ld):
        types = o.get("@type")
        types = types if isinstance(types, list) else [types]
        if not any(str(t) in ("Restaurant", "FoodEstablishment", "FastFoodRestaurant", "BarOrPub", "LocalBusiness") for t in types):
            continue
        im = o.get("image")
        if isinstance(im, list):
            im = im[0] if im else ""
        if isinstance(im, dict):
            im = im.get("url", "")
        img = img or str(im or "")
        menu = o.get("hasMenu") or o.get("menu")
        if isinstance(menu, dict):
            menu = menu.get("url", "")
        if isinstance(menu, str) and menu:
            out["mu"] = clean_url(urllib.parse.urljoin(final, menu), allow_http=True)
        sc = o.get("servesCuisine")
        if sc and not place.get("c"):
            sc = sc if isinstance(sc, list) else [sc]
            out["c"] = [re.sub(r"[^a-z_-]", "", str(x).lower().replace(" ", "_"))[:30] for x in sc][:3]
    img = img or pp.meta.get("og:image", "") or pp.meta.get("twitter:image", "")
    img = clean_url(urllib.parse.urljoin(final, img)) if img else ""
    if img and not re.search(r"\.(svg|gif)(\?|$)", img, re.I):
        out.update({"img_candidate": img, "imgk": "logo" if re.search(r"logo|favicon|icon", img, re.I) else "photo"})
    if "mu" not in out:
        for href, text in pp.links:
            if re.search(r"\bmenus?\b|\bfood\b|\bdinner\b|\beat\b|\bcarta\b|\bspeisekarte\b|\bcarte\b|\bmenú\b", f"{text} {href}", re.I) \
                    and not re.search(r"^(mailto|tel|javascript):|\.(jpe?g|png)$|facebook|instagram|wine|drink|cocktail", href, re.I):
                u = clean_url(urllib.parse.urljoin(final, href), allow_http=True)
                if u:
                    out["mu"] = u
                    break
    out["_home_text"] = " ".join(pp.text)[:40000]
    return out


def menu_text(http: Http, url: str) -> str:
    """Plain text of a menu page or PDF ('' if unreadable or blocked)."""
    got = fetch_page(http, url, max_bytes=8_000_000)
    if not got:
        return ""
    _, ctype, body = got
    if "pdf" in ctype or body[:5] == b"%PDF-":
        try:
            import io

            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(body))
            return "\n".join((pg.extract_text() or "") for pg in reader.pages[:12])[:60000]
        except Exception:  # noqa: BLE001
            return ""
    if "html" in ctype or body.lstrip()[:1] == b"<":
        pp = _PageParser()
        try:
            pp.feed(body.decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001
            pass
        return "\n".join(pp.text)[:60000]
    return ""
