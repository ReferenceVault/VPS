"""Vajradhan hero build — the vortex plate.

Cuts images/vajradhan11.png into the same five depth planes the scene has
always had (sky, moon, far, mid, near), at the same 2048x1143 frame and under
the same names, so index.html only has to point at new files.

    python tools/build_hero.py [--png]

The plate arrives clean — no baked type, unlike the first hero photo — so
there is no paint-out stage here; the cutting is all that is left. The cutting
helpers (blur, line_y, below, extend_behind) come from build_assets.py, which
still owns the logo, the cut-outs and the fonts.

Bands, back to front:
  sky   the whole cloudscape and the vortex, opaque, everything under the
        skyline replaced by smeared sky
  moon  the haze band along the horizon — the most distant land. It keeps the
        'moon' key because the scene names that slot, and fades out downward
        so the plane in front of it can never open a seam over it
  far   the city mass
  mid   the near city, the shoreline and the sea
  near  the road, its bank and the closest surf
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from build_assets import blur, below, extend_behind, line_y, out, src  # noqa: E402

PLATE = src('vajradhan11.png')
W, H = 2048, 1143                      # the frame every plane shares
SW, SH = 1678, 937                     # the plate as delivered
KX, KY = W / SW, H / SH

# ------------------------------------------------------------------ tracing
# Traced off the plate at source resolution, then scaled to the frame.
# skyline: the top of the land — distant towers, the central spire, the far
# shore on the right.
SKYLINE_S = [(0, 648), (60, 644), (120, 638), (180, 626), (230, 640), (300, 646), (380, 642),
             (440, 634), (500, 641), (560, 646), (620, 649), (700, 646), (760, 639), (820, 632),
             (870, 626), (910, 618), (950, 610), (990, 624), (1030, 616), (1070, 601),
             (1100, 556), (1112, 552), (1124, 596), (1150, 612), (1180, 622), (1220, 630),
             (1270, 636), (1330, 642), (1390, 648), (1450, 652), (1520, 657), (1600, 660),
             (1678, 663)]
# the haze band's lower edge: as far down the city as the horizon air still
# flattens it. The moon plane fades out through here rather than stopping.
HAZE_S = [(0, 700), (200, 702), (400, 706), (600, 708), (800, 700), (1000, 690), (1200, 680),
          (1400, 674), (1678, 670)]
# midline: the bottom of the city mass — the waterline on the right, the
# rooftops running down to the bank on the left.
MIDLINE_S = [(0, 748), (150, 747), (300, 750), (450, 754), (600, 758), (700, 760), (770, 752),
             (860, 744), (960, 734), (1080, 723), (1200, 714), (1350, 705), (1500, 699),
             (1678, 694)]
# nearline: the top of the foreground wedge — the road's far end and the left
# guardrail, then the grass bank and the nearest surf down to the corner.
NEARLINE_S = [(0, 802), (90, 796), (190, 789), (300, 782), (420, 775), (540, 769), (650, 764),
              (700, 763), (760, 773), (820, 789), (900, 812), (1000, 840), (1100, 867),
              (1250, 898), (1400, 916), (1550, 927), (1678, 934)]
# the vortex eye, source pixels: centre and radius (the scene's halo and its
# star-free zone key off this).
EYE_S = (892, 292, 95)


def scale(poly):
    return [(round(x * KX), round(y * KY)) for x, y in poly]


SKYLINE, HAZE, MIDLINE, NEARLINE = (scale(p) for p in (SKYLINE_S, HAZE_S, MIDLINE_S, NEARLINE_S))
EYE = (round(EYE_S[0] * KX), round(EYE_S[1] * KY), round(EYE_S[2] * KX))


def fade_below(poly, span=150, feather=2.0):
    """1 above the line, falling to 0 `span` px under it — the soft tail that
    keeps the plane in front from ever opening a seam over this one."""
    y = line_y(poly, W)
    yy = np.arange(H)[:, None]
    m = np.clip(1 - (yy - y[None, :]) / float(span), 0, 1)
    return blur(m, feather)


def band(top, bottom_fade):
    """Everything below `top`, fading out under `bottom_fade`."""
    return below(top, W, H) * bottom_fade


def save_rgba(rgb, alpha, name, png=False, q=86):
    a = np.clip(alpha * 255, 0, 255).astype(np.uint8)
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB')
    im.putalpha(Image.fromarray(a))
    if png:
        im.save(out(name.replace('.webp', '.png')), 'PNG', optimize=True)
    im.save(out(name), 'WEBP', quality=q, method=6)


def build(png=False):
    if not os.path.exists(PLATE):
        raise SystemExit('missing source: images/%s' % os.path.basename(PLATE))
    im = Image.open(PLATE).convert('RGB').resize((W, H), Image.LANCZOS)
    a = np.asarray(im).astype(np.float64)

    # sky — opaque, the land replaced by the air just above it
    sky = extend_behind(a, SKYLINE, band=26, seed=21)
    Image.fromarray(np.clip(sky, 0, 255).astype(np.uint8)).save(
        out('vajradhan11-sky.webp'), 'WEBP', quality=84, method=6)
    if png:
        Image.fromarray(np.clip(sky, 0, 255).astype(np.uint8)).save(
            out('vajradhan11-sky.png'), 'PNG', optimize=True)

    # moon slot — the horizon haze band, filled below the city line so its own
    # smear is what shows if it ever slides clear
    haze = extend_behind(a, MIDLINE, band=20, seed=22)
    save_rgba(haze, band(SKYLINE, fade_below(HAZE, span=170)), 'vajradhan11-moon.webp', png, q=88)

    far = extend_behind(a, MIDLINE, band=20, seed=23)
    save_rgba(far, below(HAZE, W, H), 'vajradhan11-far.webp', png)

    mid = extend_behind(a, NEARLINE, band=20, seed=24)
    save_rgba(mid, below(MIDLINE, W, H), 'vajradhan11-mid.webp', png)

    save_rgba(a, below(NEARLINE, W, H), 'vajradhan11-near.webp', png)

    def mean(x0, y0, x1, y1):
        return tuple(int(v) for v in a[y0:y1, x0:x1].reshape(-1, 3).mean(0))

    print('frame        ', (W, H))
    print('eye (x,y,r)  ', EYE, '-> uv', (round(EYE[0] / W, 4), round(EYE[1] / H, 4)),
          'r', round(EYE[2] / W, 4))
    print('palette - sky top   ', mean(200, 10, 1000, 120))
    print('palette - vortex rim', mean(1150, 380, 1350, 470))
    print('palette - horizon   ', mean(600, 790, 1000, 830))
    print('palette - city      ', mean(400, 820, 900, 890))
    print('palette - road      ', mean(300, 1020, 800, 1140))
    return EYE


if __name__ == '__main__':
    build(png='--png' in sys.argv)
