"""Toon materials and outlines (specs/038 T023), rewritten from the 2026-11-26 Blender test.

mat(): the light on a diffuse surface becomes two tones (a cool shadow tint over the base colour, hard edge) plus a
warm lift where the key light hits, with an optional sharp highlight; everything goes out as emission so EEVEE draws
flat cel colours. outline(): inverted hull, a Solidify shell with flipped normals and a dark back-face material."""
import bpy

from kit.core import hexc

SHADOW_TINT = (0.60, 0.62, 0.80, 1)
OUTLINE_COLOR = "#1d1b2e"
_MATS = {}


def reset() -> None:
    _MATS.clear()


def _ramp(nodes, links, src, stops):
    r = nodes.new("ShaderNodeValToRGB")
    links.new(src, r.inputs[0])
    els = r.color_ramp.elements
    els[0].position, els[0].color = stops[0]
    els[1].position, els[1].color = stops[1]
    return r


def _mix(nodes, links, kind, a, b):
    m = nodes.new("ShaderNodeMix")
    m.data_type, m.blend_type = "RGBA", kind
    m.inputs[0].default_value = 1.0
    links.new(a, m.inputs[6])
    links.new(b, m.inputs[7])
    return m.outputs[2]


def mat(name: str, col: str, spec: float = 0.0, rough: float = 0.5, emit: bool = False, tex: str = None,
        tex_col: str = None, shadow=SHADOW_TINT):
    """A cel material; the same arguments give the same material (shared, cheap)."""
    key = (name, col, spec, rough, emit, tex, tex_col, tuple(shadow))
    m = _MATS.get(key)
    if m is not None and m.name in bpy.data.materials:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    N.clear()
    out = N.new("ShaderNodeOutputMaterial")
    if emit:
        e = N.new("ShaderNodeEmission")
        e.inputs[0].default_value = hexc(col)
        e.inputs[1].default_value = 1.0
        L.new(e.outputs[0], out.inputs[0])
        _MATS[key] = m
        return m
    base = N.new("ShaderNodeRGB")
    base.outputs[0].default_value = hexc(col)
    bc = base.outputs[0]
    if tex == "planks":
        w = N.new("ShaderNodeTexWave")
        w.wave_type, w.bands_direction = "BANDS", "X"
        w.inputs["Scale"].default_value = 0.9
        w.inputs["Distortion"].default_value = 0.0
        cr = _ramp(N, L, w.outputs["Fac"], [(0.0, hexc(col)), (0.93, hexc(tex_col or "#8a5a34"))])
        cr.color_ramp.interpolation = "CONSTANT"
        bc = cr.outputs[0]
    elif tex == "tiles":
        ck = N.new("ShaderNodeTexChecker")
        ck.inputs["Scale"].default_value = 1.0
        tc, mp = N.new("ShaderNodeTexCoord"), N.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (0.8, 0.8, 0.8)
        L.new(tc.outputs["Object"], mp.inputs[0])
        L.new(mp.outputs[0], ck.inputs[0])
        ck.inputs["Color1"].default_value = hexc(col)
        ck.inputs["Color2"].default_value = hexc(tex_col or "#e9e4d8")
        bc = ck.outputs["Color"]
    d, s2r, bw = N.new("ShaderNodeBsdfDiffuse"), N.new("ShaderNodeShaderToRGB"), N.new("ShaderNodeRGBToBW")
    L.new(d.outputs[0], s2r.inputs[0])
    L.new(s2r.outputs[0], bw.inputs[0])
    tones = _ramp(N, L, bw.outputs[0], [(0.10, tuple(shadow)), (0.17, (1, 1, 1, 1))])
    last = _mix(N, L, "MULTIPLY", bc, tones.outputs[0])
    lift = _ramp(N, L, bw.outputs[0], [(0.55, (0, 0, 0, 1)), (0.62, (0.10, 0.07, 0.02, 1))])
    last = _mix(N, L, "ADD", last, lift.outputs[0])
    if spec:
        g, s3, bw2 = N.new("ShaderNodeBsdfGlossy"), N.new("ShaderNodeShaderToRGB"), N.new("ShaderNodeRGBToBW")
        g.inputs["Roughness"].default_value = rough
        L.new(g.outputs[0], s3.inputs[0])
        L.new(s3.outputs[0], bw2.inputs[0])
        hi = _ramp(N, L, bw2.outputs[0], [(0.35, (0, 0, 0, 1)), (0.45, (spec, spec, spec, 1))])
        last = _mix(N, L, "ADD", last, hi.outputs[0])
    e = N.new("ShaderNodeEmission")
    L.new(last, e.inputs[0])
    e.inputs[1].default_value = 1.0
    L.new(e.outputs[0], out.inputs[0])
    _MATS[key] = m
    return m


def outline_mat():
    m = bpy.data.materials.get("cu_outline")
    if m is None:
        m = bpy.data.materials.new("cu_outline")
        m.use_nodes = True
        n = m.node_tree.nodes
        n.clear()
        e, o = n.new("ShaderNodeEmission"), n.new("ShaderNodeOutputMaterial")
        e.inputs["Color"].default_value = hexc(OUTLINE_COLOR)
        m.node_tree.links.new(e.outputs[0], o.inputs[0])
        m.use_backface_culling = True
    return m


def outline(obj, width: float = 0.012) -> None:
    """Inverted hull: a shell `width` thick, normals flipped, drawn with the outline material on its back faces."""
    if width <= 0:
        return
    obj.data.materials.append(outline_mat())
    s = obj.modifiers.new("hull", "SOLIDIFY")
    s.thickness, s.offset, s.use_flip_normals, s.use_rim = width, 1, True, False
    s.material_offset = len(obj.data.materials) - 1
