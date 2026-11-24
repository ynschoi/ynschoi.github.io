
/* ================= characters ================= */
const H = 0.28;                      // character height on a globe of radius 1
const ACTIONS = [
  ["idle", "대기", "IDLE"], ["jump", "점프", "JUMP"], ["wave", "인사", "WAVE"],
  ["flex", "근육자랑", "FLEX"], ["squat", "스쿼트", "SQUAT"], ["walk", "다음 여행지", "WALK"]
];
const DUR = { jump: 1.0, wave: 1.8, flex: 2.0, squat: 2.2 };

function joint(x, y, z, child) { const g = new THREE.Group(); g.position.set(x, y, z); if (child) g.add(child); return g; }
function shadow() { const s = new THREE.Mesh(new THREE.CircleGeometry(H * .2, 16), new THREE.MeshBasicMaterial({ color: 0, transparent: true, opacity: .28, depthWrite: false })); s.rotation.x = -Math.PI / 2; s.scale.y = .6; s.position.y = .003; return s; }

/* ================= 나: 깔끔한 블록 인형 + 갈아입는 옷 =================
   상자마다 도트 스킨(작은 캔버스)을 6면에 입혀요. 옷을 바꾸면 스킨만 다시 칠하고 소품(모자·안경·가방)을 바꿔 끼워요. */
const C = {
  skin: "#e9a274", skinD: "#d48c5f", hair: "#3a241a", hairL: "#4a3024", hairD: "#2a1912", ink: "#1b1412",
  mouth: "#a8423c", gold: "#f2b822", white: "#f5f5f0", grey: "#c9c9c4"
};
const OUTFITS = {
  sport: { name: "운동복", top: "#e2f25a", topD: "#c9db3c", shorts: "#202024", shortsD: "#141417", sock: "#d6ef1e", sockD: "#b9d10f",
           shoe: "#f3f3ee", shoeD: "#cfcfca", shoeAccent: "#d6ef1e", acc: ["glasses"] },
  hike:  { name: "하이킹", top: "#6b2c26", topD: "#58231e", shorts: "#b29580", shortsD: "#9c8170", spots: "#3d2a22", sock: "#f3f3ee", sockD: "#d5d5cf", stripe: "#a3302a",
           shoe: "#2c2c30", shoeD: "#1c1c1f", acc: ["cap", "pack", "hangGlasses"] },
  beach: { name: "바캉스", top: "#ff7a6b", topD: "#e2604f", shorts: "#f4f1e6", shortsD: "#dedad0", flip: "#2bb3b1", acc: ["straw"] }
};

function skinTex(w, h, paint) {          // paint(i, j) → color, i: 0..w-1 left→right, j: 0..h-1 top→bottom
  const c = document.createElement("canvas"); c.width = w; c.height = h; const g = c.getContext("2d");
  for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) { const col = paint(i, j); if (col) { g.fillStyle = col; g.fillRect(i, j, 1, 1); } }
  const t = new THREE.CanvasTexture(c); t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.generateMipmaps = false; t.encoding = THREE.sRGBEncoding;
  return t;
}
/* box with a painted skin. faces: px, nx, py, ny, pz (front), nz (back). painter(face, i, j, fw, fh) */
function skinBox(w, h, d, P, painter, res) {
  const dims = Object.assign({ px: [d, h], nx: [d, h], py: [w, d], ny: [w, d], pz: [w, h], nz: [w, h] }, res || {});
  const mats = ["px", "nx", "py", "ny", "pz", "nz"].map(f => {
    const [fw, fh] = dims[f], fwi = Math.max(1, Math.round(fw)), fhi = Math.max(1, Math.round(fh));
    return new THREE.MeshLambertMaterial({ map: skinTex(fwi, fhi, (i, j) => painter(f, i, j, fwi, fhi)) });
  });
  const m = new THREE.Mesh(new THREE.BoxGeometry(w * P, h * P, d * P), mats);
  return m;
}
const hang = (mesh, h, P) => { mesh.position.y = -h * P / 2; return mesh; };   // top of the box sits on its joint

function makeSkinDoll(outfitId) {
  const P = H / 35;                       // one skin pixel in world units
  const HEAD = 10, TOR = 11, LEG = 12, ARM = 11;
  const root = new THREE.Group(), legLen = LEG * P, hips = joint(0, legLen, 0); root.add(hips); root.add(shadow()); root.userData.outfit = outfitId;
  const chest = joint(0, TOR * P, 0); hips.add(chest);
  const neck = joint(0, 0, 0); chest.add(neck);
  const headG = new THREE.Group(); headG.position.y = HEAD * P / 2; neck.add(headG);
  const parts = {};                       // meshes that get repainted on a costume change
  const acc = new THREE.Group(); headG.add(acc);
  const back = new THREE.Group(); chest.add(back);
  const legs = [], arms = [];

  // ---- face (front of the head), hair everywhere else ----
  const headPaint = (f, i, j, fw, fh) => {
    if (f === "py" || f === "nz") return (i + j) % 5 === 0 ? C.hairL : C.hair;
    if (f === "ny") return C.skinD;
    if (f === "px" || f === "nx") {          // side: i runs back→front on nx, front→back on px
      const fromBack = f === "nx" ? i : fw - 1 - i;
      if (fromBack < 5 || j < 3) return (j + fromBack) % 4 === 0 ? C.hairL : C.hair;
      return C.skin;
    }
    // front face painted at 14×14: side-swept bangs, brows angled in, tall eyes, smile
    const bang = j < 4 || (j === 4 && i < 11) || (j === 5 && i < 7) || (j === 6 && i < 3) || (i === 0 && j < 10) || (i === 13 && j < 6);
    if (bang) return (i + 2 * j) % 5 === 0 ? C.hairL : C.hair;
    if ((j === 7 && (i === 3 || i === 4 || i === 9 || i === 10)) || (j === 8 && (i === 5 || i === 8))) return C.ink;   // brows
    if ((j === 9 || j === 10) && (i === 4 || i === 5 || i === 8 || i === 9)) return C.ink;                           // eyes
    if (j === 9 && (i === 5 || i === 9)) return C.ink;
    if (j === 11 && (i === 2 || i === 11)) return "#f0927e";                                                          // blush
    if ((j === 11 && (i === 4 || i === 9)) || (j === 12 && i >= 5 && i <= 8)) return C.mouth;                        // smile
    return C.skin;
  };
  // fix: brows sit on row 4 outer + row 5 inner, eyes rows 6-7, smile rows 8-9 — keep the face readable at 10 px
  const head = skinBox(10, HEAD, 9, P, headPaint, { pz: [14, 14] }); headG.add(head);
  const hairBack = skinBox(10, 19, 1.4, P, (f, i, j) => ((i % 3 === 0) ? C.hairD : (i + j) % 6 === 0 ? C.hairL : C.hair));
  hairBack.position.set(0, HEAD * P / 2 - 19 * P / 2 - .5 * P, -(4.5 + .7) * P); headG.add(hairBack);
  for (const s of [-1, 1]) {
    const side = skinBox(1, 9, 5, P, (f, i, j) => (j % 3 === 0 ? C.hairD : C.hair));
    side.position.set(s * 5.5 * P, HEAD * P / 2 - 4.5 * P - 2 * P, -2 * P); headG.add(side);
    const ear = skinBox(.8, 2, 1.2, P, () => C.skinD); ear.position.set(s * 5.4 * P, -.5 * P, .8 * P); headG.add(ear);
    const ring = skinBox(.7, .9, .7, P, () => C.gold); ring.position.set(s * 5.6 * P, -1.9 * P, .8 * P); headG.add(ring);
  }

  // ---- torso / shorts / limbs: repainted per outfit ----
  const O = () => OUTFITS[root.userData.outfit];
  const torsoPaint = (f, i, j, fw, fh) => {
    const o = O(), front = f === "pz", backF = f === "nz", sideF = f === "px" || f === "nx";
    if (f === "py") return C.skin; if (f === "ny") return o.shorts;
    const cropEnd = { sport: 7, hike: 8, beach: 5 }[root.userData.outfit];
    if (j >= 9) return j === 9 ? o.shortsD : o.shorts;                                             // waistband
    if (j >= cropEnd) return C.skin;                                                               // midriff
    if (front && j === 0 && i >= 3 && i <= 4) return C.skin;                                       // neckline
    if (front && root.userData.outfit === "hike") {
      if (j <= 1 && i >= 2 && i <= 5) return C.skin;                                               // scoop neck
      if ((i === 1 || i === 6) && j < 7) return j % 2 ? "#1f6f6c" : "#185a57";                    // backpack straps
      if (i >= 3 && i <= 4 && (j === 3 || j === 5)) return "#5b5d62";                             // sunglasses hooked on
      if (i >= 3 && i <= 4 && (j === 4 || j === 6)) return "#2b2c30";
    }
    if (root.userData.outfit === "beach" && (front || backF) && j === 0 && (i < 2 || i > 5)) return C.skin;
    if (sideF && j === 0) return C.skin;
    return (j === cropEnd - 1) ? o.topD : o.top;
  };
  const torso = skinBox(8, TOR, 4, P, torsoPaint); chest.add(hang(torso, TOR, P)); parts.torso = torso;
  const shortsPaint = (f, i, j) => {
    const o = O();
    if (o.spots && (hash(i * 1.7 + (f === "pz" ? 0 : 11), j * 2.3) > .62)) return o.spots;
    return j === 0 ? o.shortsD : o.shorts;
  };
  const shorts = skinBox(9.2, 4, 4.8, P, shortsPaint); shorts.position.y = -2 * P + .5 * P; hips.add(shorts); parts.shorts = shorts;

  const armPaint = (part) => (f, i, j) => (part === "fore" && j >= 4 ? C.skinD : (f === "py" && part === "upper") ? C.skin : C.skin);
  for (const s of [-1, 1]) {
    const sh = joint(s * 5.5 * P, -.2 * P, 0), el = joint(0, -5.5 * P, 0);
    sh.add(hang(skinBox(3, 5.5, 3, P, armPaint("upper")), 5.5, P)); el.add(hang(skinBox(3, 5.5, 3, P, armPaint("fore")), 5.5, P));
    sh.add(el); chest.add(sh); arms.push({ sh, el, s });
  }
  const shinPaint = (f, i, j) => {
    const o = O(), id = root.userData.outfit;
    if (id === "sport" && j >= 2) return j === 2 ? o.sockD : o.sock;
    if (id === "hike" && j >= 2) return j === 3 ? o.stripe : o.sock;
    return C.skin;
  };
  for (const s of [-1, 1]) {
    const hip = joint(s * 2.1 * P, 0, 0), knee = joint(0, -6 * P, 0);
    hip.add(hang(skinBox(4, 6, 4, P, () => C.skin), 6, P));
    const shin = skinBox(4, 6, 4, P, shinPaint); knee.add(hang(shin, 6, P)); parts["shin" + s] = shin;
    const shoeG = new THREE.Group(); shoeG.position.y = -6 * P; knee.add(shoeG); parts["shoe" + s] = shoeG;
    hip.add(knee); hips.add(hip); legs.push({ hip, knee });
  }

  // ---- outfit-specific pieces ----
  function shoe(g) {
    g.clear(); const o = O(), id = root.userData.outfit;
    if (id === "beach") {
      const sole = skinBox(4.4, .7, 5.6, P, () => o.flip); sole.position.set(0, .35 * P, .6 * P); g.add(sole);
      const strap = skinBox(4.2, .6, .6, P, () => o.flip); strap.position.set(0, 1.4 * P, 1.6 * P); g.add(strap);
      return;
    }
    const tall = id === "hike" ? 3.4 : 2.6;
    const b = skinBox(4.6, tall, 5.6, P, (f, i, j, fw, fh) => {
      if (j === fh - 1) return o.shoeD;                                                            // sole line
      if (id === "sport" && (f === "px" || f === "nx") && j === fh - 2 && i > 1 && i < fw - 1) return o.shoeAccent;
      if (id === "sport" && f === "pz" && j === fh - 2 && i > 0 && i < fw - 1) return o.shoeAccent;
      if (id === "hike" && f === "py" && i > 1 && i < fw - 2 && j % 2 === 0) return "#4a4a50";      // laces
      return f === "py" ? o.shoe : (j === 0 ? o.shoe : (f === "pz" ? o.shoeD : o.shoe));
    });
    b.position.set(0, tall / 2 * P - .2 * P, .6 * P); g.add(b);
  }
  function accessories() {
    acc.clear(); back.clear(); const o = O();
    if (o.acc.includes("glasses")) {                     // sunglasses pushed up on the head
      const fr = skinBox(9.4, 2, 1.2, P, (f, i, j) => f === "pz" && j > 0 && j < 2 && (i >= 1 && i <= 3 || i >= 6 && i <= 8) ? "#6d7680" : "#141416");
      fr.position.set(0, HEAD * P / 2 + .4 * P, 2.2 * P); fr.rotation.x = -.5; acc.add(fr);
    }
    if (o.acc.includes("cap")) {                         // black cap with a small white mountain badge
      const crown = skinBox(10.8, 3.6, 9.8, P, (f, i, j, fw, fh) => {
        if (f === "pz" && ((j === 1 && i === 5) || (j === 2 && i >= 4 && i <= 6))) return C.white;
        if (f === "nz" && j === 2 && i >= 3 && i <= 7) return i === 5 ? "#5a5a60" : "#3a3a40";
        return j === fh - 1 ? "#1a1a1d" : "#26262a";
      });
      crown.position.set(0, HEAD * P / 2 + .4 * P, 0); acc.add(crown);
      const brim = skinBox(9.6, .7, 3.4, P, () => "#1d1d20"); brim.position.set(0, HEAD * P / 2 - 1.2 * P, 6.2 * P); acc.add(brim);
    }
    if (o.acc.includes("straw")) {                       // straw sun hat with a coral band
      const brim = skinBox(15, .7, 14, P, (f, i, j) => ((i + j) % 2 ? "#e8cf8a" : "#d9bd70"));
      brim.position.set(0, HEAD * P / 2 + .2 * P, 0); acc.add(brim);
      const crown = skinBox(10.4, 3.2, 9.4, P, (f, i, j, fw, fh) => j === fh - 1 ? "#ff7a6b" : ((i + j) % 2 ? "#e8cf8a" : "#d9bd70"));
      crown.position.set(0, HEAD * P / 2 + 2 * P, 0); acc.add(crown);
    }
    if (o.acc.includes("pack")) {                        // teal day pack over the hair
      const pack = skinBox(7, 7.5, 3, P, (f, i, j, fw, fh) => {
        if (f === "nz" && i >= 2 && i <= 4 && j >= 3) return "#1d1e22";
        if (f === "nz" && j === 2) return "#185a57";
        return j === 0 ? "#185a57" : "#1f7a76";
      });
      pack.position.set(0, -5.2 * P, -(2 + 1.4 + 1.6) * P); back.add(pack);
    }
  }
  root.userData.setOutfit = (id) => {
    root.userData.outfit = id;
    const repaint = (mesh, painter) => { mesh.material.forEach((m, k) => { const f = ["px", "nx", "py", "ny", "pz", "nz"][k], img = m.map.image, w = img.width, h = img.height;
      m.map.dispose(); m.map = skinTex(w, h, (i, j) => painter(f, i, j, w, h)); m.needsUpdate = true; }); };
    repaint(parts.torso, torsoPaint); repaint(parts.shorts, shortsPaint); repaint(parts["shin-1"], shinPaint); repaint(parts["shin1"], shinPaint);
    shoe(parts["shoe-1"]); shoe(parts["shoe1"]); accessories();
  };
  root.userData.outfit = outfitId;
  shoe(parts["shoe-1"]); shoe(parts["shoe1"]); accessories();
  root.userData.rig = { hips, legs, chest, neck, arms, legLen, thighLen: 6 * P };
  root.userData.pose = (a, k, time) => poseVoxel(root.userData.rig, a, k, time);
  return root;
}


