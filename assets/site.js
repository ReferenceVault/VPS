/* =====================================================================
   VAJRADHAN · the shared scene and page wiring, loaded by every page.

   Lifted whole out of index.html. Two things in it were tied to the home
   page and are now read from the DOM instead: the camera walks as many
   waypoints as the page has [data-cam] sections, and the progress rail
   takes its labels from each section's data-rail. Nothing else changed.

   NOTE: effects 2-8 of the hero brief (entrance choreography, exit
   divergence, shooting stars, scroll momentum, gyroscope parallax, pointer
   light, slow life) are not built yet; only idle drift is. When they land
   they land here, so both pages get them at once.
   ===================================================================== */
/* =====================================================================
   VAJRADHAN — a city under a vortex, cut into depth and walked through.

   The hero plate is split into five planes (sky and vortex, the horizon haze
   band, the city, the shore, the road). Each is hung at its own depth and
   sized so that, from the opening camera, all five project back onto exactly
   the original frame. Scrolling then moves the camera into them, so the bands
   separate, the road slides past and the city comes forward — Kage's camera
   travel, built from a photograph instead of a modelled temple.
   ===================================================================== */
(function () {
'use strict';

/* ------------------------------------------------------------ 0 · basics */
const Q      = new URLSearchParams(location.search);
const qs     = (k, d) => { const v = Q.get(k); return v === null ? d : v; };
const qn     = (k, d) => { const v = Q.get(k); return v === null ? d : parseFloat(v); };
const REDUCE = matchMedia('(prefers-reduced-motion: reduce)').matches;
const COARSE = matchMedia('(hover: none)').matches;

/* ------------------------------------------------------ WhatsApp routing
   Every conversion on the site opens WhatsApp with its own pre-filled
   message. The number lives here and nowhere else, so it changes once.

   The rule for which controls these are: anything phrased as an action
   opens WhatsApp; anything phrased as a place scrolls. So every .cta --
   Start a Project, Choose Package, Discuss This Tier, Discuss Your
   Project, Book a Shoot, Send on WhatsApp -- carries a data-wa message,
   while the menu's Contact link, being a destination, still scrolls to the
   section. A control labelled with a verb should never cost two clicks to
   reach one outcome.

   TODO: the client's WhatsApp number — digits only, country code first,
   no '+', spaces or dashes, e.g. '919876543210'. While this is empty every
   WhatsApp control stays disabled, exactly as the contact button does
   today, rather than linking to a number that does not answer. */
const WHATSAPP = '';

/* wa.me carries the message as one encoded query parameter.
   encodeURIComponent is what turns the line breaks into %0A. */
const waURL = msg => WHATSAPP ? 'https://wa.me/' + WHATSAPP + '?text=' + encodeURIComponent(msg) : '';

const clamp  = (v, a, b) => v < a ? a : (v > b ? b : v);
/* How hard the scene plays. A page that is not the landing page sets
   data-scene on <body> to hold the pointer parallax and the idle drift back,
   so it carries the same world without competing with the front door. 1 is
   the home page; anything lower is quieter. */
const SCENE  = (() => {
  const v = parseFloat(document.body && document.body.dataset.scene);
  return isFinite(v) ? (v < 0 ? 0 : v > 1 ? 1 : v) : 1;
})();
const sat    = v => clamp(v, 0, 1);
const lerp   = (a, b, t) => a + (b - a) * t;
const smooth = (e0, e1, x) => { const t = sat((x - e0) / (e1 - e0)); return t * t * (3 - 2 * t); };
const easeOut= t => 1 - Math.pow(1 - t, 3);
const TAU    = Math.PI * 2;
/* frame-rate independent damping */
const damp   = (cur, to, rate, dt) => lerp(cur, to, 1 - Math.exp(-rate * dt));
const $  = s => document.querySelector(s);
const $$ = s => [].slice.call(document.querySelectorAll(s));

function mulberry32(a) {
  return function () {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
function cvs(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }

/* soft round falloff — haze, glows, snow */
function texGlow(inner, mid) {
  const S = 256, c = cvs(S, S), x = c.getContext('2d');
  const g = x.createRadialGradient(S / 2, S / 2, 0, S / 2, S / 2, S / 2);
  g.addColorStop(0, inner || 'rgba(255,255,255,1)');
  g.addColorStop(.28, mid || 'rgba(255,255,255,.36)');
  g.addColorStop(.62, 'rgba(255,255,255,.07)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  x.fillStyle = g; x.fillRect(0, 0, S, S);
  return c;
}
/* a mote: a hard bright point inside a very faint, wide halo */
function texWisp() {
  const S = 128, c = cvs(S, S), x = c.getContext('2d');
  const g = x.createRadialGradient(S / 2, S / 2, 0, S / 2, S / 2, S / 2);
  g.addColorStop(0,   'rgba(255,255,255,1)');
  g.addColorStop(.07, 'rgba(236,244,252,.92)');
  g.addColorStop(.16, 'rgba(196,214,238,.40)');
  g.addColorStop(.34, 'rgba(140,166,206,.13)');
  g.addColorStop(.62, 'rgba(96,120,168,.035)');
  g.addColorStop(1,   'rgba(70,96,142,0)');
  x.fillStyle = g; x.fillRect(0, 0, S, S);
  return c;
}

/* ============================================================ 1 · gl state */
const canvas = document.getElementById('gl');
/* the layout viewport — what CSS lays out against — not innerWidth */
const vpW = () => document.documentElement.clientWidth  || innerWidth;
const vpH = () => document.documentElement.clientHeight || innerHeight;
let renderer = null, scene = null, camera = null, maxAniso = 1;
const LOW          = qs('q', COARSE ? 'low' : 'high') === 'low';
const WANT_POST    = qs('post', '1') !== '0';
const DPR_CAP      = qn('dpr', LOW ? 1.5 : 2);
const MSAA         = LOW ? 0 : 4;
/* The scene is fill-bound — five screen-sized alpha planes, haze and a bloom
   chain — so resolution is the knob. The governor trades multisampling away
   first (cheapest to lose, least visible under grain), then pixels. */
const PERF = { scale: 1, acc: 0, n: 0, calm: 0, msaa: MSAA, locked: qs('adapt', '1') === '0' };

let FALLEN = false, BOOTED = false, running = false;
const GL = { lost: false, timer: 0 };

function initGL() {
  if (qs('nogl', '0') !== '0') throw new Error('WebGL disabled by ?nogl');
  if (!window.THREE) throw new Error('three.js did not load');
  renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: !WANT_POST, alpha: false,
    powerPreference: 'high-performance' });
  /* Everything is authored and composited in display space: the plates are
     photographs, already encoded, and no light is simulated on them. So no
     texture is decoded and nothing is re-encoded on the way out. */
  renderer.outputEncoding = THREE.LinearEncoding;
  renderer.toneMapping = THREE.NoToneMapping;
  renderer.setClearColor(0x413e3f, 1);
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, DPR_CAP));
  renderer.setSize(vpW(), vpH(), true);
  maxAniso = renderer.capabilities.getMaxAnisotropy();
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x413e3f);      /* the sky's own top colour */
  camera = new THREE.PerspectiveCamera(CAM[0].fov, vpW() / vpH(), .1, 400);
  scene.add(camera);

  /* Kage never listened for these, so a dropped context — a mobile GPU
     reclaiming memory, a long tab switch — left a black canvas under a page
     that kept scrolling. three.js restores its own state on the second event;
     the page stops drawing on the first, and either rebuilds on the second or
     gives up and falls back if the context is not handed back in time. Both
     listeners go on after the renderer's own, so they run after it. */
  canvas.addEventListener('webglcontextlost', onContextLost, false);
  canvas.addEventListener('webglcontextrestored', onContextRestored, false);
}

function onContextLost(e) {
  e.preventDefault();                          /* ask for it back */
  GL.lost = true; running = false;
  console.warn('[vajradhan] WebGL context lost');
  if (!BOOTED) { fallback(new Error('WebGL context lost during boot')); return; }
  clearTimeout(GL.timer);
  GL.timer = setTimeout(() => fallback(new Error('WebGL context was not restored')), 4000);
}
function onContextRestored() {
  clearTimeout(GL.timer);
  GL.lost = false;
  if (FALLEN) return;
  console.warn('[vajradhan] WebGL context restored — rebuilding');
  try { rebuildAfterRestore(); }
  catch (err) { fallback(err); }
}
/* The renderer has a fresh context and has forgotten every GPU resource. The
   JS side still holds the images, canvases and render-target descriptions, so
   flag every texture and material dirty, drop the targets and re-measure;
   the next frame re-uploads the lot. */
function rebuildAfterRestore() {
  const dirty = m => {
    if (!m) return;
    (Array.isArray(m) ? m : [m]).forEach(mm => {
      Object.keys(mm).forEach(k => { const v = mm[k]; if (v && v.isTexture) v.needsUpdate = true; });
      if (mm.uniforms) Object.keys(mm.uniforms).forEach(k => {
        const v = mm.uniforms[k].value; if (v && v.isTexture && !v.isRenderTargetTexture) v.needsUpdate = true;
      });
      mm.needsUpdate = true;
    });
  };
  scene.traverse(o => dirty(o.material));
  ['up', 'bright', 'blur', 'comp'].forEach(k => dirty(POST[k]));
  if (POST.scene) { POST.scene.dispose(); POST.levels.forEach(L => { L.a.dispose(); L.b.dispose(); }); }
  resize();
  running = true; tPrev = performance.now(); queue();
}

