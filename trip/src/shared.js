/* ---------- small pixel postcards for examples ---------- */
function postcard(kind, h, size = 48) {
  const c = document.createElement("canvas"); c.width = c.height = size; const g = c.getContext("2d"), S = size, dark = kind === "aurora";
  const bands = dark ? [`hsl(${h + 60},45%,10%)`, `hsl(${h + 50},42%,15%)`, `hsl(${h + 40},40%,21%)`] : [`hsl(${h},70%,68%)`, `hsl(${h + 12},78%,75%)`, `hsl(${h + 25},85%,84%)`];
  bands.forEach((col, i) => { g.fillStyle = col; g.fillRect(0, Math.floor(i * S * .24), S, Math.ceil(S * .24)); });
  g.fillStyle = bands[2]; g.fillRect(0, Math.floor(S * .72), S, S);
  if (dark) { for (let x = 0; x < S; x++) { const y = Math.round(S * .3 + Math.sin(x / 5) * 3); g.fillStyle = `hsl(${h},90%,60%)`; g.fillRect(x, y, 1, 3); } }
  else if (kind !== "sea") { g.fillStyle = `hsl(${h + 10},95%,93%)`; const r = Math.round(S * .12), cx = Math.round(S * .7), cy = Math.round(S * .3); for (let y = -r; y <= r; y++) for (let x = -r; x <= r; x++) if (x * x + y * y <= r * r) g.fillRect(cx + x, cy + y, 1, 1); }
  const hill = (base, amp, col, f) => { g.fillStyle = col; for (let x = 0; x < S; x++) { const y = Math.round(base + Math.sin(x / f) * amp); g.fillRect(x, y, 1, S - y); } };
  if (kind === "sea") { hill(S * .6, 1, `hsl(${h},70%,45%)`, 3); hill(S * .78, 1, `hsl(${h},70%,35%)`, 2); }
  else { hill(S * .66, 2, dark ? `hsl(${h + 40},25%,18%)` : `hsl(${h + 200},25%,55%)`, 6); hill(S * .78, 1.5, dark ? `hsl(${h + 40},25%,10%)` : `hsl(${h + 200},30%,36%)`, 4); }
  const u = S / 48;
  if (kind === "torii") { g.fillStyle = "#c8442f"; g.fillRect(14 * u, 22 * u, 20 * u, 2 * u); g.fillRect(12 * u, 20 * u, 24 * u, 2 * u); g.fillRect(16 * u, 22 * u, 2 * u, 18 * u); g.fillRect(30 * u, 22 * u, 2 * u, 18 * u); }
  if (kind === "tower") { g.fillStyle = `hsl(${h + 200},35%,22%)`; for (let y = 10; y < 40; y++) { const w = Math.max(1, Math.round((y - 8) * .35)); g.fillRect((24 - w) * u, y * u, w * 2 * u, u); } }
  return c;
}