/* ================= 나: 보내준 그림 그대로 (앞모습·뒷모습 카드) =================
   그림을 판 두 장(앞/뒤)에 붙여 세워요. 평소엔 앞모습이 나를 보고, 걸어서 멀어질 땐 뒷모습이 보여요. */
const CARDS = {
  sport: { name: "운동복", front: "cards/sport_front.png", back: "cards/sport_back.png" },
  hike:  { name: "하이킹", front: "cards/hike_front.png",  back: "cards/hike_back.png" }
};
const cardOf = (id) => CARDS[id] ? id : "sport";          // no picture yet for an outfit → wear the sporty one
function makeCardDoll(outfitId) {
  const loader = new THREE.TextureLoader(), tex = {};
  for (const id in CLEAN_OUTFITS) { tex[id] = {}; for (const s of ["front", "back"]) { const t = loader.load(CARDS[id][s]); t.encoding = THREE.sRGBEncoding; t.anisotropy = 4; tex[id][s] = t; } }
  const FH = H * 1.12 * 485 / 480, FW = FH * 300 / 485;
  const geo = new THREE.PlaneGeometry(FW, FH); geo.translate(0, FH / 2 - FH * 2 / 485, 0);
  const fm = new THREE.MeshBasicMaterial({ transparent: true, alphaTest: .5 }), bm = new THREE.MeshBasicMaterial({ transparent: true, alphaTest: .5 });
  const front = new THREE.Mesh(geo, fm), backM = new THREE.Mesh(geo, bm); backM.rotation.y = Math.PI;
  const root = new THREE.Group(), body = new THREE.Group(); body.add(front, backM); root.add(body); root.add(shadow());
  root.userData.setOutfit = (id) => { id = cardOf(id); root.userData.outfit = id; fm.map = tex[id].front; bm.map = tex[id].back; fm.needsUpdate = bm.needsUpdate = true; };
  root.userData.setOutfit(outfitId);
  root.userData.billboard = true;
  root.userData.pose = (act, k, time) => {
    let y = 0, sx = 1, sy = 1, rz = 0;
    if (act === "walk") { y = Math.abs(Math.sin(time * 9)) * .01; rz = Math.sin(time * 9) * .05; }
    else if (act === "jump") {
      const crouch = k < .25 ? Math.sin(k / .25 * Math.PI) : k > .8 ? Math.sin((k - .8) / .2 * Math.PI) : 0;
      const air = k > .25 && k < .8 ? Math.sin((k - .25) / .55 * Math.PI) : 0;
      y = air * H * .45; sy = 1 - crouch * .12 + air * .06; sx = 1 + crouch * .08 - air * .03;
    } else if (act === "wave") { rz = Math.sin(k * Math.PI * 6) * .12 * Math.sin(k * Math.PI); y = Math.abs(Math.sin(k * Math.PI * 3)) * .012; }
    else if (act === "flex") { sx = sy = 1 + Math.sin(k * Math.PI) * .08; }
    else if (act === "squat") { const d = Math.abs(Math.sin(k * Math.PI * 2)); sy = 1 - d * .25; sx = 1 + d * .08; }
    body.position.y = y; body.scale.set(sx, sy, 1); body.rotation.z = rz;
    body.rotation.y = root.userData.away ? Math.PI : 0;                 // walking away → show the back
  };
  return root;
}


/* ================= 나: 보내준 그림과 똑같은 3D 블록 모델 =================
   앞모습·뒷모습 그림을 부위별로 잘라 각 상자의 앞면·뒷면에 그대로 붙이고(그래서 정면·후면이 그림과 똑같음),
   옆·위·아래 면은 그 그림 가장자리 색을 이어 칠해요. 팔다리는 관절로 따로 움직여요.
   좌표는 그림(300×484 px) 기준, 블록 1칸 = 그림 10px. */
const REF = {
  sport: { name: "운동복", front: "cards/sport_front.png", back: "cards/sport_back.png", hipY: 302, shortsTop: 246, shortsW: [92, 209], top: "glasses" },
  hike:  { name: "하이킹", front: "cards/hike_front.png",  back: "cards/hike_back.png",  hipY: 294, shortsTop: 254, shortsW: [95, 205], top: "cap" }
};
const refOf = (id) => REF[id] ? id : "sport";
const refImgs = {};
const refReady = Promise.all(Object.keys(REF).flatMap(id => ["front", "back"].map(s => new Promise(res => {
  const im = new Image(); im.onload = () => { (refImgs[id] || (refImgs[id] = {}))[s] = im; res(); }; im.onerror = res; im.src = REF[id][s];
}))));

/* crop a (possibly slanted) strip: top-centre (cx, cy), width w, length h, tilt a (radians, + leans toward smaller x going down) */
function strip(img, cx, cy, w, h, a = 0, mirror = false) {
  const c = document.createElement("canvas"); c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h));
  const g = c.getContext("2d"); g.imageSmoothingEnabled = false;
  g.translate(c.width / 2, 0); g.rotate(-a); if (mirror) g.scale(-1, 1); g.translate(-cx, -cy); g.drawImage(img, 0, 0);
  return c;
}
function edgeColumn(src, fromRight) {            // the colours down one edge of a crop, a pixel or two in from the side
  const g = src.getContext("2d"), w = src.width, h = src.height, d = g.getImageData(0, 0, w, h).data, out = [];
  for (let y = 0; y < h; y++) {
    let col = null;
    for (let k = 2; k < Math.min(10, w); k++) { const x = fromRight ? w - 1 - k : k, i = (y * w + x) * 4; if (d[i + 3] > 128) { col = [d[i], d[i + 1], d[i + 2]]; break; } }
    out.push(col);
  }
  return out;
}
function sideCanvas(colors, depthPx, shade) {
  const c = document.createElement("canvas"); c.width = Math.max(1, depthPx); c.height = colors.length; const g = c.getContext("2d");
  colors.forEach((col, y) => { if (!col) return; g.fillStyle = `rgb(${col.map(v => Math.round(v * shade)).join(",")})`; g.fillRect(0, y, c.width, 1); });
  return c;
}
function capCanvas(col, shade) { const c = document.createElement("canvas"); c.width = c.height = 2; const g = c.getContext("2d"); g.fillStyle = col ? `rgb(${col.map(v => Math.round(v * shade)).join(",")})` : "#000"; g.fillRect(0, 0, 2, 2); return c; }
const texOf = (cv) => { const t = new THREE.CanvasTexture(cv); t.encoding = THREE.sRGBEncoding; t.magFilter = THREE.LinearFilter; t.minFilter = THREE.LinearFilter; t.generateMipmaps = false; return t; };
const basic = (cv) => new THREE.MeshBasicMaterial({ map: texOf(cv), transparent: true, alphaTest: .5 });
function midColor(cv) { const d = cv.getContext("2d").getImageData(0, 0, cv.width, cv.height).data; for (let y = Math.floor(cv.height / 2); y < cv.height; y++) { const i = (y * cv.width + Math.floor(cv.width / 2)) * 4; if (d[i + 3] > 128) return [d[i], d[i + 1], d[i + 2]]; } return [80, 60, 50]; }

/* one block: front & back from the pictures, sides from their edges. units: picture px; S = world units per px */
function refBlock(front, back, depthPx, S, topCol, bottomCol) {
  const w = front.width, h = front.height;
  const L = edgeColumn(front, false), R = edgeColumn(front, true);
  const mats = [
    basic(sideCanvas(R, depthPx, .8)), basic(sideCanvas(L, depthPx, .8)),     // +x, -x
    basic(capCanvas(topCol || midColor(front), 1.05)), basic(capCanvas(bottomCol || midColor(front), .7)),
    basic(front), basic(back)
  ];
  const m = new THREE.Mesh(new THREE.BoxGeometry(w * S, h * S, depthPx * S), mats);
  return m;
}

