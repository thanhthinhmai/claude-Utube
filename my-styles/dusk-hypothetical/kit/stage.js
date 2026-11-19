// Stage of the Dusk Hypothetical film kit (specs/022 R5): renderer, fog, base lights and the grade that passed the
// proof frame after nine rounds. Every default number is listed in GRADE.md with the measurement it was checked
// against. Sets add their own practical lights; scenes may nudge exposure and saturation inside the style's range.
import * as THREE from 'three';
import { makePost } from '/core/three/post.js';

export const GRADE = {
  exposure: 0.8,              // ACES tone mapping exposure before EXP_MUL (round 3; scenes and sets nudge it, 0.6–1.0)
  background: '#d9a6c8', fog: '#c9a0c4', fogNear: 6, fogFar: 34,   // specs/027 v3: light warm haze, not dark violet
  vignette: 0.2, saturation: 0.62 * 1.22, contrast: 0.18,          // post.vig uniforms (v3, films/kit-post trial)
  bloom: 0.38, bloomThreshold: 0.85, bloomRadius: 0.7, warm: 0.35,  // lamps and lit windows glow; a warm cast
  dof: { focus: 2.4, aper: 4.5, maxCoc: 14 },        // subject sharp, layers behind soft (round 9)
  shadow: 0.25,                                      // key light shadow intensity (round 4)
  ao: { amount: 0.6, radius: 0.35, scale: 2, samples: 8 },       // ambient occlusion: soft shadow where things meet (specs/027 R4)
  expMul: 0.8,                                      // v3: every exposure × this (reference shots: luma p50 0.327)
  fillWhite: 0.45, frontWhite: 0.6,                  // v3: fill and front light toward white, so faces are not lilac
};
// mood floods for one shot (STYLE.md lighting #5); each stays inside the style's luma and saturation range
export const MOODS = {
  dusk:  { hemi: ['#9d84d0', '#7a5670', 1.9], key: ['#ffb08a', 1.8], rim: ['#ff9e70', 4.5], front: ['#b896e0', 4], exp: 1, sat: 1 },
  alarm: { hemi: ['#d07a8a', '#6a3040', 1.8], key: ['#ff6a5a', 2.0], rim: ['#ff5040', 4.0], front: ['#e0708a', 3.6], exp: 0.98, sat: 1.06 },
  night: { hemi: ['#6a78d0', '#3a3a70', 1.6], key: ['#9ab0ff', 1.4], rim: ['#a0b8ff', 3.6], front: ['#8090e0', 3.4], exp: 0.95, sat: 0.95 },
  lilac: { hemi: ['#c8b0f0', '#9a80b0', 2.2], key: ['#ffd0c0', 1.8], rim: ['#ffc0a0', 4.0], front: ['#d8c0f0', 4.4], exp: 1.05, sat: 0.96 },
};
export const GRADE_LIMITS = { exposure: [0.6, 1.0], saturation: [0.85, 1.15] };
const WHITE = new THREE.Color('#ffffff'), GROUND = new THREE.Color('#d8b8a8'), FRONT = new THREE.Color('#fff4ee');