/* ---------- earth texture: dots stay the same size on screen, so zooming in reveals finer dots ---------- */
let LAND = null, SEA = null;           // {q, rings:[[x*q, y*q, ...]]}; SEA = finer coasts for Southeast Asia
function ringsPath(src, W, H, path) {
  const q = src.q;
  for (const r of src.rings) {
    const xs = [r[0] / q];
    for (let i = 2; i < r.length; i += 2) { let l = r[i] / q; const p = xs[xs.length - 1]; while (l - p > 180) l -= 360; while (l - p < -180) l += 360; xs.push(l); }
    const polar = Math.abs(xs[xs.length - 1] - xs[0]) > 180;
    for (const o of polar ? [0] : [-360, 0, 360]) {
      if (!polar && (Math.max(...xs) + o < -180 || Math.min(...xs) + o > 180)) continue;
      for (let i = 0; i < xs.length; i++) { const lng = polar ? r[i * 2] / q : xs[i] + o, x = (lng + 180) / 360 * W, y = (90 - r[i * 2 + 1] / q) / 180 * H; i ? path.lineTo(x, y) : path.moveTo(x, y); }
      path.closePath();
    }
  }
}
function landMask(W, H) {
  const c = document.createElement("canvas"); c.width = W; c.height = H; const g = c.getContext("2d");
  const path = new Path2D();
  if (LAND) ringsPath(LAND, W, H, path);
  if (SEA) ringsPath(SEA, W, H, path);
  g.fill(path);
  const d = g.getImageData(0, 0, W, H).data, m = new Uint8Array(W * H);
  for (let i = 0; i < W * H; i++) m[i] = d[i * 4 + 3] > 110 ? 1 : 0;
  return m;
}
function hash(x, y) { const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453; return s - Math.floor(s); }
function vnoise(x, y) {
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi, sx = xf * xf * (3 - 2 * xf), sy = yf * yf * (3 - 2 * yf);
  const a = hash(xi, yi), b = hash(xi + 1, yi), c = hash(xi, yi + 1), d = hash(xi + 1, yi + 1);
  return a + (b - a) * sx + (c - a) * sy + (a - b - c + d) * sx * sy;
}
function hex(c) { const n = parseInt(c.slice(1), 16); return [n >> 16, (n >> 8) & 255, n & 255]; }
function dilate(m, W, H, r) {            // ocean cells within r texels of land (separable box)
  const a = new Uint8Array(W * H), b = new Uint8Array(W * H);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { let v = 0; for (let k = -r; k <= r && !v; k++) v = m[y * W + ((x + k + W) % W)]; a[y * W + x] = v; }
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) { let v = 0; for (let k = -r; k <= r && !v; k++) { const yy = y + k; if (yy >= 0 && yy < H) v = a[yy * W + x]; } b[y * W + x] = v; }
  return b;
}
function earthCanvas(W) {
  const H = W / 2, m = landMask(W, H), near = dilate(m, W, H, Math.max(1, Math.round(W / 700)));
  const P = { ocean: "#2f5bd3", ocean2: "#2a52c4", shallow: "#5f93f0", land: "#7ec850", land2: "#5fae45", land3: "#4b9a3a", sand: "#e8c872", ice: "#f4f8ff", edge: "#3c7a2c" };
  const C = {}; for (const k in P) C[k] = hex(P[k]);
  const c = document.createElement("canvas"); c.width = W; c.height = H; const g = c.getContext("2d"), img = g.createImageData(W, H), d = img.data;
  const L = (x, y) => m[((y + H) % H) * W + ((x + W) % W)];
  for (let y = 0; y < H; y++) {
    const lat = 90 - (y + .5) / H * 180, al = Math.abs(lat);
    for (let x = 0; x < W; x++) {
      const lng = (x + .5) / W * 360 - 180;
      let col;
      if (L(x, y)) {
        const n = vnoise(lng / 9, lat / 9), f = vnoise(lng / 1.6, lat / 1.6);          // big patches + fine patches seen only up close
        if (al > 63) col = C.ice;
        else if (al > 16 && al < 34 && n > .38) col = f > .7 ? C.land : C.sand;
        else col = n > .62 ? C.land2 : (f > .72 ? C.land3 : C.land);
        if (!L(x + 1, y) || !L(x - 1, y) || !L(x, y + 1) || !L(x, y - 1)) col = al > 63 ? C.ice : C.edge;
      } else if (near[y * W + x]) col = C.shallow;
      else col = vnoise(lng / 3, lat / 3) > .78 ? C.ocean2 : C.ocean;
      const i = (y * W + x) * 4; d[i] = col[0]; d[i + 1] = col[1]; d[i + 2] = col[2]; d[i + 3] = 255;
    }
  }
  g.putImageData(img, 0, 0);
  return c;
}
const LODS = [256, 512, 1024, 2048], texCache = {};
/* maps are pre-drawn images (tex/earth_W.png); a size is fetched the first time it's needed */
const texLoader = new THREE.TextureLoader();
function earthTexture(W = 256, onReady) {
  if (texCache[W]) { if (onReady) texCache[W].userData.ready ? onReady(texCache[W]) : texCache[W].userData.wait.push(onReady); return texCache[W]; }
  const t = texLoader.load("tex/earth_" + W + ".png", () => { t.userData.ready = true; t.userData.wait.forEach(f => f(t)); });
  t.magFilter = THREE.LinearFilter; t.minFilter = THREE.LinearFilter; t.generateMipmaps = false; t.wrapS = THREE.RepeatWrapping; t.encoding = THREE.sRGBEncoding;
  t.userData.size = new THREE.Vector2(W, W / 2); t.userData.wait = onReady ? [onReady] : [];
  return (texCache[W] = t);
}
const texSize = { value: new THREE.Vector2(256, 128) };
function calmPixelMaterial(tex) {
  const mat = new THREE.MeshToonMaterial({ map: tex, gradientMap: ramp });
  texSize.value.copy(tex.userData.size);
  mat.onBeforeCompile = (sh) => {
    sh.uniforms.uTexSize = texSize;
    sh.fragmentShader = "uniform vec2 uTexSize;\n" + sh.fragmentShader.replace("#include <map_fragment>", `
      #ifdef USE_MAP
        vec2 px = vUv * uTexSize;
        vec2 seam = floor(px + 0.5);
        vec2 fw = max(fwidth(px), vec2(1e-4));
        px = seam + clamp((px - seam) / fw, -0.5, 0.5);
        diffuseColor *= texture2D(map, px / uTexSize);
      #endif`);
  };
  return mat;
}
/* pick the texture whose dots land around 4-9 screen pixels; build bigger ones lazily, one at a time */
let lodBusy = false, lodW = 256;
function updateLod() {
  if (!globeMesh.material.map || lodBusy) return;
  const dist = Math.max(.05, camera.position.length() - 1);
  const ppu = stage.clientHeight / (2 * dist * Math.tan(camera.fov * Math.PI / 360));
  let want = LODS[0];
  for (const W of LODS) if ((2 * Math.PI / W) * ppu >= 4) want = W;
  if (want === lodW) return;
  lodBusy = true;                                   // keep showing the current map until the new one has arrived
  earthTexture(want, (t) => { globeMesh.material.map = t; texSize.value.copy(t.userData.size); lodW = want; lodBusy = false; });
}

