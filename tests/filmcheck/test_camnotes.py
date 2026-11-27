"""Camera notes (specs/039 T030): add and remove pins, the summary by shot, the edit ops refuse an old base, a fix on
the noted shots leaves the other shots byte for byte."""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from filmcheck import camnotes, camsuggest, edit  # noqa: E402
import test_camsuggest as ts  # noqa: E402


class CamNotes(ts.Base):
    def setUp(self):
        super().setUp()
        self.d = ts.make_film(self.root, plan=ts.PLAN)
        camsuggest.suggest(self.d)

    def test_add_list_remove(self):
        n = camnotes.add(self.d, "s2", 1, 40, 60, "slower push")
        self.assertEqual((n["shot"], n["option"], n["x"], n["y"]), ("S2", 1, 40.0, 60.0))
        self.assertEqual(list(camnotes.open_notes(self.d)), ["S2"])
        camnotes.remove(self.d, n["id"])
        self.assertEqual(camnotes.open_notes(self.d), {})

    def test_bad_pins(self):
        for args, code in ((("S9", 1, 5, 5, "x"), "bad_shot"), (("S1", 7, 5, 5, "x"), "bad_note"),
                           (("S1", 1, 150, 5, "x"), "bad_pin"), (("S1", 1, 5, 5, " "), "bad_text")):
            with self.assertRaises(camnotes.CamNoteError) as e:
                camnotes.add(self.d, *args)
            self.assertEqual(e.exception.code, code)
            self.assertEqual(e.exception.exit_code(), 2)

    def test_summary_in_film_order(self):
        camnotes.add(self.d, "S3", 1, 5, 5, "a")
        camnotes.add(self.d, "S1", 2, 5, 5, "b")
        camnotes.add(self.d, "S3", 2, 5, 5, "c")
        self.assertEqual(camnotes.summary(self.d), "3 camera notes on: S1, S3")
        self.assertEqual(camnotes.open_shots(self.d), ["S1", "S3"])

    def test_old_base_refused(self):
        b = camnotes.base(self.d)
        camnotes.add(self.d, "S1", 1, 5, 5, "first")
        with self.assertRaises(camnotes.CamNoteError) as e:
            camnotes.add(self.d, "S1", 1, 5, 5, "second", b=b)
        self.assertEqual(e.exception.exit_code(), 4)

    def test_ops(self):
        b = edit.OPS["camera-note-add"]["fp"](self.d)
        r = edit.run(self.d, "camera-note-add", {"shot": "S2", "option": 1, "x": 10, "y": 20, "text": "tighter"}, base=b)
        self.assertTrue(r["ok"], r)
        r2 = edit.run(self.d, "camera-note-add", {"shot": "S2", "option": 1, "x": 10, "y": 20, "text": "again"}, base=b)
        self.assertEqual(r2["code"], 4)                                    # opened before the first note
        nid = r["ref"]
        r = edit.run(self.d, "camera-note-remove", {"note": nid}, base=r["fingerprint"])
        self.assertTrue(r["ok"], r)
        n2 = camsuggest.load(self.d)["shots"]["S1"]["options"][1]["n"]
        r = edit.run(self.d, "camera-choose", {"shot": "S1", "n": n2})
        self.assertTrue(r["ok"], r)
        self.assertIn("camera", json.loads((self.d / "film.json").read_text())["shot_plan"]["S1"])
        self.assertEqual(edit.run(self.d, "camera-choose", {"shot": "S1", "n": 9})["code"], 2)

    def test_fix_changes_only_noted_shots(self):
        camnotes.add(self.d, "S2", 1, 5, 5, "less zoom")
        before = camsuggest.load(self.d)["shots"]
        camsuggest.suggest(self.d, shots=camnotes.open_shots(self.d), keep_others=True)
        after = camsuggest.load(self.d)["shots"]
        for s in ("S1", "S3"):
            self.assertEqual(json.dumps(after[s], sort_keys=True), json.dumps(before[s], sort_keys=True))


if __name__ == "__main__":
    unittest.main()