function tx(img, o) {
  o = o || {};
  const t = img instanceof HTMLCanvasElement ? new THREE.CanvasTexture(img) : new THREE.Texture(img);
  t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping;
  t.anisotropy = Math.min(o.aniso || 8, maxAniso);
  t.needsUpdate = true;
  return t;
}
function loadImage(url) {
  return new Promise((res, rej) => {
    const img = new Image();
    img.decoding = 'async';
    img.onload = () => res(img);
    img.onerror = () => rej(new Error('could not load ' + url));
    img.src = url;
  });
}

/* ========================================================== 2 · the frame
   The plate's own geometry, in source pixels. Only the plate covers the
   frame; the four elements in front of it are placed on it by hand, so this
   is the one aspect the cover mapping needs.                              */
const IMG_W = 1920, IMG_H = 1072, IA = IMG_W / IMG_H;
/* The layers are encoded at two widths. There is no srcset to lean on inside
   a WebGL scene, so the choice the browser would have made is made here. */
const SMALL = (innerWidth * Math.min(devicePixelRatio || 1, 2)) < 1400;
/* The two pages sit at different depths -- / and /packages/ -- so a path
   written relative to the document would resolve differently on each, and
   the scene's planes would 404 on the deeper one. Everything the scene loads
   is resolved against this script instead, which always sits at
   <root>/assets/site.js. That holds at any depth and under a project
   subpath on GitHub Pages, where a root-relative path would not. */
const SITE = (function () {
  var s = document.currentScript || [].slice.call(document.scripts).filter(
    function (x) { return /(^|\/)assets\/site\.js(\?|$)/.test(x.src); }).pop();
  return s ? new URL('../', s.src).href : new URL('./', location.href).href;
})();
const layerURL = name => SITE + 'assets/img/hero-' + name + (SMALL ? '-960' : '-1920') + '.webp';

/* One overscan for every plane — if they differed they would not register
   at the opening frame. Kept small so the hero holds the mock-up's framing;
   the walk only ever moves forward into the planes, which gains margin, and
   the pointer drift is sized to what is left at the sides. */
const OVER = 1.14;
/* Back to front; `order` is the draw order, since every plane is blended.
   The keys are the ones the scene has always used: 'moon' is the slot between
   the sky and the city, which this plate fills with the horizon haze band. */
/* Back to front. `d` is the depth, and the depth is the parallax: the plate
   at 95 barely moves, the rock at 8 moves most. `at` is where the element is
   pinned on the frame and `w`/`h` how much of the frame it takes -- the plate
   is the only one that covers. The galaxy is added rather than composited:
   it is a second field of cloud, not an object, so screening it over the
   plate reads as one deeper sky, where cutting it out only halved the disc.
   The other three carry their own alpha.

   The arrangement is one vertical axis down the middle of the frame: the eye
   above, the being beneath it, the orbital ring centred on the being, and the
   man on his rock at the foot of the same line, looking up it. The ring hangs
   twice -- once behind the being and once in front at a third of the light --
   so its near arc crosses the body and the orbit closes instead of passing
   flat behind. The plate is held to 78%, so the vortex stays the room the
   scene happens in rather than the subject of it. */
/* `port` is the same frame read on a phone, where the copy fills the screen
   and the elements have to stand out of its way: smaller, pushed to the
   edges, and dimmed so they stay scenery. `short` is the laptop-and-tablet
   case: still landscape, but the chapter strip climbs so far up a short frame
   that the elements have to lift and shrink to clear it. */
const PLANES = [
  { key: 'plate',  url: layerURL('plate'),  d: 95, order: 0,  haze: 0,   edge: 1, bright: .70 },
  { key: 'galaxy', url: layerURL('galaxy'), d: 62, order: 10, haze: .10, at: [.50, .46], w: .88, add: 1, bright: .46, flip: 1,
    short: { at: [.50, .44], w: .80 },
    port:  { at: [.50, .34], w: 1.50, dim: .6 } },
  { key: 'iris',   url: layerURL('iris'),   d: 40, order: 20, haze: .06, at: [.50, .113], w: .21,
    short: { at: [.50, .132], w: .17 },
    port:  { at: [.50, .09], w: .44, dim: .8 } },
  { key: 'figure', url: layerURL('figure'), d: 22, order: 40, haze: .02, at: [.50, .548], h: .64, near: [1.4, 5.0],
    short: { at: [.50, .466], h: .54 },
    port:  { at: [.50, .34], h: .38, dim: .38 } },
  /* the ring again, nearer than the being and at a quarter of the light:
     this is the arc of the orbit that passes in front of the body */
  { key: 'ring',   url: layerURL('galaxy'), d: 16, order: 50, haze: 0,   at: [.50, .46], w: .88, add: 1, bright: .22,
    near: [1.0, 4.2],
    short: { at: [.50, .44], w: .80 },
    port:  { at: [.50, .34], w: 1.50, dim: 0 } },
  { key: 'rock',   url: layerURL('rock'),   d: 8,  order: 60, haze: 0,   at: [.50, .899], w: .68, near: [.7, 2.9],
    short: { at: [.50, .759], w: .56 },
    port:  { at: [.50, .88], w: .50, dim: 0 } }
];
const WORLD = { planes: {}, uT: { value: 0 } };

/* ------------------------------------------------- the scene's slow life
   Everything that gives the planes a life of their own is tuned from here,
   keyed by plane, so the numbers sit together rather than being spread
   through the frame loop.

   `drift`: the scene is never quite still. Each plane wanders a few pixels
   on its own two periods, so every one traces a different slow figure and
   they never come back into step -- a single shared period would read as
   one rigid block sliding. Amplitudes are given in screen pixels at the
   opening frame and converted per plane, so the near rock genuinely travels
   further than the plate rather than only appearing to. `ph` sets each one
   off at a different point in its cycle so nothing starts together either.
       x, y   how far it wanders, in screen pixels
       px, py how long each axis takes, in seconds
       ph     phase offset, in seconds                                   */
const LIFE = {
  plate:  { drift: { x:  2, y: 1.5, px: 21.0, py: 15.5, ph:  0.0 } },
  galaxy: { drift: { x:  5, y: 3.0, px: 17.5, py: 12.5, ph:  4.3 } },
  iris:   { drift: { x:  7, y: 4.5, px: 14.5, py: 18.5, ph:  8.1 } },
  figure: { drift: { x: 10, y: 6.5, px: 12.5, py: 16.0, ph: 11.6 } },
  ring:   { drift: { x: 12, y: 8.0, px: 11.0, py: 13.5, ph:  2.9 } },
  rock:   { drift: { x: 16, y: 10.5, px: 10.0, py: 14.0, ph:  6.7 } }
};

/* where a plane has wandered to, in screen pixels, at time t */
function driftAt(key, t, out) {
  const D = LIFE[key] && LIFE[key].drift;
  if (!D || REDUCE) { out[0] = out[1] = 0; return out; }
  out[0] = Math.sin(TAU * (t + D.ph) / D.px) * D.x * SCENE;
  out[1] = Math.sin(TAU * (t + D.ph * 1.7) / D.py) * D.y * SCENE;
  return out;
}
const _dpx = [0, 0];

const PLANE_VS = 'varying vec2 vUv;\nvoid main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }';
const PLANE_FS = [
  'uniform sampler2D map; uniform float uOpacity, uHaze, uBright, uEdge; uniform vec3 uHazeCol, uBg;',
  'varying vec2 vUv;',
  'void main(){',
  '  vec4 t = texture2D(map, vUv);',
  '  vec3 c = mix(t.rgb * uBright, uHazeCol, uHaze);',
  /* the sky is the one plane whose border can come into view as the camera
     tilts up; its edges dissolve into the scene colour, which is the sky's
     own top colour, so there is no rim to find */
  '  float e = smoothstep(0.0, 0.08, vUv.x) * smoothstep(1.0, 0.92, vUv.x) * smoothstep(1.0, 0.86, vUv.y);',
  '  c = mix(c, uBg, uEdge * (1.0 - e));',
  '  gl_FragColor = vec4(c, t.a * uOpacity);',
  '}'].join('\n');

function loadPlanes() {
  return Promise.all(PLANES.map(P => loadImage(P.url).then(img => {
    const mat = new THREE.ShaderMaterial({
      uniforms: {
        map: { value: tx(img, { aniso: 8 }) }, uOpacity: { value: 1 }, uHaze: { value: P.haze },
        uBright: { value: P.bright || 1 }, uEdge: { value: P.edge || 0 },
        uHazeCol: { value: new THREE.Color(0x59524f) }, uBg: { value: new THREE.Color(0x2f2e2e) }
      },
      vertexShader: PLANE_VS, fragmentShader: PLANE_FS,
      transparent: true, depthTest: false, depthWrite: false,
      blending: P.add ? THREE.AdditiveBlending : THREE.NormalBlending
    });
    const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), mat);
    m.renderOrder = P.order; m.frustumCulled = false; m.name = P.key;
    scene.add(m);
    WORLD.planes[P.key] = { mesh: m, def: P, aspect: img.width / img.height };
  })));
}

/* Where the opening camera's frame lands at depth d, and how big the photo
   has to be there to cover it. Every plane, the moon's halo and the stars go
   through this, which is what keeps them registered. */
/* a phone held upright: the frame is taller than it is wide */
function portrait() { return vpW() / vpH() < .95; }
/* a laptop or a tablet on its side: wide, but not tall enough for the copy,
   the chapter strip and the scene at full size */