/* ---------- three ---------- */
const stage = $("stage");
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.outputEncoding = THREE.sRGBEncoding;
// diorama look: filmic tone, soft shadows from a sun that follows her
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.25;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
stage.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(40, 1, .05, 100); camera.position.set(0, .8, 3.7); scene.add(camera);
const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; controls.dampingFactor = .1; controls.enablePan = false; controls.minDistance = 1.7; controls.maxDistance = 6; controls.rotateSpeed = .5;
const hemiL = new THREE.HemisphereLight(0xdfe8ff, 0x6a5a78, .62); scene.add(hemiL);
const key = new THREE.DirectionalLight(0xffffff, .25); key.position.set(-2, 3, 4); camera.add(key);   // soft fill from the viewer
const sun = new THREE.DirectionalLight(0xfff0d8, 1.05);                                               // warm key light with shadows
sun.castShadow = true; sun.shadow.mapSize.set(2048, 2048); sun.shadow.bias = -0.0004; sun.shadow.normalBias = .0015;
Object.assign(sun.shadow.camera, { left: -.42, right: .42, top: .42, bottom: -.42, near: .05, far: 3 });
scene.add(sun); scene.add(sun.target);
const ramp = (() => { const t = new THREE.DataTexture(new Uint8Array([120, 255]), 2, 1, THREE.RedFormat); t.minFilter = t.magFilter = THREE.NearestFilter; t.needsUpdate = true; return t; })();

