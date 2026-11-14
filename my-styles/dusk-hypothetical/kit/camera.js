// Camera placements of the Dusk Hypothetical kit (specs/022 T015), one per entry of catalog.json "cams", each
// matching a shot scale and angle of shots.json. The camera sits slightly oblique to the subject (proof round 9),
// focus is on the subject's head, and the over-shoulder framing asks for a soft head and shoulder in front.
import * as THREE from 'three';

// d: distance from the subject's head; h: camera height relative to the head (or absolute with abs); yaw: degrees
// off the subject's facing; aim: look-at offset below the head; fov: degrees
export const CAMS = {
  ecu:         { d: 0.78, h: 0.02, yaw: 10, aim: 0.0, fov: 34 },
  close:       { d: 1.6, h: 0.0, yaw: 18, aim: 0.12, fov: 40 },
  'mid-eye':   { d: 2.8, h: -0.15, yaw: 24, aim: 0.32, fov: 45 },
  'mid-low':   { d: 2.4, abs: 0.55, yaw: 20, aim: 0.3, fov: 48 },
  ots:         { d: 2.5, h: 0.05, yaw: 12, aim: 0.35, fov: 44, shoulder: true },
  'wide-eye':  { d: 6.2, h: -0.25, yaw: 22, aim: 0.75, fov: 50 },
  'wide-high': { d: 6.0, abs: 4.2, yaw: 24, aim: 0.8, fov: 50 },
  'very-wide': { d: 15, h: 0.15, yaw: 14, aim: 0.6, fov: 55 },
  'huge-high': { d: 17, abs: 10, yaw: 18, aim: 0.6, fov: 55 },
  top:         { d: 0.6, abs: 15, yaw: 0, aim: 0.6, fov: 50, top: true },
  insert:      { d: 3.2, h: -0.2, yaw: 18, aim: 0.5, fov: 45, soft: true },
};

// head: world position of the subject's head centre; facing: the subject's yaw (radians, 0 = facing +z)
// opts (from the scene's cam object): {yaw, dist, height, side, drift, push} → returns {focus, shoulder?}
export function place(cam, name, head, facing = 0, opts = {}, k = 0, room = null) {
  const c = CAMS[name]; if (!c) throw new Error(`unknown cam "${name}"`);
  const side = opts.side ?? 1;
  const yaw = facing + side * THREE.MathUtils.degToRad(opts.yaw ?? c.yaw);
  let d = c.d * (opts.dist ?? 1) * (1 - (opts.push ?? 0) * k);             // slow push-in over the shot (0–0.1)
  const drift = (opts.drift ?? 0) * (k - 0.5);                               // slow sideways drift in metres
  const pos = new THREE.Vector3(Math.sin(yaw) * d, 0, Math.cos(yaw) * d).add(head);
  pos.x += Math.cos(yaw) * drift; pos.z -= Math.sin(yaw) * drift;
  pos.y = c.abs != null ? c.abs + (opts.height ?? 0) : head.y + c.h + (opts.height ?? 0);
  const look = new THREE.Vector3(head.x, head.y - c.aim, head.z);
  if (c.top) { pos.set(head.x, c.abs, head.z + c.d); look.set(head.x, 0, head.z); }
  let fov = opts.fov ?? c.fov;
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
  const focus = c.soft ? 0.45 : Math.max(0.3, dh - 0.3);
  const out = { focus, aper: c.soft ? undefined : 4.5 * Math.min(1, dh / 3) };
  if (c.shoulder) {                                                          // a soft head and shoulder in front, to one side
    const toCam = pos.clone().sub(head).normalize();
    const right = new THREE.Vector3(toCam.z, 0, -toCam.x);
    out.shoulder = pos.clone().add(toCam.clone().multiplyScalar(-0.9)).add(right.multiplyScalar(-0.55 * side));
    out.shoulder.y = head.y - 0.3;
    out.shoulderFacing = Math.atan2(-toCam.x, -toCam.z);
  }
  return out;
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
