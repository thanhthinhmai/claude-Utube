// Camera placements of the Dusk Hypothetical kit (specs/022 T015), one per entry of catalog.json "cams", each
// matching a shot scale and angle of shots.json. The camera sits slightly oblique to the subject (proof round 9),
// focus is on the subject's head, and the over-shoulder framing asks for a soft head and shoulder in front.
import * as THREE from 'three';

// d: distance from the subject's head; h: camera height relative to the head (or absolute with abs); yaw: degrees
// off the subject's facing; aim: look-at offset below the head; fov: degrees
export const CAMS = {
  ecu:         { d: 0.78, h: 0.02, yaw: 10, aim: 0.11, fov: 34, aper: 2.4 },   // aim at the eyes, low on the head (specs/023)
  close:       { d: 1.6, h: 0.0, yaw: 18, aim: 0.12, fov: 40, aper: 3.2 },
  'mid-eye':   { d: 2.8, h: -0.15, yaw: 24, aim: 0.32, fov: 45, aper: 4.5 },
  'mid-low':   { d: 2.4, abs: 0.55, yaw: 20, aim: 0.3, fov: 48, aper: 5.5 },
  ots:         { d: 2.5, h: 0.05, yaw: 12, aim: 0.35, fov: 44, shoulder: true, aper: 4.5 },
  // specs/027: hands and the held item close and shallow (film.js puts the item's point in place of the head);
  // a low hero angle for the winning moment, closer and lower than mid-low, looking up
  hands:       { d: 0.85, h: 0.22, yaw: 34, aim: 0.0, fov: 28, aper: 1.6, target: 'hands' },
  'hero-low':  { d: 2.2, abs: 0.32, yaw: 16, aim: 0.12, fov: 50, aper: 5 },
  'wide-eye':  { d: 6.2, h: -0.25, yaw: 22, aim: 0.75, fov: 50 },
  'wide-high': { d: 6.0, abs: 4.2, yaw: 24, aim: 0.8, fov: 50 },
  'very-wide': { d: 15, h: 0.15, yaw: 14, aim: 0.6, fov: 55 },
  'huge-high': { d: 17, abs: 10, yaw: 18, aim: 0.6, fov: 55 },
  top:         { d: 0.6, abs: 15, yaw: 0, aim: 0.6, fov: 50, top: true },
  insert:      { d: 3.2, h: -0.2, yaw: 18, aim: 0.5, fov: 45, soft: true },
};

// A move's speed is what learn craft would measure on the film (the reference's ranges are in those units). The
// measure under-reads on DOF-blurred backgrounds and smooth heads, so the kit moves faster by these factors, set in two
// passes on films/kit-proof-b2 (2026-11-17). Second pass, asked → measured: push 3 → 2.7 %/s, pull 2 → 1.88,
// drift-h 30 → 31.5 px/s, drift-v 15 → 12.6.
export const MEASURE_CAL = { push: 1.68, pull: 1.59, 'drift-h': 1.36, 'drift-v': 1.5, tilt: 1.5 };

// seconds of travel at full speed after lt of a shot dur long, with a soft start and stop of `ramp` s (TEMPLATE.md §12)
export function travel(lt, dur, ramp = 0.4) {
  const r = Math.min(ramp, dur / 2), v = (u) => Math.min(1, u / r, (dur - u) / r);   // trapezoid speed
  let s = 0; const n = 24, h = Math.max(0, Math.min(lt, dur)) / n;
  for (let i = 0; i < n; i++) s += v((i + 0.5) * h) * h;
  return s;
}

// where the subject sits across the frame: 'auto' keeps it in the middle, except an ECU or a huge wide that goes
// off-centre as often as the reference does (template.json → framing.by_scale.<scale>.off_centre), seeded by the scene
export function frameX(frame, scale, template, rand) {
  if (frame && typeof frame === 'object') return frame.x;
  const fr = template && template.framing && template.framing.by_scale && template.framing.by_scale[scale];
  if ((scale === 'ecu' || scale === 'huge') && fr && rand() < fr.off_centre) return rand() < 0.5 ? 0.36 : 0.64;
  return 0.5;
}