function shortFrame() { return !portrait() && vpH() < 820; }
function focus() {
  const a = vpW() / vpH();
  /* a portrait frame can only hold one of moon and peak: keep the peak */
  return [a < .9 ? .57 : .5, a > 2.1 ? .46 : .5];
}
function cover(d) {
  const vh = 2 * d * Math.tan(CAM[0].fov * Math.PI / 360), vw = vh * (vpW() / vpH());
  const H = Math.max(vh, vw / IA) * OVER;
  return [H * IA, H];
}
function uvToWorld(u, v, d, out) {
  const s = cover(d), f = focus();
  out.set((u - f[0]) * s[0], (f[1] - v) * s[1], -d);
  return s;
}
const _v = new THREE.Vector3();
function layoutPlanes() {
  const port = portrait(), shrt = shortFrame();
  Object.keys(WORLD.planes).forEach(k => {
    const P = WORLD.planes[k];
    const v = port ? P.def.port : (shrt ? P.def.short : null);
    const D = v ? Object.assign({ w: 0, h: 0 }, P.def, v) : P.def;
    P.dim = D.dim || 1;
    P.mesh.material.uniforms.uBright.value = D.bright || 1;
    const s = uvToWorld(D.at ? D.at[0] : .5, D.at ? D.at[1] : .5, D.d, _v);
    P.mesh.position.copy(_v);
    /* the resting position, which the drift is measured from, and what one
       screen pixel is worth in world units at this depth */
    P.base = (P.base || new THREE.Vector3()).copy(_v);
    P.perPx = s[0] / (vpW() * OVER);
    /* the plate covers; an element is sized by its width, or by its height
       where it stands taller than it is wide and the frame's height is what
       constrains it -- the figure of light is the one of those */
    const f = D.flip ? -1 : 1;
    if (D.w)      P.mesh.scale.set(s[0] * D.w * f, s[0] * D.w / P.aspect, 1);
    else if (D.h) P.mesh.scale.set(s[1] * D.h * P.aspect * f, s[1] * D.h, 1);
    else          P.mesh.scale.set(s[0] * f, s[1], 1);
    /* the crop now starts at the crown, so the head is just inside its top */
    if (k === 'figure' && D.h) { HEAD.u = D.at[0]; HEAD.v = D.at[1] - .455 * D.h; HEAD.h = D.h; }
  });
  if (WORLD.halo && HEAD.h) {
    const s = uvToWorld(HEAD.u, HEAD.v, 28, _v);
    WORLD.halo.position.copy(_v);
    WORLD.halo.base = (WORLD.halo.base || new THREE.Vector3()).copy(_v);
    WORLD.halo.perPx = s[0] / (vpW() * OVER);
    WORLD.halo.scale.setScalar(s[0] * HEAD.h * .40);
    WORLD.halo.visible = !portrait();
  }
  layoutStars();
}

/* ========================================================== 3 · atmosphere */
/* The being's head is a faint tracery, and it hangs in front of the vortex's
   own black eye, where there is nothing to read it against. A weak corona
   behind it -- the eye's light reaching past the head -- gives the head
   something to sit on without laying a mark on the figure itself. It is
   placed from the figure's own anchor, so it follows every reading of the
   frame. */
const HEAD = { u: .5, v: .3, h: 0 };
function buildHeadGlow() {
  const halo = new THREE.Mesh(new THREE.PlaneGeometry(1, 1),
    new THREE.MeshBasicMaterial({ map: tx(texGlow('rgba(226,236,250,.88)', 'rgba(150,178,220,.20)')),
      transparent: true, blending: THREE.AdditiveBlending, depthTest: false, depthWrite: false, opacity: .38 }));
  halo.renderOrder = 30; halo.frustumCulled = false;   /* behind the figure at 40 */
  scene.add(halo); WORLD.halo = halo;
}

/* Stars between the plate and the galaxy, so they drift a little against the
   painted ones and slide behind the elements when the camera moves. Each is
   placed in photo coordinates and projected through the same cover mapping as
   the planes. They keep to the upper field, where the plate is darkest. */
const STAR = { list: [] };
function buildStars() {
  const N = LOW ? 110 : 220, rnd = mulberry32(881);
  const pos = new Float32Array(N * 3), seed = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    STAR.list.push([rnd(), rnd() * .58, 58 + rnd() * 28]);
    seed[i] = rnd();
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('aSeed', new THREE.BufferAttribute(seed, 1));
  const pts = new THREE.Points(g, new THREE.ShaderMaterial({
    uniforms: { uT: WORLD.uT, uTex: { value: tx(texWisp()) }, uPx: { value: 1 } },
    transparent: true, blending: THREE.AdditiveBlending, depthTest: false, depthWrite: false,
    vertexShader:
      'attribute float aSeed; uniform float uT; uniform float uPx; varying float vA;\n' +
      'void main(){ vec4 mv = modelViewMatrix * vec4(position,1.0);\n' +
      ' vA = (0.30 + 0.70*aSeed) * (0.55 + 0.45*sin(uT*(0.5+aSeed*1.9) + aSeed*40.0));\n' +
      ' gl_PointSize = uPx * (3.0 + aSeed*aSeed*7.0);\n' +
      ' gl_Position = projectionMatrix * mv; }',
    fragmentShader:
      'uniform sampler2D uTex; varying float vA;\n' +
      'void main(){ vec4 t = texture2D(uTex, gl_PointCoord); gl_FragColor = vec4(t.rgb*vec3(.9,.95,1.0), t.a*vA); }'
  }));
  pts.renderOrder = 8; pts.frustumCulled = false;
  scene.add(pts); STAR.mesh = pts;
  layoutStars();
}
function layoutStars() {
  if (!STAR.mesh) return;
  const P = STAR.mesh.geometry.attributes.position;
  STAR.list.forEach((s, i) => { uvToWorld(s[0], s[1], s[2], _v); P.setXYZ(i, _v.x, _v.y, _v.z); });
  P.needsUpdate = true;
  STAR.mesh.material.uniforms.uPx.value = renderer.getPixelRatio();
}

/* Valley mist: big soft slabs hung between the ranges, drawn in the gaps of
   the plane order so each one sits behind the ridge nearer than it. */
function buildHaze() {
  const map = tx(texGlow('rgba(176,196,222,.55)', 'rgba(118,140,172,.18)'));
  const defs = [   /* x, y, z, width, opacity, order */
    [-7, -3.2, -36, 38, .09, 35], [8, -2.8, -30, 30, .07, 45],
    [-4, -1.9, -17, 18, .08, 55], [5, -1.6, -12, 14, .06, 55], [-2, -1.3, -9.5, 10, .05, 55]
  ];
  const rnd = mulberry32(66);
  WORLD.haze = defs.map(D => {
    const h = new THREE.Mesh(new THREE.PlaneGeometry(D[3], D[3] * .42),
      new THREE.MeshBasicMaterial({ map: map, transparent: true, blending: THREE.AdditiveBlending,
        depthTest: false, depthWrite: false, opacity: D[4] }));
    h.position.set(D[0], D[1], D[2]); h.renderOrder = D[5]; h.frustumCulled = false;
    h.userData = { x0: D[0], sp: .05 + rnd() * .08, ph: rnd() * TAU, o: D[4] };
    scene.add(h);
    return h;
  });
}

/* Snow — the range's own weather, in place of Kage's falling maple. A box of
   motes over the whole walk, animated entirely in the vertex shader. */
