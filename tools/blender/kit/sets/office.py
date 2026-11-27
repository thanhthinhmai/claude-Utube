"""The judges' office (charisma shot match): x -4..4, y -1.5 (door wall, behind the camera) .. 7 (back wall), 3 m high.
A wide window with blinds and trees outside on the back wall, framed certificates and a clock, a desk at y 5.2 with
a desk lamp, a photo, papers, a name plate and a fish tank; a flag by the window; a tall chair behind it (the judge stands at k.objects["judge"]);
two visitor chairs in front (k.objects["chairs"]); a bookshelf on the left wall, a filing cabinet and a picture on
the right, a plant in the corner, a rug.
Layers: fg the visitor chairs (when the camera is close), mid the desk and the judge, bg the walls, far the trees."""
import math
import random

import bpy
from mathutils import Matrix, Vector

from kit import light as lights
from kit import mesh, toon

BOOKS = ["#d9443a", "#2f6fd0", "#f2c230", "#5bb07a", "#8a7ad8", "#e8923a", "#3a3f4a"]


def _swim(k, fo, ft, tx, ty, wm):
    """The tank lives (measured 2026-11-27: the reference's fish swims and bubbles rise in every office shot): the fish
    swims side to side and turns at each end, three bubbles rise and start again."""
    c = Vector((tx - 0.02, ty - 0.134, 1.02))                    # mesh helpers bake world positions: origin to the fish
    fo.data.transform(Matrix.Translation(-c)); fo.location = c
    bpy.context.view_layer.update()
    ft.parent = fo
    ft.matrix_parent_inverse = fo.matrix_world.inverted()
    fps, n = float(getattr(k, "fps", 30) or 30), int(getattr(k, "frames", 0) or 400)   # keyed every frame
    x0, z0, sx = fo.location.x, fo.location.z, fo.scale.x
    for f in range(0, n + 2):
        t = f / float(fps)
        fo.location.x = x0 + 0.15 * math.sin(t * 1.9)
        fo.location.z = z0 + 0.025 * math.sin(t * 4.1)
        fo.scale.x = sx * (1 if math.cos(t * 1.9) >= 0 else -1)
        fo.keyframe_insert("location", frame=f)
        fo.keyframe_insert("scale", frame=f)
    bub = []
    for i in range(3):
        bub.append(mesh.sphere("bubble", (tx - 0.16 + 0.03 * i, ty - 0.134, 0.9), 0.008 + 0.003 * i, wm, seg=8))
    for f in range(0, n + 2):
        t = f / float(fps)
        for i, b in enumerate(bub):
            u = (t * 0.45 + i / 3.0) % 1.0
            b.location.z = 0.2 * u - 0.02                          # offsets from where the bubble was made
            b.location.x = 0.006 * math.sin(t * 6 + i)
            b.keyframe_insert("location", frame=f)


