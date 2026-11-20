// Director of the proof page: the page contract (READY, DUR, render, SHOTS, CARDS, TEXTS, CLEAN) on top of the scenes.
document.querySelector('#root defs').appendChild(_mp);
window.DUR = PLAN.dur;
window.SHOTS = PLAN.shots.map(s => [s.t0, s.t1, s.scene, s.id]);
window.CARDS = PLAN.shots.filter(s => s.scene === 'card').map(s => [s.t0 + .05, s.t1, s.id, s.p.big + (s.p.small ? ' ' + s.p.small : '')]);
const LINE_AT = Object.fromEntries(PLAN.lines.map(l => [l.id, l.at]));
const WORLD = $('world'), UI = $('ui');
let CAM = {cx: 960, cy: 540, zz: 1};
const W2S = (x, y) => [(x - CAM.cx) * CAM.zz + 960, (y - CAM.cy) * CAM.zz + 540];
let CUR = null;
window.render = function (t) {
  const s = PLAN.shots.find(s => t >= s.t0 && t < s.t1) || PLAN.shots[PLAN.shots.length - 1];
  const c = {t, t0: s.t0, lt: t - s.t0, d: s.t1 - s.t0, p: s.p, at: id => LINE_AT[id] - s.t0};
  const o = SCENES[s.scene](c);
  const cam = o.cam || {cx: 960, cy: 540, z: 1, z1: 1};
  // linear move with an optional drift (cx1, cy1) and a hold at the end (hold = share of the shot), as measured on the reference
  const mv = cam.hold != null ? clamp01(c.lt / (c.d * (1 - cam.hold))) : ease(c.lt / c.d);
  CAM = {cx: lerp(cam.cx, cam.cx1 == null ? cam.cx : cam.cx1, mv), cy: lerp(cam.cy, cam.cy1 == null ? cam.cy : cam.cy1, mv), zz: lerp(cam.z, cam.z1, mv)};
  WORLD.setAttribute('transform', `translate(960 540) scale(${CAM.zz}) translate(${-CAM.cx} ${-CAM.cy})`);
  WORLD.innerHTML = o.html;
  (o.chars || []).forEach(([sel, cfg, st], i) => {
    const parent = WORLD.querySelector(sel) || WORLD;
    makeChar(parent, Object.assign({}, cfg, {tag: '_' + i})).set(Object.assign({t}, st));
  });
  while (UI.firstChild) UI.removeChild(UI.firstChild);
  if (o.ui && !window.CLEAN) o.ui(UI, t, !!window.CLEAN);
  CUR = s.id;
};
// every on-screen text at t, with its box (readcheck and tier 2)
window.TEXTS = function (t) {
  window.render(t);
  return [...UI.querySelectorAll('text')].filter(e => e.textContent.trim()).map((e, i) => {
    const r = e.getBoundingClientRect();
    return {id: `${CUR}-${i}`, text: e.textContent, x0: r.left, y0: r.top, x1: r.right, y1: r.bottom};
  });
};
window.render(0);
document.fonts.load('40px Hand').then(() => document.fonts.ready).then(() => { window.READY = true; });
