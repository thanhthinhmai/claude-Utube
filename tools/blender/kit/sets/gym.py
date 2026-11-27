"""School gym on science-fair day (charisma shot match): x -12..12, y -9 (open front) .. 10 (back wall), 7 m high.
The back wall has high windows with sky, pennant strings and a green crash-pad band; folding bleachers run along the
right wall; a court is painted on the floor; with fair=True (default) fair tables with tri-fold project boards stand along the back wall, the
hero's table (k.objects["volcano"]) with a paper volcano in front of it. Doors in the left wall.
Layers: fg nothing by default (k.fg), mid the floor, tables and kids, bg the back wall and bleachers, far the sky."""
import math
import random

from kit import light as lights
from kit import mesh, toon

BOARDS = ["#f7e08a", "#9ed0f0", "#f4a6b8", "#b8e0a0", "#ffffff", "#f3b77a"]
PENNANT = ["#e8923a", "#3a9a6a", "#ffffff"]
WZ = 3.6                 # window centre height: low enough that a wide shot of the kids still shows the windows


def build(k, light: str = "day", seed: int = 11, fair: bool = True):
    random.seed(seed)
    w, d0, d1, h = 12.0, -9.0, 10.0, 7.0
    wall, band, trim = toon.mat("gwall", "#efe6d2"), toon.mat("gpad", "#3a9a6a"), toon.mat("gtrim", "#e8923a")
    mesh.box("floor", (0, (d0 + d1) / 2, -0.05), (2 * w, d1 - d0, 0.1), toon.mat("gfloor", "#d9a868", tex="planks", tex_col="#c8955a"))
    line = toon.mat("gline", "#ffffff")
    key = toon.mat("gkey", "#d2a062")                                   # a shade darker than the floor
    mesh.box("key", (-5.5, 1.0, -0.004), (4.0, 5.5, 0.01), key)          # painted key, left half of the court
    for x0, y0, sx, sy in ((0, 1.0, 0.08, 15.0), (-11.0, 1.0, 0.08, 15.0), (11.0, 1.0, 0.08, 15.0),
                           (0, 8.5, 22.0, 0.08), (0, -6.5, 22.0, 0.08)):
        mesh.box("courtline", (x0, y0, 0.002), (sx, sy, 0.01), line)
    mesh.torus("centre", (0, 1.0, 0.003), 1.8, 0.04, line, rs=4, segs=48)
    mesh.box("backwall", (0, d1 + 0.05, h / 2), (2 * w, 0.1, h), wall, layer="bg")
    mesh.box("backpad", (0, d1 - 0.05, 0.9), (2 * w, 0.1, 1.2), band, outline=0.01, layer="bg")
    mesh.box("backstripe", (0, d1 - 0.02, 1.62), (2 * w, 0.06, 0.12), trim, layer="bg")
    sky = toon.mat("gsky", "#a8d8f0", emit=True)
    frame = toon.mat("gframe", "#5a5f6a")
    for i in range(6):
        x = -10 + i * 4
        mesh.box("winframe", (x, d1 - 0.005, WZ), (2.75, 0.02, 1.45), frame, layer="bg")
        mesh.box("win", (x, d1 - 0.03, WZ), (2.6, 0.02, 1.3), sky, layer="far")
        for dx in (-0.65, 0, 0.65):
            mesh.box("mull", (x + dx, d1 - 0.06, WZ), (0.05, 0.03, 1.3), frame, layer="bg")
    for row, z in ((0, 2.75), (1, 2.35)):                                  # pennant strings: flat triangles, as in AE
        mesh.box("string", (0, d1 - 0.11, z), (2 * w, 0.01, 0.015), toon.mat("gstring", "#6b4a32"), layer="bg")
        for i in range(48):
            x = -11.5 + i * 0.49 + row * 0.24
            m = toon.mat(f"pen{i % 3}", PENNANT[i % 3])
            mesh.tri("pennant", [(x - 0.19, d1 - 0.12, z), (x, d1 - 0.12, z - 0.34), (x + 0.19, d1 - 0.12, z)], m, layer="bg")
    dark, lit = toon.mat("gboard", "#2a2d36"), toon.mat("gdigit", "#f2a03a", emit=True)   # scoreboard above the windows
    mesh.box("scoreboard", (0, d1 - 0.1, 5.4), (3.2, 0.12, 1.3), dark, outline=0.012, layer="bg")
    for dx in (-0.95, -0.55, 0.55, 0.95):
        mesh.box("digit", (dx, d1 - 0.17, 5.3), (0.3, 0.02, 0.5), lit, layer="bg")
    mesh.box("scorebar", (0, d1 - 0.17, 5.85), (2.6, 0.02, 0.18), toon.mat("gbar", "#e8923a"), layer="bg")
    for x in (-8.0, -4.0, 4.0, 8.0):                                       # school banners between the windows
        bz = WZ + 0.2
        mesh.box("banner", (x, d1 - 0.1, bz), (1.0, 0.03, 1.1), band, outline=0.01, layer="bg")
        mesh.tri("bannertip", [(x - 0.5, d1 - 0.1155, bz - 0.55), (x, d1 - 0.1155, bz - 0.95), (x + 0.5, d1 - 0.1155, bz - 0.55)],
                 band, layer="bg")
        mesh.box("bannerstripe", (x, d1 - 0.12, bz + 0.35), (1.0, 0.01, 0.12), trim, layer="bg")
        mesh.sphere("banneremblem", (x, d1 - 0.125, bz - 0.15), 0.22, trim, scale=(1, 0.05, 1), seg=16, layer="bg")
    for x in (-w - 0.05, w + 0.05):
        mesh.box("sidewall", (x, (d0 + d1) / 2, h / 2), (0.1, d1 - d0, h), wall, layer="bg")
        mesh.box("sidepad", (x - math.copysign(0.05, x), (d0 + d1) / 2, 0.9), (0.1, d1 - d0, 1.2), band, layer="bg")
    door = toon.mat("gdoor", "#3a9a6a")
    for y in (-2.0, 4.0):
        mesh.box("door", (-w + 0.02, y, 1.15), (0.06, 1.8, 2.3), door, outline=0.012, layer="bg")
        mesh.box("doorwin", (-w + 0.06, y - 0.45, 1.6), (0.02, 0.3, 0.6), sky, layer="bg")
        mesh.box("doorwin", (-w + 0.06, y + 0.45, 1.6), (0.02, 0.3, 0.6), sky, layer="bg")
    bench, riser = toon.mat("gbench", "#3a9a6a"), toon.mat("griser", "#2c3a44")
    for r in range(6):                                                     # bleachers on the right wall
        x = w - 0.6 - r * 0.0 - (5 - r) * 0.7
        mesh.box("bleacher", (x + 0.35, 1.0, 0.25 + r * 0.45), (0.7, 13.0, 0.1), bench, outline=0.01, layer="bg")
        mesh.box("riser", (x + 0.35, 1.0, 0.1 + r * 0.45 / 2), (0.7, 13.0, 0.2 + r * 0.45), riser, layer="bg")
    mesh.box("ceiling", (0, (d0 + d1) / 2, h + 0.05), (2 * w, d1 - d0, 0.1), toon.mat("gceil", "#dfe3e6"))
    steel = toon.mat("gsteel", "#9aa3ad")
    for i in range(5):
        y = -6 + i * 4
        mesh.box("truss", (0, y, h - 0.4), (2 * w, 0.12, 0.12), steel)
        mesh.sphere("lamp", (-4, y, h - 0.9), 0.35, toon.mat("glamp", "#fffbe8", emit=True), scale=(1, 1, 0.5), seg=12)
        mesh.sphere("lamp", (4, y, h - 0.9), 0.35, toon.mat("glamp", "#fffbe8", emit=True), scale=(1, 1, 0.5), seg=12)
    table, cloth = toon.mat("gtable", "#8a6a4a"), toon.mat("gcloth", "#ffffff")
    tables = []
    vx, vy = 1.5, 7.7                                                      # the hero's table and volcano
    if fair:                                                               # fair day: tables, boards, the volcano
        for i, x in enumerate((-8.5, -5.0, -1.5, 2.0, 5.5)):                   # fair tables along the back wall
            y = 9.2
            mesh.box("tabletop", (x, y, 0.74), (2.2, 0.8, 0.06), cloth, outline=0.012)
            mesh.box("tableskirt", (x, y - 0.38, 0.42), (2.2, 0.04, 0.6), cloth)
            for dx in (-1.0, 1.0):
                mesh.box("tableleg", (x + dx, y + 0.3, 0.37), (0.05, 0.05, 0.74), table)
            c = toon.mat(f"board{i}", BOARDS[i % len(BOARDS)])
            mesh.box("board", (x, y + 0.2, 1.17), (0.9, 0.03, 0.8), c, outline=0.01)
            for s in (-1, 1):
                mesh.box("wing", (x + s * 0.68, y + 0.05, 1.12), (0.45, 0.03, 0.7), c, outline=0.01,
                         rot=(0, 0, math.radians(-s * 30)))
            for j in range(3):
                mesh.box("chart", (x - 0.25 + j * 0.25, y + 0.18, 1.2 + random.uniform(-0.1, 0.15)), (0.18, 0.01, 0.16),
                         toon.mat(f"chart{(i + j) % 6}", BOARDS[(i + j + 2) % 6]))
            tables.append((x, y))
        mesh.box("vtabletop", (vx, vy, 0.74), (1.6, 0.8, 0.06), cloth, outline=0.012)
        mesh.box("vskirt", (vx, vy - 0.38, 0.42), (1.6, 0.04, 0.6), toon.mat("vskirt", "#e8604c"))
        for dx in (-0.7, 0.7):
            mesh.box("vleg", (vx + dx, vy + 0.3, 0.37), (0.05, 0.05, 0.74), table)
        mesh.tube("volcano", (vx, vy, 0.77), (vx, vy, 1.25), 0.32, toon.mat("volcano", "#8a5a34"), outline=0.012, r2=0.08,
                  seg=20)
        mesh.tube("lava", (vx, vy, 1.2), (vx, vy, 1.27), 0.1, toon.mat("lava", "#e84a3c"), r2=0.07, seg=16)
    import bpy
    bpy.context.scene.view_settings.exposure = -0.4                     # measured: the toon walls came out 5-12 points
    # brighter than the reference (HSV value) while the AE shots matched
    lights.preset(k, light, energy=1.2)                                   # indoors: a weak sun, the room lamps light it
    lights.lamp("AREA", "gymfill", (0, 0, h - 0.6), (0, 0, 0), 480, "#fff6e0", size=14)
    seats = []                                                             # kids on the bleachers (k.crowd seats=True)
    for r in range(1, 6):
        x = w - 0.6 - (5 - r) * 0.7 + 0.35
        for i in range(9):
            seats.append({"at": (x, -4.5 + i * 1.3 + random.uniform(-0.3, 0.3), 0.3 + r * 0.45)})
    random.shuffle(seats)
    k.objects.update({"seats": seats, "look": (vx, vy, 1.0), "cam_dir": (0.0, -1.0, 0.0), "volcano": (vx, vy, 1.27),
                      "tables": tables, "floor": (-w + 1, w - 5, -6.0, 7.0),
                      "walk": [(-3.0, -2.0), (vx, vy - 1.0)]})
    return k.objects
