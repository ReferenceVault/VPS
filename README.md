# Vajradhan

Static website for **Vajradhan**, a creative technology and visual production studio: *Visualizing the unimaginable.*

It is a single `index.html` that holds the markup, all the CSS and an inline Three.js scene. The hero photograph is cut into five depth planes (sky, moon, far range, mid range, near ridge). Scrolling moves the camera through them, with haze, stars, snow, a cursor trail, a light bloom/grain/vignette pass and word-by-word heading reveals. The site makes no network requests. Three.js and the fonts are both vendored.

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
assets/fonts.css        Onest + Unbounded, embedded as base64 woff2
assets/img/             generated planes, stills, cut-outs and logo
vendor/three.min.js     Three.js r149 (MIT, see vendor/three.LICENSE)
images/                 source images
tools/build_assets.py   rebuilds everything in assets/ from images/
tools/fonts-src/        source woff2 files and their OFL licences
```

## Rebuilding the assets

```bash
pip install pillow numpy
python tools/build_assets.py
```

The script:
- paints the mock-up's baked-in type out of `images/vajradhan1.webp`
- cuts the five depth planes along hand-traced silhouettes, filling the area behind each ridge so the parallax never shows a doubled edge
- keys the logo off its studio background
- grades the foreground cut-outs to moonlight
- re-embeds the fonts

Generated images follow the project naming: `vajradhan1-*` (planes of photo 1), `vajradhan2–5` (work stills), `vajradhan6–9` (cut-outs), `vajradhan-logo`.

## Placeholder content

Facts about the studio that weren't supplied are written as short placeholder copy and marked `<!-- TODO -->` in `index.html`: project names and credits, the contact email (currently `hello@example.com`), social links, studio location, one stat figure and the exact tool list. Search for `TODO` before launch.
