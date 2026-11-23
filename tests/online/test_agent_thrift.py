"""Spending less per film (asked after the 008 live runs): a lean guide for online film jobs, `job run` that shows
the agent only the end of long output, and per-run statistics of what the agent read."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from helpers import REPO, Studio, film_job

sys.path.insert(0, str(REPO / "tools" / "runner"))


class CompactSavings(unittest.TestCase):
    """specs/030 US2, US3: the agent compacts earlier, keeps the right things, and leaves a note before it does."""

    def test_compact_env_defaults_and_overrides(self):
        import worker
        self.assertEqual(worker.compact_env({}), {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "300000",
                                                  "BASH_MAX_OUTPUT_LENGTH": "20000"})
        self.assertEqual(worker.compact_env({"STUDIO_AUTO_COMPACT_WINDOW": "500000", "STUDIO_BASH_MAX_OUTPUT": "8000"}),
                         {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "500000", "BASH_MAX_OUTPUT_LENGTH": "8000"})
        with self.assertLogs("studio.worker", "WARNING"):
            bad = worker.compact_env({"STUDIO_AUTO_COMPACT_WINDOW": "50000", "STUDIO_BASH_MAX_OUTPUT": "abc"})
        self.assertEqual(bad, {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "300000", "BASH_MAX_OUTPUT_LENGTH": "20000"})

    def test_film_job_gets_the_compact_env(self):           # SC-004: what the runner actually starts with
        s = Studio()
        try:
            seen = []
            start = s.worker.runner.start
            s.worker.runner.start = lambda jid, work, env, *a, **k: (seen.append(env), start(jid, work, env, *a, **k))[1]
            c = s.signup_verified("m@x.test")
            jid = film_job(c, idea="A fox").json()["id"]
            s.start()
            self.assertEqual(s.wait(jid)["status"], "done")
            self.assertEqual(seen[0]["CLAUDE_CODE_AUTO_COMPACT_WINDOW"], "300000")
            self.assertEqual(seen[0]["BASH_MAX_OUTPUT_LENGTH"], "20000")
        finally:
            s.close()

    def test_rules_say_what_to_keep(self):
        import agent
        r = agent.rules()
        for words in ("When the conversation is compacted", "film name", "review request", "next step",
                      "Drop the contents", ".compact-state.md"):
            self.assertIn(words, r)

    def make_work(self, files=3):
        import tempfile
        work = Path(tempfile.mkdtemp())
        f = work / "films" / "f"
        (f / ".check").mkdir(parents=True)
        (f / ".check" / "hidden.json").write_text("{}")
        for i in range(files):
            (f / f"file-{i:03}.txt").write_text("x")
        (f / "checks.json").write_text(json.dumps({
            "script": {"verdict": "pass"}, "film": {"pass": False},
            "tiers": {"plan": {"pass": True, "issues": []},
                      "shots": {"pass": False, "issues": [{"severity": "block"}, {"severity": "warn"}]}}}))
        t = work / "t.jsonl"
        t.write_text(json.dumps({"input": {"command": 'sh /studio/bin/studio job step J1 "Script"'}}) + "\n" +
                     json.dumps({"input": {"command": 'sh /studio/bin/studio job step J1 "Picture"'}}) + "\n")
        return work, t

    def test_state_note(self):                              # SC-005
        import time
        import agent
        work, t = self.make_work()
        t0 = time.time()
        agent.save_compact_state(work, {"transcript_path": str(t), "trigger": "auto"})
        self.assertLess(time.time() - t0, 1.0)
        note = (work / ".compact-state.md").read_text()
        self.assertIn("auto", note)
        self.assertIn("Last step: Picture", note)
        for i in range(3):
            self.assertIn(f"films/f/file-{i:03}.txt", note)
        self.assertNotIn("hidden.json", note)
        self.assertIn("- script: pass", note)
        self.assertIn("- tier plan: pass (0 errors)", note)
        self.assertIn("- tier shots: fail (1 errors)", note)
        self.assertIn("- film: fail", note)

    def test_state_note_is_small_and_never_fails(self):
        import agent
        work, t = self.make_work(files=500)
        agent.save_compact_state(work, {"transcript_path": str(t), "trigger": "manual"})
        note = (work / ".compact-state.md").read_text()
        self.assertLessEqual(len(note.encode()), agent.STATE_MAX)
        self.assertEqual(note.count("\n- films/f/"), 20)         # 20 newest files (checks.json may be one of them)
        agent.save_compact_state(work, {"transcript_path": "/nope", "trigger": "auto"})     # overwritten, not grown
        self.assertIn("Last step: unknown", (work / ".compact-state.md").read_text())
        os.chmod(work, 0o500)
        try:
            agent.save_compact_state(work, {})                                 # read-only folder: no exception
        finally:
            os.chmod(work, 0o700)


class Thrift(unittest.TestCase):
    def test_film_jobs_follow_the_lean_guide(self):
        import agent
        guide = (REPO / "tools" / "runner" / "JOB.md").read_text()
        for stage in ("Treatment", "Script", "Look", "Voice", "Music", "Picture", "Mix", "Render", "Self-check"):
            self.assertIn(f"`{stage}`", guide)
        self.assertIn("1280 px", guide)
        rules = agent.rules()
        self.assertIn("tools/runner/JOB.md", rules)
        self.assertIn("Do not read the studio's CLAUDE.md", rules)

    def test_publish_is_made_again_after_changes(self):            # specs/011 T015, T031, FR-001, FR-015
        import inspect
        import agent
        import worker
        self.assertIn("`Publish`", (REPO / "tools" / "runner" / "JOB.md").read_text())
        self.assertIn("studio publish", inspect.getsource(worker.Worker.finished))       # the QC fix round
        p = agent.revise_prompt({"revise_of": "old", "film": "new", "style": "s", "seconds": 30, "note": "n"})
        self.assertIn("publish", p)
        self.assertIn("Publish", agent.rules())

    def test_channel_films_read_the_brief(self):                    # specs/012 T014
        import agent
        inp = {"style": "s", "seconds": 40, "film": "f", "idea": "i"}
        self.assertNotIn("CHANNEL_BRIEF", agent.film_prompt(inp))
        p = agent.film_prompt({**inp, "channel": "honey-facts"})
        self.assertIn("CHANNEL_BRIEF.md", p)
        self.assertIn("lines.json", p)
        self.assertIn("CHANNEL_BRIEF.md names another language", agent.rules())

    def test_agent_stats_from_a_transcript(self):
        import tempfile
        from pathlib import Path
        import worker
        work = Path(tempfile.mkdtemp(prefix="stats."))
        d = work / ".home" / ".claude" / "projects" / "p"
        d.mkdir(parents=True)
        rows = [
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "a", "name": "Read",
                                                           "input": {"file_path": str(work / "big.js")}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "a", "content": "x" * 50_000}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "b", "name": "Read",
                                                           "input": {"file_path": str(work / "sheet.jpg")}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "b",
                                                      "content": [{"type": "image", "source": {"data": "y" * 9000}}]}]}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "done"}]}},
        ]
        (d / "s.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n")
        st = worker.agent_stats(work)
        self.assertEqual((st["turns"], st["tools"], st["reads"], st["images"]), (3, {"Read": 2}, 2, 1))
        self.assertEqual(st["biggest"][0]["what"], "./big.js")
        self.assertGreater(st["biggest"][0]["kb"], 40)
        self.assertNotIn("xxxx", json.dumps(st))                  # sizes and names only, never the text


class QuietRun(unittest.TestCase):
    def setUp(self):
        self.s = Studio()
        self.c = self.s.signup_verified("q@x.test")

    def tearDown(self):
        self.s.close()

    def test_job_run_online_prints_only_the_end(self):
        import proxy
        from studio import jobs
        jid = film_job(self.c).json()["id"]
        jobs.set_status(jid, "running")
        token = proxy.issue(jid)
        env = {"PATH": os.environ["PATH"], "STUDIO_MODE": "online", "STUDIO_JOB": jid, "STUDIO_JOB_TOKEN": token,
               "STUDIO_PROXY": self.s.proxy.url, "HOME": str(self.s.data)}
        p = subprocess.run(["sh", str(REPO / "bin" / "studio"), "job", "run", jid, "--step", "Render", "--",
                            sys.executable, "-c", "[print(f'frame {i}') for i in range(80)]"],
                           capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        out = p.stdout.strip().splitlines()
        self.assertLessEqual(len(out), 21)
        self.assertEqual(out[-1], "frame 79")
        self.assertIn("earlier lines are in the job log", out[0])
        j = jobs.load(jid)
        self.assertEqual(j["step"], "Render")
        self.assertIn("frame 40", [x["line"] for x in j["log"]])     # the job log keeps more than the agent saw


if __name__ == "__main__":
    unittest.main()
