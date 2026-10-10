# Vajradhan

Static website for **Vajradhan**, an independent filmmaking and visual production studio: *Stories. Crafted to be felt.*

It is a single `index.html` that holds the markup, all the CSS and an inline Three.js scene. The backdrop is six planes hung at their own depths — the vortex plate, an orbital ring drawn twice (once behind the figure and once, mirrored, in front of it), the cosmic eye, the figure of light and the cloaked man on his rock. Scrolling moves the camera through them, so the near planes slide past the far ones. On top of that: haze, stars, snow, a cursor trail, a light bloom/grain/vignette pass and word-by-word heading reveals.

The site makes no third-party requests — Three.js and the fonts are local.

## Run it locally

The page loads its images into WebGL, and browsers block that for `file://` pages. Serve the folder over HTTP instead. Opening `index.html` directly shows the static fallback.

```bash
# macOS / Linux
python3 -m http.server 8000

# Windows (Python launcher)
py -m http.server 8000

# or, with Node installed
npx serve .
```

Then open <http://localhost:8000> (or the port `npx serve` prints).

### Useful query flags

| Flag | Effect |
|---|---|
| `?nogl=1` | Force the no-WebGL fallback (static CSS layer stack) |
| `?q=low` | Low quality tier (default on touch devices) |
| `?post=0` | Skip post-processing |
| `?dpr=1` | Override the device-pixel-ratio cap |
| `?adapt=0` | Freeze the adaptive quality governor |
| `?shot=3` | Jump straight to section *n* with every reveal shown (for screenshots) |

In the console, `__vajradhan.loseContext(1500)` drops the WebGL context and restores it after 1.5 s. `__vajradhan.loseContext()` drops it for good, and the page falls back after 4 s.

## Deploy to GitHub Pages

1. Push this folder to a GitHub repository. `index.html` must be at the repo root.
2. In the repository, go to **Settings → Pages**.
3. Under **Build and deployment**, set **Source** to *Deploy from a branch*. Choose the branch (e.g. `main`) and the `/ (root)` folder, then click **Save**.
4. After a minute the site is live at `https://<user>.github.io/<repo>/`.

Every path is relative, so the site works under the `/<repo>/` subpath. The `.nojekyll` file stops Pages from running Jekyll over the files.

### Clean URLs

The two pages serve at `/` and `/packages/`, with no `.html` anywhere a visitor sees. That comes from the file layout alone — `packages/index.html` rather than `packages.html` — so it needs no server rewrites and works on GitHub Pages, which does not do extensionless rewriting. A request for `/packages` is redirected to `/packages/` by the host.

**Paths are relative, not root-relative, and must stay that way.** Under a project subpath a root-relative `/assets/site.css` resolves to the user site's root and 404s; the relative `../assets/site.css` resolves correctly at any depth. The packages page therefore reaches everything through `../`, and links home as `../` and `../#about`. The shared script resolves the hero layers against its own URL rather than the document's, so the same code serves both depths.

## Project layout

```
index.html              the home page, served at /
packages/index.html     the packages page, served at /packages/
favicon.png
assets/site.css         the shared layer: tokens, type, nav, sections, footer
assets/site.js          the shared scene and page wiring
assets/fonts.css        Michroma + Space Grotesk + Space Mono, base64 woff2
assets/img/             generated hero layers and logo
vendor/three.min.js     Three.js r149 (MIT, see vendor/three.LICENSE)
images/                 source images
tools/build_assets.py   rebuilds the logo in assets/ from images/
tools/build_fonts.py    subsets the TTFs and embeds them in assets/fonts.css
tools/cut_layers.py     isolates the four hero elements out of their frames
tools/build_hero_layers.py  encodes the five hero layers as WebP at two widths
tools/fonts-src/        source TTFs and their OFL licences
masters/                full-size cut-outs, gitignored working files
```

## Rebuilding the assets

```bash
pip install pillow numpy
python tools/build_assets.py
```

`build_assets.py` keys the logo off its studio background. Each step needs its own source under `images/`; a step whose source is missing is skipped with a note instead of failing the run.

**The logo source is not in the repository.** `images/logo.jpeg` was never committed, so `assets/img/vajradhan-logo.webp`, `vajradhan-logo-64.png` and `favicon.png` cannot be rebuilt — the committed files are the only copy. Put it back under `images/` and the step runs again.

## The hero layers

```bash
python tools/cut_layers.py          # 3, then 1, 2, 4 -> masters/*-cutout.png
python tools/build_hero_layers.py   # -> assets/img/hero-*-{1920,960}.webp
```

`cut_layers.py` isolates the four elements out of their frames, in three modes, because the frames are not alike:

- **dark** (`3.jpeg`) — a cloaked figure on a lava-seamed rock against a nebula. Colour cannot separate them: the cloak's lit folds and the sky behind are the same pink. What can is that the subject is a dark mass against a sky that stays smooth at every scale, so the silhouette comes from comparing each pixel with a wide local mean, and a colour veto then drops the nebula (magenta, blue well above green) while keeping the lava and rim light (warm).
- **glow** (`1.jpeg`, `2.jpeg`) — luminous subjects on near-black, so brightness *is* the matte. The threads and flares get their own soft edges for free; the work is in keeping only the subject, by finding the main luminous mass and fading everything beyond a soft radius of it.
- **feather** (`4.jpeg`) — no cut at all. It is a second galaxy field, not an object, and segmenting it only halved the disc; it is screened over the plate instead, and its alpha only fades the frame's own edge away.

`build_hero_layers.py` crops each cut-out to its alpha bounding box, zeroes RGB behind the transparency, and writes each layer at its own fraction of 1920 and of 960.

Generated images follow the project naming: `hero-*` (the hero's layers), `vajradhan-logo`.

## Placeholder content

The copy is the client's own (see their handoff sheet). What is still outstanding is marked `<!-- TODO -->` in `index.html`: the business email (the contact button is inert until it exists), the Instagram and LinkedIn URLs, the WhatsApp number, the showreel and its poster, approved stills for the four projects, the About stats figures, and the absolute `og:` URLs. Search for `TODO` before launch.