export function makeStage(size = [innerWidth, innerHeight]) {
  const [W, H] = size;
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(W, H); renderer.setPixelRatio(1);
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = GRADE.exposure;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.domElement.style.cssText = 'display:block;position:fixed;left:0;top:0';
  document.body.appendChild(renderer.domElement);
  // software WebGL layers can't be captured: every frame is copied to a 2D canvas, graphics draw on top of it
  const view = document.createElement('canvas'); view.width = W; view.height = H;
  view.style.cssText = 'display:block;position:fixed;left:0;top:0;z-index:1'; document.body.appendChild(view);
  const ctx = view.getContext('2d');
  // graphics and subtitles go on their own canvas above: on WSL2's GPU (ANGLE/D3D12) a 2D canvas that also takes the
  // WebGL frame draws curved translucent fills as overlapping triangles (an X across every panel)
  const over = document.createElement('canvas'); over.width = W; over.height = H;
  over.style.cssText = 'display:block;position:fixed;left:0;top:0;z-index:2'; document.body.appendChild(over);
  const octx = over.getContext('2d', { willReadFrequently: true });
  for (const [id, pos] of [['cu-top', 'top:0'], ['cu-bot', 'bottom:0']]) {     // letterbox bars, 6.4 % each
    if (document.getElementById(id)) continue;
    const b = document.createElement('div'); b.id = id;
    b.style.cssText = `position:fixed;left:0;right:0;height:6.4vh;background:#000;z-index:3;${pos}`; document.body.appendChild(b);
  }
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(GRADE.background);        // seen only where a set has no walls and no sky dome
  scene.fog = new THREE.Fog(GRADE.fog, GRADE.fogNear, GRADE.fogFar);
  const cam = new THREE.PerspectiveCamera(50, W / H, 0.05, 120);

  // base light: warm pink key and sun from behind the set, violet fill, warm rim on heads, soft violet front
  const hemi = new THREE.HemisphereLight('#9d84d0', '#7a5670', 1.9);
  const key = new THREE.DirectionalLight('#ffb08a', 1.8); key.position.set(-5, 6, -6); key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048); key.shadow.intensity = GRADE.shadow;
  Object.assign(key.shadow.camera, { left: -12, right: 12, top: 12, bottom: -12, far: 40 });
  const sun = new THREE.DirectionalLight('#ffa070', 7); sun.position.set(-4, 5, -8); sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048); Object.assign(sun.shadow.camera, { left: -12, right: 12, top: 12, bottom: -12, far: 40 });
  const rim = new THREE.DirectionalLight('#ff9e70', 4.5); rim.position.set(-1, 2.6, -7);
  const front = new THREE.PointLight('#b896e0', 4, 14); front.position.set(0, 1.6, 4);
  scene.add(hemi, key, key.target, sun, sun.target, rim, rim.target, front);

  const aoOff = typeof location !== 'undefined' && new URLSearchParams(location.search).get('ao') === '0';   // timing runs (R4)
  const post = makePost(renderer, scene, cam, W, H, aoOff ? { ssaa: 1, ao: false }
    : { ssaa: 1, ao: true, aoAmt: GRADE.ao.amount, aoRadius: GRADE.ao.radius, aoScale: GRADE.ao.scale });
  // fewer AO samples than the library's 16 (R4: 16 samples cost 63 ms a frame at 1080p, over the +50 % budget)
  if (post.dof.ao) { post.dof.ao.updateGtaoMaterial({ samples: GRADE.ao.samples }); post.dof.ao.updatePdMaterial({ samples: GRADE.ao.samples, rings: 2 }); }
  setDof(post, GRADE.dof);
  post.vig.uniforms.amt.value = GRADE.vignette; post.vig.uniforms.contrast.value = GRADE.contrast;
  post.vig.uniforms.warm.value = GRADE.warm;
  post.bloom.strength = GRADE.bloom; post.bloom.threshold = GRADE.bloomThreshold; post.bloom.radius = GRADE.bloomRadius;

  let mood = 'dusk';
  const stage = {
    W, H, renderer, scene, cam, post, ctx, octx, view, lights: { hemi, key, sun, rim, front },
    // set the mood and an optional per-scene nudge: exposure replaces the value (0.6–1.0), saturation is a factor (0.85–1.15)
    grade(name = 'dusk', nudge = {}) {
      const m = MOODS[name] || MOODS.dusk; mood = name;
      hemi.color.set(m.hemi[0]); hemi.groundColor.set(m.hemi[1]); hemi.intensity = m.hemi[2];
      key.color.set(m.key[0]); key.intensity = m.key[1];
      sun.color.set(m.key[0]); sun.intensity = 7 * m.key[1] / 1.8;
      rim.color.set(m.rim[0]); rim.intensity = m.rim[1];
      front.color.set(m.front[0]); front.intensity = m.front[1];
      renderer.toneMappingExposure = clampTo(nudge.exposure ?? GRADE.exposure * m.exp, ...GRADE_LIMITS.exposure) * GRADE.expMul;
      post.vig.uniforms.sat.value = GRADE.saturation * m.sat * (nudge.saturation ?? 1);
      hemi.color.lerp(WHITE, GRADE.fillWhite); hemi.groundColor.lerp(GROUND, 0.4); front.color.lerp(FRONT, GRADE.frontWhite);
    },
    // aim the key, rim and front lights at a point (the subject), keeping their directions
    // side: -1 key from the left (the 022 default), +1 from the right, 0 soft from behind (specs/023, TEMPLATE.md §5)
    aim(target, side = -1) {
      const sx = side === 0 ? -0.4 : side;
      key.position.set(target.x + 5 * sx, 6, target.z - 6); key.target.position.copy(target);
      sun.position.set(target.x + 4 * sx, 5, target.z - 8); sun.target.position.set(target.x, 0, target.z + 1);
      rim.position.set(target.x + 1 * sx, 2.6, target.z - 7); rim.target.position.set(target.x, 1, target.z);
      front.position.set(target.x, 1.6, target.z + 4);
    },
    focus(dist, aper = GRADE.dof.aper) { setDof(post, { focus: dist, aper, maxCoc: GRADE.dof.maxCoc }); },
    draw() { post.composer.render(); ctx.drawImage(renderer.domElement, 0, 0, W, H); octx.clearRect(0, 0, W, H); },
    get mood() { return mood; },
  };
  stage.grade('dusk');
  return stage;
}

function setDof(post, { focus, aper, maxCoc }) {
  post.dof.focus = focus; post.dof.aper = aper; post.dof.maxCoc = maxCoc;
}
const clampTo = (x, a, b) => Math.max(a, Math.min(b, x));

// canvas texture in sRGB
export function tex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
