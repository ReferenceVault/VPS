"""Cut the hero's four elements out of their frames.

    python tools/cut_layers.py [3] [1] [2] [4]        (default: all four)

Two kinds of frame, so two polarities:

  dark      3.jpeg is a whole scene -- a cloaked figure on a lava-seamed rock
            against a red and blue nebula. Colour cannot separate them: the
            cloak's lit folds and the sky behind are the same pink. What does
            is that the subject is a dark mass against a sky that stays smooth
            at every scale, so the silhouette comes from comparing each pixel
            with a wide local mean. A colour veto then removes the nebula,
            which is magenta (blue well above green) where everything bright
            in the subject -- lava, rim light, lit folds -- is warm.

  glow      1 and 2 are luminous subjects on near-black. Here brightness is
            the matte: alpha rises with luminance, which gives the orbital
            threads, the flares and the galaxy's dust their own soft edges for
            free. The work is in keeping only the subject: the main luminous
            mass is found, everything beyond a soft radius of it is dropped,
            and the outer haze is faded rather than cut, so the frame's own
            starfield never reads as a rectangle.

  feather   4 is not an object at all but a second galaxy field, so it is
            screened over the plate rather than cut out. Its alpha only
            feathers the frame's edge away.

Both paths share the rest: holes judged by brightness, the contour smoothed
before matting, a guided filter against the full-size image for a one or two
pixel matte, and partial alpha kept wherever the edge is soft.

Masters land in masters/ (gitignored); the site's resized WebPs are written by
tools/build_hero_layers.py.
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'images')
OUT = os.path.join(ROOT, 'masters')

# ---------------------------------------------------------------- the frames
LAYERS = {
    # the dark subject on a bright sky
    '3': dict(mode='dark', src='3.jpeg',
              work=.5, local_r=150, dark=11, smooth=13,
              hole_bright=46, near_debris=120, debris_max=3500,
              debris_dark=78, debris_zone=.55,
              nebula_bg=13, nebula_lum=30,
              base_band=.74, base_feather=110),

    # luminous subjects on near-black: alpha follows the light
    '1': dict(mode='glow', src='1.jpeg', work=.5,
              # The figure of light and its threads; the frame's nebula haze
              # sits well below this floor. The falloff has to be generous and
              # centred high: the head and its halo ring sit near the top of
              # the frame, and a circle drawn from the waist fades them out.
              # `close` bridges the neck, which is thinner than the threshold
              # finds on its own, so the head stays part of the one body.
              lo=24, hi=130, core=70, smooth=7, close=31,
              keep_r=.46, fade_r=.64, centre=(.50, .46)),

    '2': dict(mode='glow', src='2.jpeg', work=.5,
              # the iris burns much brighter than its field, so the floor can
              # sit high and still keep the outer rings
              lo=30, hi=150, core=96, smooth=7,
              keep_r=.40, fade_r=.52, centre=(.50, .50)),

    # 4 is a field, not an object: there is nothing in it to isolate, and
    # segmenting it only cuts the disc in half. It is screened over the plate
    # instead, and all its alpha does is feather the frame's own edge away.
    '4': dict(mode='feather', src='4.jpeg',
              keep_r=.30, fade_r=.52, centre=(.52, .48)),
}


def box(img, r):
    return cv2.blur(img, (r, r))


def guided(guide, src, radius=8, eps=1e-4):
    """Guided filter: src smoothed so its edges follow the guide's."""
    g = guide.astype(np.float32) / 255.0
    p = src.astype(np.float32)
    mg, mp = box(g, radius), box(p, radius)
    a = (box(g * p, radius) - mg * mp) / (box(g * g, radius) - mg * mg + eps)
    b = mp - a * mg
    return np.clip(box(a, radius) * g + box(b, radius), 0, 1)


def keep_main(mask):
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if n < 2:
        return mask, None, lab, stats, n
    main = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return np.where(lab == main, 255, 0).astype(np.uint8), main, lab, stats, n


def holes(mask, lum, bright):
    """Enclosed holes: bright ones are background and stay open."""
    inv = cv2.bitwise_not(mask)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(inv, 4)
    edge = set(lab[0]) | set(lab[-1]) | set(lab[:, 0]) | set(lab[:, -1])
    kept = filled = 0
    for i in range(1, n):
        if i in edge:
            continue
        piece = lab == i
        if lum[piece].mean() > bright:
            kept += 1
        else:
            mask[piece] = 255
            filled += 1
    return mask, kept, filled


