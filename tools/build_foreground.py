"""Cut the four foreground pieces out of the rock in images/3.jpeg.

    python tools/build_foreground.py

The pieces that ride at the foot of each section used to be a grassy hill, a
bank of tall grass, a pile of granite and a windswept pine -- a night on
earth, taken from the plate the hero used to carry. The hero is a vortex now,
and the only ground anywhere in the scene is the lava-seamed rock the cloaked
man stands on. So the foreground is cut from that rock: it is lit by the same
light, seamed with the same fire, and needs no grading to belong.

Four pieces, all out of masters/3-cutout.png (tools/cut_layers.py builds it,
alpha and all, with a base that already dissolves into mist):

  fg-ridge    the rock below the summit, as a wide low horizon
  fg-spire    a single tall monolith
  fg-shards   a pile of broken asteroids, bottom-anchored
  fg-drift    a wide, sparse band of smaller fragments

The asteroids are not found in the frame. The debris floating in it is barely
a hundred pixels across -- far too small to show at 400px on a page. They are
cut instead: a jagged outline, from a fixed seed so the build repeats exactly,
filled with rock sampled from the master and falling away towards its own edge
so it reads as a body rather than a flat stamp.

These sit *in front of* each section's copy, which is why the originals were
near-black silhouettes. The rock's lava runs far hotter than that, so every
piece goes through a highlight rolloff: below the knee nothing moves, above it
the seams are compressed hard. The embers stay, they just stop shouting over
the text.
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(ROOT, 'masters', '3-cutout.png')
OUT = os.path.join(ROOT, 'assets', 'img')

# The rock, in fractions of the source frame. The summit is where the man
# stands, so the crop starts below his feet and he never enters it.
ROCK = (.130, .625, .895, 1.0)

KNEE, SQUASH = 55.0, .30      # the highlight rolloff: where, and how hard
Q = 84


def rnd(seed):
    return np.random.default_rng(seed)


def crop(im, box):
    W, H = im.size
    return im.crop((int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H)))


def fit(im, w):
    return im.resize((w, max(1, round(w * im.size[1] / im.size[0]))), Image.LANCZOS)


def cool(im):
    """Compress the lava so it reads as ember rather than as a light source."""
    a = np.asarray(im).astype(np.float32)
    lum = a[:, :, :3].mean(2)
    hot = np.maximum(lum - KNEE, 0)
    k = np.where(lum > KNEE, (KNEE + hot * SQUASH) / np.maximum(lum, 1e-3), 1.0)
    a[:, :, :3] *= k[:, :, None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


def base_fade(im, band=.20, strength=.85):
    """Let the bottom edge dissolve rather than end on a line."""
    a = np.asarray(im).astype(np.float32)
    y = np.arange(a.shape[0], dtype=np.float32) / a.shape[0]
    k = np.clip((1 - y) / band, 0, 1)
    k = k * k * (3 - 2 * k)
    a[:, :, 3] *= (1 - strength) + strength * k[:, None]
    return Image.fromarray(a.astype(np.uint8), 'RGBA')


# --------------------------------------------------------------- asteroids
def outline(rx, ry, n, rough, g, taper=0.0):
    """A jagged closed outline in a 2rx by 2ry box. `taper` narrows the top,
    which is what turns a boulder into a standing monolith."""
    pts = []
    for i in range(n):
        a = (i / n) * math.tau + g.uniform(-.5, .5) * (math.tau / n) * .9
        k = 1 - g.uniform(0, rough)
        up = (1 + math.sin(a)) * .5                     # 1 at the top, 0 at the foot
        pts.append((rx + rx * k * (1 - taper * up) * math.cos(a),
                    ry - ry * k * math.sin(a)))
    return pts


def body(rock, w, h, g, verts=17, rough=.42, taper=0.0):
    """One asteroid: rock texture inside a jagged outline, rim falling away."""
    RW, RH = rock.size
    s = int(max(w, h) * g.uniform(1.0, 1.4))
    s = min(s, RW - 2, RH - 2)
    x = int(g.uniform(.08, .92) * (RW - s))
    y = int(g.uniform(.12, .78) * (RH - s))
    tex = rock.crop((x, y, x + s, y + s)).resize((w, h), Image.LANCZOS)

    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).polygon(outline(w / 2, h / 2, verts, rough, g, taper), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(max(.8, min(w, h) * .005)))

    a = np.asarray(tex).astype(np.float32)
    rim = np.asarray(m.filter(ImageFilter.GaussianBlur(min(w, h) * .10))).astype(np.float32) / 255.0
    a[:, :, :3] *= (.58 + .42 * rim)[:, :, None]
    a[:, :, 3] = np.minimum(a[:, :, 3], np.asarray(m).astype(np.float32))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


def scatter(rock, w, h, spec, seed):
    """Lay bodies over a transparent canvas: (cx, cy, size, opacity) each."""
    g = rnd(seed)
    sheet = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    for cx, cy, size, op in spec:
        c = body(rock, size, int(size * g.uniform(.72, .95)), g)
        c = c.rotate(g.uniform(0, 360), Image.BICUBIC, expand=True)
        if op < 1:
            a = np.asarray(c).astype(np.float32)
            a[:, :, 3] *= op
            c = Image.fromarray(a.astype(np.uint8), 'RGBA')
        sheet.alpha_composite(c, (int(cx * w - c.size[0] / 2), int(cy * h - c.size[1] / 2)))
    return sheet.crop(sheet.getbbox())


# Laid out by hand so the pile reads as a composition rather than as scatter.
# x, y are fractions of the sheet; size is in its pixels.
SHARDS = [(.47, .74, 980, 1.0), (.24, .84, 760, 1.0), (.75, .83, 700, 1.0),
          (.36, .52, 560, .97), (.62, .56, 500, .95), (.11, .93, 440, .93),
          (.89, .93, 400, .90), (.50, .31, 280, .74)]

DRIFT = [(.07, .82, 430, .90), (.18, .66, 250, .74), (.29, .88, 520, .95),
         (.40, .60, 200, .62), (.50, .80, 380, .86), (.59, .50, 160, .52),
         (.68, .87, 460, .92), (.77, .64, 240, .70), (.85, .78, 310, .80),
         (.94, .89, 390, .88), (.23, .44, 140, .48), (.72, .38, 120, .44),
         (.35, .32, 105, .38)]


def spire(rock, seed=4409):
    """One monolith, standing: tall, tapered, and set into a low base of its
    own so it rises out of something instead of balancing on a point."""
    g = rnd(seed)
    out = Image.new('RGBA', (900, 1340), (0, 0, 0, 0))
    out.alpha_composite(body(rock, 470, 380, g, verts=15, rough=.46), (215, 960))
    out.alpha_composite(body(rock, 300, 250, g, verts=13, rough=.50), (30, 1060))
    out.alpha_composite(body(rock, 260, 210, g, verts=13, rough=.50), (610, 1090))
    out.alpha_composite(body(rock, 560, 1180, g, verts=21, rough=.30, taper=.62), (170, 60))
    return out.crop(out.getbbox())


def main():
    if not os.path.exists(MASTER):
        raise SystemExit('missing masters/3-cutout.png - run tools/cut_layers.py 3 first')
    m = Image.open(MASTER).convert('RGBA')
    print('source   masters/3-cutout.png %dx%d' % m.size)
    rock = crop(m, ROCK)

    pieces = {
        'fg-ridge':  fit(base_fade(cool(rock), .16, .85), 1400),
        'fg-spire':  fit(base_fade(cool(spire(rock)), .12, .70), 560),
        'fg-shards': fit(base_fade(cool(scatter(rock, 2400, 1460, SHARDS, 5171)), .10, .55), 1200),
        'fg-drift':  fit(cool(scatter(rock, 3000, 1350, DRIFT, 9043)), 1400),
    }
    os.makedirs(OUT, exist_ok=True)
    for name, im in pieces.items():
        dst = os.path.join(OUT, name + '.webp')
        im.save(dst, 'WEBP', quality=Q, method=6)
        a = np.asarray(im).astype(np.float32)
        sel = a[:, :, 3] > 128
        lum = a[:, :, :3].mean(2)[sel] if sel.any() else np.zeros(1)
        print('%-10s %4dx%-4d %6.0f KB   mean lum %4.1f  p95 %5.1f'
              % (name, im.size[0], im.size[1], os.path.getsize(dst) / 1024,
                 lum.mean(), np.percentile(lum, 95)))


if __name__ == '__main__':
    main()
