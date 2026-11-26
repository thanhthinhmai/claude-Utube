"""Foreground occluders (specs/038 T026, US2): k.fg("seat_backs"|"door_frame"|"plant"|"lockers"|"desk_edge").

A thing between the camera and the subject gives the frame a foreground layer, like the reference films do. Each
occluder is placed on the camera's line to the subject, at `near` of the way (default 0.25), off to one side, so it
frames the subject instead of hiding it. Call it after k.cam()."""
from mathutils import Vector

from kit import mesh, toon

KINDS = ("seat_backs", "door_frame", "plant", "lockers", "desk_edge")


def _anchor(k, near: float):
    """Point on the camera's line to the subject at `near` of the way, the right vector, and the half width of the
    frame there (from the lens), so occluders sit at the frame's edge whatever the shot size."""
    cam = k.objects.get("camera")
    if cam is None:
        raise ValueError("k.fg needs the camera first: call k.cam(...) before k.fg(...)")
    import bpy
    sc = bpy.context.scene
    sc.frame_set(sc.frame_start)                      # a moving camera: frame from where the shot starts
    look = Vector(k.objects.get("look") or (0, 0, 1.2))
    c = cam.matrix_world.translation.copy()
    p = c.lerp(look, near)
    right = (look - c).cross(Vector((0, 0, 1)))
    right = right.normalized() if right.length else Vector((1, 0, 0))
    half = (look - c).length * near * (cam.data.sensor_width / 2) / cam.data.lens
    return p, right, half


def fg(k, name: str, near: float = 0.3, side: int = 1, color: str = None):
    """side: 1 right edge, -1 left edge (single things); seat_backs, door_frame and desk_edge frame both sides."""
    if name not in KINDS:
        raise ValueError(f"k.fg takes one of {', '.join(KINDS)}, not {name!r}")
    p, right, half = _anchor(k, near)
    sd = 1 if side >= 0 else -1
    objs = []
    if name == "seat_backs":
        m = toon.mat("fg_seat", color or "#a8323a")
        for i in (-1, 1):
            c = p + right * (i * half * 0.62)
            objs.append(mesh.box("fg_seat", (c.x, c.y, 0.5), (half * 0.9, 0.12, 0.8), m, outline=0.015, bevel=0.03, layer="fg"))
    elif name == "door_frame":
        m = toon.mat("fg_frame", color or "#6b4a32")
        for i in (-1, 1):
            c = p + right * (i * half * 0.88)
            objs.append(mesh.box("fg_jamb", (c.x, c.y, 1.3), (half * 0.12, 0.18, 2.6), m, outline=0.012, layer="fg"))
        objs.append(mesh.box("fg_lintel", (p.x, p.y, 2.55), (half * 2, 0.18, 0.2), m, outline=0.012, layer="fg"))
    elif name == "plant":
        c = p + right * (sd * half * 0.82)
        objs.append(mesh.tube("fg_pot", (c.x, c.y, 0), (c.x, c.y, 0.5), 0.22, toon.mat("fg_pot", "#c8643c"),
                              outline=0.012, caps=False, r2=0.28, layer="fg"))
        leaf = toon.mat("fg_leaf", color or "#4f9a3e")
        for dx, dz, r in ((0, 0.9, 0.38), (-0.2, 1.15, 0.3), (0.22, 1.1, 0.28)):
            objs.append(mesh.sphere("fg_leaf", (c.x + dx, c.y, dz), r, leaf, outline=0.012, seg=16, layer="fg"))
    elif name == "lockers":
        m = toon.mat("fg_locker", color or "#3f7fc9")
        c = p + right * (sd * half * 0.92)
        objs.append(mesh.box("fg_locker", (c.x, c.y, 0.98), (min(0.55, half * 0.3), 0.55, 1.95), m, outline=0.012, layer="fg"))
    elif name == "desk_edge":
        m = toon.mat("fg_desk", color or "#d9a35c")
        objs.append(mesh.box("fg_desk", (p.x, p.y, 0.74), (half * 2.2, 0.6, 0.06), m, outline=0.012, bevel=0.015, layer="fg"))
    k.objects.setdefault("fg", []).extend(objs)
    return objs
