"""School auditorium (specs/038 T026): a stage at y 3..8 raised 0.9 m with curtains, banner and podium, audience
rows facing the stage from y 1.2 back to the hall's rear wall at y -12.9 with two exit doors.
The seats (k.objects["seats"]) are where k.crowd() puts the audience (cast cards, US3).
Layers: fg the nearest seat rows, mid the audience, bg the stage, far the back curtain and banner."""
import math
import random

from kit import light as lights
from kit import mesh, toon


def build(k, light: str = "stage", rows: int = 5, seed: int = 17):
    w, h, sy, sz = 8.0, 6.0, 3.0, 0.9
    mesh.box("floor", (0, -2, -0.05), (2 * w, 22, 0.1), toon.mat("afloor", "#8a4b3c"))
    mesh.box("aisle", (0, -3, -0.03), (1.4, 12, 0.1), toon.mat("carpet", "#b03a3a"))
    mesh.box("stage", (0, sy + 2.5, sz / 2), (2 * w - 2, 5, sz), toon.mat("stagewood", "#c08a55", tex="planks"),
             outline=0.015, layer="bg")
    mesh.box("stagefront", (0, sy - 0.01, sz / 2), (2 * w - 2, 0.04, sz), toon.mat("stagefront", "#5a3a2a"), layer="bg")
    mesh.box("backwall", (0, sy + 5.5, h / 2), (2 * w, 0.1, h), toon.mat("awall", "#7a2f36"), layer="far")
    side, sidew, sconce = toon.mat("aside", "#e9d9bf"), toon.mat("awains", "#7a2f36"), toon.mat("sconce", "#fff2c8", emit=True)
    for x in (-1, 1):
        mesh.box("sidewall", (x * (w + 0.05), -2, h / 2), (0.1, 22, h), side)
        mesh.box("sidewains", (x * (w - 0.01), -2, 0.6), (0.04, 22, 1.2), sidew)
        for yy in (-6, -2, 2):
            mesh.sphere("sconce", (x * (w - 0.12), yy, 3.2), 0.18, sconce, scale=(0.6, 1, 1.3), seg=12)
    mesh.box("ceiling", (0, -2, h + 0.05), (2 * w, 22, 0.1), toon.mat("aceil", "#efe2c9"))
    mesh.box("hallback", (0, -12.9, h / 2), (2 * w, 0.1, h), side)
    mesh.box("hallbackw", (0, -12.84, 0.6), (2 * w, 0.04, 1.2), sidew)
    for x in (-3.5, 3.5):
        mesh.box("halldoor", (x, -12.82, 1.1), (1.4, 0.06, 2.2), toon.mat("door", "#d9a35c"), outline=0.012)
        mesh.box("exit", (x, -12.82, 2.55), (0.6, 0.05, 0.22), toon.mat("exit", "#52b865", emit=True))
    cur, gold = toon.mat("curtain", "#c23a3a"), toon.mat("gold", "#e2b443")
    for i in range(46):
        x = -6.6 + i * 0.29
        mesh.tube("fold", (x, sy + 5.0 + 0.08 * (i % 2), sz), (x, sy + 5.0 + 0.08 * (i % 2), h), 0.17, cur, caps=False,
                  seg=10, layer="far")
    for x in (-1, 1):
        for j in range(6):
            xx = x * (6.4 - j * 0.22)
            mesh.tube("side", (xx, sy + 0.5, sz), (xx, sy + 0.5, h), 0.16, cur, caps=False, seg=10, layer="bg")
    mesh.box("valance", (0, sy + 0.35, h - 0.5), (2 * w - 2, 0.3, 1.0), cur, outline=0.015, layer="bg")
    for i in range(24):
        mesh.sphere("tassel", (-6.6 + i * 0.575, sy + 0.18, h - 1.0), 0.12, gold, scale=(1.4, 0.5, 1), seg=10, layer="bg")
    for x in (-7.0, 7.0):
        mesh.box("proc", (x, sy + 0.2, h / 2), (0.6, 0.5, h), gold, outline=0.015, layer="bg")
    mesh.box("banner", (0, sy + 4.8, 4.2), (6.0, 0.06, 1.0), toon.mat("banner", "#f7e08a"), outline=0.015, layer="far")
    sq = toon.mat("bsq", "#c23a3a")
    for i in range(10):
        mesh.arc("bsquig", (-2.4 + i * 0.53, sy + 4.74, 4.15), 0.18, math.radians(10), math.radians(170), 0.04, sq, layer="far")
    mesh.box("podium", (1.5, sy + 1.6, sz + 0.55), (0.8, 0.55, 1.1), toon.mat("podium", "#8a5a34"), outline=0.015, bevel=0.03,
             layer="bg")
    mesh.box("podtop", (1.5, sy + 1.55, sz + 1.13), (0.95, 0.65, 0.06), toon.mat("podtop", "#a8754a"), outline=0.012, layer="bg")
    mic = toon.mat("micst", "#2a2d36")
    mesh.tube("mic", (1.5, sy + 1.4, sz + 1.15), (1.5, sy + 1.15, sz + 1.45), 0.012, mic, layer="bg")
    mesh.sphere("michead", (1.5, sy + 1.13, sz + 1.47), 0.04, mic, seg=10, layer="bg")
    seat_m = toon.mat("seat", "#a8323a")
    seats = []
    random.seed(seed)
    n = max(1, min(8, rows))
    for r in range(n):
        ry = 1.2 - r * 1.2
        layer = "mid" if r < n - 1 else "fg"
        for sd in (-1, 1):
            mesh.box("seatrow", (sd * 4.0, ry - 0.3, 0.45), (6.2, 0.12, 0.9), seat_m, outline=0.012, bevel=0.02, layer=layer)
            for j in range(6):
                seats.append({"at": (sd * (1.25 + j * 0.95) + random.uniform(-0.05, 0.05), ry, 0.0), "face": 180,
                              "row": r, "col": j if sd > 0 else -j - 1})
    lights.preset(k, light)
    lights.lamp("SPOT", "stagespot", (0, -2, 5.5), (60, 0, 0), 900, "#fff0d8", size=0.6)
    lights.lamp("AREA", "house", (0, -4, h - 0.2), (0, 0, 0), 250, "#ffe8c8", size=8)
    k.objects.update({"look": (0.0, sy + 1.5, sz + 1.0), "cam_dir": (0.0, -1.0, 0.0), "seats": seats,
                      "stage": (-6.5, 6.5, sy + 0.3, sy + 4.5, sz), "floor": (-w + 0.5, w - 0.5, -12.5, sy - 0.2),
                      "walk": [(0.0, -10.0), (0.0, sy - 0.5)]})
    return k.objects