const UP = new THREE.Vector3(0, 1, 0);
function ll2v(lat, lng, r = 1) { const phi = (lng + 180) * Math.PI / 180, th = (90 - lat) * Math.PI / 180; return new THREE.Vector3(-Math.cos(phi) * Math.sin(th) * r, Math.cos(th) * r, Math.sin(phi) * Math.sin(th) * r); }
function v2ll(v) { const n = v.clone().normalize(); let lng = Math.atan2(n.z, -n.x) * 180 / Math.PI - 180; if (lng < -180) lng += 360; return { lat: 90 - Math.acos(n.y) * 180 / Math.PI, lng }; }

const globeMesh = new THREE.Mesh(new THREE.SphereGeometry(1, 96, 64), new THREE.MeshBasicMaterial({ color: 0x2f5bd3 }));
scene.add(globeMesh);
const rimMesh = new THREE.Mesh(new THREE.SphereGeometry(1.03, 64, 48), new THREE.MeshBasicMaterial({ color: 0x0b0e22, side: THREE.BackSide, transparent: true }));   // dark rim: nice from afar, faded out up close
scene.add(rimMesh);
(() => { // a few still stars
  const n = 160, pos = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { const v = new THREE.Vector3(hash(i, 1) - .5, hash(i, 2) - .5, hash(i, 3) - .5).normalize().multiplyScalar(30); pos.set([v.x, v.y, v.z], i * 3); }
  const geo = new THREE.BufferGeometry(); geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  scene.add(new THREE.Points(geo, new THREE.PointsMaterial({ color: 0xfff3c4, size: 2.5, sizeAttenuation: false, transparent: true, opacity: .7 })));
})();

/* ---------- trip flags (still) ---------- */
function flagTexture(t) {
  const c = document.createElement("canvas"); c.width = 24; c.height = 40; const g = c.getContext("2d");
  g.fillStyle = "#1b1b2f"; g.fillRect(2, 0, 2, 40);                 // pole
  g.fillRect(4, 1, 20, 16); g.fillStyle = "#fdf6e3"; g.fillRect(5, 2, 18, 14);
  g.drawImage(postcard(t.samples[0][0], t.samples[0][1], 16), 6, 3, 16, 12);
  g.fillStyle = "#ffcc33"; g.fillRect(1, 0, 4, 2);
  const tx = new THREE.CanvasTexture(c); tx.magFilter = tx.minFilter = THREE.NearestFilter; tx.generateMipmaps = false; tx.encoding = THREE.sRGBEncoding; return tx;
}
const flags = new Map(), labels = $("labels");
function surfaceRoot(lat, lng) { const r = new THREE.Group(), n = ll2v(lat, lng).normalize(); r.position.copy(n); r.quaternion.setFromUnitVectors(UP, n); return r; }
for (const t of TRIPS) {
  const root = surfaceRoot(t.lat, t.lng), turn = new THREE.Group(); root.add(turn);
  const geo = new THREE.PlaneGeometry(.054, .09); geo.translate(.027 - .007, .045, 0);
  const m = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ map: flagTexture(t), transparent: true, alphaTest: .5, side: THREE.DoubleSide }));
  turn.add(m); root.traverse(o => o.userData.flagFor = t.id); root.userData.turn = turn;
  globeMesh.add(root);
  const lab = document.createElement("button"); lab.type = "button"; lab.className = "pin-label px-box";
  lab.innerHTML = "<span></span><small></small>"; lab.firstChild.textContent = t.name; lab.lastChild.textContent = t.date; if (!t.date) lab.lastChild.remove(); const hc = document.createElement("b"); hc.className = "hc"; lab.appendChild(hc);
  lab.addEventListener("click", () => tapTrip(t.id)); labels.appendChild(lab);
  flags.set(t.id, { root, label: lab, trip: t });
}


