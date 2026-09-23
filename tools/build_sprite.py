"""Vajradhan sequence sprite — one faceted crystal.

    python tools/build_sprite.py

Writes assets/img/seq-gem.png: a small transparent sprite the scroll sequence
draws 50,000 of, additively. It is a pointed oval cut like a gem — a long
vertical axis, a narrow waist, and facets that catch the light at different
strengths so a spinning field never reads as flat dots.

Kept white and premultiplied-looking (bright core, dark nothing) because the
shader tints and brightens it by depth; a coloured sprite would fight the
site's grade. The faint halo around the stone is what the bloom pass grabs.
"""
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets', 'img', 'seq-gem.png')
S = 128                       # plenty: on screen it is a few dozen pixels


def tri_mask(yy, xx, a, b, c, soft=1.1):
    """Soft coverage of the triangle abc, in pixel space."""
    def edge(p, q):
        # signed distance to the line pq, positive inside
        ex, ey = q[0] - p[0], q[1] - p[1]
        n = np.hypot(ex, ey) or 1.0
        return ((xx - p[0]) * ey - (yy - p[1]) * ex) / n

    e0, e1, e2 = edge(a, b), edge(b, c), edge(c, a)
    inside = np.minimum(np.minimum(e0, e1), e2)
    return np.clip(inside / soft + .5, 0, 1)


def build():
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float64)
    cx = cy = (S - 1) / 2

    # the stone: a pointed oval, taller than it is wide
    ry, rx = S * .46, S * .26
    top, bot = (cx, cy - ry), (cx, cy + ry)
    left, right = (cx - rx, cy + S * .02), (cx + rx, cy + S * .02)
    # the waist sits a little above centre, which is what makes it read as cut
    wl, wr = (cx - rx * .62, cy - S * .13), (cx + rx * .62, cy - S * .13)

    facets = [
        # (triangle, brightness) — lit from the upper left, as the site is
        ((top, wl, wr), .95),
        ((wl, left, wr), .62),
        ((left, right, wr), .50),
        ((left, bot, right), .78),
        ((top, left, wl), .40),
        ((top, wr, right), .34),
    ]
    rgb = np.zeros((S, S))
    alpha = np.zeros((S, S))
    for tri, level in facets:
        m = tri_mask(yy, xx, *tri)
        rgb = np.maximum(rgb, m * level)
        alpha = np.maximum(alpha, m)

    # facet seams: a thin bright line where two faces meet reads as a cut edge
    edges = np.abs(np.gradient(rgb)[0]) + np.abs(np.gradient(rgb)[1])
    rgb = np.clip(rgb + np.clip(edges, 0, 1) * .55, 0, 1)

    # the halo the bloom pass picks up
    d = np.hypot(xx - cx, (yy - cy) * (rx / ry))
    halo = np.clip(1 - d / (rx * 2.6), 0, 1) ** 2.4
    alpha = np.clip(alpha + halo * .34, 0, 1)
    rgb = np.clip(rgb + halo * .30, 0, 1)

    # a touch of core glow so small, far stones still register as points
    core = np.clip(1 - d / (rx * .55), 0, 1) ** 1.6
    rgb = np.clip(rgb + core * .5, 0, 1)

    out = np.zeros((S, S, 4), np.uint8)
    out[..., 0] = out[..., 1] = out[..., 2] = np.round(rgb * 255)
    out[..., 3] = np.round(alpha * 255)
    Image.fromarray(out, 'RGBA').save(OUT, 'PNG', optimize=True)
    print('seq-gem.png', (S, S), os.path.getsize(OUT), 'bytes')


if __name__ == '__main__':
    build()
