"""kit use and the hero colour check (specs/022 T008, T027)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import kit  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"
CAT = {"hair": ["bald", "short"], "hats": ["cap"], "avoid_hero": {"hoodie": "#4f78b8", "min_delta_e": 25}}


def studio(root, *args):
    return subprocess.run(["sh", str(REPO / "bin" / "studio"), *map(str, args)], capture_output=True, text=True,
                          env={**os.environ, "STUDIO_ROOT": str(root), "STUDIO_LIB": "/nonexistent"})


def make_root(with_kit=True):
    TMP.mkdir(exist_ok=True)
    root = Path(tempfile.mkdtemp(dir=TMP))
    k = root / "my-styles" / "duskish" / "kit"
    if with_kit:
        (k / "test").mkdir(parents=True)
        (k / "film.js").write_text("export const v = 1;\n")
        (k / "catalog.json").write_text(json.dumps(CAT))
        (k / "test" / "a.test.mjs").write_text("// not copied\n")
    else:
        (root / "my-styles" / "duskish").mkdir(parents=True)
    (root / "films" / "demo").mkdir(parents=True)
    return root


def attach(root, film="demo", **film_fields):
    snap = {"channel": "mine", "film": {"style": "duskish", **film_fields}, "rules": {}}
    (root / "films" / film / "channel.json").write_text(json.dumps(snap))


class KitUse(unittest.TestCase):
    def test_template_comes_with_the_kit(self):                            # specs/023 T036
        root = make_root()
        tpl = root / "my-styles" / "duskish" / "template.json"
        tpl.write_text(json.dumps({"motion": {"rise_s": [0.25, 0.83]}}))
        self.assertEqual(studio(root, "kit", "use", "demo", "--style", "duskish").returncode, 0)
        got = json.loads((root / "films" / "demo" / "kit" / "template.json").read_text())
        self.assertEqual(got["motion"]["rise_s"], [0.25, 0.83])
        # a new template is a new kit: refused without --update, copied with it
        tpl.write_text(json.dumps({"motion": {"rise_s": [0.3, 0.8]}}))
        self.assertNotEqual(studio(root, "kit", "use", "demo", "--style", "duskish").returncode, 0)
        self.assertEqual(studio(root, "kit", "use", "demo", "--style", "duskish", "--update").returncode, 0)
        got = json.loads((root / "films" / "demo" / "kit" / "template.json").read_text())
        self.assertEqual(got["motion"]["rise_s"], [0.3, 0.8])

    def test_first_copy_same_and_changed(self):
        root = make_root()
        r = studio(root, "kit", "use", "demo", "--style", "duskish")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("✓ kit: duskish", r.stdout)
        dst = root / "films" / "demo" / "kit"
        self.assertTrue((dst / "film.js").is_file())
        self.assertFalse((dst / "test").exists())
        frm = json.loads((dst / ".from").read_text())
        self.assertEqual(frm["style"], "duskish")
        self.assertEqual(frm["sha256"], kit.kit_hash(root / "my-styles" / "duskish" / "kit"))
        # same hash: nothing to do
        r = studio(root, "kit", "use", "demo", "--style", "duskish")
        self.assertEqual(r.returncode, 0)
        self.assertIn("up to date", r.stdout)
        # the style's kit changed: refuse without --update
        (root / "my-styles" / "duskish" / "kit" / "film.js").write_text("export const v = 2;\n")
        r = studio(root, "kit", "use", "demo", "--style", "duskish")
        self.assertEqual(r.returncode, 2)
        self.assertIn("--update", r.stderr)
        self.assertIn("v = 1", (dst / "film.js").read_text())
        r = studio(root, "kit", "use", "demo", "--style", "duskish", "--update")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("v = 2", (dst / "film.js").read_text())

    def test_style_from_channel_and_hint(self):
        root = make_root()
        attach(root)
        r = studio(root, "kit", "use", "demo")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("hint: set the channel hero", r.stdout)
        attach(root, hero={"hoodie": "#d9b23a", "hair": "bald"})
        r = studio(root, "kit", "use", "demo", "--json")
        self.assertEqual(json.loads(r.stdout)["hint"], "")

    def test_errors(self):
        root = make_root(with_kit=False)
        r = studio(root, "kit", "use", "demo", "--style", "duskish")
        self.assertEqual(r.returncode, 2)
        self.assertIn("has no kit", r.stderr)
        root = make_root()
        r = studio(root, "kit", "use", "demo")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no style", r.stderr)

    def test_hero_too_close_to_reference(self):
        root = make_root()
        attach(root, hero={"hoodie": "#5078b4"})
        r = studio(root, "kit", "use", "demo")
        self.assertEqual(r.returncode, 2)
        self.assertIn("too close to the reference character", r.stderr)


class Colour(unittest.TestCase):
    def test_delta_e(self):
        self.assertAlmostEqual(kit.delta_e("#000000", "#000000"), 0)
        self.assertAlmostEqual(kit.delta_e("#000000", "#ffffff"), 100, delta=0.1)
        self.assertGreater(kit.delta_e("#d9b23a", "#4f78b8"), 60)
        self.assertLess(kit.delta_e("#5078b4", "#4f78b8"), 5)
        self.assertEqual(kit.hero_problem({"hoodie": "#d9b23a"}, CAT), "")
        self.assertIn("ΔE", kit.hero_problem({"hoodie": "#4a74b0"}, CAT))


if __name__ == "__main__":
    unittest.main()
