"""The shared rhythm rules and script sentences (specs/020 T010; FR-003, FR-004, FR-006, FR-010, SC-006)."""
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import qc, rhythm  # noqa: E402

import samples  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"

ALARM = "Your alarm goes off at seven. But it sounds wrong."
ASR = [["Your", -0.6, 0.14], ["alarm", 0.14, 0.5], ["goes", 0.5, 0.78], ["off", 0.78, 0.98], ["at", 0.98, 1.1],
       ["7,", 1.1, 1.62], ["but", 1.95, 2.1], ["it", 2.1, 2.2], ["sounds", 2.2, 2.6], ["wrong,", 2.6, 3.0]]


def line(lid, para, at, words, length=None):
    ws = rhythm.clamp_words(words, length)
    return {"id": lid, "para": para, "at": at, "words": [(w, at + s, at + e) for w, s, e in ws]}


class Sentences(unittest.TestCase):
    def test_script_decides_the_sentence_end(self):                    # US3 AC2
        ln = line("l01", "P01", 0.5, ASR, 3.1)
        got = rhythm.sentences([ln], {"l01": ALARM})
        self.assertEqual(len(got), 2)
        self.assertAlmostEqual(got[0]["end"], 0.5 + 1.62)                # after "seven" (written "7,")
        self.assertAlmostEqual(got[1]["start"], 0.5 + 1.95)
        old = rhythm.sentences([ln])                                    # the recogniser's commas: one sentence
        self.assertEqual(len(old), 1)

    def test_cut_after_seven_is_not_a_false_cut(self):
        ln = line("l01", "P01", 0.5, ASR, 3.1)
        sents = rhythm.sentences([ln], {"l01": ALARM})
        words = [(s, e, "P01") for _, s, e in ln["words"]]
        cut = 0.5 + 1.95                                                  # gap 0.33 < 0.4: cutting at the next start is right
        shots = [{"id": "A", "t0": 0.0, "t1": cut}, {"id": "B", "t0": cut, "t1": 4.0}]
        m, issues = rhythm.measure(sents, words, 4.0, shots=shots)
        self.assertEqual([i for i in issues if i["rule"].startswith("cut")], [])

    def test_negative_and_late_stamps_are_clamped(self):               # US3 AC3, FR-004
        ws = rhythm.clamp_words([["a", -0.6, 0.1], ["b", 0.2, 9.0]], 1.5)
        self.assertEqual(ws, [("a", 0.0, 0.1), ("b", 0.2, 1.5)])

    def test_numbers_and_spelling_map_in_proportion(self):
        ln = line("l01", "P01", 0.0, [["The", 0, .2], ["male", .2, .5], ["carrier", .5, .9], ["backs", .9, 1.2],
                                      ["away.", 1.2, 1.6], ["The", 1.9, 2.0], ["neighbors", 2.0, 2.5], ["whisper.", 2.5, 3.0]], 3.0)
        got = rhythm.sentences([ln], {"l01": "The mail carrier backs away. The neighbours whisper."})
        self.assertEqual([(x["start"], x["end"]) for x in got], [(0.0, 1.6), (1.9, 3.0)])

    def test_two_runs_are_identical(self):                             # SC-006
        ln = line("l01", "P01", 0.5, ASR, 3.1)
        a = rhythm.sentences([ln], {"l01": ALARM})
        b = rhythm.sentences([line("l01", "P01", 0.5, ASR, 3.1)], {"l01": ALARM})
        self.assertEqual(a, b)


class Rules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TMP.mkdir(exist_ok=True)
        cls.root = Path(tempfile.mkdtemp(dir=TMP))

    def test_same_issues_as_qc(self):                                  # FR-010
        d = samples.make_film(self.root, "same", move_cut=(1, 5.0))
        nar = qc.load_narration(d)
        dur = qc.probe_duration(d / "same.mp4")
        _, problems, issues = qc.narration_measures(nar, dur, nar["cuts"], style={"shot_max": 10})
        words = sorted((s, e, ln["para"]) for ln in nar["lines"] for (_, s, e) in ln["words"])
        _, again = rhythm.measure(rhythm.sentences(nar["lines"]), words, dur,
                                  shots=qc.shots_from_cuts(nar["cuts"], dur), style={"shot_max": 10})
        self.assertEqual([(i["rule"], i["at"]) for i in issues], [(i["rule"], i["at"]) for i in again])
        self.assertEqual(len(problems), 1)
        self.assertEqual(issues[0]["rule"], "cut_in_sentence")
        self.assertIn("move the cut to ≥", issues[0]["fix"])

    def _shots(self, *lengths):
        out, t = [], 0.0
        for i, L in enumerate(lengths):
            out.append({"id": f"S{i}", "t0": t, "t1": t + L})
            t += L
        return out, t

    def test_shot_lengths(self):
        shots, dur = self._shots(2.0, 0.8, 3.0, 6.5, 2.0)
        _, iss = rhythm.measure([], [], dur, shots=shots)
        self.assertEqual([(i["rule"], i["ref"]) for i in iss], [("shot_short", "S1"), ("shot_long", "S3")])
        _, iss = rhythm.measure([], [], dur, shots=shots, style={"shot_max": 7})
        self.assertEqual([i["rule"] for i in iss], ["shot_short"])
        shots, dur = self._shots(2.0, 0.5)                               # a short last shot is a tail, not a shot
        self.assertEqual(rhythm.measure([], [], dur, shots=shots)[1], [])

    def test_cue_and_card_rules(self):
        words = [(0.0, 1.5, "P01")]
        cues = [[0.0, 1.6, "too short for 1.5 s of speech"], [2.0, 4.0, "fine"]]
        _, iss = rhythm.measure([], words, 5.0, cues=cues)
        cue = [i for i in iss if i["rule"] == "cue_short"]
        self.assertEqual(len(cue), 1)
        self.assertEqual(cue[0]["ref"], "cue 1")
        self.assertAlmostEqual(cue[0]["limit"], 2.1)
        cards = [{"id": "c", "at": 1.0, "need": 2.4, "got": 1.9, "text": "THE RULES"},
                 {"id": "d", "at": 3.0, "need": 2.0, "got": 3.0, "text": "OK"}]
        _, iss = rhythm.measure([], [], 5.0, cards=cards, shots=self._shots(2.5, 2.5)[0])
        self.assertEqual([(i["rule"], i["ref"]) for i in iss], [("card_read", "S0")])

    def test_silence_tail_and_key_shot(self):
        words = [(0.0, 1.0, "P01"), (3.0, 3.5, "P02")]
        sents = [{"para": "P01", "line": "l1", "n": 0, "start": 0.0, "end": 1.0, "text": "a"},
                 {"para": "P02", "line": "l2", "n": 0, "start": 3.0, "end": 3.5, "text": "b"}]
        shots = [{"id": "A", "t0": 0, "t1": 2.6}, {"id": "B", "t0": 2.6, "t1": 6.0}]
        m, iss = rhythm.measure(sents, words, 6.0, shots=shots)
        rules = {i["rule"] for i in iss}
        self.assertIn("silence", rules)
        self.assertIn("tail", rules)
        self.assertNotIn("key_shot_short", rules)
        shots = [{"id": "A", "t0": 0, "t1": 2.0}, {"id": "B", "t0": 2.0, "t1": 6.0}]
        _, iss = rhythm.measure(sents, words, 6.0, shots=shots)
        self.assertIn(("key_shot_short", "A"), [(i["rule"], i["ref"]) for i in iss])


if __name__ == "__main__":
    unittest.main()
