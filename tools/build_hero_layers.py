"""Encode the hero's five layers as WebP at two widths.

    python tools/build_hero_layers.py

Reads the plate straight from images/background.jpeg and the four cut-out
masters from masters/ (built by tools/cut_layers.py), and writes

    assets/img/hero-<name>-1920.webp   and  -960.webp

Each cut-out is cropped to its own alpha bounding box first, so the width the
CSS gives a layer is the width of the thing in it rather than of the frame it
came in; RGB is zeroed wherever alpha is, which costs nothing (the source is
black there) and makes the encode far smaller. The two widths are a fraction
of the viewport, not of the page: a layer shown at 46vw is encoded at 46% of
1920 and of 960, which is what the srcset/sizes pair then asks for.
"""
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets', 'img')
Q = 82

#      key          name       vw     source
PLAN = [('bg',    'plate',    1.00, os.path.join(ROOT, 'images', 'background.jpeg')),
        ('4',     'galaxy',    .34, os.path.join(ROOT, 'masters', '4-cutout.png')),
        ('2',     'iris',      .46, os.path.join(ROOT, 'masters', '2-cutout.png')),
        ('1',     'figure',    .40, os.path.join(ROOT, 'masters', '1-cutout.png')),
        ('3',     'rock',      .52, os.path.join(ROOT, 'masters', '3-cutout.png'))]

PAD = .01           # a little air round the alpha bounding box


def crop_to_alpha(im):
    a = np.asarray(im.split()[-1])
    ys, xs = np.where(a > 2)
    if not len(xs):
        return im, (0, 0, 1, 1)
    H, W = a.shape
    px, py = int(W * PAD), int(H * PAD)
    box = (max(0, xs.min() - px), max(0, ys.min() - py),
           min(W, xs.max() + 1 + px), min(H, ys.max() + 1 + py))
    return im.crop(box), tuple(round(v / d, 4) for v, d in zip(box, (W, H, W, H)))


def main():
    os.makedirs(OUT, exist_ok=True)
    total = 0
    for key, name, vw, src in PLAN:
        if not os.path.exists(src):
            print('skip %-7s - missing %s' % (name, os.path.relpath(src, ROOT)))
            continue
        im = Image.open(src)
        if im.mode == 'RGBA':
            im, box = crop_to_alpha(im)
            rgb = np.asarray(im).copy()
            rgb[:, :, :3][rgb[:, :, 3] < 2] = 0      # black behind the transparency
            im = Image.fromarray(rgb, 'RGBA')
            where = '  crop %s' % (box,)
        else:
            im, where = im.convert('RGB'), ''
        line = '%-7s %4.0fvw  %dx%d%s' % (name, vw * 100, im.size[0], im.size[1], where)
        for full in (1920, 960):
            w = max(16, int(round(vw * full)))
            h = max(1, int(round(w * im.size[1] / im.size[0])))
            dst = os.path.join(OUT, 'hero-%s-%d.webp' % (name, full))
            im.resize((w, h), Image.LANCZOS).save(dst, 'WEBP', quality=Q, method=6)
            kb = os.path.getsize(dst) / 1024
            total += kb
            line += '\n         -> %-28s %4dx%-4d %6.0f KB' % (os.path.basename(dst), w, h, kb)
        print(line)
    print('total    %.0f KB across both widths (%.0f KB for the 1920 set alone)'
          % (total, sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT)
                        if f.startswith('hero-') and f.endswith('-1920.webp')) / 1024))


if __name__ == '__main__':
    main()