function makeRefDoll(outfitId) {
  const root = new THREE.Group();
  root.userData.billboard = false;
  const S = H * 1.12 / 468;                    // picture rows 12..480 → whole height
  const build = (id) => {
    id = refOf(id); root.userData.outfit = id;
    for (const ch of [...root.children]) root.remove(ch);
    const F = refImgs[id] && refImgs[id].front, B = refImgs[id] && refImgs[id].back, cfg = REF[id];
    if (!F || !B) return;
    root.add(shadow());
    const hipY = cfg.hipY, legLen = (480 - hipY) * S;
    const hips = joint(0, legLen, 0); root.add(hips);
    // ---- legs (thigh / shin+sock) and shoes ----
    const kneeY = hipY + (428 - hipY) * .55, legs = [];
    for (const s of [-1, 1]) {
      const fx = s < 0 ? 120.5 : 180.5, bx = s < 0 ? 175.5 : 122.5;          // the back view is mirrored
      const hip = joint(s * 3 * 10 * S, 0, 0), knee = joint(0, -(kneeY - hipY) * S, 0);
      const thigh = refBlock(strip(F, fx, hipY, 45, kneeY - hipY), strip(B, bx, hipY, 45, kneeY - hipY), 45, S);
      thigh.position.y = -(kneeY - hipY) * S / 2; hip.add(thigh);
      const shin = refBlock(strip(F, fx, kneeY, 45, 430 - kneeY), strip(B, bx, kneeY, 45, 430 - kneeY), 45, S);
      shin.position.y = -(430 - kneeY) * S / 2; knee.add(shin);
      const sfx = s < 0 ? 113 : 188, sbx = s < 0 ? 188 : 113;
      const shoe = refBlock(strip(F, sfx, 430, 62, 50), strip(B, sbx, 430, 62, 50), 66, S);
      shoe.position.set(0, -(430 - kneeY) * S - 25 * S, 6 * S); knee.add(shoe);
      hip.add(knee); hips.add(hip); legs.push({ hip, knee });
    }
    // ---- shorts (flared, wider than the waist) ----
    const sw = cfg.shortsW[1] - cfg.shortsW[0], sh = hipY - cfg.shortsTop + 6, scx = (cfg.shortsW[0] + cfg.shortsW[1]) / 2;
    const shorts = refBlock(strip(F, scx, cfg.shortsTop, sw, sh), strip(B, 300 - scx, cfg.shortsTop, sw, sh), 52, S);
    shorts.position.y = (hipY - cfg.shortsTop - sh / 2) * S; hips.add(shorts);
    // ---- torso ----
    const tTop = 150, tH = cfg.shortsTop + 4 - tTop;
    const chest = joint(0, (hipY - tTop) * S, 0); hips.add(chest);
    const torso = refBlock(strip(F, 150, tTop, 72, tH), strip(B, 150.5, tTop, 76, tH), 44, S);
    torso.position.y = -tH * S / 2; chest.add(torso);
    // long hair hanging down the back, below the head
    const hair = refBlock(strip(B, 153.5, 150, 128, 62), strip(B, 153.5, 150, 128, 62), 10, S);
    hair.material[4] = hair.material[5];                                         // both faces show hair
    hair.position.set(0, -31 * S, -27 * S); chest.add(hair);
    // ---- arms: slanted in the pictures, so crop along the slant ----
    const arms = [], A = .337, armLen = 132, half = armLen / 2;
    for (const s of [-1, 1]) {
      const ftop = s < 0 ? [102.3, 168] : [197.7, 168], btop = s < 0 ? [200, 168] : [99, 168];
      const fa = s < 0 ? A : -A, ba = -fa;
      const dir = (top, a, t) => [top[0] - Math.sin(a) * t, top[1] + Math.cos(a) * t];
      const shJ = joint(s * 47.7 * S, -18 * S, 0), rest = new THREE.Group(); rest.rotation.z = s * A; shJ.add(rest);
      const up = refBlock(strip(F, ...ftop, 42, half, fa), strip(B, ...btop, 42, half, ba), 40, S); up.position.y = -half * S / 2; rest.add(up);
      const el = joint(0, -half * S, 0); rest.add(el);
      const fore = refBlock(strip(F, ...dir(ftop, fa, half), 42, half, fa), strip(B, ...dir(btop, ba, half), 42, half, ba), 40, S); fore.position.y = -half * S / 2; el.add(fore);
      chest.add(shJ); arms.push({ sh: shJ, el, s });
    }
    // ---- head (+ glasses or cap on top) ----
    const neck = joint(0, 0, 0); chest.add(neck);
    const hd = refBlock(strip(F, 146.5, 12, 131, tTop - 12), strip(B, 153.5, 12, 131, tTop - 12), 112, S, [55, 39, 39], [205, 135, 90]);
    hd.position.y = (tTop - 12) * S / 2; neck.add(hd);
    if (cfg.top === "glasses") {
      const gl = refBlock(strip(F, 146, 0, 100, 14), strip(B, 155.5, 0, 100, 14), 30, S); gl.position.set(0, (tTop - 12) * S + 6 * S, 30 * S); neck.add(gl);
    } else {
      const cap = refBlock(strip(F, 150, 0, 116, 13), strip(B, 150, 0, 116, 13), 116, S); cap.position.set(0, (tTop - 12) * S + 6 * S, 0); neck.add(cap);
    }
    root.userData.rig = { hips, legs, chest, neck, arms, legLen, thighLen: (kneeY - hipY) * S };
  };
  root.userData.setOutfit = (id) => build(id);
  root.userData.pose = (act, k, time) => { if (root.userData.rig) poseVoxel(root.userData.rig, act, k, time); };
  refReady.then(() => build(outfitId));
  root.userData.outfit = refOf(outfitId);
  return root;
}


/* ================= 나: 3D 블록 모델(char.glb) + 코드 리깅 + 블록 옷 =================
   char.glb는 회색 마네킹 몸 + 머리(머리카락·얼굴·귀걸이)만 있고 뼈대가 없어요.
   Joint_* 블록 위치를 회전 중심으로 삼아 블록들을 관절 그룹에 통째로 붙이고(웨이트 없음),
   옷은 몸보다 살짝 큰 블록을 같은 관절에 붙여 만들어요. 모델 단위: 키 약 1(발바닥 y=0, 정면 +Z). */
const OUT3D = {
  sport: { name: "운동복" }
};
const out3dOf = (id) => OUT3D[id] ? id : "sport";
let glbScene = null;
const glbReady = new Promise((res) => {
  // the model ships as base64 inside char.json and is parsed in memory (no data: or .glb fetch, which the page's rules block)
  if (!THREE.GLTFLoader) return res(null);
  fetch("char.json").then(r => r.json()).then(o => {
    const bin = atob(o.glb), u8 = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
    new THREE.GLTFLoader().parse(u8.buffer, "", (g) => { glbScene = g.scene; res(glbScene); }, () => res(null));
  }).catch(() => res(null));
});
const GLB_SCALE = H * 1.12 / .98;
const mat = (hex, k = 1) => new THREE.MeshLambertMaterial({ color: new THREE.Color(hex).convertSRGBToLinear().multiplyScalar(k) });
const OUTFIT_MATS = {
  skin: null, joint: null,
  lime: mat("#e3ec3f"), limeD: mat("#c4cc2a"), sock: mat("#d8ef20"), sockD: mat("#b9cf12"),
  black: mat("#1f1f24"), blackL: mat("#2c2c33"), white: mat("#efefea"), whiteD: mat("#cfcfca"),
  frame: mat("#16161a"), lens: mat("#5d6168"), shine: mat("#d9dde3")
};
/* a box given in model space (centre x,y,z and size), re-parented onto a joint group so it moves with it */
let dressRoot = null;   // the rig's root: blocks are placed in its (model) space, then handed to a joint
function addBlock(parent, m, cx, cy, cz, sx, sy, sz, rotZ = 0) {
  const b = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), m);
  b.position.set(cx, cy, cz); b.rotation.z = rotZ;
  dressRoot.add(b); b.updateMatrixWorld(true); parent.attach(b);
  return b;
}
function atRest(r, fn) {      // put every joint back to its rest pose while clothes are attached, then restore
  const saved = [];
  r.root.traverse(o => { if (o.isGroup) saved.push([o, o.rotation.clone(), o.position.clone()]); });
  saved.forEach(([o]) => o.rotation.set(0, 0, 0)); r.hips.position.copy(r.hipsRest);
  r.root.updateMatrixWorld(true); dressRoot = r.root;
  const out = fn();
  saved.forEach(([o, rot, pos]) => { o.rotation.copy(rot); o.position.copy(pos); });
  return out;
}
function rigGlb(src) {
  const s = src.clone(true), by = {};
  s.traverse(o => { if (o.name) by[o.name] = o; });
  const root = new THREE.Group(); root.add(s); root.updateMatrixWorld(true);
  const P = (n) => by[n].getWorldPosition(new THREE.Vector3());
  const piv = (pos, parent) => { const g = new THREE.Group(); parent.updateMatrixWorld(true); g.position.copy(parent.worldToLocal(pos.clone())); parent.add(g); g.updateMatrixWorld(true); return g; };
  const hips = piv(P("Joint_Waist"), root), chest = piv(P("Joint_Waist"), hips); hips.updateMatrixWorld(true);
  ["Body_Pelvis", "Joint_Waist"].forEach(n => hips.attach(by[n]));
  chest.attach(by["Body_Torso"]);
  const neck = piv(P("Head_Neck").setY(.53), chest); neck.attach(by["Head_Clean_Planar"]);
  const side = {};
  for (const k of ["L", "R"]) {                       // note: in this file "_L" sits at −X (the character's right)
    const sh = piv(P("Joint_Shoulder_" + k), chest); ["Joint_Shoulder_", "Body_UpperArm_"].forEach(n => sh.attach(by[n + k]));
    const el = piv(P("Joint_Elbow_" + k), sh); ["Joint_Elbow_", "Body_Forearm_"].forEach(n => el.attach(by[n + k]));
    const wr = piv(P("Joint_Wrist_" + k), el); ["Joint_Wrist_", "Body_Hand_"].forEach(n => wr.attach(by[n + k]));
    const hp = piv(P("Joint_Hip_" + k), hips); ["Joint_Hip_", "Body_Thigh_"].forEach(n => hp.attach(by[n + k]));
    const kn = piv(P("Joint_Knee_" + k), hp); ["Joint_Knee_", "Body_Shin_"].forEach(n => kn.attach(by[n + k]));
    const an = piv(P("Joint_Ankle_" + k), kn); ["Joint_Ankle_", "Body_Foot_"].forEach(n => an.attach(by[n + k]));
    side[k] = { sh, el, wr, hp, kn, an };
  }
  // the mannequin body takes the skin colour; joint plates a shade darker
  root.traverse(o => {
    if (!o.isMesh) return;
    if (o.material.name === "Skin_CleanSolid" && !OUTFIT_MATS.skin) { OUTFIT_MATS.skin = o.material; OUTFIT_MATS.joint = o.material.clone(); OUTFIT_MATS.joint.color.multiplyScalar(.82); }
  });
  root.traverse(o => { if (!o.isMesh) return; if (o.material.name === "Body_LightGrey") o.material = OUTFIT_MATS.skin; if (o.material.name === "Joints_MediumGrey") o.material = OUTFIT_MATS.joint; });
  return { root, hips, chest, neck, side, hipsRest: hips.position.clone() };
}
function dressSport(r) {
  const M = OUTFIT_MATS, z = .0645, g = [];
  const put = (parent, ...a) => g.push(addBlock(parent, ...a));
  // neon crop top over the upper two-thirds of the torso, with a darker hem
  put(r.chest, M.lime, 0, .468, z, .226, .122, .168);
  put(r.chest, M.limeD, 0, .404, z, .228, .012, .170);
  // black shorts: waistband on the hips, a short leg on each thigh (so they swing with the legs)
  put(r.hips, M.blackL, 0, .338, z, .238, .036, .166);
  for (const k of ["L", "R"]) {
    const x = k === "L" ? -.071 : .071, s = r.side[k];
    put(s.hp, M.black, x + (k === "L" ? -.006 : .006), .278, z, .112, .068, .118);
    put(s.hp, M.blackL, x + (k === "L" ? -.03 : .03), .278, z + .06, .014, .06, .004);   // little side-slit trim
    // neon socks on the lower shin, white sneakers with a lime stripe
    put(s.kn, M.sock, x, .118, z, .098, .07, .106);
    put(s.kn, M.sockD, x, .152, z, .099, .008, .107);
    put(s.an, M.white, x, .040, .0755, .126, .066, .156);
    put(s.an, M.whiteD, x, .009, .0755, .128, .016, .158);
    put(s.an, M.lime, x, .045, .1545, .05, .012, .004);
  }
  // sunglasses pushed up on top of the hair, lenses facing forward
  put(r.neck, M.frame, 0, 1.06, .085, .31, .016, .02);
  for (const sx of [-.08, .08]) {
    put(r.neck, M.frame, sx, 1.025, .09, .125, .08, .018);
    put(r.neck, M.lens, sx, 1.025, .1, .105, .062, .004);
    put(r.neck, M.shine, sx, 1.025, .103, .075, .009, .002, .78);
  }
  put(r.neck, M.frame, -.155, 1.04, .0, .012, .012, .17);
  put(r.neck, M.frame, .155, 1.04, .0, .012, .012, .17);
  return g;
}
function makeGlbDoll(outfitId) {
  const root = new THREE.Group(); root.add(shadow());
  glbReady.then(sc => { if (sc) return; const fb = makeRefDoll(outfitId); root.add(fb); root.userData.pose = (a, k, tm) => fb.userData.pose(a, k, tm); root.userData.setOutfit = (id) => fb.userData.setOutfit(id); });
  const holder = new THREE.Group(); holder.scale.setScalar(GLB_SCALE); root.add(holder);
  let rig = null, clothes = [];
  const build = () => {
    if (!glbScene) return;
    const r = rigGlb(glbScene); holder.add(r.root); rig = r;
    root.userData.rig = {
      hips: r.hips, chest: r.chest, neck: r.neck,
      legs: [{ hip: r.side.L.hp, knee: r.side.L.kn }, { hip: r.side.R.hp, knee: r.side.R.kn }],
      arms: [{ sh: r.side.L.sh, el: r.side.L.el, s: -1 }, { sh: r.side.R.sh, el: r.side.R.el, s: 1 }],
      legLen: r.hips.position.y, thighLen: .3085 - .185
    };
    root.userData.setOutfit(root.userData.outfit);
  };
  root.userData.outfit = out3dOf(outfitId);
  root.userData.setOutfit = (id) => {
    root.userData.outfit = out3dOf(id);
    if (!rig) return;
    clothes.forEach(b => b.parent && b.parent.remove(b)); clothes = [];
    if (root.userData.outfit === "sport") clothes = atRest(rig, () => dressSport(rig));
  };
  root.userData.pose = (act, k, time) => { if (root.userData.rig) poseVoxel(root.userData.rig, act, k, time); };
  glbReady.then(build);
  return root;
}


