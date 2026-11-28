"""A family kitchen (specs/040, the what-if style's home set): x -3.5..3.5, y -1.5 (behind the camera) .. 5 (back wall),
2.8 m high. Measured from the reference kitchens: grey-green lower cabinets with panel doors under a light wood counter,
dark teal upper cabinets, a cream plank wall, a window over the sink, a white fridge, a stove, small appliances and jars
on the counter, a dining table with three chairs in the middle of the room, a pendant lamp.
k.objects: "look", "cam_dir", "floor", "walk", "counter" (where a person stands at the counter), "table" (table centre),
"chairs". Layers: fg the table and chairs (when the camera is close), mid the counter run, bg the walls, far the sky."""
import random

from kit import light as lights
from kit import mesh, toon


SOFT = 0.66                                         # the High Contrast look pushes saturation up: colours are mixed toward
                                                   # their grey so a quarter still measures 0.14-0.26 like the reference


def _mat(name, col, **kw):
    r, g, b = (int(col[i:i + 2], 16) for i in (1, 3, 5))
    y = 0.299 * r + 0.587 * g + 0.114 * b
    soft = "#" + "".join("%02x" % max(0, min(255, round(y + (v - y) * SOFT))) for v in (r, g, b))
    return toon.mat(name, soft, **kw)


