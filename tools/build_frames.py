"""Vajradhan sequence frames — the reference stills, encoded for the page.

    python tools/build_frames.py

Takes the 16 frames dropped in images/ (1.jpg..16.jpg or 01.jpg..16.jpg, in
story order) and writes two WebP widths of each into assets/img/frames/:

    frame-01-1920.webp   the full plate, for desktop
    frame-01-960.webp    half width, which is what phones fetch

The frames are dark and nearly monochrome, so WebP takes them a long way
down. Quality 80 with method 6 is the knob; sharp_yuv keeps the thin
light-trails from breaking up in the chroma planes, which is where a low
bitrate shows first on line-work over black.

The JPEGs stay untouched as the originals.
"""
import os
import re

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'images')
OUT = os.path.join(ROOT, 'assets', 'img', 'frames')
WIDTHS = (1920, 960)
QUALITY = 80


def frames():
    """The .jpg files in images/ whose names are numbers, in numeric order."""
    found = []
    for name in os.listdir(SRC):
        m = re.fullmatch(r'0*(\d+)\.jpe?g', name, re.I)
        if m:
            found.append((int(m.group(1)), name))
    return [n for _, n in sorted(found)]


def build():
    names = frames()
    if not names:
        raise SystemExit('no numbered .jpg frames found in images/')
    os.makedirs(OUT, exist_ok=True)
    totals = {w: 0 for w in WIDTHS}
    src_total = 0
    print('%-10s %-12s %10s %10s %10s' % ('frame', 'source', 'jpg', '1920', '960'))
    for i, name in enumerate(names, 1):
        path = os.path.join(SRC, name)
        src_total += os.path.getsize(path)
        im = Image.open(path).convert('RGB')
        row = ['%02d' % i, '%s %dx%d' % (name, im.size[0], im.size[1]),
               '%.0f KB' % (os.path.getsize(path) / 1024.0)]
        for w in WIDTHS:
            h = round(im.size[1] * w / im.size[0])
            out = os.path.join(OUT, 'frame-%02d-%d.webp' % (i, w))
            im.resize((w, h), Image.LANCZOS).save(
                out, 'WEBP', quality=QUALITY, method=6)
            n = os.path.getsize(out)
            totals[w] += n
            row.append('%.0f KB' % (n / 1024.0))
        print('%-10s %-12s %10s %10s %10s' % tuple(row))
    print()
    print('frames            ', len(names))
    print('originals (jpg)   ', '%.2f MB' % (src_total / 1048576.0))
    for w in WIDTHS:
        print('webp %-4d         ' % w, '%.2f MB  (avg %.0f KB)'
              % (totals[w] / 1048576.0, totals[w] / 1024.0 / len(names)))
    print('what a phone loads ', '%.2f MB' % (totals[960] / 1048576.0))
    print('what a desktop loads', '%.2f MB' % (totals[1920] / 1048576.0))


if __name__ == '__main__':
    build()