/* ================= 나: 깔끔한 블록 캐릭터 (세 번째 그림 기준) =================
   마인크래프트 계열의 날씬한 비율(머리 8 · 몸 12 · 팔 3폭 · 다리 12)에 면마다 단정한 도트 스킨을 입혀요.
   옷을 바꾸면 통째로 다시 만들어요(가벼워서 금방). 단위 1칸 = P(월드). */
const CLEAN = {
  skin: "#efab74", skinD: "#da925b", hair: "#1c1815", hairL: "#2b2521", eye: "#1c1815", mouth: "#b0473f", gold: "#f2b822",
  white: "#f4f2ee", red: "#b5392f"
};
const CLEAN_OUTFITS = {
  hike: { name: "하이킹", top: "#7a2d2b", topD: "#652422", shorts: "#c99d77", spots: "#33221c", sock: "#f4f2ee", stripe: "#b5392f",
          boot: "#2b2b2f", bootD: "#1b1b1e", cap: "#2a2a2d", capD: "#1f1f22", pack: "#2a8c88", packD: "#1d6b68", strap: "#1d1d20" },
  sport: { name: "운동복", top: "#e3ec3f", topD: "#c8d22e", shorts: "#1f1f24", sock: "#d8ef20", shoe: "#f3f3ee", shoeD: "#d5d5d0", shoeA: "#d8ef20" }
};
const cleanOf = (id) => CLEAN_OUTFITS[id] ? id : "sport";
function cleanBox(w, h, d, P, painter, res) {
  const m = skinBox(w, h, d, P, painter, res);
  m.material.forEach(mt => { mt.map.magFilter = THREE.NearestFilter; });
  return m;
}
function makeCleanDoll(outfitId) {
  const root = new THREE.Group(); root.add(shadow());
  const body = new THREE.Group(); root.add(body);
  // proportions measured from the reference: head+cap ≈ 36% of height, short legs, chunky boots
  const LEG = 12, TOR = 9.5, HEAD = 8, HW = 10, TW = 6.8, TD = 4, AW = 2.7, LW = 3.1;
  const P = H * 1.12 / (LEG + TOR + HEAD + 3);   // same overall height as before
  const build = (id) => {
    id = cleanOf(id); root.userData.outfit = id; body.clear();
    const O = CLEAN_OUTFITS[id], hike = id === "hike";
    const hips = joint(0, LEG * P, 0); body.add(hips);
    const chest = joint(0, TOR * P, 0); hips.add(chest);
    const neck = joint(0, 0, 0); chest.add(neck);
    const hang = (m, h) => { m.position.y = -h * P / 2; return m; };
    const leo = (i, j, k = 0) => { const cx = Math.floor((i + k) / 3), cy = Math.floor(j / 3), ox = (cx * 7 + cy * 3) % 2, oy = (cx * 5 + cy * 11) % 2;
      const dx = (i + k) % 3 - ox, dy = j % 3 - oy; return (dx >= 0 && dx <= 1 && dy >= 0 && dy <= 1) ? ((dx + dy * 2 + cx) % 3 ? O.spots : "#6b4634") : null; };
    // ---- torso: tank (hike) / crop top (sport) ----
    const topEnd = hike ? 15 : 11;                   // texture rows (19 tall) covered by the top
    chest.add(hang(cleanBox(TW, TOR, TD, P, (f, i, j, fw, fh) => {
      if (f === "py") return CLEAN.skin; if (f === "ny") return O.shorts;
      if (j >= 16) return hike ? (leo(i, j) || O.shorts) : O.shorts;
      if (j >= topEnd) return CLEAN.skin;
      if (f === "pz") {
        const c = i - 7.5;                           // 16 wide
        if (j <= 2 - Math.abs(c) * .0 && Math.abs(c) < 4 - j * .7) return CLEAN.skin;      // scoop neckline
        if (hike) {
          if (i <= 2 || i >= 13) return j < 13 ? O.strap : O.top;                             // pack straps
          const lens = (cy) => Math.abs(c) <= 1.6 && Math.abs(j - cy) <= 1.4 && !(Math.abs(c) > 1 && Math.abs(j - cy) > 1);
          if (lens(5) || lens(9)) return (c < 0 && (j === 4 || j === 8)) ? "#d8dde4" : "#6c727b";   // two lenses, one above the other
          if (Math.abs(c) <= .6 && j >= 6 && j <= 7) return "#2a2c31";
        }
      }
      if (hike && f === "nz" && (i <= 2 || i >= 13) && j < 6) return O.strap;
      return j === topEnd - 1 ? O.topD : O.top;
    }, { pz: [16, 19], nz: [16, 19], px: [9, 19], nx: [9, 19], py: [16, 9], ny: [16, 9] }), TOR));
    // ---- head: big cube, tall eyes, clear smile, bangs ----
    const head = cleanBox(HW, HEAD, HW, P, (f, i, j, fw, fh) => {
      if (f === "py" || f === "nz") return (i + j) % 9 === 0 ? CLEAN.hairL : CLEAN.hair;
      if (f === "ny") return CLEAN.skinD;
      if (f === "px" || f === "nx") { const fb = f === "nx" ? i : fw - 1 - i; return (fb < 12 || j < 4) ? CLEAN.hair : CLEAN.skin; }
      // front 20×16
      const bang = j < 3 || (j === 3 && (i < 3 || (i > 6 && i < 10) || i > 15)) || (j === 4 && (i < 2 || i > 17)) || i === 0 || i === 19;
      if (bang) return (i + j) % 7 === 0 ? CLEAN.hairL : CLEAN.hair;
      if (j >= 6 && j <= 9 && (i === 5 || i === 6 || i === 13 || i === 14)) return CLEAN.eye;             // tall eyes
      if ((j === 11 && (i === 7 || i === 12)) || (j === 12 && i >= 8 && i <= 11)) return "#8a3a2e";       // smile
      return CLEAN.skin;
    }, { pz: [20, 16], nz: [20, 16], px: [20, 16], nx: [20, 16], py: [20, 20], ny: [20, 20] });
    head.position.y = HEAD * P / 2; neck.add(head);
    // long straight hair: down the back, and in front of the shoulders on both sides
    const hb = cleanBox(HW - .4, 12, 1.2, P, (f, i) => (i % 5 === 0 ? CLEAN.hairL : CLEAN.hair));
    hb.position.set(0, HEAD * P - 6 * P, -(HW / 2 + .6) * P); neck.add(hb);
    for (const s of [-1, 1]) {
      const hs = cleanBox(1.4, 11, 4, P, (f, i, j) => (j % 6 === 0 ? CLEAN.hairL : CLEAN.hair));
      hs.position.set(s * (HW / 2 + .7) * P, HEAD * P - 5.5 * P, -.8 * P); neck.add(hs);
      const ring = cleanBox(.5, 1.2, 1, P, () => CLEAN.gold); ring.position.set(s * (HW / 2 + .2) * P, 2.2 * P, 1.6 * P); neck.add(ring);
    }
    if (hike) {                                       // flat-top cap wider than the head, mountain badge
      const crown = cleanBox(HW + .8, 3, HW + .8, P, (f, i, j, fw, fh) => {
        if (f === "pz") { const c = i - 10.5; if (j >= 1 && j <= 4) { const big = Math.abs(c + 1) <= (j - 1) * .8 + .5, small = j >= 2 && Math.abs(c - 2) <= (j - 2) * .8 + .5; if (big || small) return CLEAN.white; } }   // two-peak mountain badge
        return f === "py" ? "#343438" : (j >= fh - 1 ? O.capD : O.cap);
      }, { pz: [22, 6] });
      crown.position.y = HEAD * P + 1.2 * P; neck.add(crown);
      const brim = cleanBox(HW + .8, .7, 4, P, () => O.capD); brim.position.set(0, HEAD * P - .1 * P, (HW / 2 + 2.2) * P); neck.add(brim);
      const pack = cleanBox(6.4, 7.5, 3.4, P, (f, i, j, fw, fh) => {
        if (f === "nz" && i >= 3 && i < fw - 3 && j >= fh * .4) return "#1e1f23";
        return j < 2 ? O.packD : O.pack;
      }, { nz: [13, 15], pz: [13, 15], px: [7, 15], nx: [7, 15] });
      pack.position.set(0, -4.4 * P, -(TD / 2 + 1.2 + 1.7) * P); chest.add(pack);
    } else {
      const gl = cleanBox(HW - .6, 1.8, 1, P, (f, i, j) => (f === "pz" && j === 1 && ((i >= 1 && i <= 7) || (i >= 11 && i <= 17))) ? "#6d7680" : "#141416", { pz: [19, 3] });
      gl.position.set(0, HEAD * P + .5 * P, (HW / 2 - .8) * P); gl.rotation.x = -.35; neck.add(gl);
    }
    // ---- arms ----
    const arms = [];
    for (const s of [-1, 1]) {
      const sh = joint(s * (TW / 2 + AW / 2) * P, -.2 * P, 0), el = joint(0, -4.8 * P, 0);
      sh.add(hang(cleanBox(AW, 4.8, AW, P, () => CLEAN.skin), 4.8));
      el.add(hang(cleanBox(AW, 4.8, AW, P, (f, i, j, fw, fh) => (j >= fh - 2 ? CLEAN.skinD : CLEAN.skin)), 4.8));
      sh.add(el); chest.add(sh); arms.push({ sh, el, s });
    }
    // ---- legs: shorts, socks, chunky boots / sneakers ----
    const legs = [];
    for (const s of [-1, 1]) {
      const hip = joint(s * (LW / 2 + .25) * P, 0, 0), knee = joint(0, -6 * P, 0);
      hip.add(hang(cleanBox(LW, 6, LW, P, (f, i, j, fw, fh) => (j < fh * .45 ? (hike ? (leo(i, j, s * 3) || O.shorts) : O.shorts) : CLEAN.skin),
        { pz: [8, 12], nz: [8, 12], px: [8, 12], nx: [8, 12] }), 6));
      knee.add(hang(cleanBox(LW, 6, LW, P, (f, i, j, fw, fh) => {
        if (j >= fh * .12) return hike && j >= fh * .2 && j < fh * .3 ? O.stripe : O.sock;
        return CLEAN.skin;
      }, { pz: [8, 12], nz: [8, 12], px: [8, 12], nx: [8, 12] }), 6));
      const bh = hike ? 3 : 2.4, bw = hike ? 4.4 : 3.8, bd = hike ? 6.2 : 5.4;
      const shoe = cleanBox(bw, bh, bd, P, (f, i, j, fw, fh) => {
        if (j >= fh - 2) return hike ? O.bootD : O.shoeD;
        if (!hike && (f === "px" || f === "nx" || f === "pz") && j === fh - 3) return O.shoeA;
        if (hike && f === "py" && i % 3 === 1 && j > 2) return "#3b3b40";                 // laces
        return hike ? O.boot : O.shoe;
      }, { pz: [10, Math.round(bh * 2)], nz: [10, Math.round(bh * 2)], px: [13, Math.round(bh * 2)], nx: [13, Math.round(bh * 2)], py: [10, 13] });
      shoe.position.set(0, -6 * P + bh / 2 * P - .2 * P, .8 * P); knee.add(shoe);
      hip.add(knee); hips.add(hip); legs.push({ hip, knee });
    }
    hips.add((() => { const m = cleanBox(TW + .8, 2, TD + .6, P, (f, i, j) => hike ? (leo(i, j) || O.shorts) : O.shorts, { pz: [17, 4], nz: [17, 4], px: [10, 4], nx: [10, 4] }); m.position.y = -.3 * P; return m; })());
    root.userData.rig = { hips, legs, chest, neck, arms, legLen: LEG * P, thighLen: 6 * P };
    body.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  };
  root.userData.setOutfit = build;
  root.userData.pose = (act, k, time) => {
    const r = root.userData.rig; if (!r) return;
    if (act === "walk") {
      poseVoxel(r, "idle", 0, time);
      const sw = Math.sin(time * 8) * .7;
      r.legs[0].hip.rotation.x = sw; r.legs[1].hip.rotation.x = -sw;
      r.arms[0].sh.rotation.x = -sw * .9; r.arms[1].sh.rotation.x = sw * .9;
      r.hips.position.y = r.legLen + Math.abs(Math.cos(time * 8)) * P * .4;
      return;
    }
    poseVoxel(r, act, k, time);
  };
  build(outfitId);
  return root;
}