// head: world position of the subject's head centre; facing: the subject's yaw (radians, 0 = facing +z)
// opts (from the scene's cam object): {yaw, dist, height, side, drift, push}; specs/023: {move: {type, speed}, lt, dur,
// fx (0–1 subject across the frame)} → returns {focus, aper, shoulder?}
export function place(cam, name, head, facing = 0, opts = {}, k = 0, room = null) {
  const c = CAMS[name]; if (!c) throw new Error(`unknown cam "${name}"`);
  const side = opts.side ?? 1;
  const yaw = facing + side * THREE.MathUtils.degToRad(opts.yaw ?? c.yaw);
  const mv = opts.move || { type: 'still' }, run = opts.dur ? travel(opts.lt ?? 0, opts.dur) : 0;
  let d = c.d * (opts.dist ?? 1) * (1 - (opts.push ?? 0) * k);             // slow push-in over the shot (0–0.1)
  // specs/023 moves: push/pull change the picture's scale by speed %/s; drift/tilt move by speed px/s at 1280 wide
  // push/pull narrow or widen the lens (the whole picture scales by speed %/s); drift and tilt turn the camera (the
  // whole picture shifts by speed px/s at 1280 wide). Turning and zooming move every depth alike, as the reference's
  // camera measure reads it (learn craft); a dolly through a 3D set moved the background far less than the subject.
  const runMid = opts.dur ? travel(opts.dur, opts.dur) / 2 : 0;
  const sp = (mv.speed ?? (mv.type === 'push' || mv.type === 'pull' ? 2 : 16)) * (MEASURE_CAL[mv.type] ?? 1);
  const zoom = mv.type === 'push' ? Math.pow(1 + sp / 100, run) : mv.type === 'pull' ? Math.pow(1 + sp / 100, -run) : 1;
  const hfov = 2 * Math.atan(Math.tan(THREE.MathUtils.degToRad((opts.fov ?? c.fov) / 2)) * (16 / 9));
  const radPerPx = hfov / 1280;
  const pan = (mv.type === 'drift-h' ? sp * radPerPx * (run - runMid) : 0)
    + (mv.drift ? mv.drift * MEASURE_CAL['drift-h'] * radPerPx * (run - runMid) : 0);   // a push or pull's small sideways drift (T065)
  const tiltA = (mv.type === 'drift-v' || mv.type === 'tilt') ? sp * radPerPx * run : 0;
  const drift = (opts.drift ?? 0) * (k - 0.5);                               // slow sideways drift in metres
  const pos = new THREE.Vector3(Math.sin(yaw) * d, 0, Math.cos(yaw) * d).add(head);
  pos.x += Math.cos(yaw) * drift; pos.z -= Math.sin(yaw) * drift;
  pos.y = c.abs != null ? c.abs + (opts.height ?? 0) : head.y + c.h + (opts.height ?? 0);
  const look = new THREE.Vector3(head.x, head.y - c.aim, head.z);

  if (opts.fx != null && opts.fx !== 0.5) {                                   // the subject off the middle: aim beside it
    const w = 2 * d * Math.tan(THREE.MathUtils.degToRad((opts.fov ?? c.fov) / 2)) * (16 / 9);
    look.x += Math.cos(yaw) * (0.5 - opts.fx) * w; look.z -= Math.sin(yaw) * (0.5 - opts.fx) * w;
  }
  if (c.top) { pos.set(head.x, c.abs, head.z + c.d); look.set(head.x, 0, head.z); }
  if (pan || tiltA) {                                                         // turn the camera about itself
    const dir = look.clone().sub(pos), len = dir.length();
    dir.applyAxisAngle(new THREE.Vector3(0, 1, 0), -pan);
    const horiz = new THREE.Vector3(dir.z, 0, -dir.x).normalize();
    dir.applyAxisAngle(horiz, -tiltA);
    look.copy(pos).add(dir.setLength(len));
  }
  let fov = (opts.fov ?? c.fov);
  if (zoom !== 1) fov = 2 * THREE.MathUtils.radToDeg(Math.atan(Math.tan(THREE.MathUtils.degToRad(fov) / 2) / zoom));
  if (room) {                            // stay inside the walls and under the ceiling: move in, widen the lens
    const d0 = pos.distanceTo(look), s = inside(room, look, pos);
    if (s < 1) {
      pos.lerpVectors(look, pos, s);
      const d1 = pos.distanceTo(look);
      fov = Math.min(80, 2 * THREE.MathUtils.radToDeg(Math.atan(Math.tan(THREE.MathUtils.degToRad(fov) / 2) * d0 / Math.max(d1, 0.3))));
    }
  }
  cam.fov = fov; cam.updateProjectionMatrix();
  cam.position.copy(pos); cam.lookAt(look);
  // focus on the face (0.3 m in front of the head's centre), and a smaller aperture up close, so close-ups stay sharp
  const dh = pos.distanceTo(head);
  const focus = c.soft ? 0.45 : c.target === 'hands' ? dh : Math.max(0.3, dh - 0.3);   // hands: the item itself
  // specs/023: the aperture by shot scale, so the sharp share of the frame lands in the reference's range
  // (template.json → framing.by_scale.<scale>.focused_share); 022 closed it near the camera, which left crowds sharp
  const out = { focus, aper: c.soft ? undefined : (c.aper ?? 4.5) };
  if (c.shoulder) {                                                          // a soft head and shoulder in front, to one side
    const toCam = pos.clone().sub(head).normalize();
    const right = new THREE.Vector3(toCam.z, 0, -toCam.x);
    // a third of the frame on one side, soft (motion-depth §4.11; visual §7.4): further from the lens and to the side
    out.shoulder = pos.clone().add(toCam.clone().multiplyScalar(-1.7)).add(right.multiplyScalar(-1.05 * side));
    out.shoulder.y = head.y - 0.3;
    out.shoulderFacing = Math.atan2(-toCam.x, -toCam.z);
  }
  return out;
}

