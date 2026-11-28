"""A family living room (specs/040, the what-if style's home set): x -3.8..3.8, y -1.5 (behind the camera) .. 5.5 (back
wall), 2.8 m high. Measured from the reference living rooms: cream wallpaper with a small repeating motif, framed
pictures, a window with curtains and the street outside (a tree, house roofs), a sofa with cushions, a coffee table on
a rug, a TV on a low cabinet, a side table with a lamp, a tall plant, a bookshelf, wood floor with a baseboard.
k.objects: "look", "cam_dir", "floor", "walk", "sofa" (seat centre), "tv" (screen centre). Layers: fg the coffee table
(when the camera is close), mid the sofa, TV and lamp, bg the walls, far the street."""
import random

from kit import light as lights
from kit import mesh, toon


SOFT = 0.5                                          # the High Contrast look pushes saturation up: colours are mixed toward
                                                   # their grey so a quarter still measures 0.14-0.26 like the reference


def _mat(name, col, **kw):
    r, g, b = (int(col[i:i + 2], 16) for i in (1, 3, 5))
    y = 0.299 * r + 0.587 * g + 0.114 * b
    soft = "#" + "".join("%02x" % max(0, min(255, round(y + (v - y) * SOFT))) for v in (r, g, b))
    return toon.mat(name, soft, **kw)

MOTIF = ["#d97a5a", "#6f8fc8", "#e8b84a", "#7cae84"]


