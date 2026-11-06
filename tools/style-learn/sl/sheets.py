"""Contact sheets: every 2 s of video becomes one image holding every frame of those 2 s (research.md §9)."""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

COLS = 10


class SheetWriter:
    def __init__(self, out_dir: Path, vid: str, fps: float, orientation: str, frame_h: int, frame_w: int = 320):
        self.out, self.vid = out_dir, vid
        self.per = max(1, round(2 * fps))
        self.cw = 128 if orientation != "portrait" else 72
        self.ch = max(2, round(self.cw * frame_h / frame_w))
        self.rows = math.ceil(self.per / COLS)
        self.cells, self.label, self.seg, self.files = [], None, None, []
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)

    def add(self, frame: np.ndarray, t: float, seg: int) -> None:
        if self.cells and (seg != self.seg or len(self.cells) == self.per):
            self.flush()
        if not self.cells:
            self.label, self.seg = t, seg
        self.cells.append(Image.fromarray(frame).resize((self.cw, self.ch), Image.BILINEAR))

    def flush(self) -> None:
        if not self.cells:
            return
        sheet = Image.new("RGB", (COLS * self.cw, self.rows * self.ch), (0, 0, 0))
        for k, im in enumerate(self.cells):
            sheet.paste(im, ((k % COLS) * self.cw, (k // COLS) * self.ch))
        d = ImageDraw.Draw(sheet)
        txt = f"{self.label:.2f}s"
        d.rectangle([0, 0, 7 * len(txt) + 6, 14], fill=(0, 0, 0))
        d.text((3, 2), txt, fill=(255, 255, 0))
        name = f"{self.vid}_{len(self.files):04d}.jpg"
        if self.out:
            sheet.save(self.out / name, quality=80)
        self.files.append(name)
        self.cells = []