function buildSnow() {
  if (REDUCE) return;
  const N = LOW ? 160 : 360, rnd = mulberry32(404);
  const pos = new Float32Array(N * 3), seed = new Float32Array(N);
  for (let i = 0; i < N; i++) {
    pos[i * 3] = (rnd() - .5) * 16; pos[i * 3 + 1] = rnd() * 9 - 3.5; pos[i * 3 + 2] = -1 - rnd() * 21;
    seed[i] = rnd();
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('aSeed', new THREE.BufferAttribute(seed, 1));
  const snow = new THREE.Points(g, new THREE.ShaderMaterial({
    uniforms: { uT: WORLD.uT, uTex: { value: tx(texWisp()) }, uSize: { value: vpH() } },
    transparent: true, blending: THREE.AdditiveBlending, depthTest: false, depthWrite: false,
    vertexShader:
      'attribute float aSeed; uniform float uT; uniform float uSize; varying float vA;\n' +
      'void main(){ vec3 p = position;\n' +
      ' p.y = mod(p.y + 3.5 - uT*(0.10 + aSeed*0.22), 9.0) - 3.5;\n' +
      ' p.x += sin(uT*(0.23 + aSeed*0.3) + aSeed*31.0)*0.7 + uT*0.05;\n' +
      ' p.x = mod(p.x + 8.0, 16.0) - 8.0;\n' +
      ' p.z += cos(uT*0.19 + aSeed*17.0)*0.4;\n' +
      ' vec4 mv = modelViewMatrix * vec4(p,1.0);\n' +
      ' float dz = -mv.z;\n' +
      ' vA = (0.25 + aSeed*0.55) * smoothstep(0.3, 1.2, dz) * (1.0 - smoothstep(12.0, 20.0, dz))\n' +
      '      * smoothstep(-3.5, -2.5, p.y) * (1.0 - smoothstep(4.5, 5.5, p.y));\n' +
      ' gl_PointSize = uSize * (0.006 + aSeed*0.012) / max(dz, 0.3);\n' +
      ' gl_Position = projectionMatrix * mv; }',
    fragmentShader:
      'uniform sampler2D uTex; varying float vA;\n' +
      'void main(){ vec4 t = texture2D(uTex, gl_PointCoord); gl_FragColor = vec4(t.rgb, t.a*vA*0.8); }'
  }));
  snow.renderOrder = 70; snow.frustumCulled = false;
  scene.add(snow); WORLD.snow = snow;
}

/* ============================================ 4 · the cursor wisps (Kage)
   A drift of cold motes following the pointer. They hang as a child of the
   camera so the trail stays under the hand while the rig moves, and they are
   emitted by distance travelled, not by time. */
const WISP_D = 3.4;
const WISP = { list: [], i: 0, acc: 0, ex: 0, ey: 0, lx: 0, ly: 0, idle: 0, seen: false };
function buildWisps() {
  if (COARSE || REDUCE) return;
  const N = LOW ? 90 : 190;
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(N * 3), 3));
  g.setAttribute('aA', new THREE.BufferAttribute(new Float32Array(N), 1));
  g.setAttribute('aS', new THREE.BufferAttribute(new Float32Array(N), 1));
  const pts = new THREE.Points(g, new THREE.ShaderMaterial({
    uniforms: { uTex: { value: tx(texWisp()) }, uPx: { value: vpH() } },
    transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false,
    vertexShader:
      'attribute float aA; attribute float aS; uniform float uPx; varying float vA;\n' +
      'void main(){ vA = aA; vec4 mv = modelViewMatrix * vec4(position,1.0);\n' +
      ' gl_PointSize = uPx * aS / max(-mv.z, 0.4); gl_Position = projectionMatrix * mv; }',
    fragmentShader:
      'uniform sampler2D uTex; varying float vA;\n' +
      'void main(){ if (vA <= 0.0) discard; vec4 t = texture2D(uTex, gl_PointCoord); gl_FragColor = vec4(t.rgb, t.a*vA); }'
  }));
  pts.frustumCulled = false; pts.renderOrder = 90;
  camera.add(pts);
  WISP.mesh = pts;
  for (let i = 0; i < N; i++) WISP.list.push({ life: 0, max: 1, vx: 0, vy: 0, sz: 0, ph: 0 });
}
function wispPoint(nx, ny) {
  const hh = Math.tan(camera.fov * Math.PI / 360) * WISP_D;
  return [nx * hh * camera.aspect, ny * hh];
}
function updateWisps(dt) {
  if (!WISP.mesh) return;
  const g = WISP.mesh.geometry;
  const P = g.attributes.position.array, A = g.attributes.aA.array, S = g.attributes.aS.array;
  const L = WISP.list, N = L.length;
  const pt = wispPoint(RIG.tmx, RIG.tmy);
  if (!WISP.seen) { WISP.ex = WISP.lx = pt[0]; WISP.ey = WISP.ly = pt[1]; WISP.seen = true; }
  WISP.ex = damp(WISP.ex, pt[0], 16, dt);
  WISP.ey = damp(WISP.ey, pt[1], 16, dt);
  const dx = WISP.ex - WISP.lx, dy = WISP.ey - WISP.ly;
  const moved = Math.hypot(dx, dy);
  const ang = moved > 1e-5 ? Math.atan2(dy, dx) : 0;
  const spawn = (x, y, a, weak) => {
    const i = WISP.i; WISP.i = (i + 1) % N;
    const w = L[i], k = i * 3;
    P[k] = x + (Math.random() + Math.random() - 1) * .30;
    P[k + 1] = y + (Math.random() + Math.random() - 1) * .30;
    P[k + 2] = -WISP_D + (Math.random() - .5) * .9;
    w.life = 0; w.max = (weak ? 2.1 : 1.45) + Math.random() * 1.3;
    w.vx = -Math.cos(a) * .09 + (Math.random() - .5) * .38;
    w.vy = -Math.sin(a) * .09 + (Math.random() - .5) * .32 + .02;
    w.sz = (weak ? .018 : .024) + Math.random() * .026;
    w.ph = Math.random() * TAU;
  };
  WISP.acc += moved;
  const STEP = .030;
  let guard = 0;
  while (WISP.acc >= STEP && guard++ < 14) {
    WISP.acc -= STEP;
    const t = moved > 1e-6 ? Math.min(1, guard * STEP / moved) : 0;
    spawn(WISP.lx + dx * t, WISP.ly + dy * t, ang, false);
  }
  WISP.idle += dt;
  if (WISP.idle > .42) { WISP.idle = 0; spawn(WISP.ex, WISP.ey, Math.random() * TAU, true); }
  WISP.lx = WISP.ex; WISP.ly = WISP.ey;
  for (let i = 0; i < N; i++) {
    const w = L[i], k = i * 3;
    if (w.life >= w.max) { A[i] = 0; continue; }
    w.life += dt;
    const u = w.life / w.max;
    P[k]     += (w.vx + Math.sin(clock * 1.3 + w.ph) * .17) * dt;
    P[k + 1] += (w.vy + Math.cos(clock * 1.1 + w.ph * 1.7) * .14) * dt;
    w.vx *= 1 - .5 * dt; w.vy = w.vy * (1 - .5 * dt) + .022 * dt;
    A[i] = smooth(0, .12, u) * (1 - smooth(.22, 1, u)) * .9;
    S[i] = w.sz * (1 + u * .55);
  }
  g.attributes.position.needsUpdate = true;
  g.attributes.aA.needsUpdate = true;
  g.attributes.aS.needsUpdate = true;
}

/* ================================================ 5 · the giant wordmark
   Kage's rising letters, moved to the close. VAJRADHAN hangs just in front of
   the mid range, low in the closing frame, and climbs into place letter by
   letter as the walk arrives at Contact. (Hung behind the mid ridge it was
   occluded by the left-hand peak and read as "RADHAN".) */
const WORD_Z = -16;
const WORD = { glyphs: [], group: null, ink: null, reveal: 0 };
function buildWordmark() {
  const SZ = 280, TRACK = .12, PAD = 26, FONT = '400 ' + SZ + 'px Michroma, sans-serif';
  const m = cvs(4, 4).getContext('2d');
  m.font = FONT; m.textBaseline = 'alphabetic';
  const word = 'VAJRADHAN', gl = [];
  let pen = 0, ascMax = 0, descMax = 0, xMin = 1e9, xMax = -1e9;
  for (const ch of word) {
    const t = m.measureText(ch);
    const g = { ch: ch, adv: t.width, asc: t.actualBoundingBoxAscent, desc: t.actualBoundingBoxDescent,
                l: t.actualBoundingBoxLeft, r: t.actualBoundingBoxRight, pen: pen };
    gl.push(g);
    ascMax = Math.max(ascMax, g.asc); descMax = Math.max(descMax, g.desc);
    xMin = Math.min(xMin, pen - g.l); xMax = Math.max(xMax, pen + g.r);
    pen += t.width + TRACK * SZ;
  }
  const group = new THREE.Group();
  gl.forEach(g => {
    const cw = Math.ceil(g.l + g.r) + PAD * 2, chh = Math.ceil(g.asc + g.desc) + PAD * 2;
    const c = cvs(cw, chh), x = c.getContext('2d');
    x.font = FONT; x.textBaseline = 'alphabetic';
    const gy0 = PAD + g.asc - ascMax, gy1 = PAD + g.asc + descMax * .4;
    const grad = x.createLinearGradient(0, gy0, 0, gy1);
    grad.addColorStop(0, 'rgb(236,242,246)');
    grad.addColorStop(.55, 'rgb(196,210,222)');
    grad.addColorStop(1, 'rgb(128,146,166)');
    x.fillStyle = grad;
    x.fillText(g.ch, PAD + g.l, PAD + g.asc);
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(cw, chh),
      new THREE.MeshBasicMaterial({ map: tx(c, { aniso: 16 }), transparent: true,
        depthTest: false, depthWrite: false, opacity: 0 }));
    mesh.position.set(g.pen + (g.r - g.l) / 2, (g.asc - g.desc) / 2, 0);
    mesh.renderOrder = 52; mesh.frustumCulled = false; mesh.visible = false;
    mesh.userData.baseY = mesh.position.y;
    group.add(mesh);
    WORD.glyphs.push(mesh);
  });
  scene.add(group);
  WORD.group = group;
  WORD.ink = { cx: (xMin + xMax) / 2, w: xMax - xMin, asc: ascMax };
  layoutWord();
}
let tmpCam = null;
function layoutWord() {
  if (!WORD.group || !tmpCam) return;
  const c = CAM[5];
  tmpCam.fov = c.fov; tmpCam.aspect = vpW() / vpH();
  tmpCam.position.set(c.p[0], c.p[1], c.p[2]);
  tmpCam.lookAt(c.t[0], c.t[1], c.t[2]);
  tmpCam.updateProjectionMatrix(); tmpCam.updateMatrixWorld(true);
  const hit = (nx, ny) => {
    const v = new THREE.Vector3(nx, ny, .5).unproject(tmpCam).sub(tmpCam.position).normalize();
    return tmpCam.position.clone().addScaledVector(v, (WORD_Z - tmpCam.position.z) / v.z);
  };
  const L = hit(-1, 0), R = hit(1, 0);
  const narrow = vpW() / vpH() < 1.05;
  const s = (R.x - L.x) * (narrow ? .9 : .8) / WORD.ink.w;
  /* low in the frame, under the call to action rather than behind it */
  const base = hit(0, narrow ? -.62 : -.86);
  WORD.group.scale.setScalar(s);
  WORD.group.position.set(-WORD.ink.cx * s + (L.x + R.x) / 2, base.y, WORD_Z);
  /* Tip the word back by the closing camera's own tilt so it is square to
     that frame. Pitch only: the group's origin is the word's left end, so
     aiming it at the camera with lookAt would also yaw it by the offset. */
  WORD.group.rotation.set(Math.atan2(c.t[1] - c.p[1], c.p[2] - c.t[2]), 0, 0);
}

/* ================================================== 6 · post-processing
   Bloom (a threshold, a four-level blur pyramid, an additive recombine), then
   one composite: faint chromatic fringe at the edges, the bloom, a cool lift
   in the shadows, vignette, grain, and the opening fade.                  */