const sm = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
function poseVoxel(r, act, k, time) {
  const L = r.thighLen;
  // reset
  r.hips.position.y = r.legLen; r.chest.rotation.set(0, 0, 0); r.neck.rotation.set(0, 0, 0);
  r.legs.forEach(l => { l.hip.rotation.set(0, 0, 0); l.knee.rotation.set(0, 0, 0); });
  r.arms.forEach(a => { a.sh.rotation.set(0, 0, a.s * .12); a.el.rotation.set(0, 0, 0); });
  const squatTo = (a) => {   // thigh forward by a, shin back so feet stay planted
    r.legs.forEach(l => { l.hip.rotation.x = -a; l.knee.rotation.x = 2 * a; });
    r.hips.position.y = r.legLen - 2 * L * (1 - Math.cos(a));
    r.chest.rotation.x = a * .35;
  };
  if (act === "walk") {
    const p = time * 9;
    r.legs.forEach((l, i) => { const s = Math.sin(p + i * Math.PI); l.hip.rotation.x = s * .55; l.knee.rotation.x = Math.max(0, -s) * .7; });
    r.arms.forEach((a, i) => { a.sh.rotation.x = -Math.sin(p + i * Math.PI) * .5; a.el.rotation.x = -.35; });
    r.hips.position.y = r.legLen + Math.abs(Math.sin(p)) * L * .08;
  } else if (act === "jump") {
    const crouch = k < .25 ? sm(0, .25, k) : k > .8 ? 1 - sm(.8, 1, k) : 0;
    squatTo(crouch * .7);
    const air = k > .25 && k < .8 ? Math.sin((k - .25) / .55 * Math.PI) : 0;
    r.hips.position.y += air * H * .45;
    r.arms.forEach(a => { a.sh.rotation.z = a.s * (.12 + air * 2.6); });
    r.legs.forEach(l => { l.knee.rotation.x += air * .5; });
  } else if (act === "wave") {
    const up = sm(0, .15, k) * (1 - sm(.85, 1, k));
    const a = r.arms[1];
    a.sh.rotation.z = up * 2.7; a.el.rotation.z = up * Math.sin(time * 12) * .45;
    r.neck.rotation.z = up * -.12;
  } else if (act === "flex") {
    const up = sm(0, .2, k) * (1 - sm(.85, 1, k));
    r.arms.forEach(a => { a.sh.rotation.z = a.s * (.12 + up * 1.45); a.el.rotation.z = a.s * up * 1.75; });
    r.chest.rotation.x = -up * .08;
    r.hips.position.y += up * Math.max(0, Math.sin(k * Math.PI * 3)) * .004;
  } else if (act === "squat") {
    const reps = Math.sin(Math.min(1, k) * Math.PI * 2 - Math.PI / 2) * .5 + .5;   // two reps
    const depth = (Math.abs(Math.sin(k * Math.PI * 2))) * .85 * (1 - sm(.9, 1, k)); void reps;
    squatTo(depth);
    r.arms.forEach(a => { a.sh.rotation.x = -depth * 1.2; a.sh.rotation.z = a.s * .05; });
  }
}

/* ================= stage: character on the globe ================= */
const anchor = new THREE.Group(), facing = new THREE.Group(); anchor.add(facing); globeMesh.add(anchor);
/* ---- outfit: each trip has its own; changed on arrival with a spin and a puff ---- */
let CHAR_SCALE = .3;
facing.scale.setScalar(CHAR_SCALE);
let zoomF = 0, yawLeft = 0;
let char = makeCleanDoll(TRIPS[0].outfit); facing.add(char);
let spin = null;
const puffs = new THREE.Group(); anchor.add(puffs);
function puff() {
  puffs.clear();
  for (let i = 0; i < 14; i++) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(.018, .018, .018), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true }));
    const a = i / 14 * Math.PI * 2; m.userData.v = new THREE.Vector3(Math.cos(a) * .12, .05 + (i % 3) * .04, Math.sin(a) * .12);
    m.position.set(0, H * CHAR_SCALE * .5, 0); m.scale.setScalar(CHAR_SCALE * 1.5); m.userData.v.multiplyScalar(CHAR_SCALE); puffs.add(m);
  }
  puffs.userData.t0 = clock.elapsedTime;
}
function changeOutfit(id, animate = true) {
  id = cleanOf(id);
  if (char.userData.outfit === id) { syncCard(); return; }
  if (!animate || reduceMotion) { char.userData.setOutfit(id); syncCard(); return; }
  spin = { t0: clock.elapsedTime, id, swapped: false }; puff();
}
function syncCard() {
  document.querySelectorAll(".tab").forEach(b => b.setAttribute("aria-selected", String(b.dataset.id === char.userData.outfit)));
}
for (const id in CLEAN_OUTFITS) {
  const b = document.createElement("button"); b.type = "button"; b.className = "tab"; b.dataset.id = id; b.setAttribute("role", "tab");
  b.textContent = CLEAN_OUTFITS[id].name; b.addEventListener("click", () => changeOutfit(id)); $("tabs").appendChild(b);
}

/* ---- action state ---- */
let act = "idle", actT0 = 0, here = TRIPS[0], move = null, flight = null;
function play(a) {
  if (a === "walk") { const i = TRIPS.indexOf(here); goTo(TRIPS[(i + 1) % TRIPS.length].id); return; }
  if (move) return;
  act = a; actT0 = clock.elapsedTime; markActive();
}
function markActive() { document.querySelectorAll(".act").forEach(b => b.classList.toggle("on", b.dataset.a === act)); }
/* ---- ‹ ● › : walk to the previous / next trip, or snap a photo of where she is ---- */
const stepTrip = (d) => { if (move) return; const i = TRIPS.indexOf(here); hideInstant(); goTo(TRIPS[(i + d + TRIPS.length) % TRIPS.length].id); };
$("prevTrip").addEventListener("click", () => stepTrip(-1));
$("nextTrip").addEventListener("click", () => stepTrip(1));
let shotIdx = {}, instant = null;
function photosOf(t) { return t.photos && t.photos.length ? t.photos : null; }
function hideInstant() { if (instant) { instant.remove(); instant = null; } }
function snap() {
  if (move) return;
  const t = here, list = photosOf(t), k = shotIdx[t.id] = ((shotIdx[t.id] ?? -1) + 1) % (list ? list.length : 1);
  hideInstant();
  $("flash").classList.remove("go"); $("snapTxt").classList.remove("go"); void $("flash").offsetWidth;
  $("flash").classList.add("go"); $("snapTxt").classList.add("go");
  const b = document.createElement("button"); b.type = "button"; b.className = "instant"; b.setAttribute("aria-label", `${t.name} 사진 크게 보기`);
  if (list) { const im = document.createElement("img"); im.alt = ""; im.src = list[k]; b.appendChild(im); }
  else { const c = postcard(t.samples[0][0], t.samples[0][1], 48); b.appendChild(c); }
  const cap = document.createElement("span"); cap.textContent = t.note ? t.note : list ? `${t.name} · ${k + 1}/${list.length}` : `${t.name} · 사진 준비 중`; b.appendChild(cap);
  b.addEventListener("click", () => openAlbum(t, k));
  b.style.visibility = "hidden"; $("snapLayer").appendChild(b); instant = b;
  setTimeout(() => { if (instant !== b) return; b.style.visibility = ""; b.classList.add("eject"); setTimeout(() => b.classList.add("dev"), 150); }, 650);
  if (!reduceMotion) { act = "wave"; actT0 = clock.elapsedTime; }
}
$("shutter").addEventListener("click", snap);
let albumTrip = null, albumK = 0;
function openAlbum(t, k) {
  const list = photosOf(t); if (!list) return;
  albumTrip = t; albumK = k; showAlbum(); $("album").hidden = false; $("albumX").focus();
}
function showAlbum() {
  const list = photosOf(albumTrip); albumK = (albumK + list.length) % list.length;
  $("albumImg").src = list[albumK]; $("albumCap").textContent = albumTrip.note || `${albumTrip.name} · ${albumTrip.date}`; $("albumCnt").textContent = `${albumK + 1}/${list.length}`;
}
$("albumPrev").addEventListener("click", () => { albumK--; showAlbum(); });
$("albumNext").addEventListener("click", () => { albumK++; showAlbum(); });
$("albumX").addEventListener("click", () => { $("album").hidden = true; });
{ let sx = null; $("album").addEventListener("pointerdown", e => sx = e.clientX); $("album").addEventListener("pointerup", e => { if (sx !== null && Math.abs(e.clientX - sx) > 40) { albumK += e.clientX < sx ? 1 : -1; showAlbum(); } sx = null; }); }
document.addEventListener("keydown", e => { if (!$("album").hidden) { if (e.key === "Escape") $("album").hidden = true; if (e.key === "ArrowLeft") { albumK--; showAlbum(); } if (e.key === "ArrowRight") { albumK++; showAlbum(); } } });
/* ---------- whole-globe relief from real elevation ----------
   Elevation: grayscale height map shipped with the three-globe package (MIT; NASA source data), 0 = sea level.
   Land is cut into 0.5° blocks; each block rises in steps by its real height (exaggerated so it reads at this size).
   Built once and never moved, so the ground stays still while she walks. */
