"""Shared helpers for NTI-style ASL hand SVG glyphs (80x100, embedded PNG)."""
from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image, ImageOps

VIEWBOX_W = 96
VIEWBOX_H = 120
PADDING_PX = 6
INK_RGB = (26, 26, 26)

ROOT = Path(__file__).resolve().parent.parent / "public" / "asl-fingerspell"
OUT_DIR = ROOT


def png_to_data_uri(png_bytes: bytes) -> str:
    b64 = base64.standard_b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}"


def write_hand_svg(letter: str, png_bytes: bytes, out_path: Path | None = None) -> None:
    out_path = out_path or (OUT_DIR / f"{letter.lower()}.svg")
    data_uri = png_to_data_uri(png_bytes)
    label = letter.upper()
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
  viewBox="0 0 {VIEWBOX_W} {VIEWBOX_H}" role="img" aria-label="ASL {label} hand">
  <image xlink:href="{data_uri}" x="0" y="0" width="{VIEWBOX_W}" height="{VIEWBOX_H}"
    preserveAspectRatio="xMidYMid meet"/>
</svg>
"""
    out_path.write_text(svg, encoding="utf-8")


def _trim_transparent(im: Image.Image) -> Image.Image:
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    bbox = im.getbbox()
    return im.crop(bbox) if bbox else im


def _white_to_alpha(im: Image.Image) -> Image.Image:
    im = im.convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r > 248 and g > 248 and b > 248:
                px[x, y] = (255, 255, 255, 0)
    return im


def stylize_banner_crop(im: Image.Image) -> Image.Image:
    """Hard binarize for NTI banner hand crops (already line art)."""
    gray = im.convert("L")
    bw = gray.point(lambda p: 0 if p < 210 else 255, mode="1")
    rgba = Image.new("RGBA", im.size, (255, 255, 255, 0))
    ink = Image.new("RGBA", im.size, (*INK_RGB, 255))
    rgba.paste(ink, mask=bw.point(lambda p: 0 if p else 255))
    return _trim_transparent(rgba)


def _to_rgba(im: Image.Image) -> Image.Image:
    if im.mode == "LA":
        l, a = im.split()
        return Image.merge("RGBA", (l, l, l, a))
    if im.mode != "RGBA":
        return im.convert("RGBA")
    return im


def stylize_wikimedia(im: Image.Image) -> Image.Image:
    """Preserve detailed line art; map to NTI ink (#1a1a1a)."""
    # Wikimedia thumbs are often LA with lines in the alpha channel only
    if im.mode == "LA":
        _l, alpha = im.split()
        mask = ImageOps.autocontrast(alpha)
    else:
        im = _to_rgba(im)
        im = _white_to_alpha(im)
        mask = ImageOps.autocontrast(im.convert("L"))

    src = mask.load()
    out = Image.new("RGBA", im.size, (255, 255, 255, 0))
    dst = out.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            av = src[x, y]
            if av < 18:
                continue
            dst[x, y] = (*INK_RGB, min(255, int(av * 1.08)))
    return _trim_transparent(out)


def _fit_canvas(im: Image.Image) -> bytes:
    im = _trim_transparent(im)
    if im.width < 1 or im.height < 1:
        raise ValueError("Empty hand image after processing")

    max_w = VIEWBOX_W - PADDING_PX * 2
    max_h = VIEWBOX_H - PADDING_PX * 2
    # Scale to fit inside box so wide hands (B, W) are not clipped at the sides
    scale = min(max_h / im.height, max_w / im.width)
    new_w = max(1, int(im.width * scale))
    new_h = max(1, int(im.height * scale))
    im = im.resize((new_w, new_h), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (VIEWBOX_W, VIEWBOX_H), (255, 255, 255, 0))
    paste_x = (VIEWBOX_W - im.width) // 2
    paste_y = (VIEWBOX_H - im.height) // 2
    canvas.paste(im, (paste_x, paste_y), im)

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


def normalize_hand_raster(im: Image.Image, *, from_banner: bool = False) -> bytes:
    im = stylize_banner_crop(im) if from_banner else stylize_wikimedia(im)
    return _fit_canvas(im)