const POST = { levels: [] };
const QUAD_VS = 'varying vec2 vUv;\nvoid main(){ vUv = uv; gl_Position = vec4( position.xy, 0.0, 1.0 ); }';
function initPost() {
  if (!WANT_POST) return;
  POST.cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  POST.quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), null);
  POST.quad.frustumCulled = false;
  POST.qScene = new THREE.Scene(); POST.qScene.add(POST.quad);
  const w = renderer.domElement.width, h = renderer.domElement.height;
  const O = { minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, type: THREE.HalfFloatType,
              depthBuffer: false, stencilBuffer: false };
  POST.scene = new THREE.WebGLRenderTarget(w, h, Object.assign({}, O, { samples: PERF.msaa }));
  let lw = Math.max(2, w >> 1), lh = Math.max(2, h >> 1);
  for (let i = 0; i < 4; i++) {
    POST.levels.push({ a: new THREE.WebGLRenderTarget(lw, lh, O), b: new THREE.WebGLRenderTarget(lw, lh, O), w: lw, h: lh });
    lw = Math.max(2, lw >> 1); lh = Math.max(2, lh >> 1);
  }
  POST.up = new THREE.ShaderMaterial({
    uniforms: { tS: { value: null }, uAmt: { value: 1 } }, vertexShader: QUAD_VS,
    fragmentShader: 'uniform sampler2D tS; uniform float uAmt; varying vec2 vUv;\nvoid main(){ gl_FragColor = vec4(texture2D(tS,vUv).rgb*uAmt, 1.0); }',
    blending: THREE.AdditiveBlending, transparent: true, depthTest: false, depthWrite: false
  });
  POST.bright = new THREE.ShaderMaterial({
    uniforms: { tS: { value: null }, uThr: { value: .70 }, uKnee: { value: .28 } },
    vertexShader: QUAD_VS,
    fragmentShader:
      'uniform sampler2D tS; uniform float uThr; uniform float uKnee; varying vec2 vUv;\n' +
      'void main(){ vec3 c = texture2D(tS, vUv).rgb;\n' +
      ' float l = dot(c, vec3(0.2126,0.7152,0.0722));\n' +
      ' gl_FragColor = vec4(c * smoothstep(uThr, uThr+uKnee, l), 1.0); }'
  });
  POST.blur = new THREE.ShaderMaterial({
    uniforms: { tS: { value: null }, uDir: { value: new THREE.Vector2(1, 0) } },
    vertexShader: QUAD_VS,
    fragmentShader:
      'uniform sampler2D tS; uniform vec2 uDir; varying vec2 vUv;\n' +
      'void main(){ vec3 c = texture2D(tS, vUv).rgb * 0.2270270270;\n' +
      ' c += texture2D(tS, vUv + uDir*1.3846153846).rgb * 0.3162162162;\n' +
      ' c += texture2D(tS, vUv - uDir*1.3846153846).rgb * 0.3162162162;\n' +
      ' c += texture2D(tS, vUv + uDir*3.2307692308).rgb * 0.0702702703;\n' +
      ' c += texture2D(tS, vUv - uDir*3.2307692308).rgb * 0.0702702703;\n' +
      ' gl_FragColor = vec4(c, 1.0); }'
  });
  POST.comp = new THREE.ShaderMaterial({
    uniforms: {
      tS: { value: null }, tB: { value: null }, uRes: { value: new THREE.Vector2(w, h) },
      uT: { value: 0 }, uBloom: { value: .42 }, uCA: { value: 1 }, uGrain: { value: .026 },
      uVig: { value: .85 }, uFade: { value: 1 }, uLift: { value: 0 }
    },
    vertexShader: QUAD_VS,
    fragmentShader:
      'uniform sampler2D tS; uniform sampler2D tB; uniform vec2 uRes;\n' +
      'uniform float uT, uBloom, uCA, uGrain, uVig, uFade, uLift;\n' +
      'varying vec2 vUv;\n' +
      'void main(){\n' +
      ' vec2 d = vUv - 0.5; float r2 = dot(d,d);\n' +
      ' float ca = uCA * (0.25 + r2*2.4) * 0.0012;\n' +
      ' vec3 c;\n' +
      ' c.r = texture2D(tS, vUv + d*ca).r;\n' +
      ' c.g = texture2D(tS, vUv).g;\n' +
      ' c.b = texture2D(tS, vUv - d*ca).b;\n' +
      ' c += texture2D(tB, vUv).rgb * (uBloom + uLift*0.25);\n' +
      ' float l = dot(c, vec3(0.2126,0.7152,0.0722));\n' +
      ' c = mix(c, c*vec3(0.92,0.98,1.08), smoothstep(0.5,0.0,l)*0.5);\n' +   /* cold shadows */
      ' float v = smoothstep(1.25, 0.28, length(d*vec2(1.0,0.94))*1.42);\n' +
      ' c *= mix(1.0, v, uVig);\n' +
      ' float g = fract(sin(dot(vUv*uRes + uT*137.0, vec2(12.9898,78.233)))*43758.5453);\n' +
      ' c += (g-0.5)*uGrain;\n' +
      ' c *= uFade;\n' +
      ' gl_FragColor = vec4(clamp(c, 0.0, 1.0), 1.0);\n' +
      '}'
  });
}
function pass(mat, target, additive) {
  POST.quad.material = mat;
  renderer.setRenderTarget(target || null);
  if (!additive) renderer.clear(true, false, false);
  renderer.render(POST.qScene, POST.cam);
}
function renderPost() {
  const L = POST.levels;
  POST.bright.uniforms.tS.value = POST.scene.texture;
  pass(POST.bright, L[0].a);
  for (let i = 0; i < L.length; i++) {
    if (i > 0) { POST.up.blending = THREE.NoBlending; POST.up.uniforms.uAmt.value = 1; POST.up.uniforms.tS.value = L[i - 1].a; pass(POST.up, L[i].a); }
    POST.blur.uniforms.tS.value = L[i].a; POST.blur.uniforms.uDir.value.set(1 / L[i].w, 0); pass(POST.blur, L[i].b);
    POST.blur.uniforms.tS.value = L[i].b; POST.blur.uniforms.uDir.value.set(0, 1 / L[i].h); pass(POST.blur, L[i].a);
  }
  POST.up.blending = THREE.AdditiveBlending; POST.up.uniforms.uAmt.value = .52;
  for (let i = L.length - 1; i > 0; i--) { POST.up.uniforms.tS.value = L[i].a; pass(POST.up, L[i - 1].a, true); }
  POST.comp.uniforms.tS.value = POST.scene.texture;
  POST.comp.uniforms.tB.value = L[0].a;
  pass(POST.comp, null);
}
function setSamples(n) {
  PERF.msaa = n;
  if (POST.scene && POST.scene.samples !== n) { POST.scene.samples = n; POST.scene.dispose(); }
}

/* ================================================= 7 · the camera rig
   One waypoint per [data-cam] section. The opening one sits at the origin
   looking straight down −z, which is the pose the planes are laid out for;
   the rest walk into the range. The near ridge is passed on the way down. */
const CAM = [
  { p: [  0.00, 0.00,  0.0 ], t: [  0.00, 0.00, -10 ], fov: 36 },  /* 0 hero        */
  { p: [ -0.35, 0.04, -1.5 ], t: [  0.50, 0.12, -11 ], fov: 35 },  /* 1 about       */
  { p: [  0.32,-0.04, -3.0 ], t: [ -0.30, 0.30, -11 ], fov: 34 },  /* 2 capabilities*/
  { p: [ -0.30, 0.28, -6.2 ], t: [  0.25, 0.80, -12.5 ], fov: 33 },/* 3 process     */
  { p: [  0.00, 0.45, -8.0 ], t: [  0.00, 1.05, -16 ], fov: 34 },  /* 4 contact     */
  { p: [  0.00, 0.40, -9.0 ], t: [  0.00, 0.70, -16 ], fov: 36 }   /* 5 footer      */
];
const RIG = { prog: 0, smooth: 0, mx: 0, my: 0, tmx: 0, tmy: 0, intro: 0, focus: -1, focusAmt: 0, N: 1 };
let curveP, curveT;
function buildRig() {
  /* A page walks as many waypoints as it has [data-cam] sections. The home
     page has six of each, so this is the whole list; a page with fewer
     stops short rather than indexing past the end of CAM. */
  RIG.N = Math.min(CAM.length, SECS.length) - 1;
  const W = CAM.slice(0, RIG.N + 1);
  curveP = new THREE.CatmullRomCurve3(W.map(c => new THREE.Vector3(c.p[0], c.p[1], c.p[2])), false, 'catmullrom', .42);
  curveT = new THREE.CatmullRomCurve3(W.map(c => new THREE.Vector3(c.t[0], c.t[1], c.t[2])), false, 'catmullrom', .42);
  tmpCam = new THREE.PerspectiveCamera(CAM[0].fov, vpW() / vpH(), .1, 400);
}
const _p = new THREE.Vector3(), _t = new THREE.Vector3();
function applyCamera() {
  const N = RIG.N;
  const u = clamp(RIG.smooth / N, 0, 1);
  curveP.getPoint(u, _p); curveT.getPoint(u, _t);
  const i = clamp(Math.floor(RIG.smooth), 0, N - 1), f = clamp(RIG.smooth - i, 0, 1);
  let fov = lerp(CAM[i].fov, CAM[i + 1].fov, f);
  /* the opening move: a longer lens settling in from a touch further back */
  const io = 1 - RIG.intro;
  _p.z += io * 1.6; _p.y += io * .12; fov += io * 5;
  /* a focused discipline leans the lens in, barely */
  fov -= RIG.focusAmt * .8;
  /* hand-held drift toward the pointer; the near ridge moves most, the sky
     not at all — which is the whole read of depth */
  const par = REDUCE ? 0 : SCENE;
  _p.x += RIG.mx * 0.24 * par; _p.y += RIG.my * 0.13 * par;
  _t.x -= RIG.mx * 0.10 * par; _t.y -= RIG.my * 0.05 * par;
  camera.position.copy(_p);
  camera.lookAt(_t);
  if (Math.abs(camera.fov - fov) > 1e-4) { camera.fov = fov; camera.updateProjectionMatrix(); }
}

