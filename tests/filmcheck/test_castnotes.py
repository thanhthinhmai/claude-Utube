"""Notes on the cast sheet (specs/034 T026): pins, view requests, bases, lots, states, CLI."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from filmcheck import cast, castnotes, edit  # noqa: E402
import castfilm  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"


def sheet(d: Path, cid: str, missing=("34",)) -> None:
    s = d / "cast" / "sheets" / cid
    s.mkdir(parents=True, exist_ok=True)
    frames = []
    for k in ("front", "back", "34"):
        if k in missing:
            frames.append({"key": k, "group": "turn", "label": k, "file": None, "missing_reason": "build error"})
        else:
            (s / f"{k}.jpg").write_bytes(b"\xff\xd8" + k.encode())
            frames.append({"key": k, "group": "turn", "label": k, "file": f"{k}.jpg"})
    (s / "sheet.json").write_text(json.dumps({"character": cid, "rig": "ball@1", "built_at": "x", "frames": frames}))


class Notes(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(exist_ok=True)
        self.d = castfilm.make(Path(tempfile.mkdtemp(dir=TMP)) / "films" / "f1")
        for c in ("hero", "friend", "classmates"):
            sheet(self.d, c)

    def err(self, fn, *a, **kw):
        with self.assertRaises(castnotes.CastNoteError) as c:
            fn(*a, **kw)
        return c.exception.code

    def test_add_edit_delete(self):
        n = castnotes.add(self.d, "friend", "note", "front", 42.54, 8, "Hair: bigger curls")
        self.assertRegex(n["id"], r"^n-[0-9a-f]{8}$")
        self.assertEqual((n["x"], n["y"]), (42.5, 8.0))
        g = castnotes.add(self.d, "friend", text="A bit taller than the hero")
        self.assertIsNone(g["frame"])
        castnotes.edit(self.d, "friend", n["id"], x=50, y=20)
        moved = castnotes.load(self.d)["characters"]["friend"]["notes"][0]
        self.assertEqual((moved["x"], moved["y"], moved["text"]), (50.0, 20.0, "Hair: bigger curls"))
        castnotes.edit(self.d, "friend", n["id"], text="Curlier")
        castnotes.delete(self.d, "friend", g["id"])
        self.assertEqual(castnotes.open_counts(self.d), {"friend": 1})

    def test_rules(self):
        self.assertEqual(self.err(castnotes.add, self.d, "friend", "note", "front", 101, 5, "x"), "bad_pin")
        self.assertEqual(self.err(castnotes.add, self.d, "friend", "note", "front", -1, 5, "x"), "bad_pin")
        self.assertEqual(self.err(castnotes.add, self.d, "friend", "note", "34", 10, 10, "x"), "bad_pin")   # no picture
        self.assertEqual(self.err(castnotes.add, self.d, "friend", "note", None, None, None, ""), "bad_text")
        self.assertEqual(self.err(castnotes.add, self.d, "friend", "note", None, None, None, "x" * 2001), "bad_text")
        self.assertEqual(self.err(castnotes.add, self.d, "friend", "view", None), "bad_frame")
        self.assertEqual(self.err(castnotes.add, self.d, "nobody", text="x"), "no_character")
        self.assertEqual(self.err(castnotes.add, self.d, "friend", "note", "nope", text="x"), "bad_frame")

    def test_view_toggle_one_per_frame(self):
        v = castnotes.toggle_view(self.d, "friend", "34")
        self.assertEqual((v["kind"], v["frame"], v["x"]), ("view", "34", None))
        self.assertEqual(self.err(castnotes.add, self.d, "friend", "view", "34"), "duplicate")
        self.assertIsNone(castnotes.toggle_view(self.d, "friend", "34"))
        self.assertEqual(castnotes.open_counts(self.d), {})

    def test_base(self):
        b = castnotes.base(self.d)
        castnotes.add(self.d, "hero", text="one", b=b)
        with self.assertRaises(castnotes.CastNoteError) as c:
            castnotes.add(self.d, "hero", text="two", b=b)
        self.assertEqual((c.exception.code, c.exception.exit_code()), ("changed", 4))
        self.assertEqual(len(c.exception.current["doc"]["characters"]["hero"]["notes"]), 1)

    def test_note_makes_approved_changed_and_blocks_approval(self):
        cast.approve(self.d, ["hero"])
        self.assertEqual(cast.states(self.d)["hero"], "approved")
        n = castnotes.add(self.d, "hero", text="Bigger eyes")
        self.assertEqual(cast.states(self.d)["hero"], "changed")
        self.assertIn("open note", cast.approve(self.d, ["hero"])[0])
        castnotes.reply(self.d, n["id"], "Eyes are bigger now", done=True)
        self.assertEqual(castnotes.open_counts(self.d), {})

    def test_lot(self):
        a = castnotes.add(self.d, "hero", text="one")
        castnotes.add(self.d, "friend", text="two")
        self.assertEqual(castnotes.summary(self.d), "2 notes on: friend, hero")
        lot = castnotes.start_lot(self.d, "j-1")
        later = castnotes.add(self.d, "hero", text="three")
        self.assertNotIn(later["id"], castnotes.load(self.d)["lot"]["notes"])
        self.assertIn(a["id"], lot["notes"])
        castnotes.end_lot(self.d)
        self.assertNotIn("lot", castnotes.load(self.d))
        self.assertEqual(castnotes.load(self.d)["last_lot"]["notes"], lot["notes"])   # T057: shown with the answers
        # T059: a failed job ends only its own round, keeps the notes open and records why
        castnotes.start_lot(self.d, "j-2")
        castnotes.end_lot(self.d, "j-other", "boom")
        self.assertIn("lot", castnotes.load(self.d))
        castnotes.end_lot(self.d, "j-2", "The job failed: AE crashed")
        doc = castnotes.load(self.d)
        self.assertNotIn("lot", doc)
        self.assertEqual(doc["failed_lot"]["error"], "The job failed: AE crashed")
        self.assertNotIn("last_lot", doc)
        self.assertEqual(castnotes.open_counts(self.d), {"hero": 2, "friend": 1})
        castnotes.start_lot(self.d, "j-3")
        self.assertNotIn("failed_lot", castnotes.load(self.d))

    def test_edit_ops(self):
        b = castnotes.base(self.d)
        r = edit.run(self.d, "cast-note-add", {"character": "friend", "frame": "front", "x": "10", "y": "20", "text": "Hat"}, base=b)
        self.assertEqual(r["code"], 0, r)
        self.assertEqual(r["fingerprint"], castnotes.base(self.d))
        nid = r["ref"]
        r = edit.run(self.d, "cast-note-add", {"character": "friend", "frame": "front", "x": "300", "y": "1", "text": "x"})
        self.assertEqual(r["code"], 2)
        self.assertIn("bad_pin", r["error"])
        self.assertEqual(edit.run(self.d, "cast-note-delete", {"character": "friend", "note": nid}, base=b)["code"], 4)
        r = edit.run(self.d, "cast-view-toggle", {"ref": ["friend"], "frame": "34"})
        self.assertEqual((r["code"], r["stale"]), (0, []))
        r = edit.run(self.d, "cast-note-delete", {"ref": ["friend"], "note": nid})
        self.assertEqual(r["code"], 0, r)
        self.assertEqual(castnotes.open_counts(self.d), {"friend": 1})

    def test_cli(self):
        n = castnotes.add(self.d, "friend", "note", "front", 10, 10, "Curls")
        env = {**os.environ, "STUDIO_ROOT": str(self.d.parents[1])}
        run = lambda *a: subprocess.run(["sh", str(REPO / "bin" / "studio"), "cast", "notes", *a], capture_output=True,
                                        text=True, env=env, timeout=60)
        r = run("show", "f1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("front pin 10.0,10.0: Curls", r.stdout)
        self.assertIn("cast/sheets/friend/front.jpg", r.stdout)
        b = r.stdout.strip().splitlines()[-1].split("base: ")[1]
        self.assertEqual(run("reply", "f1", n["id"], "Done", "--done", "--base", "0" * 16).returncode, 4)
        r = run("reply", "f1", n["id"], "Curlier now", "--done", "--base", b)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("(no open notes)", run("show", "f1").stdout)
        js = json.loads(run("show", "f1", "--all", "--json").stdout)
        self.assertEqual(js["notes"][0]["reply"], "Curlier now")
        # T058 (FR-013): during a round, show lists only that round's notes; later ones wait
        a = castnotes.add(self.d, "hero", text="Round one")
        castnotes.start_lot(self.d, "j-1")
        castnotes.add(self.d, "friend", text="Written during the redraw")
        r = run("show", "f1")
        self.assertIn("Round one", r.stdout)
        self.assertNotIn("Written during the redraw", r.stdout)
        self.assertIn("1 written since wait for the next round", r.stdout)
        js = json.loads(run("show", "f1", "--json").stdout)
        self.assertEqual(([n["id"] for n in js["notes"]], js["waiting"]), ([a["id"]], 1))


if __name__ == "__main__":
    unittest.main()
