"""Vajradhan fonts — subset, compress and embed.

    python tools/build_fonts.py

Takes the upstream TTFs in tools/fonts-src/ and writes assets/fonts.css: every
face subset to Latin plus the punctuation this page actually sets, compressed
to woff2 and embedded as base64, so the page asks the network for nothing.

    Michroma        400            display: wordmark, headings, capability labels
    Space Grotesk   300 400 500    running copy, navigation
    Space Mono      400 700        numbers, eyebrows, buttons, metadata

Space Grotesk ships as a variable font, so the three weights are instanced out
of it before subsetting. All three families are SIL Open Font Licence 1.1; the
licences sit beside the sources.
"""
import base64
import io
import os

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'tools', 'fonts-src')
OUT = os.path.join(ROOT, 'assets', 'fonts.css')

# Basic Latin, then the few marks the page sets: the copyright line, the em
# dashes in the eyebrows, the typographic apostrophe, the bullet in the
# keyword strips, the middot, the arrow, and the quotes a copy edit may bring.
UNICODES = (
    'U+0020-007E,'          # basic latin
    'U+00A0,'               # no-break space
    'U+00A9,'               # (c)
    'U+00B7,'               # middot
    'U+00D7,'               # times
    'U+2013-2014,'          # en, em dash
    'U+2018-201A,U+201C-201E,'   # quotes
    'U+2022,'               # bullet
    'U+2026,'               # ellipsis
    'U+2039-203A,'          # single angle quotes
    'U+2192,'               # arrow
    'U+2212,'               # minus
    'U+20B9,'               # rupee
    'U+2122'                # trademark
)

FACES = [
    # family, weight, source, instance weight (None = static source)
    ('Michroma',      400, 'Michroma-Regular.ttf',  None),
    ('Space Grotesk', 300, 'SpaceGrotesk-var.ttf',  300),
    ('Space Grotesk', 400, 'SpaceGrotesk-var.ttf',  400),
    ('Space Grotesk', 500, 'SpaceGrotesk-var.ttf',  500),
    ('Space Mono',    400, 'SpaceMono-Regular.ttf', None),
    ('Space Mono',    700, 'SpaceMono-Bold.ttf',    None),
]


def cut(path, weight):
    """Instance if the source is variable, then subset, then woff2."""
    font = TTFont(path)
    if weight is not None:
        font = instancer.instantiateVariableFont(font, {'wght': weight})
    opts = subset.Options()
    opts.flavor = 'woff2'
    opts.desubroutinize = True
    opts.layout_features = ['kern', 'liga', 'calt', 'ccmp', 'locl', 'mark', 'mkmk']
    opts.name_IDs = ['*']
    opts.notdef_outline = True
    opts.recalc_bounds = True
    sub = subset.Subsetter(options=opts)
    sub.populate(unicodes=subset.parse_unicodes(UNICODES))
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = 'woff2'
    font.save(buf)
    font.close()
    return buf.getvalue()


def build():
    lines = ['/* Michroma, Space Grotesk and Space Mono (SIL Open Font License 1.1,',
             '   see tools/fonts-src), subset to latin and embedded as base64 woff2',
             '   so the page makes no font request. Rebuild: python tools/build_fonts.py */']
    print('%-16s %-4s %10s %10s %7s' % ('family', 'wt', 'source ttf', 'woff2', 'saved'))
    total_src = total_out = 0
    for family, weight, fname, inst in FACES:
        path = os.path.join(SRC, fname)
        if not os.path.exists(path):
            print('skip  %-14s - missing tools/fonts-src/%s' % (family, fname))
            continue
        raw = os.path.getsize(path)
        data = cut(path, inst)
        total_src += raw
        total_out += len(data)
        print('%-16s %-4d %9.1fK %9.1fK %6.1f%%'
              % (family, weight, raw / 1024, len(data) / 1024, 100 - len(data) / raw * 100))
        b64 = base64.b64encode(data).decode('ascii')
        lines.append("@font-face{font-family:'%s';font-style:normal;font-weight:%d;"
                     "font-display:swap;src:url(data:font/woff2;base64,%s) format('woff2');}"
                     % (family, weight, b64))
    with open(OUT, 'w', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    css = os.path.getsize(OUT)
    print()
    print('sources      %.1f KB' % (total_src / 1024))
    print('woff2        %.1f KB' % (total_out / 1024))
    print('fonts.css    %.1f KB  (base64 adds about a third)' % (css / 1024))


if __name__ == '__main__':
    build()
