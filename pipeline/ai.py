"""The AI steps (Claude). All optional: without ANTHROPIC_API_KEY the pipeline still grows the map data.

Every AI answer is checked by code before it's kept:
- menu picks must appear word-for-word in the menu text that was read;
- photo checks only remove or relabel images, never add them;
- recipes are re-checked by a second AI pass and their nutrition and diet flags are computed by code.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from common import FIXTURES, log, norm

MODEL = os.environ.get("W4D_AI_MODEL") or "claude-sonnet-5-5"          # recipes and recipe review
FAST_MODEL = os.environ.get("W4D_AI_FAST_MODEL") or "claude-haiku-5-5"  # menus and photo checks
FITS = ["lowCal", "lowSodium", "glp1", "highProtein", "vegetarian", "glutenFree", "dairyFree"]


class AI:
    def __init__(self, max_calls: int | None = None):
        self.key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.max_calls = int(max_calls if max_calls is not None else (os.environ.get("W4D_AI_CALLS") or 60))
        self.calls = 0
        self.client = None
        if self.key and not FIXTURES:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=self.key, max_retries=3)
            except ImportError:
                log("anthropic package missing; AI steps off")

    @property
    def on(self) -> bool:
        return (bool(self.client) or bool(FIXTURES)) and self.calls < self.max_calls

    def ask_json(self, task: str, content, system: str, model: str | None = None, max_tokens=1500):
        """Send one request and parse the JSON object in the reply. None on any failure."""
        if not self.on:
            return None
        self.calls += 1
        if FIXTURES:
            f = Path(FIXTURES) / f"ai_{task}.json"
            return json.loads(f.read_text()) if f.exists() else None
        try:
            msg = self.client.messages.create(
                model=model or FAST_MODEL, max_tokens=max_tokens, system=system,
                messages=[{"role": "user", "content": content}])
            text = "".join(getattr(b, "text", "") for b in msg.content)
        except Exception as ex:  # noqa: BLE001
            log("AI error", task, str(ex)[:200])
            return None
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None

    # ------------------------------------------------------------ photos
    def check_photo(self, url: str, name: str) -> str | None:
        """'food' | 'interior' | 'exterior' | 'logo' | 'other', or None if not checked."""
        system = ("You label restaurant website images for a dinner app. Reply with JSON only: "
                  '{"kind": "food|interior|exterior|logo|other"}. "other" = people-only shots, stock graphics, '
                  "text banners, maps, gift cards, unrelated or unclear images.")
        content = [{"type": "image", "source": {"type": "url", "url": url}},
                   {"type": "text", "text": f"Main image from the website of the restaurant “{name}”. Label it."}]
        r = self.ask_json("photo", content, system, max_tokens=50)
        k = (r or {}).get("kind")
        return k if k in ("food", "interior", "exterior", "logo", "other") else None

    # ------------------------------------------------------------ menus
    def menu_picks(self, name: str, cuisine: str, text: str) -> list[dict]:
        if len(text) < 200:
            return []
        system = (
            "You read a restaurant's own menu and pick up to 6 of the lighter, healthier dinner choices for a health-focused dinner app. "
            "Rules: copy each dish name EXACTLY as written on the menu (same words and spelling). Never invent dishes. "
            "Skip drinks, desserts, sides and kids' meals unless nothing else fits. Prefer grilled, baked, steamed or poached dishes, "
            "salads with protein, broth soups, fish and lean meats with vegetables. "
            "For each pick give a short note in your own words (max 15 words) and 'fits' tags, using only these and only when clearly likely: "
            "lowCal (about 450 kcal or less), lowSodium (plain dish without cured meats, soy, cheese or heavy sauces), "
            "glp1 (lean protein-focused, not fried, moderate portion), highProtein (a full portion of meat, fish, eggs or tofu), "
            "vegetarian / glutenFree / dairyFree ONLY when the menu itself marks the dish that way (e.g. V, VG, GF, DF). "
            'Reply with JSON only: {"picks":[{"dish":"...","note":"...","fits":["..."]}]}. If the text is not a food menu, reply {"picks":[]}.')
        content = f"Restaurant: {name}\nCuisine: {cuisine or 'unknown'}\n\nMENU TEXT:\n{text[:30000]}"
        r = self.ask_json("menu", content, system, max_tokens=900)
        picks = []
        hay = norm(text)
        for x in (r or {}).get("picks", [])[:6]:
            dish = str(x.get("dish", "")).strip()
            if not dish or len(dish) > 120 or norm(dish) not in hay:      # must be on the menu, word-for-word
                continue
            fits = [f for f in x.get("fits", []) if f in FITS]
            picks.append({"d": dish, "t": str(x.get("note", ""))[:200], "f": fits})
        return picks
