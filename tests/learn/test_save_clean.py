import json
import unittest

from PIL import Image

from helpers import Project
from sl import refset, save


class SaveClean(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        data = refset.new_set("learned-set", "channel", ["https://example.invalid/@meoluoi"])
        data["videos"].append({"id": "v01", "file": "v01.mp4", "origin": "https://example.invalid/v/1",
                               "title": "Why bridges fall down", "channel": "Mèo Lười Studio", "handle": "@meoluoi",
                               "state": "transcribed"})
        refset.save("learned-set", data)
        d = self.d = refset.set_dir("learned-set")
        (d / "videos").mkdir()
        (d / "videos" / "v01.mp4").write_bytes(b"x" * 1000)
        prof = d / "profile" / "v01"
        (prof / "sheets").mkdir(parents=True)
        (prof / "sheets" / "v01_0000.jpg").write_bytes(b"jpg")
        refset.write_json(prof / "words.json", {"words": [{"word": "hello", "start": 0, "end": .5}]})
        refset.write_json(prof / "video.json", {"schema": "style-learn/1"})
        refset.write_json(d / "profile" / "summary.json", {"schema": "style-learn/1", "set": "learned-set",
                          "by_orientation": {"landscape": {"videos": 1}}, "skipped": [{"id": "v02", "reason": "x"}],
                          "videos_measured": 1, "measured_seconds": 60.0, "majority_orientation": "landscape"})
        (d / "style").mkdir()
        (d / "style" / "STYLE.md").write_text("# Night Ink — Style Prompt\nInk outlines (evidence: summary luma_p50 0.42).\n")
        (d / "style" / "EVIDENCE.md").write_text("# Evidence\n")
        refset.write_json(d / "style" / "style.json", {"line": "Night streets in ink.", "line_cn": ""})
        (d / "proof" / "out").mkdir(parents=True)
        (d / "proof" / "index.html").write_text("<script>window.render=t=>{};window.READY=true</script>")
        Image.new("RGB", (64, 36), (20, 30, 40)).save(d / "proof" / "out" / "t_0.jpg")
        Image.new("RGB", (64, 36), (90, 30, 40)).save(d / "proof" / "out" / "ours_r1_0.jpg")
        Image.new("RGB", (64, 36), (9, 9, 9)).save(d / "proof" / "out" / "ref.jpg")      # frame from a reference video
        (d / "proof" / "compare.jpg").write_bytes(b"jpg")
        refset.write_json(d / "proof" / "compare.json", {"pass": True, "ours": "proof/out/t_0.jpg", "round": 1})
        other = refset.refs_dir() / "other-set" / "videos"
        other.mkdir(parents=True)
        (other / "keep.mp4").write_bytes(b"y")

    def tearDown(self):
        self.p.close()

    def call(self, slug="night-ink", en="Night Ink", accept=False):
        try:
            return save.save("learned-set", slug, en, "", "ink-wash", accept)
        except refset.StepError:
            return 1

    def test_rejects(self):  # FR-021, SC-006
        self.assertEqual(self.call(slug="watercolor"), 1)                  # library slug
        self.assertEqual(self.call(slug="meo-luoi-studio"), 1)             # channel name in slug
        self.assertEqual(self.call(en="Meo Luoi Night"), 1)                # channel name in name
        (self.d / "style" / "clip.mp4").write_bytes(b"x")
        self.assertEqual(self.call(), 1)                                   # media in the package
        (self.d / "style" / "clip.mp4").unlink()
        refset.write_json(self.d / "proof" / "compare.json", {"pass": False, "ours": "proof/out/t_0.jpg"})
        self.assertEqual(self.call(), 1)                                   # proof not passed, not accepted
        self.assertEqual(self.call(accept=True), 0)
        self.assertEqual(self.call(), 1)                                   # slug now taken

    def test_rejects_raster_in_proof(self):  # Constitution (copyright), T035
        Image.new("RGB", (8, 8)).save(self.d / "proof" / "texture.png")
        self.assertEqual(self.call(), 1)
        (self.d / "proof" / "texture.png").unlink()
        self.assertEqual(self.call(), 0)

    def test_saved_package_and_catalog(self):  # SC-008
        self.assertEqual(self.call(), 0)
        s = self.p.dir / "my-styles" / "night-ink"
        for f in ("STYLE.md", "EVIDENCE.md", "style.json", "measurements/summary.json", "styleframe.jpg",
                  "styleframe/index.html"):
            self.assertTrue((s / f).exists(), f)
        self.assertFalse((s / "styleframe" / "out").exists())
        meta = json.loads((s / "style.json").read_text())
        self.assertEqual(meta["slug"], "night-ink")
        self.assertEqual(meta["based_on"], "ink-wash")
        self.assertEqual(meta["source"], "learned")
        blob = (s / "measurements" / "summary.json").read_text() + (s / "style.json").read_text()
        for bad in ("learned-set", "Why bridges", "Lười", "example.invalid", "v02"):
            self.assertNotIn(bad, blob)
        rows = [l for l in (self.p.dir / "my-styles" / "README.md").read_text().splitlines() if l.startswith("| night-ink ")]
        self.assertEqual(len(rows), 1)

    def test_clean(self):  # FR-004a, SC-006
        self.assertEqual(save.clean("learned-set", keep=False), 0)
        self.assertFalse((self.d / "videos").exists())
        self.assertFalse((self.d / "profile" / "v01" / "words.json").exists())
        self.assertFalse((self.d / "profile" / "v01" / "sheets").exists())
        self.assertFalse((self.d / "proof" / "compare.jpg").exists())
        self.assertFalse((self.d / "proof" / "out" / "ref.jpg").exists())       # reference frame removed
        self.assertTrue((self.d / "proof" / "out" / "ours_r1_0.jpg").exists())   # our own drawing kept
        self.assertTrue((self.d / "profile" / "summary.json").exists())
        self.assertTrue((self.d / "profile" / "v01" / "video.json").exists())
        self.assertTrue((refset.refs_dir() / "other-set" / "videos" / "keep.mp4").exists())
        v = refset.load("learned-set")["videos"][0]
        for k in ("origin", "title", "channel", "handle"):
            self.assertNotIn(k, v)

    def test_keep(self):
        self.assertEqual(save.clean("learned-set", keep=True), 0)
        self.assertTrue((self.d / "videos" / "v01.mp4").exists())


if __name__ == "__main__":
    unittest.main()
