"""Thumbnails drawn from the film's own page (specs/011 T007, R2, R3). Skipped without node and the library."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import publish  # noqa: E402

import samples  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"
LIB = REPO / "lib" / "lemo-opuscar"
HAVE = shutil.which("node") and (LIB / "node_modules" / "playwright-core").is_dir()


@unittest.skipUnless(HAVE, "needs node and the library's playwright-core")
class Thumbs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TMP.mkdir(exist_ok=True)
        cls.root = Path(tempfile.mkdtemp(dir=TMP))

    def test_landscape_pack_passes(self):
        d = samples.make_publish_film(self.root, "land")
        publish.build(d, LIB)
        rows = json.loads((d / "publish" / "thumbs.json").read_text())
        self.assertEqual(len(rows), 3)
        for r in rows:
            self.assertEqual((r["w"], r["h"]), (1280, 720))
            self.assertGreaterEqual(r["text_height_ratio"], 0.08)
            self.assertGreaterEqual(r["contrast"], 4.5)
            self.assertTrue(r["font_loaded"])
        self.assertEqual(publish.image_size(d / "publish" / "thumbnail-1.png"), (1280, 720))
        r = publish.check(d)
        self.assertEqual(r["problems"], [])

    def test_vertical_film_gets_vertical_thumbnails(self):
        d = samples.make_publish_film(self.root, "tall", vertical=True)
        publish.build(d, LIB)
        self.assertEqual(publish.image_size(d / "publish" / "thumbnail-2.png"), (720, 1280))
        self.assertEqual(publish.check(d)["problems"], [])

    def test_big_picture_is_saved_as_jpeg(self):                 # FR-002, T032
        d = samples.make_publish_film(self.root, "big")
        old = publish.THUMB_BYTES
        publish.THUMB_BYTES = 20_000           # every PNG of the sample is bigger than this
        try:
            publish.build(d, LIB)
            files = publish.thumb_files(d)
            self.assertEqual(files, ["thumbnail-1.jpg", "thumbnail-2.jpg", "thumbnail-3.jpg"])
            self.assertFalse((d / "publish" / "thumbnail-1.png").exists())
            self.assertEqual(publish.image_size(d / "publish" / "thumbnail-1.jpg"), (1280, 720))
            publish.THUMB_BYTES = old
            self.assertNotIn("thumb_size", [p.split(":")[0] for p in publish.check(d)["problems"]])
        finally:
            publish.THUMB_BYTES = old

    def test_white_on_white_fails_contrast(self):
        d = samples.make_publish_film(self.root, "pale")
        (d / "index.html").write_text((d / "index.html").read_text().replace("hsl(${(t * 7) % 360},60%,30%)", "#ffffff"))
        pk = json.loads((d / "publish" / "pack.json").read_text())
        pk["titles"][0]["thumb"].update({"color": "#ffffff", "plate": None})
        (d / "publish" / "pack.json").write_text(json.dumps(pk))
        publish.build(d, LIB)
        rows = json.loads((d / "publish" / "thumbs.json").read_text())
        self.assertLess(rows[0]["contrast"], 1.5)
        self.assertIn("thumb_contrast", [p.split(":")[0] for p in publish.check(d)["problems"]])


if __name__ == "__main__":
    unittest.main()
