"""Cast cards (specs/038 T042, T045, research R6): characters drawn by their AE rig, placed in the 3D set as upright
cards that turn about their upright axis to the camera, feet on the floor, so they cast shadows and are hidden by
what stands in front of them.

  k.cast("hero", at=(0, -2, 0), face=180, path=[(0, -2, 0), (0, 1, 0)], act=[{"t": 0.5, "pose": "wave"}], height=1.3)
  k.crowd(area=(-6, 2, 6, 10), count=40, actions=["sit", "clap"]) — or seats=True for the set's seats (both: seats
  first, the rest of the count on the area)

face: degrees seen from above, 0 = towards +y, 90 = towards -x. path: walked at an even pace from t0 to t1 (seconds,
default the whole shot). The plan pass (measure) samples every frame; the render pass (build) puts the AE layer
sequences on the cards: <layers>/<char>-<view>/f####.png."""
import math
import os
import random

CARD_W = 1.0            # card width / height: the AE layer comps are square (tools/ae/kit/castlayer.jsx)
FILL = 0.85             # the character's height / the layer's height (CU.LAYER_FILL)
FEET = 0.98             # the feet sit at 98 % of the layer's height from its top (CU.LAYER_FEET)


def _spec(k):
    return k.objects.setdefault("cast_spec", {"chars": {}, "crowd": None})


def cast(k, char: str, at=(0, 0, 0), face: float = 180, path=None, act=None, height: float = 1.3, t0: float = 0,
         t1: float = None):
    if not char or not isinstance(char, str):
        raise ValueError("k.cast needs a character id from the film's cast")
    _spec(k)["chars"][char] = {"at": tuple(at), "face": float(face), "path": [tuple(p) for p in (path or [])],
                               "act": sorted(act or [], key=lambda a: a.get("t", 0)), "height": float(height),
                               "t0": float(t0), "t1": float(t1) if t1 is not None else None}
    k.cards.append({"id": char})
    return char


def crowd(k, area=None, count: int = 20, actions=("sit",), seats: bool = False, seed: int = 3, height: float = 1.2):
    if area is None and not seats:
        raise ValueError("k.crowd needs area=(x0, y0, x1, y1) or seats=True")
    _spec(k)["crowd"] = {"area": tuple(area) if area else None, "count": int(count), "actions": list(actions),
                         "seats": bool(seats), "seed": int(seed), "height": float(height)}


# ---------- where a character is at a frame ----------
def _at(c: dict, t: float, dur: float) -> tuple:
    """(position, facing degrees, walking) at t seconds."""
    p = c["path"]
    if len(p) < 2:
        return c["at"], c["face"], False
    t0, t1 = c["t0"], c["t1"] if c["t1"] is not None else dur
    u = 0.0 if t <= t0 else 1.0 if t >= t1 else (t - t0) / max(1e-6, t1 - t0)
    seg = [math.dist(p[i], p[i + 1]) for i in range(len(p) - 1)]
    total = sum(seg) or 1.0
    d = u * total
    for i, L in enumerate(seg):
        if d <= L or i == len(seg) - 1:
            w = 0 if L == 0 else min(1.0, d / L)
            a, b = p[i], p[i + 1]
            pos = tuple(a[j] + (b[j] - a[j]) * w for j in range(3))
            face = math.degrees(math.atan2(-(b[0] - a[0]), b[1] - a[1]))
            return pos, face, t0 < t < t1
        d -= L
    return p[-1], c["face"], False


def _state(c: dict, t: float) -> dict:
    st = {}
    for a in c["act"]:
        if a.get("t", 0) <= t + 1e-9:
            st.update({k: a[k] for k in ("pose", "expr") if k in a})
    return st


def measure(k) -> dict:
    """Plan pass: {"chars": {id: {"rig": "", "samples": [...]}}, "crowd": {...}|None} (blender/layers.py)."""
    import bpy
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    sc = bpy.context.scene
    cam = sc.camera
    spec = _spec(k)
    res_y = sc.render.resolution_y * sc.render.resolution_percentage / 100 / (0.25 if k.req.get("quarter") else 1)
    dur = k.frames / k.fps
    out = {cid: {"rig": "", "samples": []} for cid in spec["chars"]}
    for f in range(1, k.frames + 1):
        sc.frame_set(f)
        cp = cam.matrix_world.translation
        t = (f - 1) / k.fps
        for cid, c in spec["chars"].items():
            pos, face, walking = _at(c, t, dur)
            fv = Vector((-math.sin(math.radians(face)), math.cos(math.radians(face))))
            to = Vector((cp.x - pos[0], cp.y - pos[1]))
            rel = math.degrees(math.atan2(fv.x * to.y - fv.y * to.x, fv.dot(to))) if to.length else 0.0
            feet = world_to_camera_view(sc, cam, Vector(pos))
            head = world_to_camera_view(sc, cam, Vector((pos[0], pos[1], pos[2] + c["height"])))
            hpx = abs(head.y - feet.y) * res_y if feet.z > 0 and head.z > 0 else 0
            elev = math.degrees(math.atan2(cp.z - (pos[2] + c["height"] / 2), to.length or 1e-6))
            out[cid]["samples"].append({"f": f, "rel": round(rel, 1), "height_px": round(hpx), "elev": round(elev, 1),
                                        "walk": walking, **_state(c, t)})
    return {"chars": out, "crowd": spec["crowd"]}


