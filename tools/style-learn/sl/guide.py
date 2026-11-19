"""Draw the shot labeler's guide image (specs/021 SC-001 fix): one generic sphere-headed figure at each shot scale,
with the frame's bottom edge cutting the figure where the rule says. Code-drawn, so it can live in git and travel with
the studio. Run: tools/.venv/bin/python tools/style-learn/sl/guide.py  → tools/filmcheck/labeler-guide.png"""
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


def main() -> None:
    cells = [
        cell("ecu", "edge cuts the head", CH * 3.2, -CH * 0.35),
        cell("cu", "edge between chin and chest", CH * 2.0, CH * 0.05),
        cell("med", "edge between chest and knees", CH * 1.3, CH * 0.08),
        cell("wide", "whole figure, >= 1/4 of height", CH * 0.62, CH * 0.22),
        cell("huge", "figure under 1/4 of height", CH * 0.18, CH * 0.5),
    ]
    sheet = Image.new("RGB", (len(cells) * (CW + PAD) + PAD, CH + LAB + 2 * PAD), (17, 17, 17))
    for k, c in enumerate(cells):
        sheet.paste(c, (PAD + k * (CW + PAD), PAD))
    sheet.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
