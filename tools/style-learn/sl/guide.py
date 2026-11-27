"""Draw the shot labeler's guide image (specs/021 SC-001 fix): one generic sphere-headed figure at each shot scale,
with the frame's bottom edge cutting the figure where the rule says. Code-drawn, so it can live in git and travel with
the studio. specs/038 adds three rows: camera height, lens, and depth with its layers and a foreground occluder. Run: tools/.venv/bin/python tools/style-learn/sl/guide.py  → tools/filmcheck/labeler-guide.png"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[2] / "filmcheck" / "labeler-guide.png"
CW, CH, PAD, LAB = 240, 135, 8, 34


def figure(d: ImageDraw.ImageDraw, cx: float, top: float, h: float) -> None:
    """A sphere-headed figure of height h (head = 0.4 of the height, like the studio's figures) with its head top at top."""
    r = h * 0.2
    d.ellipse([cx - r, top, cx + r, top + 2 * r], fill=(235, 205, 190), outline=(40, 30, 50), width=2)
    d.ellipse([cx - r * 0.35 - 4, top + r * 0.9, cx - r * 0.35 + 4, top + r * 0.9 + 8], fill=(20, 20, 20))
    d.ellipse([cx + r * 0.35 - 4, top + r * 0.9, cx + r * 0.35 + 4, top + r * 0.9 + 8], fill=(20, 20, 20))
    body_t = top + 2 * r
    d.rounded_rectangle([cx - r * 0.75, body_t, cx + r * 0.75, body_t + h * 0.32], radius=8, fill=(120, 90, 170))
    leg_t = body_t + h * 0.32
    for dx in (-r * 0.35, r * 0.35):
        d.line([cx + dx, leg_t, cx + dx, top + h], fill=(60, 50, 80), width=max(2, int(h * 0.04)))


def cell(name: str, rule: str, h: float, top: float) -> Image.Image:
    im = Image.new("RGB", (CW, CH + LAB), (17, 17, 17))
    pic = Image.new("RGB", (CW, CH), (70, 52, 100))
    d = ImageDraw.Draw(pic)
    d.rectangle([0, CH * 0.62, CW, CH], fill=(90, 70, 110))          # floor
    figure(d, CW / 2, top, h)
    im.paste(pic, (0, LAB))
    t = ImageDraw.Draw(im)
    t.text((4, 3), name, fill=(255, 230, 120))
    t.text((4, 17), rule, fill=(220, 220, 220))
    return im


def room(d: ImageDraw.ImageDraw, hz: float, back: float, wall=(70, 52, 100), floor=(90, 70, 110), lines=6) -> tuple:
    """One-point room: a back wall of relative size `back` centred on the vanishing point at height hz (0..1);
    floor and wall lines run to it. Returns the back wall box."""
    vx, vy = CW / 2, CH * hz
    bw, bh = CW * back, CH * back
    box = (vx - bw / 2, vy - bh * 0.55, vx + bw / 2, vy + bh * 0.45)
    d.rectangle([0, 0, CW, CH], fill=wall)
    d.polygon([(0, CH), (CW, CH), (box[2], box[3]), (box[0], box[3])], fill=floor)
    d.rectangle(box, fill=(110, 95, 140))
    for k in range(lines + 1):
        x = -CW + k * 3 * CW / lines
        d.line([x, CH, vx + (x - vx) * back, box[3]], fill=(60, 45, 85), width=1)
    for c in ((0, 0), (CW, 0), (0, CH), (CW, CH)):
        d.line([c[0], c[1], box[0] if c[0] == 0 else box[2], box[1] if c[1] == 0 else box[3]], fill=(40, 30, 60), width=2)
    return box


def picture(name: str, rule: str, draw) -> Image.Image:
    im = Image.new("RGB", (CW, CH + LAB), (17, 17, 17))
    pic = Image.new("RGB", (CW, CH), (70, 52, 100))
    draw(ImageDraw.Draw(pic))
    im.paste(pic, (0, LAB))
    t = ImageDraw.Draw(im)
    t.text((4, 3), name, fill=(255, 230, 120))
    t.text((4, 17), rule, fill=(220, 220, 220))
    return im


def _top(d):
    d.rectangle([0, 0, CW, CH], fill=(90, 70, 110))
    for k in range(0, CW, 30):
        d.line([k, 0, k, CH], fill=(60, 45, 85))
    for k in range(0, CH, 30):
        d.line([0, k, CW, k], fill=(60, 45, 85))
    d.ellipse([CW / 2 - 26, CH / 2 - 26, CW / 2 + 26, CH / 2 + 26], fill=(235, 205, 190), outline=(40, 30, 50), width=2)


def _occluder(d):
    room(d, 0.45, 0.35)
    figure(d, CW / 2, CH * 0.2, CH * 0.62)
    d.rectangle([0, 0, CW * 0.12, CH], fill=(30, 22, 40))                 # door frame, left
    d.rounded_rectangle([CW * 0.55, CH * 0.78, CW * 1.1, CH * 1.2], radius=14, fill=(150, 40, 50))   # seat back
    d.rounded_rectangle([-CW * 0.1, CH * 0.82, CW * 0.4, CH * 1.2], radius=14, fill=(150, 40, 50))


def rows() -> list:
    def fig_in(hz, back, top, h, x=0.5):
        return lambda d: (room(d, hz, back), figure(d, CW * x, CH * top, CH * h))

    def deep(d):
        box = room(d, 0.45, 0.12, lines=10)
        d.rectangle([box[0] + 2, box[1] + 2, box[2] - 2, box[3] - 6], fill=(170, 210, 240))   # far window: far layer
        figure(d, CW * 0.27, CH * 0.24, CH * 0.6)

    def shallow(d):
        d.rectangle([0, 0, CW, CH], fill=(110, 95, 140))                   # a wall right behind
        figure(d, CW / 2, CH * 0.12, CH * 0.85)
    return [
        [cell("ecu", "edge cuts the head", CH * 3.2, -CH * 0.35),
         cell("cu", "edge between chin and chest", CH * 2.0, CH * 0.05),
         cell("med", "edge between chest and knees", CH * 1.3, CH * 0.08),
         cell("wide", "whole figure, >= 1/4 of height", CH * 0.62, CH * 0.22),
         cell("huge", "figure under 1/4 of height", CH * 0.18, CH * 0.5)],
        [picture("cam_height low", "horizon low, ceiling seen", fig_in(0.85, 0.3, 0.05, 0.9)),
         picture("cam_height eye", "horizon at eye level", fig_in(0.42, 0.3, 0.22, 0.62)),
         picture("cam_height high", "horizon high, floor behind", fig_in(0.08, 0.3, 0.3, 0.55)),
         picture("cam_height top", "straight down", _top)],
        [picture("lens wide", "lines rush, far wall small", fig_in(0.45, 0.12, 0.14, 0.8, x=0.25)),
         picture("lens normal", "", fig_in(0.45, 0.35, 0.2, 0.65)),
         picture("lens long", "flat, far wall fills frame", fig_in(0.45, 0.85, 0.25, 0.6))],
        [picture("depth shallow", "layers: mid", shallow),
         picture("depth mid", "layers: mid bg", fig_in(0.45, 0.4, 0.22, 0.62)),
         picture("depth deep", "layers: mid bg far", deep),
         picture("occluder", "layers: fg mid bg", _occluder)],
    ]


def main() -> None:
    grid = rows()
    cols = max(len(r) for r in grid)
    sheet = Image.new("RGB", (cols * (CW + PAD) + PAD, len(grid) * (CH + LAB + PAD) + PAD), (17, 17, 17))
    for j, row in enumerate(grid):
        for k, c in enumerate(row):
            sheet.paste(c, (PAD + k * (CW + PAD), PAD + j * (CH + LAB + PAD)))
    sheet.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