# ---------- render pass ----------
def _seq(k, name: str, view: str):
    import bpy
    d = os.path.join(k.layers_dir, f"{name}-{view}")
    files = sorted(x for x in os.listdir(d) if x.endswith(".png")) if os.path.isdir(d) else []
    if not files:
        raise ValueError(f"no AE layers for {name} {view} ({d}); run the AE layers pass (sh bin/studio ae build)")
    img = bpy.data.images.load(os.path.join(d, files[0]), check_existing=True)
    img.source = "SEQUENCE"
    return img, len(files)


def _card_mat(name: str, img, frames: int, offset: int = 0, flip: bool = False):
    import bpy
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.image_user.frame_duration = frames
    # Blender adds frame_offset after the cyclic wrap, so an offset runs past the last PNG (missing = magenta);
    # starting the sequence earlier shifts it in time and still wraps
    tex.image_user.frame_offset = 0
    tex.image_user.frame_start = 1 - offset
    tex.image_user.use_auto_refresh = True
    tex.image_user.use_cyclic = True
    tex.interpolation = "Closest"
    emit = nt.nodes.new("ShaderNodeEmission")            # the rig's own colours, as in AE
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    if flip:
        coord = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value[0] = -1
        mp.inputs["Location"].default_value[0] = 1
        nt.links.new(coord.outputs["UV"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], emit.inputs["Color"])
    nt.links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(emit.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    for attr, val in (("blend_method", "BLEND"), ("surface_render_method", "BLENDED"), ("use_transparent_shadow", True),
                      ("shadow_method", "CLIP")):
        if hasattr(m, attr):
            try:
                setattr(m, attr, val)
            except TypeError:
                pass
    return m


def _card(k, name: str, view: str, height: float, offset: int = 0, flip: bool = False):
    import bpy
    img, n = _seq(k, name, view)
    bpy.ops.mesh.primitive_plane_add(size=1)
    ob = bpy.context.active_object
    ob.name = f"card_{name}_{view}{'_flip' if flip else ''}"
    ob.rotation_euler = (math.pi / 2, 0, 0)
    bpy.ops.object.transform_apply(rotation=True)
    hc = height / FILL                                    # the layer is taller than the character (hats, raised arms)
    for v in ob.data.vertices:                             # origin at the feet
        v.co.x *= hc * CARD_W
        v.co.z = (v.co.z + 0.5 - (1 - FEET)) * hc
    ob.data.materials.append(_card_mat(f"m_{name}_{view}", img, n, offset, flip))
    con = ob.constraints.new("LOCKED_TRACK")
    con.target = bpy.context.scene.camera
    con.track_axis = "TRACK_NEGATIVE_Y"
    con.lock_axis = "LOCK_Z"
    ob["cu_layer"] = "mid"
    return ob


def build(k, plan: dict = None):
    """Render pass: one card per (char, view) the layers plan uses, shown only on the frames of its view; the
    character moves along its path; the crowd from the pool, shifted in time and flipped."""
    import bpy
    spec = _spec(k)
    plan = plan or {}
    dur = k.frames / k.fps
    for cid, c in spec["chars"].items():
        cp = next((x for x in plan.get("chars", []) if x["id"] == cid), None) or \
            {"views": ["front"], "track": [{"f": 1, "view": "front", "dir": 1}]}
        # the 3/4 layer is drawn facing right (dir 1); dir -1 shows the same frames on a mirrored card
        cards = {}
        for v in cp["views"]:
            cards[(v, 1)] = _card(k, cid, v, c["height"])
            if v == "34" and any(t.get("dir") == -1 for t in cp["track"] if t["view"] == "34"):
                cards[(v, -1)] = _card(k, cid, v, c["height"], flip=True)
        for f in range(1, k.frames + 1):
            pos, _, _ = _at(c, (f - 1) / k.fps, dur)
            cur = [t for t in cp["track"] if t["f"] <= f][-1:] or cp["track"][:1]
            view = cur[0]["view"] if cur else "front"
            want = (view, cur[0].get("dir", 1) if cur and view == "34" else 1)
            for key, ob in cards.items():
                ob.location = pos
                ob.hide_render = ob.hide_viewport = (key != want)
                ob.keyframe_insert("location", frame=f)
                ob.keyframe_insert("hide_render", frame=f)
                ob.keyframe_insert("hide_viewport", frame=f)
    cr = spec["crowd"]
    pool = (plan.get("crowd") or {}).get("pool") or []
    if cr and pool:
        rnd = random.Random(cr["seed"])
        spots = [s["at"] for s in k.objects.get("seats", [])] if cr["seats"] else []
        if cr["area"] and len(spots) < cr["count"]:      # seats first, the rest of the count on the floor area
            x0, y0, x1, y1 = cr["area"]
            spots += [(rnd.uniform(x0, x1), rnd.uniform(y0, y1), 0.0) for _ in range(cr["count"] - len(spots))]
        for i, at in enumerate(spots[:cr["count"]]):
            ob = _card(k, pool[i % len(pool)], "front", cr["height"], offset=rnd.randrange(0, max(1, k.frames)),
                       flip=bool(rnd.getrandbits(1)))
            ob.location = at
    bpy.context.scene.frame_set(1)
