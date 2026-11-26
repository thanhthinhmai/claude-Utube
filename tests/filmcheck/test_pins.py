"""specs/035 T037: the pinned notes shared by the cast sheet and the Animatic (filmcheck/pins.py, research R9)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from filmcheck import pins  # noqa: E402


class Pins(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.book = pins.Book("sub/notes.json", "shots")

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, key, **f):
        doc = self.book.load(self.d)
        n = self.book.new(doc, key, **f)
        self.book.write(self.d, doc)
        return n

    def test_empty_and_base(self):
        self.assertEqual(self.book.load(self.d), {"version": 1, "shots": {}})
        b0 = self.book.base(self.d)
        self.add("S2", kind="note", frame=None, x=None, y=None, text="general")      # a general note: frame null
        self.assertNotEqual(self.book.base(self.d), b0)
        self.assertEqual(json.loads((self.d / "sub" / "notes.json").read_text())["shots"]["S2"]["notes"][0]["frame"], None)
        with self.assertRaises(pins.PinError) as e:
            self.book.check_base(self.d, b0)
        self.assertEqual((e.exception.code, e.exception.exit_code()), ("changed", 4))
        self.assertIn("doc", e.exception.current)

    def test_xy_and_text(self):
        self.assertEqual(pins.xy("40", 30.04), (40.0, 30.0))
        for bad in ((-1, 0), (0, 100.1), ("a", 1)):
            with self.assertRaises(pins.PinError):
                pins.xy(*bad)
        for bad in ("", "   ", "x" * (pins.TEXT_MAX + 1), None):
            with self.assertRaises(pins.PinError):
                pins.text(bad)

    def test_lot_reply_and_late_notes(self):
        a = self.add("S2", text="faster")
        b = self.add("S6", text="slower")
        lot = self.book.start_lot(self.d, "j1")
        self.assertEqual(lot["notes"], [a["id"], b["id"]])
        late = self.add("S6", text="late")
        self.assertNotIn(late["id"], self.book.load(self.d)["lot"]["notes"])        # waits for the next lot
        self.book.reply(self.d, a["id"], "faster now", done=True)
        self.book.end_lot(self.d, "j1")
        doc = self.book.load(self.d)
        self.assertEqual(doc["last_lot"]["notes"], [a["id"], b["id"]])
        self.assertEqual(self.book.open_counts(self.d), {"S6": 2})
        self.assertEqual(self.book.summary(self.d), "2 notes on: S6")
        self.book.delete(self.d, "S6", late["id"])
        with self.assertRaises(pins.PinError):
            self.book.reply(self.d, "n-none", "x")

    def test_failed_lot_and_other_job(self):
        self.add("S2", text="faster")
        self.book.start_lot(self.d, "j1")
        self.book.end_lot(self.d, "other", error="x")                            # not this job's lot: nothing
        self.assertIn("lot", self.book.load(self.d))
        self.book.end_lot(self.d, "j1", error="AE stopped")
        doc = self.book.load(self.d)
        self.assertEqual((doc["failed_lot"]["error"], self.book.open_counts(self.d)), ("AE stopped", {"S2": 1}))

    def test_bad_file(self):
        (self.d / "sub").mkdir()
        (self.d / "sub" / "notes.json").write_text("{nope")
        with self.assertRaises(pins.PinError) as e:
            self.book.load(self.d)
        self.assertEqual(e.exception.code, "bad_notes")


if __name__ == "__main__":
    unittest.main()
