"""Lights and sky of the kit (specs/038 T026): k.light("day"|"dusk"|"night"|"stage") and helpers for sets.

world(): the camera sees `sky`, every surface is lit by a soft ambient `amb` (light path mix), so shadows stay
coloured, never black. A preset is a key sun plus that world; sets add their own practical lights."""
import math

import bpy

from kit.core import hexc

PRESETS = {
    "day":   {"sky": "#9ccff0", "amb": "#fff4e0", "amb_s": 0.35, "sun": "#fff2d6", "energy": 4.0, "rot": (52, 0, 38)},
    "dusk":  {"sky": "#f2a66b", "amb": "#ffd7b0", "amb_s": 0.30, "sun": "#ffb070", "energy": 3.0, "rot": (72, 0, 60)},
    "night": {"sky": "#1d2440", "amb": "#5a6aa0", "amb_s": 0.25, "sun": "#a8b8ff", "energy": 1.2, "rot": (60, 0, -30)},
    "stage": {"sky": "#20141a", "amb": "#ffe6c8", "amb_s": 0.30, "sun": "#fff0d8", "energy": 2.5, "rot": (40, 0, 0)},
}


def lamp(kind: str, name: str, loc, rot, energy: float, col: str = "#ffffff", size: float = 1.0, angle: float = 2.0):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = hexc(col)[:3]
    if kind == "SUN":
        ld.angle = math.radians(angle)
    elif kind == "AREA":
        ld.shape, ld.size, ld.size_y = "RECTANGLE", size, size * 0.6
    else:
        ld.shadow_soft_size = size
    o = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = [math.radians(a) for a in rot]
    return o


def world(sky: str = "#9ccff0", amb: str = "#fff4e0", amb_s: float = 0.35):
    sc = bpy.context.scene
    w = bpy.data.worlds.new("sky")
    sc.world = w
    w.use_nodes = True
    n, ln = w.node_tree.nodes, w.node_tree.links
    n.clear()
    cam_bg, amb_bg = n.new("ShaderNodeBackground"), n.new("ShaderNodeBackground")
    cam_bg.inputs[0].default_value, cam_bg.inputs[1].default_value = hexc(sky), 1.0
    amb_bg.inputs[0].default_value, amb_bg.inputs[1].default_value = hexc(amb), amb_s
    lp, mix, out = n.new("ShaderNodeLightPath"), n.new("ShaderNodeMixShader"), n.new("ShaderNodeOutputWorld")
    ln.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    ln.new(amb_bg.outputs[0], mix.inputs[1])
    ln.new(cam_bg.outputs[0], mix.inputs[2])
    ln.new(mix.outputs[0], out.inputs[0])
    return w


def preset(k, name: str = "day", energy: float = None):
    p = PRESETS.get(name)
    if p is None:
        raise ValueError(f"light must be one of {', '.join(PRESETS)}, not {name!r}")
    world(p["sky"], p["amb"], p["amb_s"])
    sun = lamp("SUN", "key", (0, 0, 10), p["rot"], energy if energy is not None else p["energy"], p["sun"])
    k.objects["light"] = name
    return sun