# ------------------------------------------------------------ dark on bright
def cut_dark(img, c):
    H, W = img.shape[:2]
    small = cv2.resize(img, (int(W * c['work']), int(H * c['work'])), interpolation=cv2.INTER_AREA)
    h, w = small.shape[:2]
    lum = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)
    b, g = small[:, :, 0].astype(np.float32), small[:, :, 1].astype(np.float32)
    nebula = ((b - g) > c['nebula_bg']) & (lum > c['nebula_lum'])
    print('  nebula     %.1f%% vetoed by colour' % (nebula.mean() * 100))

    local = cv2.GaussianBlur(lum, (0, 0), c['local_r'] / 3.0)
    core = (((local - lum) > c['dark']) & ~nebula).astype(np.uint8) * 255
    core = cv2.morphologyEx(core, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    core = cv2.morphologyEx(core, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))

    keep, main, lab, stats, n = keep_main(core)
    keep = cv2.morphologyEx(keep, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (19, 19)))
    keep, _, _, _, _ = keep_main(keep)
    print('  silhouette %.1f%% of the frame' % ((keep > 0).mean() * 100))

    reach = cv2.dilate(keep, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (c['near_debris'], c['near_debris'])))
    kept = dropped = 0
    for i in range(1, n):
        if i == main or stats[i, cv2.CC_STAT_AREA] < 6:
            continue
        piece = lab == i
        if ((reach[piece] > 0).mean() > .5 and stats[i, cv2.CC_STAT_AREA] < c['debris_max']
                and lum[piece].mean() < c['debris_dark'] and stats[i, cv2.CC_STAT_TOP] > c['debris_zone'] * h):
            keep[piece] = 255
            kept += 1
        else:
            dropped += 1
    print('  debris     kept %d near the rock, dropped %d' % (kept, dropped))

    keep, hk, hf = holes(keep, lum, c['hole_bright'])
    print('  holes      %d open (sky), %d filled (rock)' % (hk, hf))

    soft = cv2.GaussianBlur(keep.astype(np.float32) / 255.0, (0, 0), c['smooth'] / 3.0)
    up = cv2.resize((soft > .5).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)

    guide = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    alpha = guided(guide, up, radius=10, eps=2e-4)
    alpha = np.clip((alpha - .45) / .22, 0, 1)
    alpha = guided(guide, alpha, radius=4, eps=8e-5)

    band = np.zeros((H, W), np.float32)
    band[int(c['base_band'] * H):] = 1.0
    band = cv2.GaussianBlur(band, (0, 0), H * .045)
    wide = cv2.GaussianBlur(alpha, (0, 0), c['base_feather'] * .5)
    alpha = alpha * (1 - band) + np.minimum(alpha, wide) * band
    glow = np.clip((guide.astype(np.float32) - 30) / 85.0, 0, 1) * band
    alpha = np.clip(np.maximum(alpha, np.minimum(glow, wide * 1.5)), 0, 1)

    fb, fg_ = img[:, :, 0].astype(np.float32), img[:, :, 1].astype(np.float32)
    veto = (((fb - fg_) > c['nebula_bg']) & (guide.astype(np.float32) > c['nebula_lum'])).astype(np.float32)
    alpha = np.clip(alpha * (1 - cv2.GaussianBlur(veto, (0, 0), 2.0) * .92), 0, 1)
    return alpha


# ----------------------------------------------------------- glow on near-black
def cut_glow(img, c):
    """Brightness is the matte; the work is keeping only the subject."""
    H, W = img.shape[:2]
    guide = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    lum = guide.astype(np.float32)

    # alpha straight off the light, which gives soft edges for nothing
    alpha = np.clip((lum - c['lo']) / float(c['hi'] - c['lo']), 0, 1)

    # where is the subject? the bright core, grown and softened
    small = cv2.resize(guide, (int(W * c['work']), int(H * c['work'])), interpolation=cv2.INTER_AREA)
    h, w = small.shape[:2]
    core = (small > c['core']).astype(np.uint8) * 255
    k = c.get('close', 21)
    core = cv2.morphologyEx(core, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    keep, _, _, _, _ = keep_main(core)
    keep, hk, hf = holes(keep, small.astype(np.float32), 10 ** 9)   # never fill: a dark pupil stays dark
    print('  core       %.1f%% of the frame is the luminous mass' % ((keep > 0).mean() * 100))

    soft = cv2.GaussianBlur(keep.astype(np.float32) / 255.0, (0, 0), c['smooth'])
    region = cv2.resize(soft, (W, H), interpolation=cv2.INTER_LINEAR)

    # a soft ellipse around the mass: inside it everything survives, outside it
    # the frame's own starfield fades out rather than ending on a line
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = c['centre'][0] * W, c['centre'][1] * H
    r = np.sqrt(((xx - cx) / W) ** 2 + ((yy - cy) / H) ** 2)
    ring = np.clip((c['fade_r'] - r) / max(1e-6, c['fade_r'] - c['keep_r']), 0, 1)
    ring = ring * ring * (3 - 2 * ring)

    alpha = alpha * np.maximum(region, 0) * ring
    alpha = guided(guide, alpha, radius=4, eps=1e-4)
    return np.clip(alpha, 0, 1)


# --------------------------------------------------- a field, screened, feathered
def cut_feather(img, c):
    """No segmentation: every pixel is kept, the frame's edge is faded out."""
    H, W = img.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = c['centre'][0] * W, c['centre'][1] * H
    r = np.sqrt(((xx - cx) / W) ** 2 + ((yy - cy) / H) ** 2)
    a = np.clip((c['fade_r'] - r) / max(1e-6, c['fade_r'] - c['keep_r']), 0, 1)
    a = a * a * (3 - 2 * a)
    print('  feather    no cut; %.1f%% of the frame at full strength' % ((a > .98).mean() * 100))
    return a


def build(keys):
    os.makedirs(OUT, exist_ok=True)
    for k in keys:
        c = LAYERS[k]
        path = os.path.join(SRC, c['src'])
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        if img is None:
            print('skip %s - missing images/%s' % (k, c['src']))
            continue
        H, W = img.shape[:2]
        print('%s  %s  %dx%d  (%s)' % (k, c['src'], W, H, c['mode']))
        alpha = {'dark': cut_dark, 'glow': cut_glow, 'feather': cut_feather}[c['mode']](img, c)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        out = np.dstack([rgb, (alpha * 255 + .5).astype(np.uint8)])
        dst = os.path.join(OUT, '%s-cutout.png' % k)
        Image.fromarray(out, 'RGBA').save(dst, 'PNG', optimize=True)
        print('  written    masters/%s-cutout.png  %.1f MB   opaque %.1f%%  partial %.1f%%'
              % (k, os.path.getsize(dst) / 1048576, (alpha > .98).mean() * 100,
                 ((alpha > .02) & (alpha <= .98)).mean() * 100))


if __name__ == '__main__':
    keys = [a for a in sys.argv[1:] if a in LAYERS] or ['3', '1', '2', '4']
    build(keys)