/* ============================================== 8 · scroll ↔ sections */
const SECS = $$('[data-cam]');
/* The section the page opens on: the one the preloader hands over to, and the
   one whose reveals are staggered by hand rather than by the observer. */
const OPENER = $('#hero') || SECS[0] || null;
let anchors = [], maxScroll = 1, activeSec = 0;
function measure() {
  maxScroll = Math.max(1, document.documentElement.scrollHeight - vpH());
  anchors = SECS.map((el, i) => {
    if (i === 0) return 0;
    if (i === SECS.length - 1) return maxScroll;
    return clamp(el.offsetTop + el.offsetHeight * .5 - vpH() * .5, 0, maxScroll);
  });
  for (let i = 1; i < anchors.length; i++) anchors[i] = Math.max(anchors[i], anchors[i - 1] + 1);
}
function progressFor(y) {
  if (!anchors.length || y <= anchors[0]) return 0;
  for (let i = 0; i < anchors.length - 1; i++)
    if (y <= anchors[i + 1]) return i + (y - anchors[i]) / (anchors[i + 1] - anchors[i]);
  return anchors.length - 1;
}

/* =================================================== 9 · page wiring */
const nav = $('#nav'), preEl = $('#pre'), preFill = $('#pre-fill'), prePct = $('#pre-pct'), preStep = $('#pre-step');

function wireReveals() {
  splitHeadingWords();
  const groups = new Map();
  const items = $$('[data-rv]');
  items.forEach(el => {
    const key = el.parentElement;
    const arr = groups.get(key) || []; arr.push(el); groups.set(key, arr);
  });
  groups.forEach(arr => arr.forEach((el, i) => el.dataset.rvd = i * 85));
  if (!('IntersectionObserver' in window)) { items.forEach(el => el.classList.add('rv-in')); return; }
  const io = new IntersectionObserver(es => {
    es.forEach(e => {
      if (!e.isIntersecting) return;
      io.unobserve(e.target);
      const d = parseFloat(e.target.dataset.rvd || 0);
      setTimeout(() => e.target.classList.add('rv-in'), REDUCE ? 0 : d);
    });
  }, { rootMargin: '0px 0px -10% 0px', threshold: .04 });
  const watched = items.filter(el => !OPENER || !OPENER.contains(el));
  watched.forEach(el => io.observe(el));
  /* The observer ignores the bottom tenth of the viewport, so whatever sits
     at the very end of the page can never clear it. At the foot of the
     document, show what is left rather than leave the colophon hidden. */
  const atEnd = () => {
    if (scrollY + vpH() < document.documentElement.scrollHeight - 2) return;
    watched.forEach(el => {
      if (el.classList.contains('rv-in')) return;
      io.unobserve(el);
      setTimeout(() => el.classList.add('rv-in'), REDUCE ? 0 : parseFloat(el.dataset.rvd || 0));
    });
    removeEventListener('scroll', atEnd);
  };
  addEventListener('scroll', atEnd, { passive: true });
}

/* Word-level masks so each display heading arrives at a reading pace. The
   visual words are presentational (aria-hidden); the line keeps the whole
   phrase as its aria-label, so a screen reader hears the sentence, once. */
function splitHeadingWords() {
  if (REDUCE) return;
  $$('h1.display, h2.display').forEach(heading => {
    if (heading.dataset.wordReady === 'true') return;
    const targets = [heading];
    /* the heading (a role that takes a name) carries the readable sentence;
       the word spans built below are presentational */
    heading.setAttribute('aria-label', heading.textContent.replace(/\s+/g, ' ').trim());
    heading.dataset.wordReady = 'true';
    let n = 0;
    targets.forEach(target => {
      const phrase = target.textContent.replace(/\s+/g, ' ').trim();
      if (!phrase) return;
      target.classList.add('word-reveal');
      target.textContent = '';
      phrase.split(' ').forEach((word, i) => {
        if (i) target.appendChild(document.createTextNode(' '));
        const mask = document.createElement('span');
        const inner = document.createElement('span');
        mask.className = 'word-mask'; mask.setAttribute('aria-hidden', 'true');
        inner.className = 'word'; inner.textContent = word;
        inner.style.setProperty('--word-delay', (n++ * 72) + 'ms');
        mask.appendChild(inner); target.appendChild(mask);
      });
    });
  });
}

function wireHeroExit() {
  /* The hero hands over from the top down: the standfirst first, then the
     keyword strip, the button, and the four chips in turn, so the frame has
     emptied by the time the section below it is under the nav. The headline
     stays put, as it always has. */
  const seq = [
    { el: $('.hero-sub'), at: .05, span: .42, shift: true },
    { el: $('.hero-cta'), at: .14, span: .40, shift: true },
    ...$$('.chip').map((el, i) => ({ el: el, at: .20 + i * .10, span: .38, shift: true }))
  ].filter(o => o.el);
  let on = false;
  const apply = () => {
    const t = clamp(scrollY / Math.max(1, vpH() * .6), 0, 1);
    if (t <= 0) {
      if (!on) return;
      seq.forEach(o => { o.el.style.opacity = ''; o.el.style.transform = ''; o.el.style.transition = ''; o.el.style.pointerEvents = ''; });
      on = false; return;
    }
    on = true;
    seq.forEach(o => {
      o.el.style.transition = 'none';
      const a = 1 - smooth(o.at, o.at + o.span, t);
      o.el.style.opacity = a.toFixed(3);
      if (o.shift) o.el.style.transform = 'translate3d(0,' + ((1 - a) * 15).toFixed(1) + 'px,0)';
      o.el.style.pointerEvents = a < .05 ? 'none' : '';
    });
  };
  addEventListener('scroll', apply, { passive: true });
  addEventListener('resize', apply, { passive: true });
  apply();
}

function wireNav() {
  const rail = $('#rail'), burger = $('#burger'), menu = $('#menu'), scrim = $('#scrim');
  const names = SECS.map(s => s.dataset.rail || '');
  SECS.forEach((s, i) => {
    const b = document.createElement('button');
    b.type = 'button'; b.innerHTML = '<i></i>'; b.title = names[i] || '';
    b.setAttribute('aria-label', 'Go to ' + (names[i] || 'section'));
    b.addEventListener('click', () => scrollTo({ top: anchors[i] || 0, behavior: REDUCE ? 'auto' : 'smooth' }));
    rail.appendChild(b);
  });
  const dots = $$('#rail button');
  const links = $$('.menu .mlink');
  const setMenu = open => {
    if (open) nav.classList.remove('hide');
    menu.classList.toggle('open', open);
    scrim.classList.toggle('open', open);
    burger.setAttribute('aria-expanded', String(open));
    burger.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    document.documentElement.classList.toggle('nav-open', open);
    if (open) setTimeout(() => { if (links[0]) links[0].focus({ preventScroll: true }); }, 60);
  };
  const isOpen = () => menu.classList.contains('open');
  const closeMenu = (returnFocus) => {
    if (!isOpen()) return;
    setMenu(false);
    if (returnFocus) burger.focus({ preventScroll: true });
  };
  burger.addEventListener('click', () => setMenu(!isOpen()));
  scrim.addEventListener('click', () => closeMenu(true));
  links.forEach(l => l.addEventListener('click', () => closeMenu(false)));
  addEventListener('keydown', e => {
    if (e.key === 'Escape' && isOpen()) { e.preventDefault(); closeMenu(true); return; }
    /* keep Tab inside the open sheet (and the burger that closes it) */
    if (e.key === 'Tab' && isOpen()) {
      const ring = [burger].concat($$('#menu a'));
      const i = ring.indexOf(document.activeElement);
      if (e.shiftKey && i <= 0) { e.preventDefault(); ring[ring.length - 1].focus(); }
      else if (!e.shiftKey && i === ring.length - 1) { e.preventDefault(); ring[0].focus(); }
    }
  });
  let last = 0;
  /* a menu link may point at another page, which is not a selector */
  const linkSec = links.map(l => {
    const h = l.getAttribute('href') || '';
    return h.charAt(0) === '#' ? SECS.indexOf(document.querySelector(h)) : -1;
  });
  addEventListener('scroll', () => {
    const y = scrollY;
    nav.classList.toggle('stuck', y > 40);
    nav.classList.toggle('hide', !isOpen() && y > last + 4 && y > vpH() * .8);
    last = y;
    rail.classList.toggle('show', y > vpH() * .5);
    const a = Math.round(progressFor(y));
    if (a !== activeSec) {
      activeSec = a;
      const cur = (el, on) => on ? el.setAttribute('aria-current', 'true') : el.removeAttribute('aria-current');
      dots.forEach((d, i) => { d.classList.toggle('on', i === a); cur(d, i === a); });
      /* a link to another page has no section to be inside, so the scroll
         position must not strip the marker that says which page this is */
      links.forEach((l, i) => { if (linkSec[i] >= 0) cur(l, linkSec[i] === a); });
    }
  }, { passive: true });
  $$('a[href^="#"]').forEach(a => a.addEventListener('click', e => {
    const href = a.getAttribute('href');
    const t = href === '#top' ? document.body : document.querySelector(href);
    if (!t) return;
    e.preventDefault();
    scrollTo({ top: href === '#top' ? 0 : t.getBoundingClientRect().top + scrollY - 40, behavior: REDUCE ? 'auto' : 'smooth' });
  }));
}

