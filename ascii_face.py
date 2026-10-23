#!/usr/bin/env python3
"""Turn assets/face.png into an animated, colored ASCII-art SVG (dist/face.svg).

The SVG "types itself" row by row using CSS animation, which GitHub allows
inside <img> tags (no JavaScript involved).

Usage:  python scripts/ascii_face.py [--src assets/face.png] [--cols 96] [--seconds 3.5]
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

RAMP = " .`:-=+*cs#%@"          # dark -> light on a dark background
BG = "#0b0e14"
LIGHT, BLUE, ORANGE, DIM = "#e6edf3", "#79c0ff", "#f2a65a", "#6e7681"
GAMMA = 1.3                     # >1 pushes mid-greys (walls) toward blank
FONT_SIZE = 7.0
CHAR_W = FONT_SIZE * 0.602      # monospace advance
LINE_H = FONT_SIZE * 1.18


def pick_color(r, g, b, lum, x, y):
    if lum > 0.85:
        return LIGHT
    if lum < 0.2:
        return DIM
    if abs(r - b) > 12:                      # colour photo: follow warmth
        return ORANGE if r > b else BLUE
    # greyscale photo: stable pseudo-random blue/orange/white mix
    n = (x * 73856093 ^ y * 19349663) % 100
    return ORANGE if n < 28 else BLUE if n < 80 else LIGHT


def build(src: Path, cols: int, seconds: float, invert=None):
    img = Image.open(src).convert("RGB")
    img = ImageOps.exif_transpose(img)
    img = ImageOps.autocontrast(img, cutoff=1)
    img = ImageEnhance.Contrast(img).enhance(1.35)
    w, h = img.size
    rows = max(1, int(cols * h / w * 0.5))       # chars are ~2x taller than wide
    img = img.resize((cols, rows), Image.LANCZOS)
    # Light background? Invert tones so the subject (hair, glasses, shadows) becomes the dense part.
    gray = img.convert("L")
    gp = gray.load()
    edge = [gp[x, y] for x in range(cols) for y in (0, rows - 1)] + [gp[x, y] for y in range(rows) for x in (0, cols - 1)]
    if invert is None:
        invert = sum(edge) / len(edge) / 255 > 0.4
    if invert:
        img = ImageOps.invert(img)
    px = img.load()

    lines = []
    for y in range(rows):
        runs, cur_color, cur = [], None, ""
        for x in range(cols):
            r, g, b = px[x, y]
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            ch = RAMP[min(len(RAMP) - 1, int(lum ** GAMMA * len(RAMP)))]
            color = pick_color(r, g, b, lum, x, y)
            if ch == " ":
                color = cur_color or color
            if color != cur_color and cur:
                runs.append((cur_color, cur))
                cur = ""
            cur_color = color
            cur += ch
        if cur:
            runs.append((cur_color, cur))
        lines.append(runs)

    width = cols * CHAR_W + 24
    height = rows * LINE_H + 24
    step = seconds / rows
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="ASCII portrait of Tejas Joshi">',
        "<style>",
        "text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace;"
        f"font-size:{FONT_SIZE}px;white-space:pre}}",
        ".r{opacity:0;animation:show .01s steps(1) forwards}",
        "@keyframes show{to{opacity:1}}",
        "@keyframes blink{50%{opacity:0}}",
        ".cur{animation:blink 1s steps(1) infinite}",
        "</style>",
        f'<rect width="100%" height="100%" fill="{BG}"/>',
    ]
    cx = width / 2
    for i, runs in enumerate(lines):
        y = 12 + (i + 1) * LINE_H
        spans = "".join(
            f'<tspan fill="{c}">{t.replace("&", "&amp;").replace("<", "&lt;")}</tspan>' for c, t in runs
        )
        out.append(
            f'<text class="r" x="{cx:.1f}" y="{y:.1f}" text-anchor="middle" '
            f'xml:space="preserve" style="animation-delay:{i * step:.2f}s">{spans}</text>'
        )
    out.append(
        f'<rect class="cur" x="{cx + 8:.1f}" y="{12 + rows * LINE_H - 6:.1f}" width="{CHAR_W:.1f}" '
        f'height="{FONT_SIZE:.1f}" fill="{LIGHT}" style="animation-delay:{seconds:.2f}s"/>'
    )
    out.append("</svg>")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="assets/face.png")
    ap.add_argument("--out", default="dist/face.svg")
    ap.add_argument("--cols", type=int, default=96)
    ap.add_argument("--seconds", type=float, default=3.5)
    ap.add_argument("--invert", choices=["auto", "yes", "no"], default="auto")
    a = ap.parse_args()
    src = Path(a.src)
    if not src.exists():
        sys.exit(f"Missing {src}. Add a front-facing, well-lit photo with a plain background.")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(build(src, a.cols, a.seconds, {'auto': None, 'yes': True, 'no': False}[a.invert]), encoding="utf-8")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
