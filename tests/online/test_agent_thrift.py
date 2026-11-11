"""Spending less per film (asked after the 008 live runs): a lean guide for online film jobs, `job run` that shows
the agent only the end of long output, and per-run statistics of what the agent read."""
import json
import os
import subprocess
import sys
import unittest

from helpers import REPO, Studio, film_job

sys.path.insert(0, str(REPO / "tools" / "runner"))


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
