"""School hallway (specs/038 T026): x -2.2..2.2, y -6..14, lockers on both sides, a classroom door on the right,
a tall window at the far end. Layers: fg the nearest lockers, mid the hall, bg the far half, far the end window."""
import random

from kit import light as lights
from kit import mesh, toon


def build(k, light: str = "day", length: float = 20.0, doors: bool = True, seed: int = 21):
    hw, y0, h = 2.2, -6.0, 3.2
    y1 = y0 + length
    lay = lambda y: "fg" if y < -3 else ("mid" if y < (y0 + y1) / 2 else "bg")       # noqa: E731
    mesh.box("floor", (0, (y0 + y1) / 2, -0.05), (2 * hw, y1 - y0, 0.1), toon.mat("tile", "#c9d6e3", tex="tiles"))
    mesh.box("ceiling", (0, (y0 + y1) / 2, h + 0.05), (2 * hw, y1 - y0, 0.1), toon.mat("ceil", "#faf4e6"))
    wall, stripe = toon.mat("hwall", "#f3e9d2"), toon.mat("hstripe", "#e8923a")
    for x in (-1, 1):
        mesh.box("wall", (x * (hw + 0.05), (y0 + y1) / 2, h / 2), (0.1, y1 - y0, h), wall)
        mesh.box("stripe", (x * (hw - 0.01), (y0 + y1) / 2, 2.25), (0.03, y1 - y0, 0.12), stripe)
    trim, sky = toon.mat("trim", "#6b4a32"), toon.mat("winsky", "#bfe3f7", emit=True)
    mesh.box("endwall", (0, y1 + 0.05, h / 2), (2 * hw, 0.1, h), wall, layer="far")
    mesh.box("endwin", (0, y1 - 0.02, 1.6), (2.4, 0.04, 2.0), sky, layer="far")
    for xx in (-1.2, 0, 1.2):
        mesh.box("endmull", (xx, y1 - 0.05, 1.6), (0.08, 0.06, 2.0), trim, layer="far")
    mesh.box("endmullh", (0, y1 - 0.05, 1.6), (2.4, 0.06, 0.08), trim, layer="far")
    lk = [toon.mat("lk0", "#3f7fc9"), toon.mat("lk1", "#3aa6a8")]
    vent, knob = toon.mat("vent", "#2a3346"), toon.mat("knob", "#d9dde6")
    door = toon.mat("door", "#d9a35c")
    random.seed(seed)
    k.objects["doors"] = []
    for x in (-1, 1):
        y, i = y0 + 0.4, 0
        while y < y1 - 0.6:
            if doors and x == 1 and i % 7 == 4:
                mesh.box("door", (x * (hw - 0.04), y + 0.45, 1.05), (0.06, 1.0, 2.1), door, outline=0.01, layer=lay(y))
                mesh.box("doorwin", (x * (hw - 0.08), y + 0.45, 1.55), (0.02, 0.45, 0.5), sky, layer=lay(y))
                k.objects["doors"].append((x * (hw - 0.3), y + 0.45))
                y, i = y + 1.3, i + 1
                continue
            mesh.box("locker", (x * (hw - 0.25), y + 0.27, 0.98), (0.5, 0.52, 1.92), lk[(i // 3) % 2], outline=0.01, layer=lay(y))
            for v in range(3):
                mesh.box("vent", (x * (hw - 0.51), y + 0.27, 1.62 + v * 0.07), (0.01, 0.3, 0.025), vent, layer=lay(y))
            mesh.box("handle", (x * (hw - 0.52), y + 0.43, 1.05), (0.02, 0.04, 0.14), knob, layer=lay(y))
            y, i = y + 0.55, i + 1
    lamp_m = toon.mat("lamp", "#fffbe8", emit=True)
    for yy in range(int(y0) + 1, int(y1), 3):
        mesh.box("lamp", (0, yy, h - 0.02), (0.6, 1.4, 0.05), lamp_m, layer=lay(yy))
        lights.lamp("AREA", f"hl{yy}", (0, yy, h - 0.1), (0, 0, 0), 120, "#fffaf0", size=2.5)
    paper = ["#ffffff", "#f7e08a", "#9ed0f0", "#f4a6b8"]
    for yy in (0.5, 6.5):
        mesh.box("notice", (-hw + 0.03, yy, 1.5), (0.02, 1.4, 0.9), toon.mat("cork", "#c79a63"), outline=0.01, layer=lay(yy))
        for p in range(4):
            mesh.box("np", (-hw + 0.05, yy - 0.45 + p * 0.3, 1.5 + (p % 2) * 0.12), (0.01, 0.24, 0.3),
                     toon.mat(f"pap{p}", paper[p]), layer=lay(yy))
    lights.preset(k, light)
    k.objects.update({"look": (0.0, 3.0, 1.2), "cam_dir": (0.0, -1.0, 0.0), "floor": (-hw + 0.5, hw - 0.5, y0, y1),
                      "walk": [(0.0, y0 + 2), (0.0, y1 - 2)]})
    return k.objects
