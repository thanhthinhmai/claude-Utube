"""The machine script check (specs/010 T008–T011; FR-001–FR-006, FR-009, SC-002, SC-004)."""
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import script  # noqa: E402

import samples  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"


def film(text, sources="", opened=samples.OPENED) -> Path:
    TMP.mkdir(exist_ok=True)
    return samples.write_script(Path(tempfile.mkdtemp(dir=TMP)) / "f", text, sources, opened)


def rules(result):
    return {i["rule"] for i in result["issues"]}


class Good(unittest.TestCase):
    def test_good_scripts_pass(self):
        for text, src in ((samples.GOOD_EN, samples.GOOD_EN_SOURCES), (samples.GOOD_VI, samples.GOOD_VI_SOURCES)):
            r = script.check(film(text, src))
            self.assertTrue(r["pass"], r)
            self.assertGreaterEqual(r["score"], 7)
            self.assertEqual(r["issues"], [])


class EachRule(unittest.TestCase):
    def test_each_bad_script_breaks_its_rule(self):
        hard = {"sources": "sources", "sources_unopened": "sources", "length": "length"}
        for name, (text, src) in samples.BAD.items():
            if name == "format":
                continue
            r = script.check(film(text, src))
            rule = hard.get(name, name)
            self.assertIn(rule, rules(r), name)
            if name in hard:
                self.assertFalse(r["hard"][rule], name)
                self.assertFalse(r["pass"], name)

    def test_bad_header_cannot_run(self):
        with self.assertRaises(script.ScriptError):
            script.check(film(*samples.BAD["format"]))
        for bad in ("Target: 3s", "Target: 45", "Target: 1000s"):
            with self.assertRaises(script.ScriptError, msg=bad):
                script.check(film(samples.GOOD_EN.replace("Target: 45s", bad), samples.GOOD_EN_SOURCES))

    def test_locations(self):
        r = script.check(film(*samples.BAD["long_sentence"]))
        i = next(x for x in r["issues"] if x["rule"] == "long_sentence")
        self.assertEqual((i["para"], i["sentence"]), ("P02", 1))
        r = script.check(film(*samples.BAD["risky_number"]))
        i = next(x for x in r["issues"] if x["rule"] == "risky_number")
        self.assertEqual((i["para"], i["sentence"]), ("P04", 1))
        self.assertIn("4:45", i["detail"])

    def test_paragraph_numbers(self):
        r = script.check(film(samples.GOOD_EN.replace("[P03]", "[P07]"), samples.GOOD_EN_SOURCES))
        self.assertFalse(r["hard"]["format"])
        self.assertIn("P03", next(i for i in r["issues"] if i["rule"] == "format")["detail"])


class Numbers(unittest.TestCase):
    def test_small_number_words_need_no_source(self):
        text = samples.GOOD_EN.replace("Hanoi has more than six million motorbikes. ", "")
        r = script.check(film(text, ""))
        self.assertTrue(r["hard"]["sources"], r["issues"])

    def test_big_number_words_and_digits_need_a_source(self):
        for s in ("Twenty bakers work here.", "It takes 3 hours.", "Hà Nội có mười con phố như vậy."):
            self.assertTrue(script.has_number(s, "vi" if "Hà" in s else "en"), s)
        self.assertFalse(script.has_number("One man and four loaves.", "en"))

    def test_fiction_marker(self):
        text = samples.GOOD_EN.replace("[P02] Minh is a night baker.", "[P02] Twenty years later, Minh is a night baker.")
        src = samples.GOOD_EN_SOURCES + '- [P02] "Twenty years later": fiction\n'
        self.assertTrue(script.check(film(text, src))["hard"]["sources"])
        self.assertFalse(script.check(film(text, samples.GOOD_EN_SOURCES))["hard"]["sources"])

    def test_no_factual_claims(self):
        text = samples.GOOD_EN.replace("Hanoi has more than six million motorbikes. ", "")
        self.assertTrue(script.check(film(text, "no factual claims\n"))["hard"]["sources"])
        r = script.check(film(samples.GOOD_EN, "no factual claims\n"))     # still checks sentences with a number
        self.assertFalse(r["hard"]["sources"])

    def test_quote_must_be_in_paragraph(self):
        src = '- [P01] "seven million cars": Hanoi Department of Transport, 2024, https://example.org/hanoi-motorbikes\n'
        self.assertFalse(script.check(film(samples.GOOD_EN, src))["hard"]["sources"])

    def test_provided_material(self):
        src = '- [P01] "six million motorbikes": Customer notes, 2026, provided:notes.pdf\n'
        self.assertTrue(script.check(film(samples.GOOD_EN, src, opened=[]))["hard"]["sources"])