// specs/027 R6: a real over-the-shoulder shot between two people: the camera stands behind the partner's head and
// to one side (side ±1 keeps the 180° line), looking at the subject's face; the partner's head and shoulder fill a
// soft third of the frame. No stand-in figure is needed. → {focus, aper}
export function otsPair(cam, subject, partner, side = 1, room = null, { back = 0.75, across = 1.05, up = 0.18, fov = 40, aim = 0.2, shift = 0.25, aper = 10 } = {}) {
  const dir = subject.clone().sub(partner); dir.y = 0;
  if (dir.lengthSq() < 1e-6) dir.set(0, 0, 1);
  dir.normalize();
  const right = new THREE.Vector3(dir.z, 0, -dir.x);
  const pos = partner.clone().addScaledVector(dir, -back).addScaledVector(right, across * side);
  pos.y = partner.y + up;
  // aim a little past the subject, away from the partner: the subject sits about two thirds across the frame
  const look = new THREE.Vector3(subject.x, subject.y - aim, subject.z).addScaledVector(right, -shift * side);
  let f = fov;
  if (room) {
    const d0 = pos.distanceTo(look), k = inside(room, look, pos);
    if (k < 1) { pos.lerpVectors(look, pos, k); f = Math.min(80, 2 * THREE.MathUtils.radToDeg(Math.atan(Math.tan(THREE.MathUtils.degToRad(f) / 2) * d0 / Math.max(pos.distanceTo(look), 0.3)))); }
  }
  cam.fov = f; cam.updateProjectionMatrix(); cam.position.copy(pos); cam.lookAt(look);
  // a wide aperture: the partner's head close to the lens goes soft, as the reference's shoulder does
  return { focus: Math.max(0.3, pos.distanceTo(subject) - 0.3), aper };
}

// largest s in [0, 1] so that look + s·(pos − look) stays inside the room (with a margin)
export function inside(room, look, pos, m = 0.15) {
  let s = 1;
  const lim = (p0, p1, lo, hi) => {
    if (lo != null && p1 < lo + m) s = Math.min(s, (lo + m - p0) / (p1 - p0));
    if (hi != null && p1 > hi - m) s = Math.min(s, (hi - m - p0) / (p1 - p0));
  };
  lim(look.x, pos.x, room.x0, room.x1); lim(look.z, pos.z, room.z0, room.z1); lim(look.y, pos.y, null, room.y1);
  return Math.max(0.05, s);
}
