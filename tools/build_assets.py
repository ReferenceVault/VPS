"""
Vajradhan asset build.

Regenerates everything under assets/ from the sources in images/ and
tools/fonts-src/. Run from the repository root:

    python tools/build_assets.py

Needs Pillow and numpy only. The output is committed, so the site itself never
runs this — it is here so every generated file can be rebuilt and audited.

What it makes
  assets/img/vajradhan1-{sky,moon,far,mid,near}.webp   depth planes cut from
      the hero photo (the sky is opaque, the rest carry alpha)
  assets/img/vajradhan1-clean.webp   the hero photo with the mock-up's baked
      type painted out (used by the no-WebGL fallback and as the og image)
  assets/img/vajradhan2..5.webp      selected-work stills, re-encoded
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


def grow(mask, px):
    """Binary dilation by roughly px pixels."""
    m = Image.fromarray((mask * 255).astype(np.uint8))
    size = px * 2 + 1
    return np.asarray(m.filter(ImageFilter.MaxFilter(size))) > 127


# ---------------------------------------------------------------- inpainting
def push_pull(img, hole):
    """Fill `hole` (bool HxW) from its surroundings.

    A weighted image pyramid: known pixels are averaged down level by level
    until every hole has been covered, then each level is pulled back up and
    only the hole pixels take the coarser estimate. Smooth, seam-free, and
    fast in numpy — good enough for type set over a dark, soft background.
    """
    w = (~hole).astype(np.float64)
    levels = []
    cur = img * w[..., None]
    cw = w.copy()
    while True:
        levels.append((cur, cw))
        h, wd = cw.shape
        if min(h, wd) <= 2:
            break
        h2, w2 = h // 2, wd // 2
        c = cur[:h2 * 2, :w2 * 2].reshape(h2, 2, w2, 2, -1).sum((1, 3))
        k = cw[:h2 * 2, :w2 * 2].reshape(h2, 2, w2, 2).sum((1, 3))
        cur, cw = c, k
    # pull
    est = levels[-1][0] / np.maximum(levels[-1][1], 1e-6)[..., None]
    for c, k in reversed(levels[:-1]):
        h, wd = k.shape
        up = np.stack([np.asarray(Image.fromarray(est[..., i].astype(np.float32), 'F')
                                  .resize((wd, h), Image.BILINEAR)) for i in range(est.shape[2])], -1)
        known = c / np.maximum(k, 1e-6)[..., None]
        a = np.clip(k, 0, 1)[..., None]
        est = known * a + up * (1 - a)
    out_ = img.copy()
    out_[hole] = est[hole]
    return out_


def add_grain(img, hole, sigma, seed):
    rnd = np.random.default_rng(seed)
    n = rnd.normal(0, sigma, img.shape[:2])
    n = blur(n, .6)
    res = img.copy()
    res[hole] += n[hole][:, None]
    return res


# ------------------------------------------------------------ the hero photo
HERO = src('vajradhan1.webp')

# Where the mock-up's own type sits (source pixels). Only bright strokes inside
# these boxes are treated as type, so the mountains around them survive.
TYPE_BOXES = [
    (36, 36, 336, 112),       # logo + wordmark
    (1928, 54, 2012, 96),     # burger
    (40, 626, 846, 812),      # headline
    (40, 820, 776, 910),      # standfirst
    (40, 958, 1960, 1080),    # the four chips
]

# Depth silhouettes, traced off the photo: every column below the line belongs
# to that plane or something nearer.
SKYLINE = [(0, 425), (40, 440), (95, 425), (150, 470), (200, 540), (265, 590), (340, 560),
           (400, 600), (450, 628), (520, 640), (560, 610), (620, 560), (680, 520), (720, 540),
           (770, 560), (800, 545), (850, 505), (900, 462), (960, 440), (1000, 432), (1050, 400),
           (1100, 330), (1150, 262), (1215, 205), (1270, 230), (1330, 300), (1380, 380),
           (1410, 385), (1460, 420), (1500, 470), (1555, 490), (1600, 500), (1660, 440),
           (1690, 410), (1730, 440), (1800, 490), (1840, 500), (1870, 510), (1900, 480),
           (1950, 380), (1990, 300), (2048, 270)]
MIDLINE = [(0, 425), (40, 440), (95, 425), (150, 470), (200, 540), (265, 590), (340, 560),
           (400, 600), (450, 628), (520, 640), (560, 610), (620, 560), (680, 520), (720, 540),
           (770, 570), (820, 610), (880, 660), (940, 710), (1000, 760), (1040, 800), (1070, 793),
           (1110, 800), (1160, 825), (1220, 860), (1290, 885), (1350, 895), (1420, 890),
           (1480, 880), (2048, 880)]
NEARLINE = [(0, 900), (300, 950), (600, 985), (900, 975), (1100, 930), (1200, 905), (1300, 890),
            (1400, 845), (1450, 765), (1510, 695), (1555, 678), (1600, 705), (1640, 600),
            (1700, 578), (1760, 575), (1820, 578), (1860, 555), (1900, 480), (1955, 375),
            (2000, 300), (2048, 265)]
MOON = (543, 257, 131)        # centre x, centre y, radius


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


def save_rgba(rgb, alpha, name, q=86):
    a = np.clip(alpha * 255, 0, 255).astype(np.uint8)
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB')
    im.putalpha(Image.fromarray(a))
    im.save(out(name), 'WEBP', quality=q, method=6)


def build_hero():
    im = Image.open(HERO).convert('RGB')
    a = np.asarray(im).astype(np.float64)
    H, W, _ = a.shape
    L = lum(a)
    sat = a.max(2) - a.min(2)
    local = blur(L, 18)

    box = np.zeros((H, W), bool)
    for x0, y0, x1, y1 in TYPE_BOXES:
        box[y0:y1, x0:x1] = True
    stroke = box & (((L - local) > 16) | (L > 150) | (sat > 60))
    hole = grow(stroke, 4) & box
    for x0, y0, x1, y1 in TYPE_BOXES[:2]:
        hole[y0:y1, x0:x1] = True
    clean = push_pull(a, hole)
    clean = add_grain(clean, hole, 2.4, 11)
    Image.fromarray(np.clip(clean, 0, 255).astype(np.uint8)).save(
        out('vajradhan1-clean.webp'), 'WEBP', quality=86, method=6)

    # moon: its own plane, so it can breathe and drift apart from the sky
    mx, my, mr = MOON
    yy, xx = np.mgrid[0:H, 0:W]
    dist = np.hypot(xx - mx, yy - my)
    # saved full-frame (almost all transparent, which costs nothing in webp) so
    # every plane shares one frame: the scene and the CSS fallback can both
    # size all five layers with the same cover rule and they stay registered
    disc = np.clip(mr + .8 - dist, 0, 1)
    save_rgba(clean, disc, 'vajradhan1-moon.webp', q=90)

    # sky: moon lifted out, everything under the skyline replaced by sky
    # A pyramid fill averages the halo with the far sky and leaves a bright ring
    # at the old limb. Continuing the halo inward along each ray keeps the glow
    # at the level it has just outside the disc, which is what the air does.
    inner = dist < mr + 7
    ang = np.arctan2(yy - my, xx - mx)
    R0 = mr + 12
    sx = np.clip(np.round(mx + np.cos(ang) * R0).astype(int), 0, W - 1)
    sy = np.clip(np.round(my + np.sin(ang) * R0).astype(int), 0, H - 1)
    sky = clean.copy()
    sky[inner] = clean[sy[inner], sx[inner]]
    soft = blur(sky, 6)
    edge = (dist < mr + 16)[..., None]
    sky = np.where(edge, soft, sky)
    sky = add_grain(sky, dist < mr + 16, 1.6, 12)
    sky = extend_behind(sky, SKYLINE, band=26, seed=13)
    Image.fromarray(np.clip(sky, 0, 255).astype(np.uint8)).save(
        out('vajradhan1-sky.webp'), 'WEBP', quality=84, method=6)

    far = extend_behind(clean, MIDLINE, band=20, seed=14)
    save_rgba(far, below(SKYLINE, W, H), 'vajradhan1-far.webp')
    mid = extend_behind(clean, NEARLINE, band=20, seed=15)
    save_rgba(mid, below(MIDLINE, W, H), 'vajradhan1-mid.webp')
    save_rgba(clean, below(NEARLINE, W, H), 'vajradhan1-near.webp')

    # palette, measured rather than guessed
    def mean(x0, y0, x1, y1):
        return tuple(int(v) for v in clean[y0:y1, x0:x1].reshape(-1, 3).mean(0))
    print('palette - sky top      ', mean(900, 10, 1800, 120))
    print('palette - sky mid      ', mean(1400, 250, 1800, 380))
    print('palette - horizon haze ', mean(1150, 700, 1350, 820))
    print('palette - moon         ', mean(mx - 40, my - 40, mx + 40, my + 40))
    print('palette - snow         ', mean(1150, 280, 1200, 330))
    print('palette - rock         ', mean(1600, 760, 1800, 880))
    print('palette - ground       ', mean(200, 1090, 1800, 1140))
    return W, H


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


# -------------------------------------------------- stills and cut-outs
WORK = ['vajradhan2.webp', 'vajradhan3.webp', 'vajradhan4.webp', 'vajradhan5.webp']
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


def build_stills():
    sizes = {}
    for name in WORK:
        im = Image.open(src(name)).convert('RGB')
        im.thumbnail((1600, 1600), Image.LANCZOS)
        im.save(out(name), 'WEBP', quality=82, method=6)
        sizes[name] = im.size
    for s, d in CUTOUTS:
        im = moonlight(Image.open(src(s)))
        im.thumbnail((1400, 1400), Image.LANCZOS)
        im.save(out(d), 'WEBP', quality=84, method=6)
        sizes[d] = im.size
    for k, v in sizes.items():
        print('still', k, v)


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


if __name__ == '__main__':
    print('hero', build_hero())
    build_logo()
    build_stills()
    build_fonts()
    shutil.copyfile(out('vajradhan-logo-64.png'), os.path.join(ROOT, 'favicon.png'))