class EdgeCases(unittest.TestCase):
    def test_short_film_hook_window(self):
        text = ("Title: Short\nTarget: 10s\nLanguage: en\n\n[P01] Minh bakes bread in the dark kitchen every night. "
                "Why does he never sleep?\n")
        r = script.check(film(text))
        self.assertIn("no_hook", rules(r))       # the question starts after the first 2 s (20% of 10 s)
        text2 = text.replace("Minh bakes bread in the dark kitchen every night. Why does he never sleep?",
                             "Why does Minh never sleep? He bakes bread in the dark kitchen.")
        self.assertNotIn("no_hook", rules(script.check(film(text2))))

    def test_chinese_counts_characters(self):
        long = "一" * 45
        text = f"Title: 面包\nTarget: 10s\nLanguage: zh\n\n[P01] 为什么他从不睡觉？{long}。\n"
        r = script.check(film(text))
        i = next(x for x in r["issues"] if x["rule"] == "long_sentence")
        self.assertIn("45 characters", i["detail"])

    def test_retention_gap_only_in_long_films(self):
        r = script.check(film(samples.long_script(200, gap_paragraphs=range(2, 30))))
        self.assertIn("retention_gap", rules(r))
        r = script.check(film(samples.long_script(200)))
        self.assertNotIn("retention_gap", rules(r))


class KeptParagraphs(unittest.TestCase):
    def round1(self, issues):
        d = film(samples.GOOD_EN, samples.GOOD_EN_SOURCES)
        (d / ".check" / "script-r1.md").write_text(samples.GOOD_EN)
        (d / ".check" / "review-r1.json").write_text(json.dumps({"score": 7, "issues": issues}))
        return d

    def test_only_flagged_paragraphs_may_change(self):           # SC-004
        d = self.round1([{"level": "P1", "para": "P02", "reason": "x"}, {"level": "P3", "para": "P03", "reason": "y"}])
        fixed = samples.GOOD_EN.replace("Minh is a night baker.", "Minh bakes at night.")
        (d / "SCRIPT.md").write_text(fixed)
        self.assertTrue(script.check(d)["hard"]["unchanged"])
        (d / "SCRIPT.md").write_text(fixed.replace("The dough is soft", "The dough is warm"))   # P03 has only a P3
        r = script.check(d)
        self.assertFalse(r["hard"]["unchanged"])
        self.assertEqual([i["para"] for i in r["issues"] if i["rule"] == "unchanged"], ["P03"])
        self.assertTrue(script.check(d, customer_round=True)["hard"]["unchanged"])

    def test_trailing_spaces_do_not_count(self):
        d = self.round1([])
        (d / "SCRIPT.md").write_text(samples.GOOD_EN.replace("tomorrow.\n", "tomorrow.   \n"))
        self.assertTrue(script.check(d)["hard"]["unchanged"])


class Speed(unittest.TestCase):
    def test_sc002_fast_and_offline(self):
        d = film(samples.long_script(300))
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("no process may start")):
            t = time.time()
            script.check(d)
            self.assertLess(time.time() - t, 5)


if __name__ == "__main__":
    unittest.main()
