"""`sh bin/studio script …` and `web fetch` end to end with the fake editor (specs/010 T012–T014, FR-006–FR-010)."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import samples

REPO = Path(__file__).resolve().parents[2]
TMP = Path(__file__).resolve().parent / ".tmp"
FAKE = REPO / "tests/online/fake_claude"


class Flow(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(exist_ok=True)
        self.root = Path(tempfile.mkdtemp(dir=TMP))
        self.d = samples.write_script(self.root / "films" / "baker", samples.GOOD_EN, samples.GOOD_EN_SOURCES)
        self.log = self.root / "fake.log"
        self.env = {**os.environ, "STUDIO_ROOT": str(self.root), "STUDIO_CLAUDE_BIN": str(FAKE),
                    "FAKE_CLAUDE_LOG": str(self.log)}
        for k in ("STUDIO_MODE", "STUDIO_JOB", "STUDIO_EDITOR_MODEL", "STUDIO_MODEL"):
            self.env.pop(k, None)

    def studio(self, *args):
        p = subprocess.run(["sh", str(REPO / "bin/studio"), *args], env=self.env, cwd=self.root,
                           capture_output=True, text=True, timeout=120)
        return p.returncode, p.stdout + p.stderr

    def tag(self, tag):
        (self.d / "SCRIPT.md").write_text(f"> {tag}\n" + samples.GOOD_EN)

    def checks(self):
        return json.loads((self.d / "checks.json").read_text())

    def test_pass_first_round(self):
        rc, outp = self.studio("script", "check", "baker")
        self.assertEqual(rc, 0, outp)
        rc, outp = self.studio("script", "review", "baker")
        self.assertEqual(rc, 0, outp)
        s = self.checks()["script"]
        self.assertEqual((s["verdict"], s["fix_rounds"], len(s["editor"])), ("pass", 0, 1))
        self.assertTrue((self.d / ".check/script-r1.md").is_file())
        self.assertIn("Script:** pass", (self.d / "CHECKS.md").read_text())
        self.assertEqual(self.studio("script", "status", "baker")[0], 0)
        args = json.loads(self.log.read_text().splitlines()[-1])
        self.assertIn("Read,Grep,WebSearch,Bash", args)
        self.assertNotIn("--model", args)                       # inherit and no STUDIO_MODEL: the session's model

    def test_one_fix_round(self):
        self.tag("[editor-p1 P02]")
        rc, outp = self.studio("script", "review", "baker")
        self.assertEqual(rc, 1, outp)
        self.assertIn("P1 P02", outp)
        self.assertEqual(self.studio("script", "status", "baker")[0], 1)
        # changing a paragraph that was not flagged breaks the check
        text = (self.d / "SCRIPT.md").read_text()
        (self.d / "SCRIPT.md").write_text(text.replace("The dough is soft", "The dough is warm"))
        rc, outp = self.studio("script", "review", "baker")
        self.assertEqual(rc, 1)
        self.assertIn("unchanged", outp)
        # change only P02
        (self.d / "SCRIPT.md").write_text(text.replace("Minh is a night baker.", "Minh bakes through the night."))
        rc, outp = self.studio("script", "review", "baker")
        self.assertEqual(rc, 0, outp)
        s = self.checks()["script"]
        self.assertEqual((s["verdict"], s["fix_rounds"]), ("pass", 1))
        self.assertEqual([e["p1"] for e in s["editor"]], [1, 0])

    def test_fails_after_two_fix_rounds(self):
        self.tag("[editor-low]")
        codes = [self.studio("script", "review", "baker")[0] for _ in range(3)]
        self.assertEqual(codes, [1, 1, 3])
        s = self.checks()["script"]
        self.assertEqual((s["verdict"], s["fix_rounds"]), ("failed", 2))
        self.assertEqual(self.studio("script", "review", "baker")[0], 3)       # no fourth round
        self.assertEqual(self.studio("script", "status", "baker")[0], 3)
        # a round the customer asked for opens again (FR-019) and does not count
        self.assertEqual(self.studio("script", "review", "baker", "--customer-round")[0], 1)
        self.assertEqual(self.checks()["script"]["fix_rounds"], 2)

    def test_bad_answer_counts_as_a_round(self):
        self.tag("[editor-bad-json]")
        rc, outp = self.studio("script", "review", "baker")
        self.assertEqual(rc, 1, outp)
        e = self.checks()["script"]["editor"][0]
        self.assertTrue(e["bad_answer"])
        self.assertEqual(len(self.log.read_text().splitlines()), 2)          # asked twice

    def test_review_needs_a_passing_check(self):
        (self.d / "SOURCES.md").write_text("no factual claims\n")
        rc, outp = self.studio("script", "review", "baker")
        self.assertEqual(rc, 1)
        self.assertFalse(self.log.exists())                                   # Claude was not called

    def test_change_after_pass_is_pending(self):
        self.studio("script", "review", "baker")
        (self.d / "SCRIPT.md").write_text(samples.GOOD_EN.replace("tomorrow", "the next morning"))
        rc, outp = self.studio("script", "status", "baker")
        self.assertEqual(rc, 1)
        self.assertIn("changed after the editor passed it", outp)

    def test_editor_model_setting(self):
        self.env["STUDIO_EDITOR_MODEL"] = "sonnet"
        self.studio("script", "review", "baker")
        args = json.loads(self.log.read_text().splitlines()[-1])
        self.assertEqual(args[args.index("--model") + 1], "sonnet")
        self.assertEqual(self.checks()["script"]["editor"][0]["model"], "sonnet")

    def test_skip_only_without_narration(self):
        rc, _ = self.studio("script", "skip", "baker", "--reason", "no narration")
        self.assertEqual(rc, 0)
        self.assertEqual(self.checks()["script"]["verdict"], "skipped")
        (self.d / "narration.json").write_text("{}")
        self.assertEqual(self.studio("script", "skip", "baker", "--reason", "no narration")[0], 1)

    def test_missing_editor_is_not_a_round(self):
        self.env["STUDIO_CLAUDE_BIN"] = str(self.root / "no-such-claude")
        rc, outp = self.studio("script", "review", "baker")
        self.assertEqual(rc, 2, outp)
        self.assertEqual(self.checks()["script"]["editor"], [])
        self.assertFalse((self.d / ".check/script-r1.md").exists())

    def test_editor_page_budget(self):
        budget = self.root / "left"
        budget.write_text("1")
        self.env["STUDIO_FETCH_BUDGET_FILE"] = str(budget)
        rc, outp = self.studio("web", "fetch", "http://10.0.0.1/")
        self.assertIn("blocked_address", outp)                  # the first page is tried (and refused here)
        self.assertEqual(budget.read_text(), "0")
        rc, outp = self.studio("web", "fetch", "https://example.org/")
        self.assertEqual(rc, 1)
        self.assertIn("at most 3 pages", outp)

    def test_web_fetch_refuses_internal_and_records_nothing(self):
        rc, outp = self.studio("web", "fetch", "http://127.0.0.1:8790/", "--film", "baker")
        self.assertEqual(rc, 1)
        self.assertIn("blocked_address", outp)
        self.assertEqual(json.loads((self.d / ".check/opened.json").read_text()), samples.OPENED)


if __name__ == "__main__":
    unittest.main()
