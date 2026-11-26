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