def build(k, light: str = "day", seed: int = 7):
    random.seed(seed)
    w, d0, d1, h = 3.8, -1.5, 5.5, 2.8
    paper, trim = _mat("lwall", "#f0e4cc"), _mat("ltrim", "#8a5e3c")
    mesh.box("floor", (0, (d0 + d1) / 2, -0.05), (2 * w, d1 - d0, 0.1), _mat("lfloor", "#b08c68"))
    for i in range(-14, 15):                                               # floor boards
        mesh.box("board", (i * 0.26, (d0 + d1) / 2, 0.002), (0.01, d1 - d0, 0.004), _mat("lboard", "#957255"))
    mesh.box("ceiling", (0, (d0 + d1) / 2, h + 0.05), (2 * w, d1 - d0, 0.1), _mat("lceil", "#f7f2e6"))
    wx0, wx1, wz0, wz1 = 1.2, 3.1, 0.85, 2.25                              # the window, right of centre
    mesh.box("bw_l", ((-w + wx0) / 2, d1 + 0.05, h / 2), (wx0 + w, 0.1, h), paper, layer="bg")
    mesh.box("bw_r", ((w + wx1) / 2, d1 + 0.05, h / 2), (w - wx1, 0.1, h), paper, layer="bg")
    mesh.box("bw_lo", ((wx0 + wx1) / 2, d1 + 0.05, wz0 / 2), (wx1 - wx0, 0.1, wz0), paper, layer="bg")
    mesh.box("bw_hi", ((wx0 + wx1) / 2, d1 + 0.05, (h + wz1) / 2), (wx1 - wx0, 0.1, h - wz1), paper, layer="bg")
    # wallpaper motif: small flowers on a grid, every other row shifted (back wall, around the window)
    mats = [_mat("lmotif" + c[1:], c) for c in MOTIF]
    for r in range(9):
        for c in range(-13, 14):
            x, z = c * 0.29 + (0.145 if r % 2 else 0), 0.25 + r * 0.29
            if wx0 - 0.1 < x < wx1 + 0.1 and wz0 - 0.1 < z < wz1 + 0.1:
                continue
            mesh.sphere("motif", (x, d1 - 0.004, z), 0.022, mats[(r + c) % 4], scale=(1, 0.2, 1), seg=6, layer="bg")
    win = _mat("lwin", "#f4f1ea")
    for cx, cz, sx, sz in (((wx0 + wx1) / 2, wz1 + 0.03, wx1 - wx0 + 0.1, 0.06), ((wx0 + wx1) / 2, wz0 - 0.03, wx1 - wx0 + 0.2, 0.07),
                           (wx0 - 0.03, (wz0 + wz1) / 2, 0.06, wz1 - wz0), (wx1 + 0.03, (wz0 + wz1) / 2, 0.06, wz1 - wz0),
                           ((wx0 + wx1) / 2, (wz0 + wz1) / 2, 0.04, wz1 - wz0), ((wx0 + wx1) / 2, wz0 + 0.45, wx1 - wx0, 0.04)):
        mesh.box("winframe", (cx, d1 - 0.02, cz), (sx, 0.05, sz), win, outline=0.006, layer="bg")
    curtain = _mat("lcurtain", "#7a5c78")
    for cx in (wx0 - 0.22, wx1 + 0.22):
        mesh.box("curtain", (cx, d1 - 0.08, (wz0 + h) / 2 - 0.1), (0.36, 0.06, h - wz0 - 0.1), curtain, outline=0.008, bevel=0.02, layer="bg")
    mesh.tube("rod", (wx0 - 0.5, d1 - 0.1, h - 0.15), (wx1 + 0.5, d1 - 0.1, h - 0.15), 0.015, trim, layer="bg")
    # outside: sky, a big orange tree, house roofs and a railing
    mesh.box("sky", ((wx0 + wx1) / 2, d1 + 3.0, 1.6), (6, 0.1, 4), _mat("lsky", "#c4e4f2", emit=True), layer="far")
    mesh.sphere("tree", (wx0 + 0.6, d1 + 2.5, 2.0), 0.75, _mat("ltree", "#d39a5e"), seg=16, layer="far")
    mesh.tube("trunk", (wx0 + 0.6, d1 + 2.5, 0.6), (wx0 + 0.6, d1 + 2.5, 1.5), 0.07, _mat("ltrunk", "#7a5434"), layer="far")
    for i, col in enumerate(("#e8dcc8", "#c9d6e2")):
        hx = wx0 + 1.0 + i * 0.8
        mesh.box("house", (hx, d1 + 2.2, 0.85), (0.7, 0.5, 0.6), _mat("lhouse" + str(i), col), outline=0.006, layer="far")
        mesh.box("roof", (hx, d1 + 2.2, 1.25), (0.8, 0.55, 0.12), _mat("lroof", "#8a5a5a"), rot=(0, 0, 0), layer="far")
    for i in range(9):
        mesh.box("rail", (wx0 + 0.1 + i * 0.22, d1 + 0.6, 0.95), (0.03, 0.03, 0.35), win, layer="far")
    mesh.box("railtop", ((wx0 + wx1) / 2, d1 + 0.6, 1.13), (wx1 - wx0, 0.04, 0.04), win, layer="far")
    for x in (-w - 0.05, w + 0.05):
        mesh.box("sidewall", (x, (d0 + d1) / 2, h / 2), (0.1, d1 - d0, h), paper, layer="bg")
    mesh.box("frontwall", (0, d0 - 0.05, h / 2), (2 * w, 0.1, h), paper, layer="bg")
    for x, y, sx, sy in ((0, d1 - 0.01, 2 * w, 0.03), (-w + 0.01, (d0 + d1) / 2, 0.03, d1 - d0), (w - 0.01, (d0 + d1) / 2, 0.03, d1 - d0)):
        mesh.box("baseboard", (x, y, 0.06), (sx, sy, 0.12), trim)
    # framed pictures over the sofa
    frame = _mat("lframe", "#c9a24a")
    for x, z, fw, fh, col in ((-2.0, 1.85, 0.5, 0.62, "#9fd0e8"), (-1.25, 2.0, 0.42, 0.42, "#f2c230"), (-1.25, 1.45, 0.42, 0.34, "#8a7ad8")):
        mesh.box("picframe", (x, d1 - 0.02, z), (fw, 0.03, fh), frame, outline=0.006, layer="bg")
        mesh.box("picture", (x, d1 - 0.04, z), (fw - 0.08, 0.02, fh - 0.08), _mat("lpic" + col[1:], col), layer="bg")
        for j in range(3):
            mesh.sphere("picdot", (x - 0.1 + 0.1 * j, d1 - 0.055, z - 0.05), 0.04, _mat("lpdot", "#2a2d36"), scale=(1, 0.2, 1), seg=8, layer="bg")
    # the sofa along the back wall
    sofa, sofadk = _mat("lsofa", "#7f9fb4"), _mat("lsofadk", "#6a879b")
    sx, sy = -1.6, d1 - 0.6
    mesh.box("sofabase", (sx, sy, 0.25), (2.2, 0.85, 0.3), sofadk, outline=0.012, bevel=0.04)
    mesh.box("sofaback", (sx, sy + 0.32, 0.65), (2.2, 0.25, 0.65), sofa, outline=0.012, bevel=0.08)
    for s in (-1, 1):
        mesh.box("sofaarm", (sx + s * 1.05, sy, 0.5), (0.24, 0.85, 0.5), sofa, outline=0.012, bevel=0.08)
    for i in (-1, 1):
        mesh.box("seatcush", (sx + i * 0.46, sy - 0.05, 0.45), (0.9, 0.7, 0.14), sofa, outline=0.01, bevel=0.05)
    for dx, col, rot in ((-0.6, "#e8923a", 0.2), (0.55, "#f2c230", -0.25)):
        mesh.box("pillow", (sx + dx, sy + 0.12, 0.72), (0.4, 0.14, 0.36), _mat("lpil" + col[1:], col), outline=0.008, bevel=0.06, rot=(0, rot, 0))
    # rug and coffee table
    mesh.box("rug", (sx + 0.2, sy - 1.6, 0.004), (2.6, 1.7, 0.01), _mat("lrug", "#b37a5e"))
    mesh.box("rugin", (sx + 0.2, sy - 1.6, 0.006), (2.3, 1.4, 0.01), _mat("lrugin", "#d8c09a"))
    ct = _mat("lctable", "#8a5a34")
    mesh.box("ctop", (sx + 0.2, sy - 1.5, 0.42), (1.2, 0.6, 0.05), ct, outline=0.01, bevel=0.01, layer="fg")
    for lx in (-0.52, 0.52):
        for ly in (-0.24, 0.24):
            mesh.box("cleg", (sx + 0.2 + lx, sy - 1.5 + ly, 0.2), (0.05, 0.05, 0.4), ct, layer="fg")
    mesh.box("magazine", (sx - 0.05, sy - 1.55, 0.452), (0.3, 0.22, 0.01), _mat("lmag", "#d9443a"), rot=(0, 0, 0.3), layer="fg")
    mesh.tube("mug", (sx + 0.45, sy - 1.45, 0.445), (sx + 0.45, sy - 1.45, 0.54), 0.045, _mat("lmug", "#2f6fd0"), outline=0.004, layer="fg")
    mesh.box("remote", (sx + 0.25, sy - 1.62, 0.452), (0.05, 0.18, 0.02), _mat("lremote", "#2a2d36"), layer="fg")
    # TV on a low cabinet against the left wall
    tvx, tvy = -w + 0.3, 1.6
    mesh.box("tvcab", (tvx, tvy, 0.25), (0.45, 1.6, 0.5), _mat("ltvcab", "#6b4a32"), outline=0.01)
    for dy in (-0.4, 0.4):
        mesh.box("tvcabdoor", (tvx + 0.23, tvy + dy, 0.25), (0.01, 0.7, 0.4), _mat("ltvdoor", "#7a5434"), outline=0.004)
    mesh.box("tv", (tvx + 0.05, tvy, 0.95), (0.08, 1.2, 0.72), _mat("ltv", "#22252c"), outline=0.01, bevel=0.01)
    mesh.box("screen", (tvx + 0.095, tvy, 0.95), (0.01, 1.1, 0.62), _mat("lscreen", "#3a5a7a", emit=True))
    mesh.box("tvstand", (tvx, tvy, 0.53), (0.25, 0.3, 0.06), _mat("ltv", "#22252c"))
    # side table and lamp right of the sofa, a plant, a bookshelf by the window
    stx = sx + 1.45
    mesh.box("sidetable", (stx, sy, 0.3), (0.45, 0.45, 0.6), _mat("lside", "#a8754a"), outline=0.01)
    mesh.tube("lampbase", (stx, sy, 0.6), (stx, sy, 0.95), 0.03, _mat("lbase", "#f4f1ea"), outline=0.004)
    mesh.sphere("lampfoot", (stx, sy, 0.64), 0.09, _mat("lbase", "#f4f1ea"), scale=(1, 1, 0.5), seg=12)
    mesh.tube("lampshade", (stx, sy, 0.92), (stx, sy, 1.2), 0.2, _mat("lshade", "#f6ecd2", emit=True), r2=0.13, outline=0.006, caps=False)
    mesh.tube("plantpot", (w - 0.4, d1 - 0.5, 0), (w - 0.4, d1 - 0.5, 0.45), 0.2, _mat("lpot", "#c8643c"), r2=0.24, outline=0.01, caps=False)
    leaf = _mat("lleaf", "#5f9a55")
    for dx, dz, r in ((0, 0.8, 0.32), (-0.18, 1.05, 0.24), (0.2, 1.0, 0.22), (0.02, 1.3, 0.2)):
        mesh.sphere("plant", (w - 0.4 + dx, d1 - 0.5, dz), r, leaf, outline=0.01, seg=14)
    shelf = _mat("lshelf", "#7a5434")
    bx, by = w - 0.22, 2.4
    mesh.box("shelfback", (w - 0.03, by, 0.9), (0.06, 1.2, 1.8), shelf)
    for s in (-1, 1):
        mesh.box("shelfside", (bx, by + s * 0.6, 0.9), (0.34, 0.04, 1.8), shelf, outline=0.01)
    books = ["#d9443a", "#2f6fd0", "#f2c230", "#5bb07a", "#8a7ad8", "#e8923a", "#3a3f4a"]
    for j in range(4):
        z = 0.08 + j * 0.45
        mesh.box("shelfboard", (bx, by, z), (0.34, 1.2, 0.04), shelf)
        if j < 3:
            y = by - 0.52
            while y < by + 0.5:
                bw, bh = random.uniform(0.05, 0.09), random.uniform(0.26, 0.36)
                col = books[random.randrange(7)]
                mesh.box("book", (bx - 0.02, y + bw / 2, z + 0.02 + bh / 2), (0.24, bw, bh), _mat("lbook" + col[1:], col))
                y += bw + 0.01
    mesh.sphere("ceilinglamp", (0, 2.2, h - 0.04), 0.4, _mat("llamp", "#fffbe8", emit=True), scale=(1, 1, 0.12), seg=16)
    import bpy
    vs = bpy.context.scene.view_settings                                   # measured on quarter stills: luma 0.64-0.71 at
    vs.exposure = -1.4                                                     # -0.35 against 0.44-0.58 in the reference rooms
    try:
        vs.look = "Very High Contrast"                                     # contrast 0.16 -> the reference 0.17-0.23
    except TypeError:
        pass
    lights.preset(k, light, energy=1.2)
    lights.lamp("AREA", "window", ((wx0 + wx1) / 2, d1 - 0.5, 1.6), (-90, 0, 0), 110, "#fff4dc", size=2)
    lights.lamp("AREA", "room", (0, 2.2, h - 0.1), (0, 0, 0), 150, "#fff2dc", size=4)
    k.objects.update({"look": (-0.4, d1 - 0.8, 1.0), "cam_dir": (0.0, -1.0, 0.0), "sofa": (sx, sy - 0.05, 0.45),
                      "tv": (tvx + 0.1, tvy, 0.95), "floor": (-w + 0.8, w - 0.8, d0 + 0.3, d1 - 1.2),
                      "walk": [(-2.4, 2.0), (1.6, 2.6)]})
    return k.objects