def build(k, light: str = "day", seed: int = 7):
    random.seed(seed)
    w, d0, d1, h = 4.0, -1.5, 7.0, 3.0
    wall, wains, trim = toon.mat("owall", "#eadfca"), toon.mat("owains", "#9a6a44"), toon.mat("otrim", "#6b4a32")
    mesh.box("floor", (0, (d0 + d1) / 2, -0.05), (2 * w, d1 - d0, 0.1), toon.mat("ocarpet", "#5f7fb0"))
    mesh.box("rug", (0, 3.8, 0.004), (3.6, 3.0, 0.01), toon.mat("orug", "#a8423a"))
    mesh.box("rugedge", (0, 3.8, 0.002), (3.9, 3.3, 0.008), toon.mat("orugedge", "#e2b443"))
    mesh.box("ceiling", (0, (d0 + d1) / 2, h + 0.05), (2 * w, d1 - d0, 0.1), toon.mat("oceil", "#f6f0e2"))
    mesh.sphere("ceilinglamp", (0, 3.0, h - 0.05), 0.5, toon.mat("olamp", "#fffbe8", emit=True), scale=(0.6, 0.6, 0.08), seg=16)
    wx0, wx1, wz0, wz1 = -1.7, 1.7, 1.0, 2.5                               # the window in the back wall
    mesh.box("bw_l", ((-w + wx0) / 2, d1 + 0.05, h / 2), (wx0 + w, 0.1, h), wall, layer="bg")
    mesh.box("bw_r", ((w + wx1) / 2, d1 + 0.05, h / 2), (w - wx1, 0.1, h), wall, layer="bg")
    mesh.box("bw_lo", (0, d1 + 0.05, wz0 / 2), (wx1 - wx0, 0.1, wz0), wall, layer="bg")
    mesh.box("bw_hi", (0, d1 + 0.05, (h + wz1) / 2), (wx1 - wx0, 0.1, h - wz1), wall, layer="bg")
    for cx, cz, sx, sz in ((0, wz1 + 0.03, wx1 - wx0 + 0.12, 0.06), (0, wz0 - 0.03, wx1 - wx0 + 0.12, 0.06),
                           (wx0 - 0.03, (wz0 + wz1) / 2, 0.06, wz1 - wz0), (wx1 + 0.03, (wz0 + wz1) / 2, 0.06, wz1 - wz0)):
        mesh.box("winframe", (cx, d1 - 0.02, cz), (sx, 0.06, sz), trim, outline=0.008, layer="bg")   # a border: the
        # blinds' gaps show the trees, not a solid board
    slat = toon.mat("oslat", "#f4f1ea")
    n = 16
    for i in range(n):                                                     # blinds, half open: gaps show the trees
        z = wz0 + 0.05 + i * (wz1 - wz0 - 0.1) / (n - 1)
        mesh.box("slat", (0, d1 - 0.07, z), (wx1 - wx0 - 0.04, 0.02, 0.075), slat, layer="bg")
    mesh.box("sky", (0, d1 + 2.5, 1.8), (8, 0.1, 4), toon.mat("osky", "#bfe3f2", emit=True), layer="far")
    leaf = toon.mat("oleaf", "#6aa85a")
    for i in range(7):
        mesh.sphere("tree", (-2.4 + i * 0.8, d1 + 1.8, 1.5 + random.uniform(0, 0.6)), 0.7, leaf, seg=14, layer="far")
    for x in (-w - 0.05, w + 0.05):
        mesh.box("sidewall", (x, (d0 + d1) / 2, h / 2), (0.1, d1 - d0, h), wall, layer="bg")
    for x, y, sx, sy in ((0, d1 - 0.01, 2 * w, 0.03), (-w + 0.01, 2.75, 0.03, d1 - d0), (w - 0.01, 2.75, 0.03, d1 - d0)):
        mesh.box("baseboard", (x, y, 0.06), (sx, sy, 0.12), trim)
    for x, y, sx, sy in ((0, d1 - 0.012, 2 * w, 0.024), (-w + 0.012, 2.75, 0.024, d1 - d0), (w - 0.012, 2.75, 0.024, d1 - d0)):
        mesh.box("wainscot", (x, y, 0.42), (sx, sy, 0.84), wains, layer="bg")            # wood below the rail, as in AE
        mesh.box("rail", (x, y, 0.86), (sx + (0.02 if sx > sy else 0), sy + (0.02 if sy > sx else 0), 0.05), trim, layer="bg")
    mesh.box("frontwall", (0, d0 - 0.05, h / 2), (2 * w, 0.1, h), wall, layer="bg")
    paper, gold = toon.mat("ocert", "#fbf6e8"), toon.mat("ogold", "#d9a63a")
    for x, z in ((-2.7, 2.15), (-2.7, 1.55), (3.2, 2.15)):                  # certificates
        mesh.box("certframe", (x, d1 - 0.02, z), (0.55, 0.03, 0.42), trim, outline=0.006, layer="bg")
        mesh.box("cert", (x, d1 - 0.04, z), (0.45, 0.02, 0.32), paper, layer="bg")
        mesh.sphere("seal", (x + 0.12, d1 - 0.05, z - 0.08), 0.04, gold, scale=(1, 0.3, 1), seg=10, layer="bg")
    mesh.torus("clock", (0, d1 - 0.03, 2.75), 0.14, 0.02, trim, rot=(1.5708, 0, 0), layer="bg")
    mesh.sphere("clockface", (0, d1 - 0.02, 2.75), 0.13, paper, scale=(1, 0.1, 1), seg=14, layer="bg")
    shelf = toon.mat("oshelf", "#7a5434")                                  # bookshelf on the left wall
    sx, sy = -w + 0.2, 4.5
    mesh.box("shelfback", (-w + 0.03, sy, 1.0), (0.06, 1.4, 2.0), shelf)
    for s in (-1, 1):
        mesh.box("shelfside", (sx, sy + s * 0.71, 1.0), (0.36, 0.04, 2.0), shelf, outline=0.01)
    for j in range(5):
        z = 0.1 + j * 0.45
        mesh.box("shelfboard", (sx + 0.02, sy, z), (0.36, 1.4, 0.04), shelf)
        if j < 4:
            y = sy - 0.6
            while y < sy + 0.6:
                bw = random.uniform(0.05, 0.1)
                bh = random.uniform(0.28, 0.38)
                mesh.box("book", (sx + 0.05, y + bw / 2, z + 0.02 + bh / 2), (0.24, bw, bh),
                         toon.mat(f"obook{random.randrange(7)}", BOOKS[random.randrange(7)]))
                y += bw + 0.01
    mesh.box("cabinet", (w - 0.35, 5.8, 0.65), (0.5, 0.6, 1.3), toon.mat("ocab", "#8a9099"), outline=0.01)
    for z in (0.35, 0.8, 1.15):
        mesh.box("drawer", (w - 0.62, 5.8, z), (0.02, 0.3, 0.04), toon.mat("ohandle", "#4a4f58"))
    mesh.box("picframe", (w - 0.02, 3.0, 1.9), (0.04, 1.1, 0.75), trim, outline=0.006, layer="bg")
    mesh.box("picture", (w - 0.05, 3.0, 1.9), (0.02, 0.95, 0.6), toon.mat("opic", "#9fd0e8"), layer="bg")
    mesh.box("pichill", (w - 0.06, 3.0, 1.72), (0.02, 0.95, 0.22), toon.mat("ohill", "#6aa85a"), layer="bg")
    mesh.tube("pot", (-w + 0.5, 6.4, 0), (-w + 0.5, 6.4, 0.4), 0.18, toon.mat("opot", "#c8643c"), outline=0.01,
              r2=0.22, caps=False)
    for dx, dz, r in ((0, 0.75, 0.3), (-0.15, 0.95, 0.22), (0.18, 0.9, 0.2)):
        mesh.sphere("plant", (-w + 0.5 + dx, 6.4, dz), r, leaf, outline=0.01, seg=14)
    desk, top = toon.mat("odesk", "#8a5a34"), toon.mat("odesktop", "#a8754a")   # the desk
    dx, dy = 0.0, 5.2
    mesh.box("desktop", (dx, dy, 0.76), (2.2, 0.9, 0.06), top, outline=0.012, bevel=0.01)
    mesh.box("deskfront", (dx, dy - 0.4, 0.38), (2.2, 0.06, 0.74), desk, outline=0.01)
    for s in (-1, 1):
        mesh.box("deskside", (dx + s * 1.07, dy, 0.38), (0.06, 0.9, 0.74), desk)
    mesh.box("chairback", (dx, dy + 0.85, 1.05), (0.75, 0.12, 1.3), toon.mat("ochair", "#6a2e2e"), outline=0.012, bevel=0.05,
             layer="bg")
    mesh.box("paper", (dx - 0.35, dy - 0.15, 0.8), (0.3, 0.22, 0.005), paper)
    mesh.box("paper2", (dx - 0.32, dy - 0.12, 0.802), (0.3, 0.22, 0.005), toon.mat("opink", "#f4c6d0"))
    mesh.box("nameplate", (dx + 0.2, dy - 0.35, 0.82), (0.5, 0.06, 0.08), toon.mat("oplate", "#2a2d36"), outline=0.005)
    mesh.box("platestripe", (dx + 0.2, dy - 0.385, 0.82), (0.4, 0.005, 0.03), gold)
    mesh.tube("lampstem", (dx - 0.85, dy + 0.1, 0.79), (dx - 0.85, dy + 0.1, 1.15), 0.015, toon.mat("olampst", "#5a8a5a"))
    mesh.tube("lampshade", (dx - 0.85, dy, 1.1), (dx - 0.85, dy - 0.05, 1.2), 0.17, toon.mat("oshade", "#5a8a5a"), r2=0.05,
              outline=0.008)
    dark = toon.mat("otank", "#2a2d36")                                    # fish tank (right of the desk)
    tx, ty = dx + 0.72, dy + 0.02
    mesh.box("tankbase", (tx, ty, 0.81), (0.56, 0.3, 0.04), dark, outline=0.006)
    mesh.box("tanklid", (tx, ty, 1.13), (0.56, 0.3, 0.04), dark, outline=0.006)
    mesh.box("tankwater", (tx, ty, 0.97), (0.52, 0.26, 0.28), toon.mat("owater", "#9fd6f0", emit=True), outline=0.004)
    mesh.box("gravel", (tx, ty - 0.131, 0.855), (0.5, 0.005, 0.05), toon.mat("ogravel", "#c9a07a"))
    weed = toon.mat("oweed", "#4f9a50")
    for wx in (-0.18, -0.12, 0.17):
        mesh.box("weed", (tx + wx, ty - 0.132, 0.95), (0.025, 0.005, 0.16), weed)
    mesh.box("castle", (tx + 0.08, ty - 0.132, 0.92), (0.08, 0.005, 0.1), toon.mat("ocastle", "#a89ac8"))
    fish = toon.mat("ofish", "#f08a2a")
    wm = toon.mat("obubble", "#e8f6ff", emit=True)
    fo = mesh.sphere("fish", (tx - 0.02, ty - 0.134, 1.02), 0.05, fish, scale=(1.2, 0.1, 0.8), seg=12)
    ft = mesh.box("fishtail", (tx + 0.05, ty - 0.134, 1.02), (0.04, 0.005, 0.06), fish, rot=(0, 0.785, 0))
    _swim(k, fo, ft, tx, ty, wm)
    mesh.box("photo", (dx - 0.62, dy - 0.1, 0.89), (0.16, 0.02, 0.2), gold, outline=0.005, rot=(0.2, 0, 0.3))   # photo
    mesh.box("photopic", (dx - 0.62, dy - 0.112, 0.89), (0.12, 0.005, 0.15), toon.mat("ophoto", "#9fd0e8"), rot=(0.2, 0, 0.3))
    pole = toon.mat("opole", "#c9a24a")                                      # flag right of the window
    fx = 1.95
    mesh.tube("flagpole", (fx, d1 - 0.25, 0), (fx, d1 - 0.25, 2.6), 0.02, pole)
    mesh.sphere("flagtop", (fx, d1 - 0.25, 2.63), 0.04, pole, seg=10)
    for i in range(7):
        mesh.box("flagstripe", (fx + 0.33, d1 - 0.25, 2.5 - i * 0.07), (0.62, 0.01, 0.07),
                 toon.mat("ored" if i % 2 == 0 else "owhite", "#c8443c" if i % 2 == 0 else "#ffffff"))
    mesh.box("flagcanton", (fx + 0.16, d1 - 0.26, 2.39), (0.28, 0.01, 0.28), toon.mat("oblue", "#2f4a8a"))
    seat = toon.mat("ovisit", "#8a2e34")
    chairs = []
    for s in (-1, 1):                                                      # visitor chairs
        cx, cy = s * 0.8, 4.05
        mesh.box("vseat", (cx, cy, 0.45), (0.55, 0.5, 0.08), seat, outline=0.01, bevel=0.02)
        mesh.box("vback", (cx, cy - 0.25, 0.85), (0.55, 0.08, 0.75), seat, outline=0.01, bevel=0.03)
        for lx in (-0.22, 0.22):
            for ly in (-0.2, 0.2):
                mesh.box("vleg", (cx + lx, cy + ly, 0.2), (0.04, 0.04, 0.4), trim)
        chairs.append((cx, cy))
    import bpy
    bpy.context.scene.view_settings.exposure = -0.35                     # measured: the toon walls came out 5-12 points
    # brighter than the reference (HSV value) while the AE shots matched
    lights.preset(k, light, energy=1.2)                                   # indoors: a weak sun
    lights.lamp("AREA", "window", (0, d1 - 0.5, 1.8), (-90, 0, 0), 100, "#fff4dc", size=3)
    lights.lamp("AREA", "room", (0, 2.5, h - 0.1), (0, 0, 0), 140, "#fff2dc", size=4)
    k.objects.update({"look": (dx, dy + 0.4, 1.2), "cam_dir": (0.0, -1.0, 0.0), "judge": (dx, dy + 0.45, 0.0),
                      "chairs": chairs, "floor": (-w + 0.6, w - 0.8, d0 + 0.3, 4.4),
                      "walk": [(-1.6, 0.0), (-0.6, 3.5)]})
    return k.objects