const GW = 720, GH = 360, GCELL = 360 / GW, GSTEP = .0012;
let gLevel = null;
const terrain = new THREE.Group(); globeMesh.add(terrain);
function loadTopo() {
  return new Promise(res => { const im = new Image(); im.onload = () => res(im); im.onerror = () => res(null); im.src = "topo.png"; });
}
function levelGrid(topo) {
  const c = document.createElement("canvas"); c.width = GW; c.height = GH; const g = c.getContext("2d");
  const path = new Path2D(); if (LAND) ringsPath(LAND, GW, GH, path); if (SEA) ringsPath(SEA, GW, GH, path);
  g.fill(path); const land = g.getImageData(0, 0, GW, GH).data;
  let elev = null;
  if (topo) { const t = document.createElement("canvas"); t.width = GW; t.height = GH; const tg = t.getContext("2d"); tg.drawImage(topo, 0, 0, GW, GH); elev = tg.getImageData(0, 0, GW, GH).data; }
  const L = new Uint8Array(GW * GH);
  for (let i = 0; i < GW * GH; i++) {
    if (land[i * 4 + 3] < 70) continue;                                             // small islands count too
    const e = elev ? elev[i * 4] : 0;
    L[i] = Math.min(16, 1 + Math.floor(Math.sqrt(e) * .95));                       // √ so lowland hills show too
  }
  return L;
}
function blockColor(lv, x, y, coast) {
  const lat = 90 - (y + .5) * GCELL, lng = (x + .5) * GCELL - 180, al = Math.abs(lat);
  if (al > 63 || lv >= 14) return "#f4f8ff";                                        // ice and snowy peaks
  if (lv >= 11) return "#b8ab92";
  if (lv >= 8) return "#9a7b52";
  if (lv >= 6) return "#4b9a3a";
  if (coast && lv === 1) return "#e8c872";                                          // beaches
  const n = vnoise(lng / 9, lat / 9);
  if (al > 16 && al < 34 && n > .38 && lv < 8) return "#e2c47a";                    // desert belt
  return lv >= 4 ? "#5fae45" : (n > .62 ? "#6dbb48" : "#7ec850");
}
function buildGlobalTerrain(L) {          // L: one level per 0.5° cell, read from tex/levels.png
  gLevel = L;
  const lvAt = (x, y) => (y < 0 || y >= GH) ? 0 : L[y * GW + ((x + GW) % GW)];
  const D = Math.PI / 180;
  const sT = new Float32Array(GH + 1), cT = new Float32Array(GH + 1), sP = new Float32Array(GW + 1), cP = new Float32Array(GW + 1);
  for (let j = 0; j <= GH; j++) { sT[j] = Math.sin(j * GCELL * D); cT[j] = Math.cos(j * GCELL * D); }
  for (let i = 0; i <= GW; i++) { sP[i] = Math.sin(i * GCELL * D); cP[i] = Math.cos(i * GCELL * D); }
  let land = 0; for (let k = 0; k < L.length; k++) if (L[k]) land++;
  let cap = land * 6 + 1024, pos = new Float32Array(cap * 12), nor = new Float32Array(cap * 12), col = new Float32Array(cap * 12), q = 0;
  const grow = () => { cap *= 2; const g = (a) => { const b = new Float32Array(cap * 12); b.set(a); return b; }; pos = g(pos); nor = g(nor); col = g(col); };
  const cc = new THREE.Color(), rOf = (lv) => lv ? 1 + lv * GSTEP : .999;
  // a quad from 4 corners given as (lng-edge index, lat-edge index, radius); n = wanted outward normal
  const quad = (i0, j0, r0, i1, j1, r1, i2, j2, r2, i3, j3, r3, nx, ny, nz, cr, cg, cb) => {
    if (q >= cap) grow();
    const o = q * 12, V = [[i0, j0, r0], [i1, j1, r1], [i2, j2, r2], [i3, j3, r3]];
    for (let k = 0; k < 4; k++) { const [i, j, r] = V[k]; pos[o + k * 3] = -cP[i] * sT[j] * r; pos[o + k * 3 + 1] = cT[j] * r; pos[o + k * 3 + 2] = sP[i] * sT[j] * r; }
    // wind so the face points along n
    const ax = pos[o + 3] - pos[o], ay = pos[o + 4] - pos[o + 1], az = pos[o + 5] - pos[o + 2], bx = pos[o + 9] - pos[o], by = pos[o + 10] - pos[o + 1], bz = pos[o + 11] - pos[o + 2];
    if ((ay * bz - az * by) * nx + (az * bx - ax * bz) * ny + (ax * by - ay * bx) * nz < 0) {
      for (let k = 0; k < 3; k++) { const t1 = pos[o + 3 + k]; pos[o + 3 + k] = pos[o + 9 + k]; pos[o + 9 + k] = t1; }
    }
    for (let k = 0; k < 4; k++) { nor[o + k * 3] = nx; nor[o + k * 3 + 1] = ny; nor[o + k * 3 + 2] = nz; col[o + k * 3] = cr; col[o + k * 3 + 1] = cg; col[o + k * 3 + 2] = cb; }
    q++;
  };
  for (let y = 0; y < GH; y++) {
    if (y * GCELL < 4 || (y + 1) * GCELL > 176) continue;
    const yc = (y + .5) * GCELL * D, sYc = Math.sin(yc), cYc = Math.cos(yc);
    let x = 0;
    while (x < GW) {
      const lv = lvAt(x, y); if (!lv) { x++; continue; }
      const coast = (k) => !lvAt(k - 1, y) || !lvAt(k + 1, y) || !lvAt(k, y - 1) || !lvAt(k, y + 1);
      const hex = blockColor(lv, x, y, coast(x));
      let x2 = x + 1;
      while (x2 < GW && x2 - x < 6 && lvAt(x2, y) === lv && blockColor(lv, x2, y, coast(x2)) === hex) x2++;
      cc.set(hex).convertSRGBToLinear();
      const r = rOf(lv), xc = (x + x2) / 2 * GCELL * D, sXc = Math.sin(xc), cXc = Math.cos(xc);
      // top
      quad(x, y, r, x2, y, r, x2, y + 1, r, x, y + 1, r, -cXc * sYc, cYc, sXc * sYc, cc.r, cc.g, cc.b);
      // west / east walls (normal along ∓east)
      const wl = lvAt(x - 1, y); if (wl < lv) quad(x, y, rOf(wl), x, y, r, x, y + 1, r, x, y + 1, rOf(wl), -sP[x], 0, -cP[x], cc.r * .78, cc.g * .78, cc.b * .78);
      const el = lvAt(x2, y); if (el < lv) quad(x2, y, rOf(el), x2, y, r, x2, y + 1, r, x2, y + 1, rOf(el), sP[x2], 0, cP[x2], cc.r * .78, cc.g * .78, cc.b * .78);
      // north / south walls, merged where the neighbour matches
      for (const dy of [-1, 1]) {
        const j = dy < 0 ? y : y + 1, sh = dy < 0 ? .9 : .7;
        let k = x;
        while (k < x2) {
          const nl = lvAt(k, y + dy); if (nl >= lv) { k++; continue; }
          let k2 = k + 1; while (k2 < x2 && lvAt(k2, y + dy) === nl) k2++;
          const pc = (k + k2) / 2 * GCELL * D, nx = Math.cos(pc) * cT[j], ny = sT[j], nz = -Math.sin(pc) * cT[j], f = dy < 0 ? 1 : -1;
          quad(k, j, rOf(nl), k, j, r, k2, j, r, k2, j, rOf(nl), nx * f, ny * f, nz * f, cc.r * sh, cc.g * sh, cc.b * sh);
          k = k2;
        }
      }
      x = x2;
    }
  }
  const idx = new Uint32Array(q * 6);
  for (let k = 0; k < q; k++) { const v = k * 4, o = k * 6; idx[o] = v; idx[o + 1] = v + 1; idx[o + 2] = v + 2; idx[o + 3] = v; idx[o + 4] = v + 2; idx[o + 5] = v + 3; }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(pos.subarray(0, q * 12), 3));
  geo.setAttribute("normal", new THREE.BufferAttribute(nor.subarray(0, q * 12), 3));
  geo.setAttribute("color", new THREE.BufferAttribute(col.subarray(0, q * 12), 3));
  geo.setIndex(new THREE.BufferAttribute(idx, 1));
  { // fake ambient occlusion: the lower edge of every wall is darker
    for (let k = 0; k < q; k++) {
      const o = k * 12; let rmax = 0; const rr = [];
      for (let v = 0; v < 4; v++) { const x = pos[o + v * 3], y = pos[o + v * 3 + 1], z = pos[o + v * 3 + 2], r = Math.sqrt(x * x + y * y + z * z); rr.push(r); rmax = Math.max(rmax, r); }
      for (let v = 0; v < 4; v++) if (rr[v] < rmax - 1e-5) { col[o + v * 3] *= .55; col[o + v * 3 + 1] *= .55; col[o + v * 3 + 2] *= .6; }
    }
  }
  terrain.clear(); const tmesh = new THREE.Mesh(geo, new THREE.MeshLambertMaterial({ vertexColors: true })); tmesh.castShadow = tmesh.receiveShadow = true; terrain.add(tmesh);
  plantTrees();
  for (const f of flags.values()) { const fn = f.root.position.clone().normalize(); f.root.position.copy(fn.multiplyScalar(1 + groundAt(fn))); }
  for (const id in traceOf) placeOnGround(traceOf[id].root, TRIPS.find(x => x.id === id));
  placeAnchor(anchor.position.clone().normalize(), true);
}
function loadLevels() {
  return new Promise(res => { const im = new Image(); im.onload = () => {
    const c = document.createElement("canvas"); c.width = GW; c.height = GH; const g = c.getContext("2d"); g.drawImage(im, 0, 0);
    // levels are stored ×16 so tiny read-back noise (Safari's fingerprint protection) rounds away instead of raising sea cells
    const d = g.getImageData(0, 0, GW, GH).data, L = new Uint8Array(GW * GH); for (let i = 0; i < L.length; i++) L[i] = Math.round(d[i * 4] / 16);
    res(L); }; im.onerror = () => res(null); im.src = "tex/levels.png"; });
}
function groundAt(n) {                  // top of the block under a point (0 at sea)
  if (!gLevel) return 0;
  const { lat, lng } = v2ll(n), y = Math.min(GH - 1, Math.max(0, Math.floor((90 - lat) / GCELL))), x = Math.min(GW - 1, Math.floor((lng + 180) / GCELL));
  return gLevel[y * GW + x] * GSTEP;
}

for (const f of flags.values()) f.root.scale.setScalar(.55);   // flags in step with the smaller character

/* ---------- traces: leaving a place leaves a copy of her there, in that day's outfit ---------- */
const traces = new THREE.Group(); globeMesh.add(traces);
const traceOf = {};
const store = { get(k) { try { return JSON.parse(localStorage.getItem(k) || "null"); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} } };
function placeOnGround(root, t) { const n = ll2v(t.lat, t.lng).normalize(); root.quaternion.setFromUnitVectors(UP, n); root.position.copy(n).multiplyScalar(1 + groundAt(n)); }
function leaveTrace(t, outfit) {
  if (traceOf[t.id]) { traceOf[t.id].doll.userData.setOutfit(outfit); traceOf[t.id].outfit = outfit; }
  else {
    const root = new THREE.Group(), turn = new THREE.Group(); root.add(turn); turn.scale.setScalar(CHAR_SCALE);
    const doll = makeGlbDoll(outfit); turn.add(doll); root.userData.tripId = t.id;
    placeOnGround(root, t); traces.add(root); traceOf[t.id] = { root, turn, doll, outfit };
  }
  const saved = store.get("traces") || {}; saved[t.id] = outfit; store.set("traces", saved);
}
function restoreTraces() { store.set("traces", null); }   // copies left behind were too crowded; turned off

