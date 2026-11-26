"""k.cam() (specs/038 T025): place and move the camera from the shot plan (size, height, lens, move) or from
explicit points.

Lens: wide 18 mm, normal 35 mm, long 85 mm (36 mm sensor). Height of the lens above the floor: low 0.6 m, eye 1.5 m,
high 3.0 m, top 8 m looking down. Size sets the distance to the subject so the frame holds about this much height at
the subject: ecu 0.3 m, cu 0.6 m, med 1.2 m, wide 3.6 m, huge 9 m, insert 0.35 m. The set gives the subject point and
the side the camera stands on (k.objects["look"], k.objects["cam_dir"]); a shot may pass its own frm/to/look.
Moves are keyed with ease in and out: push/pull 25 % of the distance, pan ±12°, dolly/track a sideways slide of a
fifth of the distance, orbit 30° around the subject, crane up 1.5 m."""
import math

import bpy
from mathutils import Vector

from kit.core import ease_io

LENS = {"wide": 18.0, "normal": 35.0, "long": 85.0}
HEIGHT = {"low": 0.6, "eye": 1.5, "high": 3.0, "top": 8.0}
FRAME_H = {"ecu": 0.3, "cu": 0.6, "med": 1.2, "wide": 3.6, "huge": 9.0, "insert": 0.35}
SENSOR = 36.0


def distance(size: str, lens_mm: float, aspect: float) -> float:
    """Distance at which the frame is FRAME_H[size] metres high (vertical sensor = 36 / aspect)."""
    vfov = 2 * math.atan((SENSOR / aspect) / (2 * lens_mm))
    return FRAME_H.get(size, 1.2) / (2 * math.tan(vfov / 2))


def _look_at(cam, target: Vector, prev=None):
    e = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    if prev is not None:
        e.make_compatible(prev)
    cam.rotation_euler = e
    return e


def _path(move: str, frm: Vector, look: Vector, d: float):
    """(start, end, look_start, look_end) of a move."""
    side = (frm - look).cross(Vector((0, 0, 1)))
    side = side.normalized() if side.length else Vector((1, 0, 0))
    to, l0, l1 = frm.copy(), look.copy(), look.copy()
    if move == "push":
        to = frm.lerp(look, 0.25)
    elif move == "pull":
        to = frm + (frm - look) * 0.25
    elif move in ("dolly", "track"):
        to = frm + side * (d * 0.2)
        l1 = look + side * (d * 0.2) if move == "track" else look
    elif move == "pan":
        r = (look - frm)
        ang = math.radians(12)
        l0 = frm + Vector((r.x * math.cos(-ang) - r.y * math.sin(-ang), r.x * math.sin(-ang) + r.y * math.cos(-ang), r.z))
        l1 = frm + Vector((r.x * math.cos(ang) - r.y * math.sin(ang), r.x * math.sin(ang) + r.y * math.cos(ang), r.z))
    elif move == "orbit":
        v = frm - look
        ang = math.radians(30)
        to = look + Vector((v.x * math.cos(ang) - v.y * math.sin(ang), v.x * math.sin(ang) + v.y * math.cos(ang), v.z))
    elif move == "crane":
        to = frm + Vector((0, 0, 1.5))
    return frm, to, l0, l1


def cam(k, size: str = None, height: str = None, lens=None, move: str = None, frm=None, to=None, look=None,
        dof: bool = False, fstop: float = 2.8, t0: float = 0.0, t1: float = None):
    plan = k.plan or {}
    size = size or plan.get("size") or "med"
    height = height or plan.get("cam_height") or "eye"
    lens_mm = float(lens) if isinstance(lens, (int, float)) else LENS.get(lens or plan.get("lens") or "normal", 35.0)
    move = move or plan.get("move") or "static"
    aspect = k.size[0] / float(k.size[1])
    look = Vector(look or k.objects.get("look") or (0, 0, 1.2))
    d = distance(size, lens_mm, aspect)
    if frm is None:
        cdir = Vector(k.objects.get("cam_dir") or (0, -1, 0))
        cdir.z = 0
        cdir = cdir.normalized() if cdir.length else Vector((0, -1, 0))
        z = HEIGHT.get(height, 1.5)
        flat = math.sqrt(max(0.01, d * d - (z - look.z) ** 2)) if height == "top" else d
        frm = look + cdir * (flat * (0.35 if height == "top" else 1.0))
        frm.z = z
    frm = Vector(frm)
    a, b, l0, l1 = _path(move, frm, look, d) if to is None else (frm, Vector(to), look, look)
    cd = bpy.data.cameras.new("cam")
    cd.lens, cd.sensor_width, cd.sensor_fit = lens_mm, SENSOR, "HORIZONTAL"
    cd.clip_start, cd.clip_end = 0.05, 400
    c = bpy.data.objects.new("cam", cd)
    bpy.context.scene.collection.objects.link(c)
    bpy.context.scene.camera = c
    c.rotation_mode = "XYZ"
    f0 = k.f(t0)
    f1 = k.f(t1) if t1 is not None else k.frames
    prev = None
    steps = 1 if (a - b).length < 1e-6 and (l0 - l1).length < 1e-6 else max(2, (f1 - f0) // 2 + 1)
    for i in range(steps):
        u = i / (steps - 1) if steps > 1 else 0.0
        e = ease_io(u)
        f = f0 + round((f1 - f0) * u)
        c.location = a.lerp(b, e)
        prev = _look_at(c, l0.lerp(l1, e), prev)
        c.keyframe_insert("location", frame=f)
        c.keyframe_insert("rotation_euler", frame=f)
    if dof:
        cd.dof.use_dof = True
        cd.dof.focus_distance = (look - a).length
        cd.dof.aperture_fstop = fstop
    k.objects["camera"] = c
    k.objects["cam_info"] = {"size": size, "height": height, "lens": lens_mm, "move": move, "distance": round(d, 2)}
    return c
