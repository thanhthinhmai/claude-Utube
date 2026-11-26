"""Mesh helpers of the kit (specs/038 T024): box, plane, sphere, tube, torus, arc, join. Every object can carry the
depth layer it belongs to (fg, mid, bg, far), read by the depth check and by k.fg()."""
import math

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

from kit import toon

LAYER_KEY = "cu_layer"


def _link(o, layer: str = "mid"):
    bpy.context.scene.collection.objects.link(o)
    o[LAYER_KEY] = layer
    return o


def from_bm(name: str, bm, m, outline: float = 0.0, smooth: bool = True, layer: str = "mid"):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    o = _link(bpy.data.objects.new(name, me), layer)
    if m is not None:
        o.data.materials.append(m)
    toon.outline(o, outline)
    return o


def box(name, c, size, m, outline: float = 0.0, bevel: float = 0.0, smooth: bool = False, layer: str = "mid", rot=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    if bevel:
        bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=bevel, segments=3, affect="EDGES")
    if rot:
        bmesh.ops.rotate(bm, cent=Vector((0, 0, 0)), matrix=Euler(rot).to_matrix(), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(c), verts=bm.verts)
    return from_bm(name, bm, m, outline, smooth=smooth, layer=layer)


def plane(name, c, size, m, rot=(0, 0, 0), layer: str = "mid"):
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bmesh.ops.scale(bm, vec=Vector((size[0], size[1], 1)), verts=bm.verts)
    bmesh.ops.rotate(bm, cent=Vector((0, 0, 0)), matrix=Euler(rot).to_matrix(), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(c), verts=bm.verts)
    return from_bm(name, bm, m, smooth=False, layer=layer)


def sphere(name, c, r, m, scale=(1, 1, 1), outline: float = 0.0, seg: int = 24, layer: str = "mid"):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(6, seg // 2), radius=r)
    bmesh.ops.scale(bm, vec=Vector(scale), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(c), verts=bm.verts)
    return from_bm(name, bm, m, outline, layer=layer)


def tube(name, a, b, r, m, outline: float = 0.0, caps: bool = True, r2: float = None, seg: int = 16, layer: str = "mid"):
    """A cylinder (capsule when caps) from a to b."""
    a, b = Vector(a), Vector(b)
    d = b - a
    length = d.length
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r2 or r, depth=length)
    bmesh.ops.translate(bm, vec=Vector((0, 0, length / 2)), verts=bm.verts)
    if caps:
        for z, rr in ((0, r), (length, r2 or r)):
            bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(6, seg // 2), radius=rr,
                                      matrix=Matrix.Translation((0, 0, z)))
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    bmesh.ops.rotate(bm, cent=Vector((0, 0, 0)), matrix=q.to_matrix(), verts=bm.verts)
    bmesh.ops.translate(bm, vec=a, verts=bm.verts)
    return from_bm(name, bm, m, outline, layer=layer)


def torus(name, c, R, r, m, rot=(0, 0, 0), outline: float = 0.0, segs: int = 32, rs: int = 12, layer: str = "mid"):
    bm = bmesh.new()
    rows = []
    for i in range(segs):
        th = 2 * math.pi * i / segs
        rows.append([bm.verts.new(((R + r * math.cos(2 * math.pi * j / rs)) * math.cos(th),
                                   (R + r * math.cos(2 * math.pi * j / rs)) * math.sin(th),
                                   r * math.sin(2 * math.pi * j / rs))) for j in range(rs)])
    for i in range(segs):
        for j in range(rs):
            bm.faces.new((rows[i][j], rows[(i + 1) % segs][j], rows[(i + 1) % segs][(j + 1) % rs], rows[i][(j + 1) % rs]))
    bmesh.ops.rotate(bm, cent=Vector((0, 0, 0)), matrix=Euler(rot).to_matrix(), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(c), verts=bm.verts)
    return from_bm(name, bm, m, outline, layer=layer)


def arc(name, center, rad, a0, a1, thick, m, layer: str = "mid"):
    """A curved stroke on the XZ plane (squiggles, smiles)."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions, cu.bevel_depth, cu.bevel_resolution = "3D", thick, 3
    sp = cu.splines.new("POLY")
    n = 10
    sp.points.add(n - 1)
    for i in range(n):
        a = a0 + (a1 - a0) * i / (n - 1)
        sp.points[i].co = (center[0] + rad * math.cos(a), center[1], center[2] + rad * math.sin(a), 1)
    o = _link(bpy.data.objects.new(name, cu), layer)
    o.data.materials.append(m)
    return o


def join(objs: list, name: str = None):
    """Join objects into the first one (fewer objects render faster)."""
    objs = [o for o in objs if o is not None]
    if len(objs) < 2:
        return objs[0] if objs else None
    with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=objs, object=objs[0]):
        bpy.ops.object.join()
    if name:
        objs[0].name = name
    return objs[0]