/* ---------- hearts: tap her head; one heart per person per place, counted across visitors ---------- */
let heartCounts = {}, myHearts = store.get("myHearts") || {}, heartsDb = null, heartsUid = null;
function renderHeartLabels() { for (const f of flags.values()) { const n = heartCounts[f.trip.id] || 0; const hc = f.label.querySelector(".hc"); if (hc) hc.textContent = n ? "♥" + n : ""; } }
(async () => {
  try {
    if (!window.claude || !window.claude.use) return;
    const [db, user] = await Promise.all([window.claude.use("db"), window.claude.use("user")]);
    if (!db || !user) return;
    heartsUid = await user.id(); heartsDb = db;
    db.collection("hearts").onSnapshot((snap) => {
      heartCounts = {}; snap.docs.forEach(d => { const v = d.data() || {}; for (const k in v) if (v[k]) heartCounts[k] = (heartCounts[k] || 0) + 1; if (d.id === heartsUid) myHearts = Object.assign({}, v); });
      renderHeartLabels();
    }, () => {});
  } catch (e) { /* no shared store here: hearts stay on this device */ }
})();
function heartsAt(x, y, tripId) {
  for (let i = 0; i < 6; i++) {
    const h = document.createElement("div"); h.className = "heart";
    h.style.left = (x - 9 + (i - 2.5) * 6) + "px"; h.style.top = (y - 8) + "px"; h.style.setProperty("--dx", ((i - 2.5) * 9) + "px"); h.style.animationDelay = (i * .06) + "s";
    $("hearts").appendChild(h); setTimeout(() => h.remove(), 1500);
  }
  const first = !myHearts[tripId];
  if (first) {
    myHearts[tripId] = true; heartCounts[tripId] = (heartCounts[tripId] || 0) + 1; store.set("myHearts", myHearts); renderHeartLabels();
    if (heartsDb && heartsUid) heartsDb.doc("hearts/" + heartsUid).set(Object.assign({}, myHearts)).catch(() => {});
  }
  const c = document.createElement("div"); c.className = "heartCount"; c.textContent = "♥ " + (heartCounts[tripId] || 1);
  c.style.left = x + "px"; c.style.top = (y - 40) + "px"; $("hearts").appendChild(c); setTimeout(() => c.remove(), 1500);
}

/* ---------- sky tint per destination (slow cross-fade, banded like the rest) ---------- */
const SKY = {
  beach: ["#0f1434", "#2a2f66", "#5b4a7a", "#b56d6a"], jungle: ["#0a1822", "#10302f", "#173f36", "#22533e"],
  city: ["#0a1230", "#11264f", "#16395f", "#1e5470"], dusk: ["#0b1030", "#1a1d4a", "#2c2a5c", "#463a72"],
  warm: ["#110f2a", "#2b1d43", "#4d2c4a", "#8f4d45"], cold: ["#0b1030", "#14234a", "#22385e", "#3a5878"]
};
let skyFront = "skyA";
function setSky(id, instant) {
  const tr = TRIPS.find(x => x.id === id), c = SKY[tr ? tr.sky : id]; if (!c) return;
  const next = skyFront === "skyA" ? "skyB" : "skyA";
  $(next).style.background = `linear-gradient(${c[0]} 0 30%, ${c[1]} 30% 60%, ${c[2]} 60% 85%, ${c[3]} 85%)`;
  if (instant || reduceMotion) { $(next).style.transition = "none"; $(skyFront).style.transition = "none"; }
  $(next).classList.add("on"); $(skyFront).classList.remove("on"); skyFront = next;
  if (instant) requestAnimationFrame(() => { $("skyA").style.transition = ""; $("skyB").style.transition = ""; });
}


/* ---------- scenery: little voxel trees around each place, by climate ---------- */
const trees = new THREE.Group(); globeMesh.add(trees);
const TREE_COL = { trunk: "#7a5236", trunkD: "#5e3e28", leaf: "#4f9a3c", leafL: "#6cb84a", leafD: "#3b7a2e", pine: "#2f6b4f", pineL: "#3f8460",
  palm: "#5fae45", blossom: "#eaa6c6", blossomL: "#f4c2d8", lilac: "#b9a3e3", snow: "#f4f8ff", olive: "#8aa65a" };
function treeKind(sky) { return { beach: "palm", jungle: "broad", dusk: "pine", cold: "snowpine", warm: "blossom", city: "lilac" }[sky] || "broad"; }
function treeBlocks(kind, h) {        // [x, y, z, sx, sy, sz, color] in tree-local units (y up), h ≈ 1
  const B = [];
  if (kind === "palm") {
    B.push([0, .32, 0, .07, .64, .07, "trunk"], [.03, .66, 0, .07, .1, .07, "trunkD"]);
    for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) B.push([dx * .15, .7, dz * .15, dx ? .28 : .09, .05, dz ? .28 : .09, "palm"]);
    B.push([0, .74, 0, .12, .08, .12, "leafL"]);
  } else if (kind === "pine" || kind === "snowpine") {
    B.push([0, .1, 0, .09, .2, .09, "trunk"]);
    [[.26, .42], [.19, .62], [.12, .8]].forEach(([w, y], i) => { B.push([0, y, 0, w * 2, .2, w * 2, i % 2 ? "pineL" : "pine"]); if (kind === "snowpine") B.push([0, y + .11, 0, w * 1.6, .04, w * 1.6, "snow"]); });
  } else {
    const leaf = kind === "blossom" ? ["blossom", "blossomL"] : kind === "lilac" ? ["lilac", "blossomL"] : ["leaf", "leafL"];
    B.push([0, .2, 0, .1, .4, .1, "trunk"], [0, .52, 0, .5, .32, .5, leaf[0]], [.05, .74, -.03, .32, .16, .32, leaf[1]]);
  }
  return B;
}
function plantTrees() {
  trees.clear();
  const list = [], M = new THREE.Matrix4(), Q = new THREE.Quaternion(), S = new THREE.Vector3(), Pv = new THREE.Vector3(), col = new THREE.Color();
  TRIPS.forEach((t, ti) => {
    const kind = treeKind(t.sky), c = ll2v(t.lat, t.lng).normalize();
    for (let k = 0; k < 26; k++) {
      const r = 1.3 + hash(ti * 31 + k, 7) * 3.4, a = hash(ti * 17 + k, 3) * Math.PI * 2;      // degrees away from the spot (her own spot stays clear)
      const lat = t.lat + Math.cos(a) * r, lng = t.lng + Math.sin(a) * r / Math.max(.3, Math.cos(t.lat * Math.PI / 180));
      const n = ll2v(lat, lng).normalize(), g = groundAt(n); if (!g) continue;              // land only
      const hgt = .036 + hash(ti, k * 5) * .022, yaw = hash(k, ti * 3) * 6.28;   // a bit shorter than her
      for (const b of treeBlocks(kind, hgt)) list.push([n, g, hgt, yaw, b]);
    }
  });
  const mesh = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshLambertMaterial(), list.length);
  const up = new THREE.Vector3(0, 1, 0);
  list.forEach(([n, g, h, yaw, b], i) => {
    Q.setFromUnitVectors(up, n).multiply(new THREE.Quaternion().setFromAxisAngle(up, yaw));
    Pv.set(b[0] * h, b[1] * h, b[2] * h).applyQuaternion(Q).add(n.clone().multiplyScalar(1 + g));
    S.set(b[3] * h, b[4] * h, b[5] * h); M.compose(Pv, Q, S); mesh.setMatrixAt(i, M);
    mesh.setColorAt(i, col.set(TREE_COL[b[6]]).convertSRGBToLinear());
  });
  mesh.instanceMatrix.needsUpdate = true; if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  mesh.castShadow = mesh.receiveShadow = true; mesh.frustumCulled = false; trees.add(mesh);
}

/* ---------- weather around her: snow in the cold, drifting petals elsewhere ---------- */
const FX_N = 260, fxPos = new Float32Array(FX_N * 3), fxVel = new Float32Array(FX_N);
for (let i = 0; i < FX_N; i++) { fxPos[i * 3] = (hash(i, 1) - .5) * .8; fxPos[i * 3 + 1] = hash(i, 2) * .5; fxPos[i * 3 + 2] = (hash(i, 3) - .5) * .8; fxVel[i] = .5 + hash(i, 4); }
const fxGeo = new THREE.BufferGeometry(); fxGeo.setAttribute("position", new THREE.BufferAttribute(fxPos, 3));
const fxMat = new THREE.PointsMaterial({ color: 0xffffff, size: .006, transparent: true, opacity: .9, depthWrite: false });
const fx = new THREE.Points(fxGeo, fxMat); fx.frustumCulled = false; anchor.add(fx);
function weatherFor(t) { return t.sky === "cold" ? "snow" : (t.sky === "warm" || t.sky === "city" || t.sky === "dusk") ? "petal" : (t.sky === "jungle" ? "firefly" : "none"); }
function stepWeather(dt, time) {
  const w = weatherFor(here); fx.visible = w !== "none" && !reduceMotion;
  if (!fx.visible) return;
  fxMat.color.set(w === "snow" ? 0xffffff : w === "petal" ? 0xffb7d0 : 0xfff3a0); fxMat.size = w === "snow" ? .006 : w === "petal" ? .007 : .004;
  for (let i = 0; i < FX_N; i++) {
    const v = fxVel[i];
    if (w === "firefly") { fxPos[i * 3 + 1] = .03 + (Math.sin(time * .7 * v + i) * .5 + .5) * .18; fxPos[i * 3] += Math.sin(time + i) * .0004; }
    else {
      fxPos[i * 3 + 1] -= dt * (w === "snow" ? .05 : .035) * v;
      fxPos[i * 3] += dt * (w === "petal" ? .03 : .008) * Math.sin(time * 1.3 + i);
      if (fxPos[i * 3 + 1] < 0) { fxPos[i * 3 + 1] = .5; fxPos[i * 3] = (hash(i, time) - .5) * .8; }
    }
  }
  fxGeo.attributes.position.needsUpdate = true;
}
function followSun() {   // keep the sun (and its small, sharp shadow box) over her, light from the upper side
  const p = anchor.getWorldPosition(new THREE.Vector3()), n = p.clone().normalize();
  const e = new THREE.Vector3().crossVectors(new THREE.Vector3(0, 1, 0), n); if (e.lengthSq() < 1e-6) e.set(1, 0, 0); e.normalize();
  const no = new THREE.Vector3().crossVectors(n, e);
  sun.target.position.copy(p); sun.position.copy(p).addScaledVector(n, 1.2).addScaledVector(e, .55).addScaledVector(no, .35);
  sun.target.updateMatrixWorld();
}

// height under her is eased, so crossing block steps feels like a smooth slope instead of a jolt
let groundSm = null;
function placeAnchor(n, snap) {
  const g = groundAt(n);
  groundSm = (groundSm === null || snap) ? g : groundSm + (g - groundSm) * .06;
  anchor.quaternion.setFromUnitVectors(UP, n); anchor.position.copy(n).multiplyScalar(1 + groundSm);
}
placeAnchor(ll2v(here.lat, here.lng).normalize());
function goTo(id) {
  const t = TRIPS.find(x => x.id === id); if (!t || t === here || move) return;
  const a = anchor.position.clone().normalize(), b = ll2v(t.lat, t.lng).normalize(), ang = a.angleTo(b);
  move = { a, b, t0: performance.now(), dur: reduceMotion ? 1 : Math.min(4200, 900 + ang * 1800), trip: t };
  camRig.distGoal = camRig.dMin() * 1.1;   // walking zooms in close
  here = t; act = "walk"; markActive(); syncCard();
}
function tapTrip(id) { hideInstant(); goTo(id); }
/* Camera follows her around the globe (as before), but it lives in her own frame:
   'up' is always the ground under her (never upside down), and it stays above the surface (never inside). */