function wireFocus() {
  const set = i => { RIG.focus = i; };
  $$('[data-chip]').forEach(el => {
    el.addEventListener('mouseenter', () => { set(+el.dataset.chip); $$('[data-chip]').forEach(o => o.classList.toggle('on', o === el)); });
    el.addEventListener('mouseleave', () => { set(-1); el.classList.remove('on'); });
  });
  $$('[data-focus]').forEach(el => {
    el.addEventListener('mouseenter', () => set(+el.dataset.focus));
    el.addEventListener('mouseleave', () => set(-1));
  });
}

/* One delegated press handler for every [data-press]: touch screens have no
   hover, so this is how a tap says it landed. Released on pointerup, on
   cancel, on leaving the element and on any scroll, so nothing can stick. */
/* Each control carries its own message in data-wa. Until the number is
   set they stay exactly as the markup leaves them: focusable buttons that
   announce themselves disabled. Once it is set each becomes a real link,
   so the browser's own new-tab, copy-link and middle-click all work. */
function wireWhatsApp() {
  $$('[data-wa]').forEach(el => {
    const msg = el.getAttribute('data-wa');
    if (!WHATSAPP || !msg) return;
    if (el.tagName === 'LI') {                 /* the footer entry: text until wired */
      const a = document.createElement('a');
      a.href = waURL(msg); a.target = '_blank'; a.rel = 'noopener';
      a.setAttribute('data-cursor', '');
      a.textContent = el.textContent.trim();
      el.textContent = ''; el.appendChild(a);
      return;
    }
    const a = document.createElement('a');
    a.href = waURL(msg); a.target = '_blank'; a.rel = 'noopener';
    a.innerHTML = el.innerHTML;
    [].slice.call(el.attributes).forEach(at => {
      if (at.name === 'type' || at.name === 'aria-disabled') return;
      a.setAttribute(at.name, at.value);
    });
    el.replaceWith(a);
  });
}

/* The Customize group. One service at a time, so this is a radio group, not
   four toggles: role="radio" with aria-checked, arrow keys that move and
   select together, and a roving tabindex so Tab enters and leaves the group
   once instead of stopping at all four.

   A choice cannot be taken back. That is the radio convention — once
   something is chosen, something is always chosen — and it is right here,
   because the action has nothing to send without a service. So clicking the
   chosen tile again leaves it chosen, and the action is disabled only up to
   the first choice.

   The count line and the message are both rebuilt from the selection every
   time it changes, so neither can disagree with what is on screen.

   The action stays a button rather than becoming a link, because its target
   changes with the selection and because it has to be genuinely inactive
   before anything is chosen — which an anchor cannot be. */
function wireCustomize() {
  const tiles = $$('.svc');
  if (!tiles.length) return;
  const count = $('#svc-count'), go = $('#svc-go');
  const chosen = () => tiles.find(t => t.getAttribute('aria-checked') === 'true') || null;
  const sync = () => {
    const t = chosen(), name = t ? t.dataset.svc : '';
    count.textContent = name ? name + ' selected' : 'No service selected';
    /* Only the chosen tile is tabbable. With nothing chosen yet the first
       one holds the stop, so the group is always reachable by Tab. */
    tiles.forEach(el => el.tabIndex = (t ? el === t : el === tiles[0]) ? 0 : -1);
    /* Before the first choice there is no message to build: the action is
       inactive, so an empty service must never reach the attribute either.
       TODO: client to approve copy */
    if (!go) return;
    go.dataset.wa = name
      ? 'Hi Vajradhan — I’d like a custom package. I’m interested in '
        + name + '. Could we scope it?'
      : '';
    go.setAttribute('aria-disabled', String(!(name && WHATSAPP)));
  };
  /* Selecting is always "this one and no other", so clicking what is already
     chosen is a no-op rather than a way back to nothing. */
  const pick = (t, focus) => {
    tiles.forEach(el => el.setAttribute('aria-checked', String(el === t)));
    sync();
    if (focus) t.focus();
  };
  tiles.forEach(t => t.addEventListener('click', () => pick(t, false)));
  /* Arrow keys move and select in one step, which is what a radio group
     does; the ends wrap. Space is the button's own activation and needs
     nothing here. */
  const STEP = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };
  tiles.forEach((t, i) => t.addEventListener('keydown', e => {
    let next = null;
    if (e.key in STEP) next = tiles[(i + STEP[e.key] + tiles.length) % tiles.length];
    else if (e.key === 'Home') next = tiles[0];
    else if (e.key === 'End') next = tiles[tiles.length - 1];
    if (!next) return;
    e.preventDefault();
    pick(next, true);
  }));
  if (go) go.addEventListener('click', () => {
    if (go.getAttribute('aria-disabled') === 'true') return;
    open(waURL(go.dataset.wa), '_blank', 'noopener');
  });
  sync();
}

function wirePress() {
  let held = null;
  const off = () => { if (held) { held.classList.remove('is-press'); held = null; } };
  document.addEventListener('pointerdown', e => {
    const t = e.target.closest && e.target.closest('[data-press]');
    if (!t) return;
    off(); held = t; t.classList.add('is-press');
  }, { passive: true });
  ['pointerup', 'pointercancel', 'pointerleave', 'dragstart'].forEach(t =>
    document.addEventListener(t, off, { passive: true }));
  addEventListener('scroll', off, { passive: true });
  addEventListener('blur', off);
}

function wireCursor() {
  const dot = $('#cursor');
  if (COARSE) { dot.style.display = 'none'; return; }
  let x = vpW() / 2, y = vpH() / 2, tx2 = x, ty = y, lastT = '';
  addEventListener('pointermove', e => {
    tx2 = e.clientX; ty = e.clientY;
    RIG.tmx = (e.clientX / vpW()) * 2 - 1;
    RIG.tmy = -((e.clientY / vpH()) * 2 - 1);
  }, { passive: true });
  $$('[data-cursor]').forEach(el => {
    el.addEventListener('mouseenter', () => dot.classList.add('act'));
    el.addEventListener('mouseleave', () => dot.classList.remove('act'));
  });
  (function tick() {
    x = lerp(x, tx2, .18); y = lerp(y, ty, .18);
    /* write only when it moved: an idle pointer costs no style work */
    const t = x.toFixed(1) + 'px ' + y.toFixed(1) + 'px';
    if (t !== lastT) { dot.style.translate = t; lastT = t; }
    requestAnimationFrame(tick);
  })();
}

/* ==================================================== 10 · the machine */
let tPrev = 0, clock = 0, fadeIn = 0, FRAME = 0;
const INTRO = { t0: 0 };

function resize() {
  if (!renderer || GL.lost) return;
  const w = vpW(), h = vpH();
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, DPR_CAP) * PERF.scale);
  renderer.setSize(w, h, true);
  camera.aspect = w / h; camera.updateProjectionMatrix();
  const pw = renderer.domElement.width, ph = renderer.domElement.height;
  if (POST.scene) {
    POST.scene.setSize(pw, ph);
    POST.comp.uniforms.uRes.value.set(pw, ph);
    let lw = Math.max(2, pw >> 1), lh = Math.max(2, ph >> 1);
    POST.levels.forEach(L => { L.a.setSize(lw, lh); L.b.setSize(lw, lh); L.w = lw; L.h = lh; lw = Math.max(2, lw >> 1); lh = Math.max(2, lh >> 1); });
  }
  if (WORLD.snow) WORLD.snow.material.uniforms.uSize.value = h * renderer.getPixelRatio();
  if (WISP.mesh) WISP.mesh.material.uniforms.uPx.value = h * renderer.getPixelRatio();
  layoutPlanes();
  layoutWord();
  measure();
}

/* Frame-time governor. Over budget: multisampling goes first, then
   resolution in steps. Under budget for a while: resolution comes back first,
   multisampling last, and only after a run of calm windows. */
function govern(raw) {
  if (PERF.locked || clock < 2.2) return;
  PERF.acc += raw; PERF.n++;
  if (PERF.n < 40 && PERF.acc < .9) return;
  const avg = PERF.acc / PERF.n; PERF.acc = 0; PERF.n = 0;
  if (avg > .0235) {
    PERF.calm = 0;
    if (PERF.msaa > 0) { setSamples(0); return; }
    if (PERF.scale > .55) { PERF.scale = Math.max(.55, PERF.scale * (avg > .05 ? .66 : .86)); resize(); }
  } else if (avg < .0135) {
    PERF.calm++;
    if (PERF.scale < 1) { PERF.scale = Math.min(1, PERF.scale + .08); resize(); }
    else if (PERF.msaa === 0 && MSAA > 0 && PERF.calm > 6) setSamples(MSAA);
  }
}

