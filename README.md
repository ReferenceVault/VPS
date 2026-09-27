# Vajradhan

Static website for **Vajradhan**, an independent filmmaking and visual production studio: *Stories. Crafted to be felt.*

It is a single `index.html` that holds the markup, all the CSS and an inline Three.js scene. The hero plate is cut into five depth planes (sky and vortex, horizon haze, city, shore, road). Scrolling moves the camera through them, with haze, stars, snow, a cursor trail, a light bloom/grain/vignette pass and word-by-word heading reveals.

Below the hero, the studio film hangs on a WebGL cloth: the video is painted into a canvas frame by frame and mapped onto a fabric that billows on a wind field and lifts under the pointer. On touch, or under `prefers-reduced-motion`, the plain video element shows instead.

The site makes no third-party requests — Three.js, the fonts and the film are all local.

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

## Project layout

```
index.html              page, styles and the inline Three.js scene
favicon.png
assets/fonts.css        Michroma + Space Grotesk + Space Mono, base64 woff2
assets/img/             generated planes, cut-outs and logo
vendor/three.min.js     Three.js r149 (MIT, see vendor/three.LICENSE)
images/                 source images
tools/build_assets.py   rebuilds the logo and cut-outs in assets/ from images/
tools/build_hero.py     cuts the hero plate into its five depth planes
tools/fonts-src/        source TTFs and their OFL licences
```

## Rebuilding the assets

```bash
pip install pillow numpy
python tools/build_assets.py
```

`build_assets.py` keys the logo off its studio background, grades the foreground cut-outs into the hero plate's dusk and re-embeds the fonts. Each step needs its own source under `images/`; a step whose source is missing is skipped with a note instead of failing the run.

**The logo source is not in the repository.** `images/logo.jpeg` was never committed, so `assets/img/vajradhan-logo.webp`, `vajradhan-logo-64.png` and `favicon.png` cannot be rebuilt — the committed files are the only copy. Put it back under `images/` and the step runs again.

The cut-outs' own originals are gone too, so the first build's moonlit output was kept as their source (`images/cutout-6..9.webp`); the grade now carries those into the hero plate's dusk.

`build_hero.py` cuts `images/vajradhan11.png` into the five depth planes along hand-traced lines (skyline, horizon haze, city, road), filling the area behind each one so the parallax never shows a doubled edge. Pass `--png` to write transparent PNGs beside the webp plates.

Generated images follow the project naming: `vajradhan11-*` (planes of the hero plate), `vajradhan6–9` (cut-outs), `vajradhan-logo`.

## The studio film

`assets/videos/vajradhan1.mp4` is the file as delivered: **HEVC (hvc1)**, 1918x1080, 60 fps, 10.1 s, 17.35 MB. It is not re-encoded.

Two things follow from that, and both want a decision before launch:

- **HEVC only plays where the operating system provides a decoder.** Chrome and Edge lean on the OS for it, Safari has it, and Firefox does not support it at all. A visitor whose machine cannot decode it sees the card with nothing in it.
- **There is no poster frame yet**, which is exactly what would cover that case. It needs one frame exported as WebP; ffmpeg is the usual way.

The `<video>` is muted, looped, inline, `preload="metadata"`, without controls, and is started and stopped by an IntersectionObserver so nothing decodes off-screen.

## Placeholder content

The copy is the client's own (see their handoff sheet). What is still outstanding is marked `<!-- TODO -->` in `index.html`: the business email (the contact button is inert until it exists), the Instagram and LinkedIn URLs, the WhatsApp number, the showreel and its poster, a poster frame for the studio film, approved stills for the four projects, the About stats figures, and the absolute `og:` URLs. Search for `TODO` before launch.
