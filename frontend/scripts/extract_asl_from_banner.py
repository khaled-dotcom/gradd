"""
Extract ASL hand crops from the NTI fingerspell banner.
Requires: pip install pillow

Outputs:
  public/asl-fingerspell/source/crops/{letter}.png  (11 letters from banner)
  public/asl-fingerspell/{letter}.svg               (embedded raster, hand-only)
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from asl_glyph_common import OUT_DIR, normalize_hand_raster, write_hand_svg

SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE = OUT_DIR / "source"
BANNER = SOURCE / "nti-banner.png"
SLICES_JSON = SOURCE / "banner_slices.json"
CROPS_DIR = SOURCE / "crops"

HAND_TOP_PX = 18
BANNER_LETTERS = frozenset("ACEILMNOSTU")


def load_meta() -> dict:
    with open(SLICES_JSON, encoding="utf-8") as f:
        return json.load(f)


def crop_hand(im: Image.Image, slice_info: dict, hand_top: int) -> Image.Image:
    x, y, w, h = slice_info["x"], slice_info["y"], slice_info["w"], slice_info["h"]
    box = (x, y + hand_top, x + w, y + h)
    crop = im.crop(box)
    if crop.mode != "RGBA":
        crop = crop.convert("RGBA")
    return crop


def extract_crops_and_svgs() -> list[str]:
    if not BANNER.exists():
        raise FileNotFoundError(f"Banner not found: {BANNER}")

    meta = load_meta()
    hand_top = meta.get("hand_top_px", HAND_TOP_PX)
    first_idx: dict[str, int] = meta["first_occurrence_index"]
    slices_by_index = {s["index"]: s for s in meta["slices"]}

    im = Image.open(BANNER)
    CROPS_DIR.mkdir(parents=True, exist_ok=True)

    extracted: list[str] = []
    for letter, idx in sorted(first_idx.items(), key=lambda x: x[1]):
        key = letter.lower()
        if letter not in BANNER_LETTERS:
            continue
        sl = slices_by_index[idx]
        hand = crop_hand(im, sl, hand_top)
        png_bytes = normalize_hand_raster(hand, from_banner=True)

        crop_path = CROPS_DIR / f"{key}.png"
        crop_path.write_bytes(png_bytes)

        svg_path = OUT_DIR / f"{key}.svg"
        write_hand_svg(key, png_bytes, svg_path)
        extracted.append(key)
        print(f"  {key}.svg <- banner index {idx}")

    return extracted


if __name__ == "__main__":
    print(f"Extracting from {BANNER}")
    letters = extract_crops_and_svgs()
    print(f"Done: {len(letters)} letters from banner -> {OUT_DIR}")
