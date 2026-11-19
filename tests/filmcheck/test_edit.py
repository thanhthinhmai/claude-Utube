"""Edits: the common frame and each operation (specs/026 T007, T017, T029, T039, T045)."""
import hashlib
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from filmcheck import edit, points, report  # noqa: E402
import samples  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"


def tree_hash(d: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(d.rglob("*")):
        if p.is_file() and ".check" not in p.parts:
            h.update(p.relative_to(d).as_posix().encode() + p.read_bytes())
    return h.hexdigest()


class Frame(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(exist_ok=True)
        self.d = samples.review_film(Path(tempfile.mkdtemp(dir=TMP)), kit=False)
        os.environ.pop("STUDIO_JOB_STEP", None)

    def para(self, text="By day three, you begin to see things that are not there.", base=None):
        return edit.run(self.d, "script-para", {"para": "P03", "text": text},
                        base=points.fingerprint(self.d, "script") if base is None else base)

    def test_old_base_writes_nothing(self):
        before = tree_hash(self.d)
        r = self.para(base="0" * 16)
        self.assertEqual(r["code"], 4)
        self.assertEqual(tree_hash(self.d), before)

    def test_unknown_op(self):
        self.assertEqual(edit.run(self.d, "bogus", {})["code"], 2)

    def test_busy_lock(self):
        lk = edit.take_lock(self.d, "Voice", by="job run")          # this process: alive; Voice depends on Script
        r = self.para()
        self.assertEqual(r["code"], 5)
        self.assertIn("Voice", r["error"])
        edit.drop_lock(self.d)
        lk["pid"] = 999999                                           # a dead pid on this host: ignored
        edit.write_atomic(edit.lock_file(self.d), json.dumps(lk))
        self.assertEqual(self.para()["code"], 0)

    def test_lock_from_another_host(self):
        lk = {"step": "Voice", "pid": 1, "host": "job-container", "since": edit.now(), "by": "job run"}
        edit.write_atomic(edit.lock_file(self.d), json.dumps(lk))
        self.assertEqual(self.para()["code"], 5)                     # no word from the runner: < 6 h, alive
        os.environ["STUDIO_JOB_STEP"] = "Render"                     # the job runs another step
        try:
            self.assertEqual(self.para("Day three brings things that are not there.")["code"], 0)
        finally:
            os.environ.pop("STUDIO_JOB_STEP")

    def test_edit_log(self):
        r = self.para()
        self.assertEqual(r["code"], 0, r)
        rows = [json.loads(x) for x in (self.d / ".check" / "edits.jsonl").read_text().splitlines()]
        self.assertEqual(set(rows[-1]), {"at", "by", "source", "op", "point", "ref", "old", "new", "result", "stale"})
        self.assertEqual((rows[-1]["ref"], rows[-1]["result"]), ("P03", "ok"))
        self.assertEqual(rows[-1]["stale"][0], "Voice")


class ScriptPara(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(exist_ok=True)
        self.d = samples.review_film(Path(tempfile.mkdtemp(dir=TMP)), kit=False)

    def run_para(self, para, text):
        return edit.run(self.d, "script-para", {"para": para, "text": text}, base=points.fingerprint(self.d, "script"))

    def test_replaces_only_that_paragraph(self):
        before = (self.d / "SCRIPT.md").read_text().splitlines()
        r = self.run_para("P03", "By day three, you begin to see things that are not there.")
        self.assertEqual(r["code"], 0, r)
        after = (self.d / "SCRIPT.md").read_text().splitlines()
        self.assertEqual([a for a, b in zip(before, after) if a != b], ["[P03] By day three you start seeing things that are not there."])
        self.assertIn("[P03] By day three, you begin to see things that are not there.", after)
        self.assertEqual(r["check"]["pass"], True)
        self.assertIsInstance(r["check"]["score"], (int, float))
        self.assertEqual(report.load(self.d)["script"]["editor"], [])      # no editor round: no Claude call

    def test_invalid_writes_nothing(self):
        before = tree_hash(self.d)
        for para, text in (("P09", "Some text."), ("P03", "  "), ("P03", "x" * 4001), ("P03", "Text [P04] more."),
                           ("3", "Text.")):
            r = self.run_para(para, text)
            self.assertEqual(r["code"], 2, (para, r))
        self.assertEqual(tree_hash(self.d), before)

    def test_saved_but_check_fails(self):
        long = " ".join(["The night is long and the room is dark and nobody comes."] * 6)
        r = self.run_para("P03", long)
        self.assertEqual(r["code"], 1, r)
        self.assertIn("length", r["check"]["failed"])
        self.assertIn(long[:40], (self.d / "SCRIPT.md").read_text())


if __name__ == "__main__":
    unittest.main()


class Shots(unittest.TestCase):                                    # specs/026 T029
    def setUp(self):
        TMP.mkdir(exist_ok=True)
        os.environ["STUDIO_EDIT_NO_RUN"] = "1"
        self.d = samples.review_film(Path(tempfile.mkdtemp(dir=TMP)))

    def tearDown(self):
        os.environ.pop("STUDIO_EDIT_NO_RUN", None)

    def shot(self, *ref, **kw):
        return edit.run(self.d, "shot", {"ref": list(ref), **kw}, base=points.fingerprint(self.d, "shots"))

    def scenes(self):
        return json.loads((self.d / "scenes.json").read_text())["scenes"]

    def test_changes_one_shot(self):
        r = self.shot("S02", cam="mid-eye", act="wave")
        self.assertEqual(r["code"], 0, r)
        s = self.scenes()
        self.assertEqual((s[1]["cam"], s[1]["cast"][0]["act"]), ("mid-eye", [[0.4, "wave"]]))
        self.assertEqual(s[0], samples.REVIEW_SCENES["scenes"][0])
        self.assertEqual(r["stale"], ["Render", "Self-check", "Publish"])

    def test_outside_the_catalogue_writes_nothing(self):
        before = (self.d / "scenes.json").read_bytes()
        for kw in ({"cam": "fisheye"}, {"set": "moon"}, {"act": "backflip"}, {"set": "custom:platform"}, {}):
            r = self.shot("S02", **kw)
            self.assertEqual(r["code"], 2, (kw, r))
        self.assertEqual(self.shot("S99", cam="close")["code"], 2)
        self.assertEqual((self.d / "scenes.json").read_bytes(), before)
        self.assertFalse((self.d / ".check" / "scenes.edit.json").exists())

    def test_no_scene_table(self):
        (self.d / "scenes.json").unlink()
        r = self.shot("S02", cam="close")
        self.assertEqual(r["code"], 2)
        self.assertIn("no scene table", r["error"])

    def test_exception_and_style_need_a_reason(self):
        from filmcheck import tiers
        (self.d / ".check").mkdir(exist_ok=True)
        (self.d / ".check" / "plan-input.json").write_text(json.dumps({"fingerprint": tiers.fingerprint(self.d),
                                                                        "shots": [{"id": "S02", "t0": 3, "t1": 6}]}))
        base = points.fingerprint(self.d, "shots")
        r = edit.run(self.d, "except", {"ref": ["S02", "dark"], "reason": ""}, base=base)
        self.assertEqual(r["code"], 2)
        r = edit.run(self.d, "except", {"ref": ["S02", "dark"], "reason": "a night beat on purpose"}, base=base)
        self.assertIn(r["code"], (0, 1), r)
        self.assertEqual(tiers.load_exceptions(self.d)[0]["reason"], "a night beat on purpose")
        tiers.save_tier(self.d, "shots", tiers.result("shots", [{"ref": "S02", "at": 4, "rule": "style_depth", "severity": "warn",
                        "measure": 1, "limit": 0, "text": "", "fix": "", "excepted": None}], {}, [], 0.0, tiers.fingerprint(self.d)))
        self.assertEqual(edit.run(self.d, "accept-style", {"reason": " "}, base=base)["code"], 2)
        self.assertEqual(edit.run(self.d, "accept-style", {"reason": "deliberate dark beat"}, base=base)["code"], 0)
        self.assertEqual(tiers.load_tier(self.d, "shots")["style_accept"]["reason"], "deliberate dark beat")


class Voice(unittest.TestCase):                                    # specs/026 T039
    def setUp(self):
        TMP.mkdir(exist_ok=True)
        os.environ["STUDIO_EDIT_NO_RUN"] = "1"
        self.d = samples.review_film(Path(tempfile.mkdtemp(dir=TMP)), kit=False)

    def tearDown(self):
        os.environ.pop("STUDIO_EDIT_NO_RUN", None)

    def run_op(self, op, **a):
        return edit.run(self.d, op, a, base=points.fingerprint(self.d, "voice"))

    def rows(self):
        return json.loads((self.d / "lines.json").read_text())

    def test_say_keeps_the_text(self):
        text = self.rows()[2]["text"]
        r = self.run_op("voice-say", ref=["L03"], say="R. E. M.")
        self.assertEqual(r["code"], 0, r)
        self.assertEqual((self.rows()[2]["text"], self.rows()[2]["say"]), (text, "R. E. M."))
        self.assertEqual(self.run_op("voice-say", ref=["L03"], say="")["code"], 0)
        self.assertNotIn("say", self.rows()[2])
        self.assertEqual(self.run_op("voice-say", ref=["L03"], say="x" * 401)["code"], 2)
        self.assertEqual(self.run_op("voice-say", ref=["L99"], say="x")["code"], 2)

    def test_voice_set_is_checked(self):
        before = (self.d / "lines.json").read_bytes()
        for a in ({"voice": "xx_fake", "confirm": "all"}, {"voice": "am_adam"}, {"speed": "1.5", "confirm": "all"},
                  {"speed": "fast", "confirm": "all"}, {"confirm": "all"}):
            self.assertEqual(self.run_op("voice-set", **a)["code"], 2, a)
        self.assertEqual((self.d / "lines.json").read_bytes(), before)
        r = self.run_op("voice-set", speed="0.95", confirm="all")
        self.assertEqual(r["code"], 0, r)
        self.assertTrue(all(x["speed"] == 0.95 for x in self.rows()))


class Mix(unittest.TestCase):                                      # specs/026 T045
    def setUp(self):
        TMP.mkdir(exist_ok=True)
        os.environ["STUDIO_EDIT_NO_RUN"] = "1"
        self.d = samples.review_film(Path(tempfile.mkdtemp(dir=TMP)))

    def tearDown(self):
        os.environ.pop("STUDIO_EDIT_NO_RUN", None)

    def test_ranges_and_picture_kept(self):
        from filmcheck import tiers
        pic = tiers.fingerprint(self.d)
        base = points.fingerprint(self.d, "mix")
        for a in ({"under": "-40"}, {"duck": "3"}, {"sfx": "-30"}, {"music": "loud"}, {}):
            self.assertEqual(edit.run(self.d, "mix", a, base=base)["code"], 2, a)
        self.assertFalse((self.d / "mix.json").exists())
        r = edit.run(self.d, "mix", {"music": "seed:3", "under": "-6"}, base=base)
        self.assertEqual(r["code"], 0, r)
        self.assertEqual(json.loads((self.d / "mix.json").read_text()), {"music": "seed:3", "music_under_voice_db": -6.0})
        self.assertEqual(r["stale"], ["Self-check", "Publish"])
        self.assertEqual(tiers.fingerprint(self.d), pic)                 # the picture is not touched


class OwnerEditsKeepTheScriptPassing(unittest.TestCase):           # found online: the agent's own check after an edit
    def test_unchanged_rule_skips_owner_paragraphs(self):
        from filmcheck import script
        TMP.mkdir(exist_ok=True)
        d = samples.review_film(Path(tempfile.mkdtemp(dir=TMP)), kit=False)
        (d / ".check").mkdir(exist_ok=True)
        (d / ".check" / "script-r1.md").write_text((d / "SCRIPT.md").read_text())          # an editor round on this text
        (d / ".check" / "review-r1.json").write_text(json.dumps({"score": 9, "issues": []}))
        r = edit.run(d, "script-para", {"para": "P03", "text": "By day three, you begin to see things that are not there."},
                     base=points.fingerprint(d, "script"))
        self.assertEqual(r["code"], 0, r)
        self.assertTrue(script.check(d)["hard"]["unchanged"])                     # the normal check passes too
        p = d / "SCRIPT.md"
        p.write_text(p.read_text().replace("nothing happens", "the night goes on"))  # the agent changed P01 alone
        self.assertFalse(script.check(d)["hard"]["unchanged"])