const camRig = {
  az: Math.PI, el: .62, dist: null, distGoal: null,                      // az from north toward east; start south of her, looking north
  d0: () => innerWidth < 640 ? 1.15 : .95, dMin() { return this.d0() / 2; }, dMax: () => 3.6,
  elMin: .22, elMax: 1.35
};
camRig.dist = camRig.d0();
controls.enabled = false;
{ // drag to look around her, pinch / wheel to zoom
  const el = renderer.domElement, pts = new Map(); let pinch0 = null;
  el.addEventListener("pointerdown", e => { pts.set(e.pointerId, { x: e.clientX, y: e.clientY }); if (pts.size === 2) { const [a, b] = [...pts.values()]; pinch0 = { d: Math.hypot(a.x - b.x, a.y - b.y), dist: camRig.dist }; } });
  el.addEventListener("pointermove", e => {
    const p = pts.get(e.pointerId); if (!p) return;
    if (pts.size === 1) { camRig.az -= (e.clientX - p.x) * .008; camRig.el = Math.min(camRig.elMax, Math.max(camRig.elMin, camRig.el + (e.clientY - p.y) * .006)); }
    p.x = e.clientX; p.y = e.clientY;
    if (pts.size === 2 && pinch0) { const [a, b] = [...pts.values()]; const d = Math.hypot(a.x - b.x, a.y - b.y); camRig.dist = Math.min(camRig.dMax(), Math.max(camRig.dMin(), pinch0.dist * pinch0.d / Math.max(1, d))); camRig.distGoal = null; }
  });
  const up = e => { pts.delete(e.pointerId); if (pts.size < 2) pinch0 = null; };
  el.addEventListener("pointerup", up); el.addEventListener("pointercancel", up);
  el.addEventListener("wheel", e => { e.preventDefault(); camRig.dist = Math.min(camRig.dMax(), Math.max(camRig.dMin(), camRig.dist * Math.exp(e.deltaY * .0012))); camRig.distGoal = null; }, { passive: false });
}
const _e = new THREE.Vector3(), _nn = new THREE.Vector3(), _no = new THREE.Vector3(), _off = new THREE.Vector3();
function placeCamera() {
  if (camRig.distGoal) { camRig.dist += (camRig.distGoal - camRig.dist) * .05; if (Math.abs(camRig.dist - camRig.distGoal) < .005) camRig.distGoal = null; }
  anchor.getWorldPosition(lookPt); _nn.copy(lookPt).normalize();
  lookPt.addScaledVector(_nn, H * CHAR_SCALE * .45);
  _e.crossVectors(UP, _nn); if (_e.lengthSq() < 1e-6) _e.set(1, 0, 0); _e.normalize();   // east
  _no.crossVectors(_nn, _e);                                                               // north
  _off.copy(_e).multiplyScalar(Math.sin(camRig.az)).addScaledVector(_no, Math.cos(camRig.az)).multiplyScalar(Math.cos(camRig.el)).addScaledVector(_nn, Math.sin(camRig.el));
  camera.position.copy(lookPt).addScaledVector(_off, camRig.dist);
  camera.up.copy(_nn); camera.lookAt(lookPt);
}
const lookPt = new THREE.Vector3();
const ease = k => k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
const slerpDir = (a, b, e) => { const q = new THREE.Quaternion().setFromUnitVectors(a, b); return a.clone().applyQuaternion(new THREE.Quaternion().slerp(q, e)); };

const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(); let down = null;
renderer.domElement.addEventListener("pointerdown", e => { down = { x: e.clientX, y: e.clientY }; });
renderer.domElement.addEventListener("pointerup", e => {
  if (!down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 6) return;
  const r = renderer.domElement.getBoundingClientRect();
  ndc.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1); ray.setFromCamera(ndc, camera);
  { // tap a head → heart (her, or a copy left behind); tap her body → a random move
    const hits = ray.intersectObjects([facing, traces], true);
    if (hits.length) {
      const h = hits[0]; let o = h.object, tripId = here.id, base = anchor;
      while (o) { if (o.userData && o.userData.tripId) { tripId = o.userData.tripId; base = o; break; } if (o === facing) break; o = o.parent; }
      const local = base.worldToLocal(h.point.clone()), headY = local.y / (H * CHAR_SCALE);
      if (headY > .6) {
        const top = base.localToWorld(new THREE.Vector3(0, H * CHAR_SCALE * 1.1, 0)).project(camera);
        heartsAt((top.x * .5 + .5) * stage.clientWidth, (-top.y * .5 + .5) * stage.clientHeight, tripId);
      } else if (base === anchor) play(["jump", "wave", "flex", "squat"][Math.floor(Math.random() * 4)]);
      return;
    }
  }
  const hit = ray.intersectObjects([...flags.values()].map(f => f.root), true)[0];
  if (hit) tapTrip(hit.object.userData.flagFor);
});

function resize() { const w = stage.clientWidth, h = stage.clientHeight; renderer.setSize(w, h, false); camera.aspect = w / h; camera.fov = w < 640 ? 50 : 40; camera.updateProjectionMatrix(); }
addEventListener("resize", resize); resize();
const wp = new THREE.Vector3(), v3 = new THREE.Vector3(), clock = new THREE.Clock();
function turnTo(root, turn, dirWorld) {
  root.getWorldPosition(wp);
  const d = (dirWorld || camera.position.clone().sub(wp)).clone().applyQuaternion(root.quaternion.clone().invert()); d.y = 0;
  if (d.lengthSq() > 1e-8) turn.rotation.y = Math.atan2(d.x, d.z);
}
function tick() {
  clock.getDelta(); const time = clock.elapsedTime;
  if (flight) { const k = Math.min(1, (performance.now() - flight.t0) / flight.dur), e = flight.linear ? k : ease(k);
    camera.position.copy(slerpDir(flight.from, flight.to, e).multiplyScalar(flight.fromLen + (flight.toLen - flight.fromLen) * e)); camera.lookAt(0, 0, 0); if (k >= 1) flight = null; }
  let travelDir = null;
  if (!move) placeAnchor(anchor.position.clone().normalize());
  if (move) {
    const k = Math.min(1, (performance.now() - move.t0) / move.dur), e = k;   // steady walking pace
    const prev = anchor.position.clone(); placeAnchor(slerpDir(move.a, move.b, e).normalize());
    travelDir = anchor.position.clone().sub(prev); if (travelDir.lengthSq() < 1e-12) travelDir = null;
    if (k >= 1) { const t = move.trip; move = null; act = "wave"; actT0 = time + .7; markActive(); changeOutfit(t.outfit); syncCard(); setSky(t.id); }
  }
  placeCamera();
  for (const f of flags.values()) f.root.visible = !traceOf[f.trip.id] && (f.trip !== here || !!move);
  for (const id in traceOf) {                       // copies left behind: face you, hide the one where she stands now
    const tr = traceOf[id]; tr.root.visible = !(id === here.id && !move);
    tr.root.getWorldPosition(wp); const d = camera.position.clone().sub(wp).applyQuaternion(tr.root.getWorldQuaternion(new THREE.Quaternion()).invert());
    tr.turn.rotation.y = Math.atan2(d.x, d.z) + .4; tr.doll.userData.pose("idle", 0, time);
  }
  updateLod(); followSun();
  { const op = sm(2.7, 3.3, camera.position.length());   // rim only once nearly the whole globe is in view
    rimMesh.material.opacity = op; rimMesh.visible = op > .01; }
  // facing: voxel dolls face where they walk (else face you); the 2.5D board always faces you
  if (char && char.userData.billboard) { turnTo(anchor, facing); char.userData.away = !!travelDir && travelDir.dot(camera.position.clone().sub(anchor.getWorldPosition(new THREE.Vector3()))) < 0; }
  else if (travelDir) {
    const target = Math.atan2(...(() => { const d = travelDir.clone().applyQuaternion(anchor.quaternion.clone().invert()); return [d.x, d.z]; })());
    facing.rotation.y += Math.atan2(Math.sin(target - facing.rotation.y), Math.cos(target - facing.rotation.y)) * .2;
  } else {
    anchor.getWorldPosition(wp);
    const d = camera.position.clone().sub(wp).applyQuaternion(anchor.quaternion.clone().invert());
    const target = Math.atan2(d.x, d.z) + .55;   // three-quarter view reads as 3D
    facing.rotation.y += Math.atan2(Math.sin(target - facing.rotation.y), Math.cos(target - facing.rotation.y)) * .12;
  }
  // action progress
  let k = 0;
  if (act !== "idle" && act !== "walk") { k = (time - actT0) / (reduceMotion ? .01 : DUR[act]); if (k >= 1) { act = "idle"; k = 0; markActive(); } }
  if (spin) {
    const sk = (time - spin.t0) / .7;
    char.rotation.y = Math.min(1, sk) * Math.PI * 2;
    if (!spin.swapped && sk > .45) { char.userData.setOutfit(spin.id); spin.swapped = true; syncCard(); }
    if (sk >= 1) { char.rotation.y = 0; spin = null; }
  }
  if (puffs.children.length) {
    const pt = time - puffs.userData.t0;
    puffs.children.forEach(m => { m.position.addScaledVector(m.userData.v, .016); m.userData.v.multiplyScalar(.93); m.material.opacity = Math.max(0, 1 - pt / .8); });
    if (pt > .8) puffs.clear();
  }
  if (char) char.userData.pose(act, Math.max(0, Math.min(1, k)), time);
  stepWeather(Math.min(.05, time - (tick.last || time)), time); tick.last = time;
  // flag labels
  // flag labels: nearest first; a label that would overlap one already placed stays hidden
  const w = stage.clientWidth, h = stage.clientHeight, cand = [];
  for (const f of flags.values()) {
    turnTo(f.root, f.root.userData.turn);
    f.root.getWorldPosition(wp);
    const vis = wp.clone().normalize().dot(camera.position.clone().sub(wp).normalize());
    v3.copy(wp).add(wp.clone().normalize().multiplyScalar(.065)).project(camera);
    const x = (v3.x * .5 + .5) * w, y = (-v3.y * .5 + .5) * h;
    f.label.style.transform = `translate(${x}px, ${y}px) translate(-50%, -100%)`;
    const show = vis >= .25 && !(f.trip === here && !move);
    if (show) cand.push({ f, x, y, d: wp.distanceTo(camera.position) }); else { f.label.classList.add("far"); f.label.tabIndex = -1; }
  }
  cand.sort((a, b) => a.d - b.d);
  const placed = [];
  for (const c of cand) {
    const bw = (c.f.label.offsetWidth || 70) / 2 + 4, bh = (c.f.label.offsetHeight || 26) + 4;
    const hit = placed.some(p => Math.abs(p.x - c.x) < bw + p.bw && Math.abs(p.y - c.y) < bh);
    c.f.label.classList.toggle("far", hit); c.f.label.tabIndex = hit ? -1 : 0;
    if (!hit) placed.push({ x: c.x, y: c.y, bw });
  }
  if (instant || $("snapTxt").classList.contains("go")) {
    const p = anchor.getWorldPosition(new THREE.Vector3()), head = p.clone().addScaledVector(p.clone().normalize(), H * CHAR_SCALE * 1.05).project(camera);
    const sx = (head.x * .5 + .5) * stage.clientWidth, sy = (-head.y * .5 + .5) * stage.clientHeight;
    if (instant) { const topMin = document.querySelector(".top").getBoundingClientRect().bottom + 8; instant.style.transform = `translate(${Math.round(sx - 66)}px, ${Math.round(Math.max(topMin, sy - 205))}px) rotate(4deg)`; }   // above her head, below the title
    $("snapTxt").style.left = Math.round(sx + 26) + "px"; $("snapTxt").style.top = Math.round(sy - 30) + "px";
  }
  renderer.render(scene, camera);
  requestAnimationFrame(tick);
}
globeMesh.material = calmPixelMaterial(earthTexture(256)); globeMesh.receiveShadow = true;
syncCard(); markActive(); restoreTraces(); setSky(here.id, true);
requestAnimationFrame(tick);
loadLevels().then(L => { if (L) setTimeout(() => buildGlobalTerrain(L), 50); });

})();
</script>
