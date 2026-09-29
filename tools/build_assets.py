"""
Vajradhan asset build.

Regenerates the logo under assets/ from its source in images/. The other
generated assets have their own scripts: tools/build_fonts.py for the faces,
tools/cut_layers.py and tools/build_hero_layers.py for the hero's layers, and
tools/build_foreground.py for the rock pieces that ride at the foot of each
section. Run from the repository root:

    python tools/build_assets.py

Needs Pillow and numpy only. The output is committed, so the site itself never
runs this — it is here so every generated file can be rebuilt and audited.

Each step needs its own source under images/. A step whose source is missing
is skipped with a note rather than crashing the run, so the steps that can
still rebuild do. The committed files under assets/img are the record of the
ones that cannot.

What it makes
  assets/img/vajradhan-logo.webp     the mark, keyed off its leather ground
  assets/img/vajradhan-logo-64.png   favicon
"""
import os
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'images')
OUT = os.path.join(ROOT, 'assets', 'img')
os.makedirs(OUT, exist_ok=True)


def src(name):
    return os.path.join(SRC, name)


def out(name):
    return os.path.join(OUT, name)


def lum(a):
    return a[..., 0] * .2126 + a[..., 1] * .7152 + a[..., 2] * .0722


def _box(a, r, axis):
    """Box filter of radius r along one axis, edges clamped."""
    if r < 1:
        return a
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode='edge'), axis=axis)
    n = a.shape[axis]
    hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return (hi - lo) / (2 * r + 1)


def blur(a, sigma):
    """Near-gaussian blur (three box passes) of a float array, 2-D or HxWxC."""
    a = np.asarray(a, dtype=np.float64)
    r = max(0, int(round((np.sqrt(4 * sigma * sigma + 1) - 1) / 2)))
    if r == 0:
        return a
    for axis in (0, 1):
        for _ in range(3):
            a = _box(a, r, axis)
    return a


# ----------------------------------------------------------------- the logo
# Outline of the mark in source pixels. It only has to be accurate along the
# lower-left, where the studio shot throws a drop shadow the key would keep;
# everywhere else the key's own edge wins, since the two are intersected.
LOGO_POLY = [(52, 336), (262, 408), (690, 436), (744, 398), (1348, 326), (1386, 540),
             (1310, 800), (1232, 792), (1162, 864), (1072, 964), (972, 1044), (842, 1094),
             (823, 1110), (819, 1262), (745, 1338), (676, 1254), (676, 1100), (500, 1092),
             (356, 1108), (446, 902), (452, 832), (342, 694), (192, 514), (62, 348)]


def build_logo():
    im = Image.open(src('logo.jpeg')).convert('RGB')
    a = np.asarray(im).astype(np.float64)
    H, W, _ = a.shape
    L = lum(a)
    S = a.max(2) - a.min(2)
    yy, xx = np.mgrid[0:H, 0:W]
    u, v = xx / W, yy / H
    ring = (xx < 50) | (xx > W - 50) | (yy < 300) | (yy > H - 40)
    Lb = blur(L, 12)
    A = np.stack([np.ones_like(u), u, v, u * u, u * v, v * v, v ** 3, u ** 3], -1)
    coef, *_ = np.linalg.lstsq(A[ring], Lb[ring], rcond=None)
    ground = A @ coef
    d = blur(L, 2) - ground
    key = ((np.abs(d) > 30) | (S > 40)).astype(np.uint8) * 255
    k = Image.fromarray(key).filter(ImageFilter.MedianFilter(7))
    k = k.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9))
    ImageDraw.floodfill(k, (0, 0), 128)
    key = np.where(np.asarray(k) == 128, 0, 255).astype(np.uint8)

    poly = Image.new('L', (W, H), 0)
    ImageDraw.Draw(poly).polygon(LOGO_POLY, fill=255)
    m = np.minimum(key, np.asarray(poly)).astype(np.float64) / 255
    m = blur(m, 1.2)
    rgba = Image.fromarray(a.astype(np.uint8), 'RGB')
    rgba.putalpha(Image.fromarray((m * 255).astype(np.uint8)))
    bb = rgba.getbbox()
    rgba = rgba.crop((bb[0] - 6, bb[1] - 6, bb[2] + 6, bb[3] + 6))
    lg = rgba.copy()
    lg.thumbnail((640, 640), Image.LANCZOS)
    lg.save(out('vajradhan-logo.webp'), 'WEBP', quality=90, method=6)
    sq = Image.new('RGBA', (max(rgba.size),) * 2, (0, 0, 0, 0))
    sq.paste(rgba, ((sq.width - rgba.width) // 2, (sq.height - rgba.height) // 2))
    sq.resize((64, 64), Image.LANCZOS).save(out('vajradhan-logo-64.png'), optimize=True)
    print('logo', lg.size, 'palette - magenta', tuple(int(c) for c in a[640:680, 1050:1090].reshape(-1, 3).mean(0)),
          '- iris', tuple(int(c) for c in a[905:925, 740:760].reshape(-1, 3).mean(0)))
    return lg.size


def missing(*names):
    """The sources a step needs that are not in images/."""
    return [n for n in names if not os.path.exists(src(n))]


def step(name, needs, run):
    gone = missing(*needs)
    if gone:
        print('skip  %-9s - missing from images/: %s' % (name, ', '.join(gone)))
        return False
    run()
    return True


if __name__ == '__main__':
    logo = step('logo', ['logo.jpeg'], build_logo)
    if logo:
        shutil.copyfile(out('vajradhan-logo-64.png'), os.path.join(ROOT, 'favicon.png'))
