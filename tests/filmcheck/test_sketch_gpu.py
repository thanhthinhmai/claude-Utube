"""GPU-safe drawing in the Sketch Explainer kit and the people library (specs/028 T030, T031; FR-019, FR-020, SC-005).

The machine's GPU Chrome does not fill SVG arc commands, breaks rounded `rx` corners, and shows seams on a thick
stroked polyline around a filled shape. Part 1 scans the code; part 2 renders the kit's catalogue on the GPU and in
software and compares them tile by tile (skipped without a GPU).
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
KIT = REPO / "my-styles" / "sketch-explainer" / "kit"
LIB = REPO / "lib" / "lemo-opuscar"

# a path string: d="…" (markup) or d: '…' / `…` (an attribute object); not a default parameter such as d = '#4f9a5e'
D_ATTR = re.compile(r"""\bd(?:=|:\s*)(["'`])(.*?)\1""", re.S)
ARC = re.compile(r"(?<![A-Za-z$])[Aa]\s*-?\d")
RX = re.compile(r"""\brx\s*[:=]""")
ELLIPSE = re.compile(r"<ellipse\b|'ellipse'|\"ellipse\"")
# a filled path with a thick stroke: fill other than none and stroke-width ≥ 6
FILLED_THICK = re.compile(r"""<path\b[^>]*\bd="([^"]*)"[^>]*>""")


def sources():
    files = sorted(KIT.rglob("*.js")) + sorted((REPO / "people").glob("*/figure.js"))
    return [p for p in files if "examples" not in p.parts]


def problems(text: str, name: str = "") -> list:
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in D_ATTR.finditer(line):
            d = re.sub(r"\$\{[^}]*\}", "0", m.group(2))
            if ARC.search(d):
                out.append(f"{name}:{i}: arc command in a path")
        if RX.search(line) and not ELLIPSE.search(line):
            out.append(f"{name}:{i}: rx corner (use rrect)")
        for m in FILLED_THICK.finditer(line):
            tag = m.group(0)
            fill = re.search(r'fill="([^"]*)"', tag)
            sw = re.search(r'stroke-width="(\d+(?:\.\d+)?)"', tag)
            if fill and fill.group(1) != "none" and sw and float(sw.group(1)) >= 6 and "stroke=\"none\"" not in tag:
                # the seam shows on wide, flat filled shapes (the bar charts of two earlier films); small shapes render fine
                for sub in ([] if "$" in m.group(1) or re.search(r"[CQcq]", m.group(1)) else re.split(r"(?=[Mm])", m.group(1))):
                    nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", sub)]
                    if len(nums) < 8:
                        continue
                    xs, ys = nums[0::2], nums[1::2]
                    w, h = max(xs) - min(xs), max(ys) - min(ys)
                    if w >= 200 and h <= w / 3:
                        out.append(f"{name}:{i}: thick outline on a wide flat filled shape {w:.0f}×{h:.0f} (use segOutline)")
    return out


class StaticScan(unittest.TestCase):
    def test_the_scan_catches_the_known_faults(self):
        bad = ['<path d="M0 0 A10 10 0 0 1 20 0 Z" fill="#fff"/>', "el('rect', {x: 0, y: 0, width: 9, height: 9, rx: 30})",
               '<path d="M0 0 L400 0 L420 40 L400 80 L0 80 Z" fill="#c33" stroke-width="9"/>']
        for b in bad:
            self.assertTrue(problems(b), b)
        good = ['<path d="M0 0 C10 0 20 10 20 20 Z" fill="#fff"/>', '<ellipse class="eyeL" cx="-48" cy="-6" rx="11" ry="16"/>',
                '<path d="M0 0 L100 0 L100 80 L0 80 Z" fill="#c33" stroke="none"/>', "const col = (c, d = '#4f9a5e') => c || d;",
                '<path d="M-48 132 L-84 196 L-30 178 L0 214 L30 178 L84 196 L48 132" fill="#eee" stroke-width="6"/>']
        for g in good:
            self.assertFalse(problems(g), g)

    def test_kit_and_people_are_gpu_safe(self):
        found = []
        for p in sources():
            found += problems(p.read_text(encoding="utf-8"), str(p.relative_to(REPO)))
        self.assertFalse(found, "\n".join(found))


def gpu_available() -> bool:
    if os.environ.get("STUDIO_TEST_GPU") == "0" or not shutil.which("node") or not (LIB / "node_modules" / "playwright-core").is_dir():
        return False
    try:
        st = json.loads(subprocess.run(["sh", str(REPO / "bin" / "studio"), "status", "--json"], capture_output=True, text=True, timeout=60).stdout or "{}")
    except (ValueError, subprocess.TimeoutExpired):
        return False
    return "gpu" in json.dumps(st).lower() and "software" not in str(st.get("render", "")).lower()


SHOT = r"""
import path from 'node:path'; import { pathToFileURL } from 'node:url';
const [dir, lib, out] = process.argv.slice(2);
const P = await import(pathToFileURL(path.join(lib, 'core/render/page.mjs')).href);
const { browser, page } = await P.openDemo(dir, { w: 960, h: 540 });
const shots = await page.evaluate(() => window.SHOTS);
for (const s of shots) { await page.evaluate(t => window.render(t), s[0] + 0.7); await page.screenshot({ path: `${out}/${s[3]}.png` }); }
await browser.close(); P.closeServer();
"""


@unittest.skipUnless(gpu_available(), "needs the GPU renderer (sh bin/studio status shows GPU)")
class GpuMatchesSoftware(unittest.TestCase):
    def test_catalogue_tiles_match(self):
        import numpy as np
        tmp = Path(tempfile.mkdtemp())
        page = tmp / "page"
        shutil.copytree(KIT, page)
        shutil.copy(page / "catalog.html", page / "index.html")
        (tmp / "shot.mjs").write_text(SHOT)
        outs = {}
        for name, env in (("soft", {}), ("gpu", {"PLAYWRIGHT_CHROME": str(REPO / "tools" / "render" / "chrome-gpu.sh")})):
            d = tmp / name
            d.mkdir()
            subprocess.run(["node", str(tmp / "shot.mjs"), str(page), str(LIB), str(d)], env={**os.environ, **env}, check=True, capture_output=True, timeout=900)
            outs[name] = d
        bad = []
        for f in sorted(outs["soft"].glob("*.png")):
            a = self._px(f)
            b = self._px(outs["gpu"] / f.name)
            diff = float(np.abs(a.astype(int) - b.astype(int)).mean())
            if diff > 6:
                bad.append(f"{f.stem}: mean difference {diff:.1f}/255")
        self.assertFalse(bad, "\n".join(bad))

    @staticmethod
    def _px(p: Path):
        import numpy as np
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
        return np.frombuffer(raw, np.uint8)


if __name__ == "__main__":
    unittest.main()
