"""
Vajradhan asset build.

Regenerates the logo, the cut-outs and the fonts under assets/ from the
sources in images/ and tools/fonts-src/. The hero plate has its own script,
tools/build_hero.py, which shares the cutting helpers below. Run from the
repository root:

    python tools/build_assets.py

Needs Pillow and numpy only. The output is committed, so the site itself never
runs this — it is here so every generated file can be rebuilt and audited.

Each step needs its own source under images/. A step whose source is missing
is skipped with a note rather than crashing the run, so the steps that can
still rebuild do. The committed files under assets/img are the record of the
ones that cannot.

What it makes
  assets/img/vajradhan6..9.webp      foreground cut-outs, graded to moonlight
  assets/img/vajradhan-logo.webp     the mark, keyed off its leather ground
  assets/img/vajradhan-logo-64.png   favicon
  assets/fonts.css                   Onest + Unbounded as base64 woff2
"""
import base64
import os
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'images')
OUT = os.path.join(ROOT, 'assets', 'img')
FONTS = os.path.join(ROOT, 'tools', 'fonts-src')
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


def add_grain(img, hole, sigma, seed):
    rnd = np.random.default_rng(seed)
    n = rnd.normal(0, sigma, img.shape[:2])
    n = blur(n, .6)
    res = img.copy()
    res[hole] += n[hole][:, None]
    return res


# ------------------------------------------------------- cutting the planes
# Shared with tools/build_hero.py, which owns the hero plate's own lines.
def line_y(poly, W):
    xs, ys = zip(*poly)
    return np.interp(np.arange(W), xs, ys)


def below(poly, W, H, feather=1.4):
    y = line_y(poly, W)
    yy = np.arange(H)[:, None]
    m = np.clip((yy - y[None, :]) + .5, 0, 1)
    return blur(m, feather) if feather else m


def extend_behind(img, poly, band=22, seed=0):
    """Replace everything under `poly` with the colour just above it, smeared
    down and softened — the pixels a plane shows when the one in front of it
    slides aside. Without this the parallax reveals a second copy of the
    nearer ridge instead of more of the farther one."""
    H, W, _ = img.shape
    y = line_y(poly, W).astype(int)
    res = img.copy()
    col = np.zeros((W, 3))
    for x in range(W):
        y0 = max(0, y[x] - band - 6)
        y1 = max(1, y[x] - 6)
        col[x] = img[y0:y1, x].mean(0)
    # wide, or every column's own colour runs down as a curtain
    col = blur(np.repeat(col[None], 3, 0), 38)[1]
    haze = col.mean(0)
    yy = np.arange(H)[:, None]
    under = yy >= (y[None, :] - 2)
    depth = np.clip((yy - y[None, :]) / 220.0, 0, 1)[..., None]
    fillc = (col[None, :, :] * (1 - depth) + haze * depth) * (1 - .30 * depth)
    res = np.where(under[..., None], fillc, res)
    # soften the seam the smear leaves at the silhouette
    soft = blur(res, 3)
    seam = (np.abs(yy - y[None, :]) < 6)[..., None]
    res = np.where(seam, soft, res)
    return add_grain(res, under, 2.2, seed)



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


# -------------------------------------------------------------- cut-outs
# Kage cut-outs kept for the cold palette, under the project's own names.
CUTOUTS = [('tall-grass.webp', 'vajradhan6.webp'), ('basalt-stones.webp', 'vajradhan7.webp'),
           ('hill.webp', 'vajradhan8.webp'), ('pine-tree.webp', 'vajradhan9.webp')]


def moonlight(im):
    """Pull a warm-lit cut-out into the photo's moonlight: less chroma, the
    reds and mosses pushed toward slate, a touch darker."""
    rgba = np.asarray(im.convert('RGBA')).astype(np.float64)
    rgb = rgba[..., :3]
    L = lum(rgb)[..., None]
    rgb = L + (rgb - L) * .55
    rgb = rgb * np.array([.80, .88, 1.02]) * .92
    rgba[..., :3] = np.clip(rgb, 0, 255)
    return Image.fromarray(rgba.astype(np.uint8), 'RGBA')


def build_cutouts():
    sizes = {}
    for s, d in CUTOUTS:
        im = moonlight(Image.open(src(s)))
        im.thumbnail((1400, 1400), Image.LANCZOS)
        im.save(out(d), 'WEBP', quality=84, method=6)
        sizes[d] = im.size
    for k, v in sizes.items():
        print('cut-out', k, v)


# ---------------------------------------------------------------- fonts
FACES = [('Onest', 300, 'onest-latin-300-normal.woff2'),
         ('Onest', 400, 'onest-latin-400-normal.woff2'),
         ('Onest', 500, 'onest-latin-500-normal.woff2'),
         ('Unbounded', 400, 'unbounded-latin-400-normal.woff2'),
         ('Unbounded', 500, 'unbounded-latin-500-normal.woff2')]


def build_fonts():
    lines = ['/* Onest and Unbounded (SIL Open Font License 1.1, see tools/fonts-src),',
             '   latin subsets embedded as base64 woff2 so the page makes no font request. */']
    for fam, wt, f in FACES:
        with open(os.path.join(FONTS, f), 'rb') as fh:
            b = base64.b64encode(fh.read()).decode('ascii')
        lines.append("@font-face{font-family:'%s';font-style:normal;font-weight:%d;"
                     "font-display:swap;src:url(data:font/woff2;base64,%s) format('woff2');}"
                     % (fam, wt, b))
    with open(os.path.join(ROOT, 'assets', 'fonts.css'), 'w', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('fonts.css', os.path.getsize(os.path.join(ROOT, 'assets', 'fonts.css')), 'bytes')


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
    step('cut-outs', [s for s, _ in CUTOUTS], build_cutouts)
    build_fonts()
    if logo:
        shutil.copyfile(out('vajradhan-logo-64.png'), os.path.join(ROOT, 'favicon.png'))
