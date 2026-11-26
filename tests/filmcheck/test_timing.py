"""specs/035 T003, T005: timing.json (shot lengths) and lines that move with their shots."""
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
sys.path.insert(0, str(HERE))

import animfilm  # noqa: E402
from filmcheck import timing  # noqa: E402

FRAMES = {"S1": 75, "S2": 117, "S3": 83, "S4": 48, "S5": 78, "S6": 120, "S7": 138, "S8": 108, "S9": 90}


class Timing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = animfilm.make(Path(self.tmp.name) / "f1", timing=False)

    def tearDown(self):
        self.tmp.cleanup()

    def test_from_marks_once(self):
        self.assertIsNone(timing.load(self.d))
        with self.assertRaises(timing.TimingError) as e:
            timing.require(self.d)
        self.assertEqual(e.exception.code, "missing")
        doc = timing.from_marks(self.d, self.d / "out" / "build-shots.json")
        self.assertEqual(doc["frames"], FRAMES)
        self.assertEqual(doc["origin"]["frames"], FRAMES)
        self.assertEqual((doc["version"], doc["fps"], doc["history"]), (1, 30, []))
        raw = timing.path(self.d).read_bytes()
        timing.from_marks(self.d, [[0, 9, "", "S1"]])                      # a film with timing.json keeps it
        self.assertEqual(timing.path(self.d).read_bytes(), raw)

    def test_bounds_and_duration(self):
        doc = timing.from_marks(self.d, self.d / "out" / "build-shots.json")
        b = timing.bounds(doc)
        self.assertEqual([x["id"] for x in b], list(FRAMES))
        self.assertEqual((b[1]["t0"], b[1]["t1"]), (2.5, 6.4))
        self.assertAlmostEqual(timing.duration(doc), 28.5667, places=3)

    def test_checks(self):
        doc = timing.from_marks(self.d, self.d / "out" / "build-shots.json")
        for bad in ({"S1": 5}, {"S1": 7.5}, {"S10": 30}):
            x = json.loads(json.dumps(doc))
            x["frames"].update(bad)
            with self.assertRaises(timing.TimingError):
                timing.save(self.d, x)
        x = json.loads(json.dumps(doc))
        del x["frames"]["S9"]
        with self.assertRaises(timing.TimingError) as e:
            timing.save(self.d, x)
        self.assertIn("missing S9", e.exception.message)
        x = json.loads(json.dumps(doc))
        x["history"] = [{}] * 60
        timing.save(self.d, x)                                             # save keeps the last 50
        self.assertEqual(len(timing.load(self.d)["history"]), 50)

    def test_marks_missing_a_shot(self):
        with self.assertRaises(timing.TimingError):
            timing.from_marks(self.d, [[0, 2.5, "", "S1"]])
        self.assertFalse(timing.path(self.d).exists())


class Lines(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = animfilm.make(Path(self.tmp.name) / "f1")

    def tearDown(self):
        self.tmp.cleanup()

    def test_lines_belong_to_the_shot_with_most_of_them(self):
        rows = timing.lines(self.d)
        self.assertEqual(len(rows), 14)
        got = {r["id"]: r["shot"] for r in rows}
        self.assertEqual((got["l01"], got["l03"], got["l06"], got["l14"]), ("S1", "S2", "S4", "S9"))
        l03 = next(r for r in rows if r["id"] == "l03")
        self.assertAlmostEqual(l03["last_word_end"], 5.82, places=3)
        self.assertAlmostEqual(l03["end"], 4.0 + 2.057, places=3)
        b = [{"id": "S1", "t0": 0, "t1": 2}, {"id": "S2", "t0": 2, "t1": 5}]
        self.assertEqual(timing.assign([("a", 1.5, 3.0), ("b", 0.2, 1.2), ("c", 4.0, 7.0)], b),
                         {"a": "S2", "b": "S1", "c": "S2"})                # a line across the cut: the bigger part

    def test_start_keeps_origin_once(self):
        timing.start(self.d)
        timing.shift(self.d, {"S2": 100})
        doc = timing.start(self.d)
        self.assertEqual(doc["origin"]["frames"]["S2"], 117)

    def test_shift_moves_lines_with_their_shots(self):
        timing.start(self.d)
        before_t, before_n = timing.path(self.d).read_bytes(), (self.d / "narration.json").read_bytes()
        b0 = timing.base(self.d)
        with self.assertRaises(timing.TimingError) as e:
            timing.shift(self.d, {"S2": 100}, expect="0" * 16)
        self.assertEqual((e.exception.code, e.exception.exit_code()), ("changed", 4))
        timing.shift(self.d, {"S2": 84}, head={"S2": 0.15}, why="fit S2", expect=b0)   # −33 frames, head 0.15 s
        doc = timing.load(self.d)
        self.assertEqual(doc["frames"]["S2"], 84)
        self.assertEqual(len(doc["history"]), 1)
        self.assertEqual(doc["history"][0]["frames"]["S2"], 117)
        at = {ln["id"]: ln["at"] for ln in json.loads((self.d / "narration.json").read_text())["lines"]}
        self.assertEqual(at["l01"], 0.3)                                    # S1 unchanged
        self.assertEqual(at["l02"], 2.5)                                    # 2.65 − head: at the cut
        self.assertEqual(at["l03"], 3.85)
        self.assertEqual(at["l04"], 5.65)                                   # S3 starts 1.1 s earlier
        self.assertEqual(at["l14"], 24.767)
        timing.undo(self.d)                                                 # same bytes back
        self.assertEqual(timing.path(self.d).read_bytes(), before_t)
        self.assertEqual((self.d / "narration.json").read_bytes(), before_n)
        with self.assertRaises(timing.TimingError) as e:
            timing.undo(self.d)
        self.assertEqual(e.exception.code, "origin")

    def test_bad_shot_and_short(self):
        with self.assertRaises(timing.TimingError) as e:
            timing.shift(self.d, {"S10": 30})
        self.assertEqual(e.exception.code, "bad_shot")
        with self.assertRaises(timing.TimingError):
            timing.shift(self.d, {"S2": 3})
        self.assertEqual(timing.load(self.d)["history"], [])

    def test_lock_serialises_writers(self):
        timing.start(self.d)
        errs = []

        def go(n):
            try:
                timing.shift(self.d, {"S1": 60 + n})
            except Exception as e:          # noqa: BLE001
                errs.append(e)
        ts = [threading.Thread(target=go, args=(i,)) for i in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(errs, [])
        doc = timing.load(self.d)
        self.assertEqual(len(doc["history"]), 8)
        at = json.loads((self.d / "narration.json").read_text())["lines"][1]["at"]
        self.assertAlmostEqual(at, 2.65 + (doc["frames"]["S1"] - 75) / 30, places=3)


if __name__ == "__main__":
    unittest.main()
