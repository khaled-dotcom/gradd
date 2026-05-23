"""
Build missing ASL letters (B,D,F,...) from Wikimedia "Sign language X.svg" thumbs.
Processed to match NTI banner glyphs (black line art, 80x100 embedded PNG).

Requires: pip install pillow

License: Wikimedia Commons — see ATTRIBUTION.md.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image

from asl_glyph_common import OUT_DIR, normalize_hand_raster, write_hand_svg

CROPS_DIR = OUT_DIR / "source" / "wikimedia-crops"
USER_AGENT = "EmpowerWork/1.0 (accessibility ASL glyphs; local dev)"
MISSING = "bdfghjkpqrvwxyz"
THUMB_WIDTH = 280
REQUEST_DELAY_S = 2.0
MAX_RETRIES = 5


def fetch_thumb_png(letter: str) -> bytes:
    title = f"File:Sign_language_{letter.upper()}.svg"
    api = (
        "https://commons.wikimedia.org/w/api.php?action=query&titles="
        + urllib.parse.quote(title)
        + f"&prop=imageinfo&iiprop=url|thumburl&iiurlwidth={THUMB_WIDTH}&format=json"
    )
    req = urllib.request.Request(api, headers={"User-Agent": USER_AGENT})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())
    page = list(data["query"]["pages"].values())[0]
    if "missing" in page:
        raise FileNotFoundError(f"Wikimedia file not found: {title}")
    ii = page["imageinfo"][0]
    thumb_url = ii["thumburl"]
    req2 = urllib.request.Request(thumb_url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req2, timeout=60).read()


def fetch_with_retry(letter: str) -> bytes:
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            return fetch_thumb_png(letter)
        except Exception as e:
            last_err = e
            time.sleep(REQUEST_DELAY_S * (attempt + 2))
    raise last_err  # type: ignore[misc]


def main() -> None:
    CROPS_DIR.mkdir(parents=True, exist_ok=True)
    for i, letter in enumerate(MISSING):
        if i > 0:
            time.sleep(REQUEST_DELAY_S)

        cache_raw = CROPS_DIR / f"{letter}_raw.png"
        if cache_raw.exists():
            raw = cache_raw.read_bytes()
        else:
            raw = fetch_with_retry(letter)
            cache_raw.write_bytes(raw)

        im = Image.open(BytesIO(raw))
        png_bytes = normalize_hand_raster(im)
        (CROPS_DIR / f"{letter}.png").write_bytes(png_bytes)
        write_hand_svg(letter, png_bytes, OUT_DIR / f"{letter}.svg")
        print(f"  {letter}.svg <- Wikimedia Sign language {letter.upper()}.svg")

    print(f"Done: {len(MISSING)} letters -> {OUT_DIR}")


if __name__ == "__main__":
    main()
