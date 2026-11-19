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