def build(k, light: str = "day", seed: int = 7):
    random.seed(seed)
    w, d0, d1, h = 3.5, -1.5, 5.0, 2.8
    wall, trim = _mat("kwall", "#efe8d8"), _mat("ktrim", "#b89a78")
    plank = _mat("kplank", "#d9d0bd")
    cab, cabdk = _mat("kcab", "#86a897"), _mat("kcabdk", "#6f9483")
    upper, wood = _mat("kupper", "#5f857a"), _mat("kwood", "#c9925f")
    mesh.box("floor", (0, (d0 + d1) / 2, -0.05), (2 * w, d1 - d0, 0.1), _mat("kfloor", "#dcc29a"))
    for i in range(-6, 7):                                                 # floor tile lines
        mesh.box("tileline", (i * 0.55, (d0 + d1) / 2, 0.002), (0.012, d1 - d0, 0.004), _mat("ktile", "#c8ad84"))
    mesh.box("ceiling", (0, (d0 + d1) / 2, h + 0.05), (2 * w, d1 - d0, 0.1), _mat("kceil", "#f7f2e6"))
    wx0, wx1, wz0, wz1 = 0.15, 1.35, 1.15, 1.95                            # window over the sink
    mesh.box("bw_l", ((-w + wx0) / 2, d1 + 0.05, h / 2), (wx0 + w, 0.1, h), wall, layer="bg")
    mesh.box("bw_r", ((w + wx1) / 2, d1 + 0.05, h / 2), (w - wx1, 0.1, h), wall, layer="bg")
    mesh.box("bw_lo", ((wx0 + wx1) / 2, d1 + 0.05, wz0 / 2), (wx1 - wx0, 0.1, wz0), wall, layer="bg")
    mesh.box("bw_hi", ((wx0 + wx1) / 2, d1 + 0.05, (h + wz1) / 2), (wx1 - wx0, 0.1, h - wz1), wall, layer="bg")
    for z in [0.95 + 0.11 * i for i in range(9)]:                          # cream planks between counter and cabinets
        for x0, x1 in ((-w, wx0), (wx1, w)):
            mesh.box("plankline", ((x0 + x1) / 2, d1 - 0.004, z), (x1 - x0, 0.006, 0.01), plank, layer="bg")
    for cx, cz, sx, sz in (((wx0 + wx1) / 2, wz1 + 0.03, wx1 - wx0 + 0.1, 0.06), ((wx0 + wx1) / 2, wz0 - 0.03, wx1 - wx0 + 0.1, 0.06),
                           (wx0 - 0.03, (wz0 + wz1) / 2, 0.06, wz1 - wz0), (wx1 + 0.03, (wz0 + wz1) / 2, 0.06, wz1 - wz0),
                           ((wx0 + wx1) / 2, (wz0 + wz1) / 2, 0.04, wz1 - wz0)):
        mesh.box("winframe", (cx, d1 - 0.02, cz), (sx, 0.05, sz), _mat("kwin", "#f4f1ea"), outline=0.006, layer="bg")
    mesh.box("sky", (0.75, d1 + 2.0, 1.6), (5, 0.1, 3), _mat("ksky", "#bfe3f2", emit=True), layer="far")
    leaf = _mat("kleaf", "#7cb46a")
    for i in range(4):
        mesh.sphere("tree", (-0.2 + i * 0.6, d1 + 1.5, 1.1 + random.uniform(0, 0.4)), 0.55, leaf, seg=14, layer="far")
    for x in (-w - 0.05, w + 0.05):
        mesh.box("sidewall", (x, (d0 + d1) / 2, h / 2), (0.1, d1 - d0, h), wall, layer="bg")
    mesh.box("frontwall", (0, d0 - 0.05, h / 2), (2 * w, 0.1, h), wall, layer="bg")
    for x, y, sx, sy in ((0, d1 - 0.01, 2 * w, 0.03), (-w + 0.01, (d0 + d1) / 2, 0.03, d1 - d0), (w - 0.01, (d0 + d1) / 2, 0.03, d1 - d0)):
        mesh.box("baseboard", (x, y, 0.05), (sx, sy, 0.1), trim)

    # the counter run along the back wall: lower cabinets with panel doors, a light wood top
    cy, x0, x1 = d1 - 0.32, -w + 0.05, 1.95
    mesh.box("lower", ((x0 + x1) / 2, cy, 0.45), (x1 - x0, 0.6, 0.9), cab, outline=0.01)
    mesh.box("kick", ((x0 + x1) / 2, cy - 0.27, 0.05), (x1 - x0, 0.04, 0.1), cabdk)
    n = int((x1 - x0) / 0.6)
    for i in range(n):
        x = x0 + 0.3 + i * (x1 - x0) / n
        if abs(x - (-0.65)) < 0.35:
            continue                                                       # the oven door goes here
        mesh.box("door", (x, cy - 0.305, 0.5), (0.5, 0.02, 0.7), cabdk, outline=0.006)
        mesh.box("doorpanel", (x, cy - 0.318, 0.5), (0.38, 0.01, 0.56), cab, outline=0.004)
        mesh.tube("knob", (x + 0.17, cy - 0.32, 0.72), (x + 0.17, cy - 0.36, 0.72), 0.015, _mat("kknob", "#3a3f4a"))
    mesh.box("counter", ((x0 + x1) / 2, cy - 0.02, 0.925), (x1 - x0 + 0.04, 0.66, 0.05), wood, outline=0.01, bevel=0.01)
    # upper cabinets (none over the window)
    for ux0, ux1 in ((-w + 0.05, wx0 - 0.1), (wx1 + 0.1, 1.95)):
        mesh.box("upper", ((ux0 + ux1) / 2, d1 - 0.18, 2.3), (ux1 - ux0, 0.34, 0.75), upper, outline=0.01, layer="bg")
        m = max(1, int((ux1 - ux0) / 0.55))
        for i in range(m):
            ux = ux0 + (i + 0.5) * (ux1 - ux0) / m
            mesh.box("updoor", (ux, d1 - 0.355, 2.3), ((ux1 - ux0) / m - 0.06, 0.012, 0.66), _mat("kupdoor", "#557a70"), outline=0.004, layer="bg")
    # stove and oven
    sx = -0.65
    mesh.box("stovetop", (sx, cy - 0.02, 0.955), (0.6, 0.55, 0.015), _mat("kstove", "#2a2d36"), outline=0.006)
    for bx in (-0.14, 0.14):
        for by in (-0.12, 0.12):
            mesh.torus("burner", (sx + bx, cy - 0.02 + by, 0.966), 0.07, 0.01, _mat("kburner", "#5a5f6a"))
    mesh.box("ovendoor", (sx, cy - 0.31, 0.45), (0.56, 0.02, 0.6), _mat("koven", "#3a3f4a"), outline=0.006)
    mesh.box("ovenglass", (sx, cy - 0.322, 0.47), (0.4, 0.01, 0.3), _mat("kglass", "#1f2229"))
    mesh.tube("ovenbar", (sx - 0.22, cy - 0.35, 0.72), (sx + 0.22, cy - 0.35, 0.72), 0.012, _mat("ksteel", "#c9ccd2"))
    mesh.box("hood", (sx, d1 - 0.22, 1.95), (0.7, 0.42, 0.18), _mat("khood", "#c9ccd2"), outline=0.008, layer="bg")
    # sink and tap under the window
    kx = 0.75
    mesh.box("sink", (kx, cy - 0.02, 0.952), (0.6, 0.45, 0.01), _mat("ksink", "#b8bec6"), outline=0.005)
    steel = _mat("ksteel", "#c9ccd2")
    mesh.tube("tap", (kx, d1 - 0.12, 0.95), (kx, d1 - 0.12, 1.18), 0.018, steel)
    mesh.tube("spout", (kx, d1 - 0.12, 1.18), (kx, d1 - 0.3, 1.15), 0.016, steel)
    # small things on the counter
    mesh.box("toaster", (1.55, cy, 1.05), (0.32, 0.2, 0.2), _mat("ktoast", "#d4d7dc"), outline=0.008, bevel=0.03)
    mesh.box("toastslot", (1.55, cy, 1.152), (0.2, 0.04, 0.01), _mat("kslot", "#2a2d36"))
    mesh.box("breadbin", (-2.6, cy, 1.08), (0.5, 0.32, 0.26), _mat("kbin", "#d7774a"), outline=0.01)
    jar = _mat("kjar", "#dfeef2")
    mesh.tube("jar", (-1.55, cy - 0.05, 0.95), (-1.55, cy - 0.05, 1.18), 0.1, jar, outline=0.006)
    mesh.tube("jarlid", (-1.55, cy - 0.05, 1.18), (-1.55, cy - 0.05, 1.22), 0.105, _mat("klid", "#d9443a"), outline=0.005)
    for i in range(3):
        mesh.sphere("cookie", (-1.58 + 0.04 * i, cy - 0.12, 0.99 + 0.03 * (i % 2)), 0.035, _mat("kcookie", "#c08a4a"), scale=(1, 0.4, 1), seg=10)
    mesh.tube("kettle", (-1.1, cy, 0.95), (-1.1, cy, 1.15), 0.1, _mat("kkettle", "#e8604c"), outline=0.008, r2=0.07)
    mesh.sphere("bowl", (-2.05, cy, 0.99), 0.16, _mat("kbowl", "#f4f1ea"), scale=(1, 1, 0.4), outline=0.006, seg=16)
    for dx, col in ((-0.05, "#e8c43a"), (0.06, "#d9443a"), (0.0, "#7cb46a")):
        mesh.sphere("fruit", (-2.05 + dx, cy + dx, 1.05), 0.055, _mat("kfruit" + col[1:], col), seg=10)
    mesh.tube("pot", (wx1 - 0.1, d1 - 0.12, 1.12), (wx1 - 0.1, d1 - 0.12, 1.24), 0.06, _mat("kpot", "#c8643c"), outline=0.005)
    mesh.sphere("herb", (wx1 - 0.1, d1 - 0.12, 1.3), 0.08, leaf, seg=10)
    # the fridge at the end of the run
    fx = 2.55
    mesh.box("fridge", (fx, d1 - 0.38, 0.95), (0.85, 0.72, 1.9), _mat("kfridge", "#eef1f3"), outline=0.012, bevel=0.03)
    mesh.box("fridgeline", (fx, d1 - 0.745, 1.25), (0.84, 0.01, 0.012), _mat("kfline", "#b8bec6"))
    for z0, z1 in ((0.75, 1.1), (1.4, 1.65)):
        mesh.tube("fhandle", (fx - 0.32, d1 - 0.76, z0), (fx - 0.32, d1 - 0.76, z1), 0.015, steel)
    for i, col in enumerate(("#f2c230", "#5bb07a", "#2f6fd0")):
        mesh.box("magnet", (fx - 0.1 + 0.12 * i, d1 - 0.75, 1.5 - 0.08 * i), (0.08, 0.01, 0.1), _mat("kmag" + col[1:], col))
    # dining table and chairs
    tx, ty = -0.6, 1.9
    tab = _mat("ktable", "#b5794a")
    mesh.box("tabletop", (tx, ty, 0.74), (1.5, 0.9, 0.05), tab, outline=0.012, bevel=0.01, layer="fg")
    for lx in (-0.68, 0.68):
        for ly in (-0.38, 0.38):
            mesh.box("tableleg", (tx + lx, ty + ly, 0.36), (0.06, 0.06, 0.72), _mat("ktleg", "#8a5a34"), layer="fg")
    mesh.box("placemat", (tx - 0.35, ty - 0.2, 0.77), (0.35, 0.25, 0.005), _mat("kmat", "#e8923a"), layer="fg")
    mesh.tube("cup", (tx + 0.3, ty - 0.15, 0.765), (tx + 0.3, ty - 0.15, 0.86), 0.045, _mat("kcup", "#f4f1ea"), outline=0.004, layer="fg")
    seat = _mat("kseat", "#d9a63a")
    chairs = []
    for cx, cyy, back in ((tx - 0.45, ty + 0.65, 1), (tx + 0.45, ty + 0.65, 1), (tx + 1.05, ty, 0)):
        mesh.box("cseat", (cx, cyy, 0.45), (0.45, 0.42, 0.05), seat, outline=0.008, layer="fg")
        if back:
            mesh.box("cback", (cx, cyy + 0.2, 0.75), (0.45, 0.05, 0.55), seat, outline=0.008, layer="fg")
        else:
            mesh.box("cback", (cx + 0.2, cyy, 0.75), (0.05, 0.45, 0.55), seat, outline=0.008, layer="fg")
        for lx in (-0.19, 0.19):
            for ly in (-0.17, 0.17):
                mesh.box("cleg", (cx + lx, cyy + ly, 0.22), (0.035, 0.035, 0.44), _mat("ktleg", "#8a5a34"), layer="fg")
        chairs.append((cx, cyy))
    mesh.tube("cord", (tx, ty, h), (tx, ty, 2.1), 0.008, _mat("kcord", "#3a3f4a"))
    mesh.tube("pendant", (tx, ty, 2.1), (tx, ty, 1.9), 0.06, _mat("kpend", "#2f6f5f"), r2=0.25, outline=0.006)
    mesh.sphere("bulb", (tx, ty, 1.9), 0.06, _mat("kbulb", "#fff6d8", emit=True), seg=10)
    mesh.box("clock", (-1.9, d1 - 0.03, 2.0), (0.01, 0.01, 0.01), wall, layer="bg")
    mesh.torus("clockrim", (-w + 0.03, 2.6, 1.9), 0.16, 0.02, trim, rot=(0, 1.5708, 0), layer="bg")
    mesh.sphere("clockface", (-w + 0.02, 2.6, 1.9), 0.15, _mat("kclockf", "#fbf6e8"), scale=(0.1, 1, 1), seg=14, layer="bg")
    import bpy
    vs = bpy.context.scene.view_settings                                   # measured on quarter stills: luma 0.64-0.71 at
    vs.exposure = -1.4                                                     # -0.35 against 0.44-0.58 in the reference rooms
    try:
        vs.look = "Very High Contrast"                                     # contrast 0.16 -> the reference 0.17-0.23
    except TypeError:
        pass
    lights.preset(k, light, energy=1.2)
    lights.lamp("AREA", "window", ((wx0 + wx1) / 2, d1 - 0.5, 1.6), (-90, 0, 0), 80, "#fff4dc", size=1.5)
    lights.lamp("AREA", "room", (0, 1.8, h - 0.1), (0, 0, 0), 160, "#fff2dc", size=4)
    k.objects.update({"look": (0.0, d1 - 0.6, 1.1), "cam_dir": (0.0, -1.0, 0.0), "counter": (-0.65, d1 - 1.0, 0.0),
                      "table": (tx, ty, 0.74), "chairs": chairs, "floor": (-w + 0.5, w - 0.6, d0 + 0.3, d1 - 0.8),
                      "walk": [(-2.6, 0.6), (1.2, 3.6)]})
    return k.objects