function updateWorld(dt) {
  WORLD.uT.value = clock;
  RIG.focusAmt = damp(RIG.focusAmt, RIG.focus >= 0 ? 1 : 0, 5, dt);
  const f = RIG.focusAmt;
  /* planes the camera closes on dissolve before it reaches them, and every
     one of them wanders a little around where it was laid out */
  Object.keys(WORLD.planes).forEach(k => {
    const P = WORLD.planes[k], n = P.def.near;
    const a = n ? smooth(n[0], n[1], camera.position.z - P.mesh.position.z) : 1;
    P.mesh.material.uniforms.uOpacity.value = a * (P.dim || 1);
    P.mesh.visible = a * (P.dim || 1) > .004;
    if (P.base) {
      driftAt(k, clock, _dpx);
      P.mesh.position.x = P.base.x + _dpx[0] * P.perPx;
      P.mesh.position.y = P.base.y + _dpx[1] * P.perPx;
    }
  });
  /* the corona rides with the head it is lighting */
  if (WORLD.halo && WORLD.halo.base) {
    driftAt('figure', clock, _dpx);
    WORLD.halo.position.x = WORLD.halo.base.x + _dpx[0] * WORLD.halo.perPx;
    WORLD.halo.position.y = WORLD.halo.base.y + _dpx[1] * WORLD.halo.perPx;
  }
  if (WORLD.halo) WORLD.halo.material.opacity = .34 + f * .10 + Math.sin(clock * .34) * .03;
  /* the iris breathes as the walk settles on it */
  if (WORLD.planes.iris) WORLD.planes.iris.mesh.material.uniforms.uBright.value =
    1 + f * .08 + Math.sin(clock * .34) * .035;
  if (WORLD.haze) WORLD.haze.forEach(h => {
    const u = h.userData;
    h.position.x = u.x0 + Math.sin(clock * u.sp + u.ph) * 3.2;
    h.material.opacity = u.o * (1 + f * .5);
    h.quaternion.copy(camera.quaternion);
  });
  /* the wordmark climbs as the walk arrives at Contact */
  if (WORD.group) {
    WORD.reveal = smooth(4.2, 5.0, RIG.smooth) * 1.25;
    const leave = 1 - smooth(5.15, 5.8, RIG.smooth);     /* gone before the colophon */
    WORD.glyphs.forEach((g, i) => {
      const e = easeOut(clamp((WORD.reveal - i * .075) / .62, 0, 1));
      g.position.y = g.userData.baseY - (1 - e) * (WORD.ink.asc * 1.1);
      g.material.opacity = e * .78 * leave;
      g.visible = g.material.opacity > .004;
    });
  }
  if (POST.comp) POST.comp.uniforms.uLift.value = f;
  updateWisps(dt);
}

function render() {
  FRAME++;
  renderer.setRenderTarget(POST.scene || null);
  renderer.clear(true, true, false);
  renderer.render(scene, camera);
  renderer.setRenderTarget(null);
  if (POST.scene) {
    POST.comp.uniforms.uT.value = clock;
    POST.comp.uniforms.uFade.value = fadeIn;
    renderPost();
  }
}

function frame(now) {
  if (!running || FALLEN || GL.lost) return;
  const raw = (now - tPrev) / 1000 || 0;
  const dt = Math.min(raw, .05);              /* animation never jumps … */
  tPrev = now; clock += dt;
  fadeIn = INTRO.t0 ? sat((now - INTRO.t0) / 700) : 1;
  govern(raw);                                /* … the governor reads the truth */
  /* The rig follows the scroll on a looser clamp than the particles: on a
     slow device a 50 ms cap would leave the camera trailing the page by
     seconds, and damping is stable at any step. */
  const rdt = Math.min(raw, .25);
  RIG.prog = progressFor(scrollY);
  RIG.smooth = REDUCE ? RIG.prog : damp(RIG.smooth, RIG.prog, 5.2, rdt);
  RIG.mx = damp(RIG.mx, RIG.tmx, 2.6, rdt);
  RIG.my = damp(RIG.my, RIG.tmy, 2.6, rdt);
  if (INTRO.t0) RIG.intro = REDUCE ? 1 : sat((now - INTRO.t0) / 2400);
  try {
    applyCamera();
    updateWorld(dt);
    render();
  } catch (err) {
    /* a draw that throws (a tainted texture, a driver fault) must not leave a
       frozen frame behind the page */
    console.error('[vajradhan] render failed', err);
    fallback(err); return;
  }
  queue();
}
const TIMER = qs('driver', 'raf') === 'timer';
function queue() { TIMER ? setTimeout(() => frame(performance.now()), 16) : requestAnimationFrame(frame); }

/* ======================================================== 11 · booting
   Every step says whether the page can live without it. Critical steps —
   the renderer, the planes, the post chain — send the page to fallback() if
   they throw or reject; decorative ones log a warning and the boot carries
   on without them. (Kage only guarded its first two steps, so a broken post
   pipeline booted into a half-built scene.)                              */
const JOBS = [
  { name: 'Reading the type',      critical: false, run: () => document.fonts &&
      Promise.all([document.fonts.load('400 200px Michroma'), document.fonts.load('400 40px "Space Grotesk"')]) },
  { name: 'Starting the renderer', critical: true,  run: () => { initGL(); buildRig(); } },
  { name: 'Building the frame',    critical: true,  run: () => loadPlanes() },
  { name: 'Lighting the sky',      critical: false, run: () => { buildHeadGlow(); buildStars(); } },
  { name: 'Drawing in the haze',   critical: false, run: () => { buildHaze(); buildSnow(); buildWisps(); } },
  { name: 'Setting the wordmark',  critical: false, run: () => buildWordmark() },
  { name: 'Grading the frame',     critical: true,  run: () => initPost() }
];

function boot() {
  /* wireWhatsApp swaps each control for a fresh <a>, so it has to run before
     wireReveals: the reveal observer holds element references, and a node
     replaced after it was observed would never receive .rv-in -- it would sit
     at opacity 0 for good. The DOM must be final before the reveals are wired. */
  wireCustomize(); wireWhatsApp();
  wireReveals(); wireNav(); wireHeroExit(); wireFocus(); wireCursor(); wirePress();
  document.body.classList.add('is-locked');
  let i = 0;
  const step = () => {
    if (FALLEN) return;
    const j = JOBS[i];
    preStep.textContent = j.name;
    let settled = false;
    const done = () => {
      if (settled || FALLEN) return; settled = true;
      i++;
      const p = i / JOBS.length;
      preFill.style.right = ((1 - p) * 100).toFixed(1) + '%';
      prePct.textContent = Math.round(p * 100);
      if (i < JOBS.length) setTimeout(step, 16); else setTimeout(start, 220);
    };
    const fail = err => {
      if (settled || FALLEN) return;
      if (j.critical) {
        settled = true;
        console.error('[vajradhan] critical step "' + j.name + '" failed — falling back', err);
        fallback(err);
      } else {
        console.warn('[vajradhan] decorative step "' + j.name + '" failed — continuing without it', err);
        done();
      }
    };
    let r;
    try { r = j.run(); } catch (err) { fail(err); return; }
    (r && typeof r.then === 'function') ? r.then(done, fail) : done();
  };
  setTimeout(step, 60);
}

/* The page stays a page: scrolling unlocked, every reveal shown, the canvas
   hidden, and the five photographic layers stacked in CSS in its place. */
function fallback(err) {
  if (FALLEN) return;
  FALLEN = true; running = false;
  clearTimeout(GL.timer);
  document.documentElement.classList.add('no-webgl');
  document.body.classList.add('no-webgl');
  document.body.classList.remove('is-locked');
  preEl.classList.add('done');
  $$('[data-rv]').forEach(e => e.classList.add('rv-in'));
  window.__vajradhan = { fallback: true, error: String(err && err.message || err) };
}

function start() {
  if (FALLEN) return;
  BOOTED = true;
  addEventListener('resize', resize, { passive: true });
  addEventListener('orientationchange', () => setTimeout(resize, 250));
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) running = false;
    else if (!running && !FALLEN && !GL.lost) { running = true; tPrev = performance.now(); queue(); }
  });
  resize();

  const shot = Q.get('shot');
  if (shot !== null) {                       /* deterministic states for review */
    RIG.intro = 1; fadeIn = 1; INTRO.t0 = 0;
    const n = clamp(parseInt(shot, 10) || 0, 0, SECS.length - 1);
    scrollTo(0, anchors[n]);
    RIG.smooth = RIG.prog = progressFor(anchors[n]);
    $$('[data-rv]').forEach(e => e.classList.add('rv-in'));
    document.body.classList.remove('is-locked');
    preEl.classList.add('done');
  } else {
    preEl.classList.add('done');
    setTimeout(() => {
      document.body.classList.remove('is-locked');
      if (OPENER) OPENER.querySelectorAll('[data-rv]').forEach((e, i) =>
        setTimeout(() => e.classList.add('rv-in'), REDUCE ? 0 : 120 + i * 95));
    }, REDUCE ? 0 : 340);
  }
  running = true; tPrev = performance.now();
  INTRO.t0 = shot !== null ? 0 : performance.now();
  queue();
  window.__vajradhan = {
    RIG: RIG, WORLD: WORLD, WORD: WORD, CAM: CAM, POST: POST, PERF: PERF, renderer: renderer, scene: scene, camera: camera,
    anchors: () => anchors,
    /* hand-testing: every WhatsApp control, its message and the URL it
       builds. Pass a sample number to preview the URLs before the real one
       is set, e.g. __vajradhan.whatsapp('910000000000'). */
    whatsapp(sample) {
      const num = sample || WHATSAPP;
      return $$('[data-wa]').map(el => ({
        page: location.pathname,
        where: (el.closest('section') || el.closest('footer') || {}).id || el.closest('footer') ? 'footer' : '?',
        control: ((el.querySelector('span') || el).textContent || '').replace(/\s+/g, ' ').trim().slice(0, 30),
        disabled: el.tagName === 'LI' ? !el.querySelector('a')
                                      : el.getAttribute('aria-disabled') === 'true',
        message: el.getAttribute('data-wa') || '',
        url: num ? 'https://wa.me/' + num + '?text=' + encodeURIComponent(el.getAttribute('data-wa') || '')
                 : '(no number set \u2014 control stays disabled)'
      }));
    },
    /* hand-testing: drop the context, and give it back after `ms` (omit ms to never restore) */
    loseContext(ms) {
      const ext = renderer.getContext().getExtension('WEBGL_lose_context');
      if (!ext) return 'WEBGL_lose_context unavailable';
      ext.loseContext();
      if (ms !== undefined) setTimeout(() => ext.restoreContext(), ms);
      return 'context lost' + (ms !== undefined ? ', restoring in ' + ms + 'ms' : ', not restoring');
    }
  };
}

if (document.readyState === 'loading') addEventListener('DOMContentLoaded', boot);
else setTimeout(boot, 0);
})();
