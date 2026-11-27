"""Effects of the kit (specs/038 T026): k.fx("confetti", t0=1.5, at=(0, 0, 5), area=(8, 6), count=500)."""
import bmesh
import bpy
from mathutils import Vector

from kit import toon

CONFETTI = ["#e84a3c", "#f2c230", "#3b82e0", "#52b865", "#ec6fb0", "#ffffff"]


def confetti(k, t0: float = 0.0, t1: float = None, at=None, area=(8.0, 6.0), count: int = 500, seed: int = 3):
    """Paper bits falling and tumbling from a sheet above `at` (default: above the set's subject)."""
    at = Vector(at or (*(k.objects.get("look") or (0, 0, 1))[:2], 5.0))
    pieces = bpy.data.collections.new("confetti_pieces")
    for i, c in enumerate(CONFETTI):
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.035)
        bmesh.ops.scale(bm, vec=Vector((1.0, 0.55, 1)), verts=bm.verts)
        me = bpy.data.meshes.new(f"cf{i}")
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(f"cf{i}", me)
        o.data.materials.append(toon.mat(f"cf{i}", c, emit=True))
        pieces.objects.link(o)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    me = bpy.data.meshes.new("confetti_emit")
    bm.to_mesh(me)
    bm.free()
    em = bpy.data.objects.new("confetti", me)
    bpy.context.scene.collection.objects.link(em)
    em.location, em.scale = at, (area[0], area[1], 1)
    em["cu_layer"] = "fg"
    ps = em.modifiers.new("cf", "PARTICLE_SYSTEM")
    ps.particle_system.seed = seed
    st = ps.particle_system.settings
    st.count, st.lifetime, st.emit_from = count, 400, "FACE"
    st.frame_start = k.f(t0)
    st.frame_end = k.f(t1) if t1 is not None else min(k.frames, k.f(t0) + int(k.fps * 1.5))
    st.normal_factor, st.factor_random = -0.5, 0.8
    st.render_type, st.instance_collection, st.use_collection_pick_random = "COLLECTION", pieces, True
    st.particle_size, st.size_random = 1.0, 0.4
    st.use_rotations, st.rotation_mode, st.rotation_factor_random, st.phase_factor_random = True, "NONE", 1.0, 2.0
    st.angular_velocity_mode, st.angular_velocity_factor, st.use_dynamic_rotation = "RAND", 10.0, True
    st.effector_weights.gravity, st.brownian_factor, st.drag_factor = 0.1, 0.4, 0.3
    em.show_instancer_for_render = False
    return em


def foam(k, t0: float = 0.0, at=None, count: int = 40, power: float = 3.2, seed: int = 5, col: str = "#e84a3c"):
    """A paper volcano erupting: blobs shoot up from `at` (default the set's volcano), arc under gravity and splat
    on the floor, keyed per frame (no simulation, so every run gives the same frames)."""
    import math
    import random
    from kit import mesh
    rnd = random.Random(seed)
    at = Vector(at or k.objects.get("volcano") or (0, 0, 1))
    mats = [toon.mat("foam0", col), toon.mat("foam1", "#ff8a5c"), toon.mat("foam2", "#fff1e0")]
    f0 = k.f(t0)
    g = 9.8
    for i in range(count):
        r = rnd.uniform(0.05, 0.13)
        o = mesh.sphere(f"foam{i}", tuple(at), r, mats[i % 3], outline=0.006, seg=10, layer="mid")
        a = rnd.uniform(0, 2 * math.pi)
        sp = rnd.uniform(0.3, 1.0) * power * 0.45
        vz = rnd.uniform(0.7, 1.0) * power
        vx, vy = math.cos(a) * sp, math.sin(a) * sp
        start = f0 + rnd.randrange(0, max(1, int(k.fps * 0.6)))
        o.hide_render = True
        o.keyframe_insert("hide_render", frame=max(1, start - 1))
        o.hide_render = False
        o.keyframe_insert("hide_render", frame=start)
        landed = None
        for f in range(start, k.frames + 1, 2):
            t = (f - start) / k.fps
            z = at.z + vz * t - g * t * t / 2
            if z <= r * 0.4:
                if landed is None:
                    landed = (at.x + vx * t, at.y + vy * t)
                o.location = (landed[0], landed[1], r * 0.4)
                o.scale = (1.4, 1.4, 0.4)
            else:
                o.location = (at.x + vx * t, at.y + vy * t, z)
                o.scale = (1, 1, 1)
            o.keyframe_insert("location", frame=f)
            o.keyframe_insert("scale", frame=f)


def ball(k, frm=(0, 0, 1.2), to=(0, 5, 3), t0: float = 0.5, t1: float = 1.2, r: float = 0.11, col: str = "#e05a4f",
         arc: float = 0.8, hide_after: bool = True, hide_before: bool = False, show_from: float | None = None):
    """A thrown ball: held at `frm` until t0, flies on an arc (`arc` metres above the straight line) to `to` by t1,
    gone after t1 when hide_after (it went through the window); hidden until t0 when hide_before (held out of sight),
    or until show_from when given (the hand comes up with it before the throw).
    Keyed per frame."""
    from kit import mesh
    o = mesh.sphere("ball", (0, 0, 0), r, toon.mat("ball", col), outline=0.006, seg=20)
    a, b = Vector(frm), Vector(to)
    f0, f1 = k.f(t0), k.f(t1)
    fs = k.f(show_from) if show_from is not None else f0
    for f in range(1, k.frames + 1):
        u = 0.0 if f <= f0 else 1.0 if f >= f1 else (f - f0) / max(1, f1 - f0)
        o.location = a.lerp(b, u) + Vector((0, 0, arc * 4 * u * (1 - u)))
        o.hide_render = o.hide_viewport = bool((hide_after and f > f1) or (hide_before and f < fs))
        o.keyframe_insert("location", frame=f)
        o.keyframe_insert("hide_render", frame=f)
        o.keyframe_insert("hide_viewport", frame=f)
    return o
