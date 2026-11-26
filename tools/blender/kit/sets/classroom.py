"""Classroom (specs/038 T026): x -5..5, y -7.5 (front) .. 6 (back wall), three windows on the left wall with trees
outside, a notice board, clock, shelf and posters, desks in four rows with an aisle at x = 0.
The seats (k.objects["seats"]) are where k.crowd() puts seated classmates (cast cards, US3).
Layers: fg the front row of desks, mid the room, bg the back wall and its things, far the trees outside."""
import math
import random

from kit import light as lights
from kit import mesh, toon

PAPER = ["#ffffff", "#f7e08a", "#9ed0f0", "#f4a6b8", "#b8e0a0"]
BOOKS = ["#d9443a", "#2f6fd0", "#f2c230", "#5bb07a", "#8a7ad8", "#e8923a"]


def build(k, light: str = "day", rows: int = 4, seed: int = 5):
    random.seed(seed)
    wall, wains, ceil = toon.mat("wall", "#f1e6cf"), toon.mat("wains", "#8fb89a"), toon.mat("ceil", "#faf4e6")
    floor, trim = toon.mat("floor", "#c08a55", tex="planks"), toon.mat("trim", "#6b4a32")
    rw, d0, d1, rh = 5.0, -7.5, 6.0, 3.4
    mesh.box("floor", (0, (d0 + d1) / 2, -0.05), (2 * rw, d1 - d0, 0.1), floor)
    mesh.box("ceiling", (0, (d0 + d1) / 2, rh + 0.05), (2 * rw, d1 - d0, 0.1), ceil)
    mesh.box("backwall", (0, d1 + 0.05, rh / 2), (2 * rw, 0.1, rh), wall, layer="bg")
    mesh.box("backwains", (0, d1 - 0.01, 0.5), (2 * rw, 0.04, 1.0), wains, layer="bg")
    mesh.box("rightwall", (rw + 0.05, (d0 + d1) / 2, rh / 2), (0.1, d1 - d0, rh), wall)
    mesh.box("rightwains", (rw - 0.01, (d0 + d1) / 2, 0.5), (0.04, d1 - d0, 1.0), wains)
    wins = [(-4.2, -1.8), (-0.6, 1.8), (3.0, 4.8)]
    ys = [d0] + [v for w in wins for v in w] + [d1]
    for i in range(0, len(ys), 2):
        mesh.box("lwall", (-rw - 0.05, (ys[i] + ys[i + 1]) / 2, rh / 2), (0.1, ys[i + 1] - ys[i], rh), wall)
    for y0, y1 in wins:
        cy, ly = (y0 + y1) / 2, y1 - y0
        mesh.box("lwall_lo", (-rw - 0.05, cy, 0.5), (0.1, ly, 1.0), wains)
        mesh.box("lwall_hi", (-rw - 0.05, cy, 3.05), (0.1, ly, 0.7), wall)
        mesh.box("sill", (-rw + 0.05, cy, 1.0), (0.18, ly + 0.1, 0.06), trim, outline=0.01)
        for yy in (y0, cy, y1):
            mesh.box("mullion", (-rw, yy, 1.85), (0.08, 0.07, 1.7), trim)
        mesh.box("transom", (-rw, cy, 2.0), (0.08, ly, 0.06), trim)
        mesh.box("wintop", (-rw, cy, 2.7), (0.08, ly, 0.07), trim)
    trunk = toon.mat("trunk", "#7a5434")
    for i in range(9):
        yy = -7 + i * 1.6
        leaf = toon.mat(f"leaf{i % 3}", ["#6db34a", "#e8a33a", "#4f9a3e"][i % 3])
        mesh.tube("trunk", (-8.5, yy, 0), (-8.5, yy, 2.2), 0.15, trunk, layer="far")
        for _ in range(3):
            mesh.sphere("leaf", (-8.5 + random.uniform(-0.5, 0.5), yy + random.uniform(-0.5, 0.5), 2.6 + random.uniform(0, 0.8)),
                        random.uniform(0.7, 1.0), leaf, seg=16, layer="far")
    mesh.box("lawn", (-12, 0, -0.06), (14, 40, 0.1), toon.mat("lawn", "#8cc46a"), layer="far")
    mesh.box("doorframe", (3.4, d1 - 0.03, 1.1), (1.2, 0.08, 2.2), trim, outline=0.01, layer="bg")
    mesh.box("door", (3.4, d1 - 0.07, 1.08), (1.02, 0.06, 2.1), toon.mat("door", "#d9a35c"), outline=0.01, layer="bg")
    mesh.sphere("knob", (3.05, d1 - 0.12, 1.05), 0.04, toon.mat("gold", "#e2b443", spec=0.5, rough=0.2), layer="bg")
    mesh.box("board", (-1.0, d1 - 0.04, 1.85), (3.6, 0.05, 1.3), toon.mat("cork", "#c79a63"), outline=0.012, layer="bg")
    mesh.box("boardframe", (-1.0, d1 - 0.02, 1.85), (3.75, 0.03, 1.45), trim, layer="bg")
    random.seed(seed + 6)
    for i in range(9):
        px, pz = -2.5 + (i % 5) * 0.72 + random.uniform(-0.08, 0.08), 1.6 + (i // 5) * 0.55 + random.uniform(-0.05, 0.05)
        mesh.box("paper", (px, d1 - 0.08, pz), (0.5, 0.01, 0.38 if i % 2 else 0.45), toon.mat(f"pap{i % 5}", PAPER[i % 5]),
                 rot=(0, math.radians(random.uniform(-6, 6)), 0), layer="bg")
        mesh.sphere("pin", (px, d1 - 0.1, pz + 0.17), 0.02, toon.mat("pin", "#d9443a"), seg=8, layer="bg")
    mesh.torus("clockrim", (1.6, d1 - 0.06, 2.75), 0.24, 0.035, toon.mat("rim", "#33384a"), rot=(math.pi / 2, 0, 0),
               outline=0.008, layer="bg")
    mesh.sphere("clockface", (1.6, d1 - 0.05, 2.75), 0.24, toon.mat("white", "#ffffff"), scale=(1, 0.1, 1), layer="bg")
    mesh.box("clockh", (1.6, d1 - 0.09, 2.82), (0.025, 0.01, 0.15), toon.mat("ink", "#1d1b2e"), layer="bg")
    mesh.box("shelf", (-4.0, d1 - 0.25, 0.55), (1.6, 0.45, 1.1), toon.mat("shelf", "#a8754a"), outline=0.012, bevel=0.02, layer="bg")
    for i in range(11):
        mesh.box("book", (-4.7 + i * 0.13, d1 - 0.3, 1.25 + (i % 3) * 0.03), (0.1, 0.3, 0.28 + (i % 3) * 0.06),
                 toon.mat(f"bk{i % 6}", BOOKS[i % 6]), outline=0.006, layer="bg")
    for i, (yy, c) in enumerate(((-3.5, "#f7e08a"), (-0.5, "#9ed0f0"), (2.5, "#f4a6b8"))):
        mesh.box("poster", (rw - 0.04, yy, 1.9), (0.02, 1.2, 0.85), toon.mat(f"post{i}", c), outline=0.01)
        mesh.box("posterart", (rw - 0.06, yy, 1.95), (0.02, 0.6, 0.35), toon.mat(f"pa{i}", BOOKS[i]))
    lamp_m = toon.mat("lamp", "#fffbe8", emit=True)
    for yy in (-4, 0, 4):
        for xx in (-2.2, 2.2):
            mesh.box("lamp", (xx, yy, rh - 0.02), (1.4, 0.35, 0.05), lamp_m)
    desk, deskd, leg = toon.mat("desk", "#d9a35c"), toon.mat("deskd", "#b9824a"), toon.mat("leg", "#4a4f5e")
    chair = toon.mat("chair", "#4f86d0")
    cols = [-3.3, -1.55, 1.55, 3.3]
    row_y = [-3.6, -1.4, 0.8, 3.0][:max(1, min(4, rows))]
    seats = []
    random.seed(seed + 4)
    for ri, ry in enumerate(row_y):
        layer = "fg" if ri == 0 else "mid"
        for ci, cx in enumerate(cols):
            mesh.box("desktop", (cx, ry - 0.42, 0.74), (1.1, 0.6, 0.06), desk, outline=0.012, bevel=0.015, layer=layer)
            mesh.box("deskpanel", (cx, ry - 0.7, 0.42), (1.06, 0.04, 0.6), deskd, outline=0.012, layer=layer)
            for xx in (-0.5, 0.5):
                mesh.box("deskleg", (cx + xx, ry - 0.42, 0.36), (0.05, 0.5, 0.72), leg, layer=layer)
            if random.random() < 0.6:
                mesh.box("bookdesk", (cx + random.uniform(-0.3, 0.3), ry - 0.45, 0.79), (0.32, 0.24, 0.04),
                         toon.mat(f"bk{(ri * 4 + ci) % 6}", BOOKS[(ri * 4 + ci) % 6]), outline=0.006,
                         rot=(0, 0, math.radians(random.uniform(-20, 20))), layer=layer)
            mesh.box("chairback", (cx, ry + 0.22, 0.75), (0.5, 0.05, 0.4), chair, outline=0.01, bevel=0.02, layer=layer)
            seats.append({"at": (cx, ry, 0.0), "face": 0, "row": ri, "col": ci})
    lights.preset(k, light)
    lights.lamp("AREA", "room", (0, 0, rh - 0.1), (0, 0, 0), 300, "#fffaf0", size=6)
    k.objects.update({"look": (0.0, 0.0, 1.0), "cam_dir": (0.15, -1.0, 0.0), "seats": seats,
                      "floor": (-rw + 0.5, rw - 0.5, d0 + 0.5, d1 - 0.5), "walk": [(0.0, d0 + 1.5), (0.0, d1 - 1.0)]})
    return k.objects
