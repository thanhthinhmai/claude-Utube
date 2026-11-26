"""specs/037 US3 (before 035): sound notes per shot (sound/notes.json), the `sound notes` commands, and the Sound edits
of the app (cue-set, cue-rm, cue-add, shot-set, sound-note-add, sound-note-delete) with their 16-character bases."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(HERE))

import soundfilm  # noqa: E402
import soundfix  # noqa: E402
from filmcheck import edit, points, soundlib, soundnotes, soundplan  # noqa: E402


class Notes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = soundfilm.make(Path(self.tmp.name) / "f1")

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_reply_and_bases(self):
        b0 = soundnotes.base(self.d)
        self.assertEqual(len(b0), 16)
        n = soundnotes.add(self.d, "s2", "The window crash is late", b=b0)
        self.assertEqual(n["shot"], "S2")
        with self.assertRaises(soundnotes.SoundNoteError) as e:          # old base: refused, nothing written
            soundnotes.add(self.d, "S3", "x", b=b0)
        self.assertEqual((e.exception.code, e.exception.exit_code()), ("changed", 4))
        with self.assertRaises(soundnotes.SoundNoteError) as e:          # not a shot of this film
            soundnotes.add(self.d, "S9", "x")
        self.assertEqual(e.exception.code, "bad_shot")
        self.assertEqual(soundnotes.open_counts(self.d), {"S2": 1})
        self.assertEqual(soundnotes.summary(self.d), "1 sound note on: S2")
        soundnotes.reply(self.d, n["id"], "Moved 4 frames earlier", done=True)
        self.assertEqual(soundnotes.open_counts(self.d), {})
        doc = soundnotes.load(self.d)
        self.assertEqual(doc["shots"]["S2"][0]["reply"], "Moved 4 frames earlier")

    def test_lot(self):
        a = soundnotes.add(self.d, "S1", "Too loud")
        soundnotes.start_lot(self.d, "j1")
        b = soundnotes.add(self.d, "S3", "Later note")                 # waits for the next round
        self.assertEqual(soundnotes.load(self.d)["lot"]["notes"], [a["id"]])
        soundnotes.end_lot(self.d, "other")                              # another job: nothing
        self.assertIn("lot", soundnotes.load(self.d))
        soundnotes.end_lot(self.d, "j1", error="AE crashed")
        doc = soundnotes.load(self.d)
        self.assertNotIn("lot", doc)
        self.assertEqual(doc["failed_lot"]["job"], "j1")
        soundnotes.start_lot(self.d, "j2")
        self.assertEqual(sorted(soundnotes.load(self.d)["lot"]["notes"]), sorted([a["id"], b["id"]]))
        soundnotes.end_lot(self.d, "j2")
        doc = soundnotes.load(self.d)
        self.assertNotIn("failed_lot", doc)
        self.assertEqual(doc["last_lot"]["job"], "j2")

    def test_end_lot_without_file(self):
        soundnotes.end_lot(self.d, "j1", error="x")
        self.assertFalse(soundnotes.path(self.d).exists())

    def test_cli(self):
        def cli(*a):
            return subprocess.run(["sh", str(REPO / "bin" / "studio"), "sound", "notes", *a], capture_output=True,
                                  text=True, cwd=REPO)
        r = cli("add", "f1", "S2", "--text", "Crash late", "--dir", str(self.d))
        self.assertEqual(r.returncode, 0, r.stderr)
        r = cli("show", "f1", "--json", "--dir", str(self.d))
        doc = json.loads(r.stdout)
        nid = doc["shots"]["S2"][0]["id"]
        r = cli("add", "f1", "S2", "--text", "x", "--base", "0" * 16, "--dir", str(self.d))
        self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
        r = cli("reply", "f1", nid, "--text", "Done", "--done", "--dir", str(self.d))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(soundnotes.load(self.d)["shots"]["S2"][0]["done"])
        r = cli("delete", "f1", "S2", nid, "--dir", str(self.d))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(soundnotes.load(self.d)["shots"], {})


class Edits(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"STUDIO_DATA": str(t / "data"), "STUDIO_ROOT": str(t / "repo"),
                                                "FREESOUND_API_KEY": "", "STUDIO_EDIT_NO_RUN": "1"})
        self.env.start()
        self.noenv = mock.patch("filmcheck.eleven.load_env", return_value={})
        self.noenv.start()
        (t / "repo" / "references").mkdir(parents=True)
        soundlib.add_root(soundfix.make(t / "Sonniss" / "GDC2024"))
        soundlib.index()
        self.d = soundfilm.make(t / "films" / "f1")
        (self.d / "ae").mkdir()
        (self.d / "ae" / "shots.jsx").write_text("// test\n")         # a whole AE film (points.is_ae)

    def tearDown(self):
        self.noenv.stop()
        self.env.stop()
        self.tmp.cleanup()

    def run_op(self, op, args, base=None):
        fp = {"sound-note-add": soundnotes.base, "sound-note-delete": soundnotes.base}.get(op, soundplan.base)
        return edit.run(self.d, op, args, base=fp(self.d) if base is None else base)

    def test_bases_are_16(self):
        self.assertEqual(len(soundplan.base(self.d)), 16)
        self.assertEqual(len(soundnotes.base(self.d)), 16)

    def test_cue_add_at_seconds_set_and_remove(self):
        r = self.run_op("cue-add", {"shot": "S2", "action": "window breaks", "query": "glass break", "at": "1.5"})
        self.assertEqual(r["code"], 0, r)
        cue = r["ref"]
        c = next(x for x in soundplan.load(self.d)["cues"] if x["id"] == cue)
        self.assertEqual(c["anchor"], {"shot_at": 0.5})                    # 1.5 s of a 3 s shot
        r = self.run_op("cue-set", {"cue": cue, "offset_f": "-2", "gain_db": "-3"})
        self.assertEqual(r["code"], 0, r)
        c = next(x for x in soundplan.load(self.d)["cues"] if x["id"] == cue)
        self.assertEqual((c["anchor"].get("offset_f"), c["gain_db"]), (-2, -3.0))
        self.assertEqual(self.run_op("cue-set", {"cue": cue, "gain_db": "0"}, base="0" * 16)["code"], 4)
        self.assertEqual(self.run_op("cue-set", {"cue": cue})["code"], 2)  # nothing to change
        self.assertEqual(self.run_op("cue-rm", {"cue": cue})["code"], 0)
        self.assertFalse(any(x["id"] == cue for x in soundplan.load(self.d)["cues"]))

    def test_shot_set(self):
        r = self.run_op("shot-set", {"ref": ["S2"], "on": "no"})
        self.assertEqual(r["code"], 0, r)
        self.assertIn("S2", soundplan.load(self.d)["off"])
        r = self.run_op("shot-set", {"shot": "S2", "on": "yes"})
        self.assertNotIn("S2", soundplan.load(self.d).get("off") or [])
        self.assertEqual(self.run_op("shot-set", {"shot": "S2", "on": "maybe"})["code"], 2)

    def test_note_ops_and_stale(self):
        soundfilm.tone(self.d / "out" / "mix.wav", 0.5, 220, rate=48000, channels=2)
        r = self.run_op("sound-note-add", {"ref": ["S3"], "text": "Bubbles too loud"})
        self.assertEqual(r["code"], 0, r)
        self.assertEqual(r["stale"], [])
        nid = r["ref"]
        self.assertEqual(self.run_op("sound-note-add", {"shot": "S3", "text": "x"}, base="0" * 16)["code"], 4)
        self.assertTrue(any("open sound note" in m for m in points.checks_pass(self.d, "mix")))
        r = self.run_op("sound-note-delete", {"shot": "S3", "note": nid})
        self.assertEqual(r["code"], 0, r)
        self.assertEqual(soundnotes.open_counts(self.d), {})


if __name__ == "__main__":
    unittest.main()
