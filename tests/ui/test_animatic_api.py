"""specs/035 T024, T035: the Animatic panel's data, files, approval and fit edits on the film job page (local mode)."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from helpers import REPO, Project, W, client

sys.path.insert(0, str(REPO / "tests" / "filmcheck"))
sys.path.insert(0, str(REPO / "tools"))
import animfilm  # noqa: E402
import samples  # noqa: E402

FAKE_ENV = ("STUDIO_AE_FAKE", "STUDIO_AE_WORK", "STUDIO_AE_CONFIG")


class AnimaticApi(unittest.TestCase):
    def setUp(self):
        self.p = Project(ports="18850-18859")
        self.film = animfilm.make(self.p.dir / "films" / "anim", wavs=True, tones=True)
        samples.review_film(self.p.dir, "pagefilm", kit=False)
        os.environ.update(STUDIO_AE_FAKE="1", STUDIO_AE_WORK=str(self.p.dir / "aework"),
                          STUDIO_AE_CONFIG=str(self.p.dir / "ae.json"))      # before the page server starts
        self.c = client()
        self.jid = self.job("anim")

    def tearDown(self):
        for k in FAKE_ENV:
            os.environ.pop(k, None)
        self.p.close()

    def job(self, film):
        out = self.p.cli("job", "start", "--kind", "film", "--name", film, "--film", film)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.url = out.stdout.splitlines()[1] if len(out.stdout.splitlines()) > 1 else ""
        return out.stdout.splitlines()[0]

    def steps(self, jid=None):
        r = self.c.get(f"/api/v1/jobs/{jid or self.jid}/steps")
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def act(self, op, args=None, base=None, wait=True):
        r = self.c.post(f"/api/v1/jobs/{self.jid}/actions", headers=W, json={
            "point": "animatic", "op": op, "args": args or {}, "base": base})
        self.assertEqual(r.status_code, 202, r.text)
        if not wait:
            return r.json()
        from studio import actions
        self.assertTrue(actions.wait_idle(self.jid, 120))
        return self.c.get(f"/api/v1/jobs/{self.jid}/actions/{r.json()['id']}").json()

    def test_animatic_block(self):
        v = self.steps()
        names = [s["name"] for s in v["steps"]]
        self.assertLess(names.index("Voice"), names.index("Animatic"))
        self.assertNotIn("Shots", names)
        a = v["animatic"]
        self.assertTrue(a["started"])
        self.assertEqual(len(a["shots"]), 9)
        self.assertEqual(a["shots"][1]["frames"], 117)
        self.assertAlmostEqual(a["silence"], 0.329, delta=0.01)
        self.assertEqual(a["limit"], 0.20)
        self.assertTrue(a["gaps"])
        self.assertIsNone(a["draft"])
        self.assertEqual(a["shots"][1]["fit"]["frames_new"], 103)
        self.assertEqual(len(a["timing_base"]), 16)
        self.assertFalse(a["can_undo"])
        self.assertIsNone(self.steps(self.job("pagefilm"))["animatic"])

    def test_files_with_range(self):
        clips = self.film / "animatic" / "clips"
        clips.mkdir(parents=True)
        (clips / "S2.mp4").write_bytes(bytes(range(256)) * 4)
        r = self.c.get(f"/api/v1/jobs/{self.jid}/files/animatic/clips/S2.mp4", headers={"Range": "bytes=10-19"})
        self.assertEqual(r.status_code, 206, r.text)
        self.assertEqual(r.content, bytes(range(10, 20)))
        animfilm.fake_draft(self.film)
        self.assertEqual(self.c.get(f"/api/v1/jobs/{self.jid}/files/animatic/draft.mp4").status_code, 200)
        for bad in ("animatic/draft.json", "animatic/keys.json", "animatic/fit.json", "timing.json", "animatic/../timing.json"):
            self.assertEqual(self.c.get(f"/api/v1/jobs/{self.jid}/files/{bad}").status_code, 404, bad)
        d = self.steps()["animatic"]["draft"]
        self.assertTrue(d["current"])
        self.assertTrue(d["url"].startswith("animatic/draft.mp4?v="))

    def test_approve_needs_anyway(self):
        animfilm.fake_draft(self.film)
        summary = self.p.dir / "s.md"
        summary.write_text("Animatic ready")
        self.assertEqual(self.p.cli("review", "request", self.jid, "--kind", "animatic", "--film", "anim",
                                    "--summary", str(summary)).returncode, 0)
        rid = next(r["id"] for r in self.c.get("/api/v1/reviews?status=pending").json()["reviews"] if r["kind"] == "animatic")
        base = self.steps()["points"]["animatic"]["fingerprint"]
        r = self.c.post(f"/api/v1/reviews/{rid}/decision", headers=W, json={"value": "approve", "base": base})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "needs_anyway"), r.text)
        r = self.c.post(f"/api/v1/reviews/{rid}/decision", headers=W, json={"value": "approve", "base": base, "anyway": True})
        self.assertEqual(r.status_code, 201, r.text)
        rv = json.loads((self.film / "checks.json").read_text())["reviews"]["approved"]["animatic"]
        self.assertTrue(rv["anyway"])
        self.assertAlmostEqual(rv["silence"], 0.329, delta=0.01)

    def test_fit_edits_rebuild_the_changed_shots(self):
        v = self.steps()["animatic"]
        a = self.act("animatic-fit-accept", {"shots": "S2"}, v["timing_base"])
        self.assertEqual(a["status"], "done", a)
        self.assertEqual(a["result"]["rebuild"], ["S2"])
        from studio import actions, store
        self.assertTrue(actions.wait_idle(self.jid, 300))
        drafts = [x for x in store.doc_list("action") if x["job_id"] == self.jid and x["op"] == "animatic-draft"]
        self.assertEqual([(x["args"]["shots"], x["status"]) for x in drafts], [("S2", "done")], drafts)
        v = self.steps()["animatic"]
        self.assertEqual(v["shots"][1]["frames"], 103)
        self.assertTrue(v["draft"]["current"])
        self.assertIsNone(v["building"])
        self.assertTrue(v["can_undo"])
        a = self.act("animatic-fit-skip", {"shot": "S9"}, v["timing_base"])
        self.assertEqual(a["status"], "done", a)
        self.assertEqual(next(s for s in self.steps()["animatic"]["shots"] if s["id"] == "S9")["fit"]["state"], "skipped")
        a = self.act("animatic-fit-undo", {}, "0" * 16)                      # stale base
        self.assertEqual(a["status"], "conflict", a)
        a = self.act("animatic-fit-undo", {}, self.steps()["animatic"]["timing_base"])
        self.assertEqual((a["status"], a["result"]["rebuild"]), ("done", ["S2"]), a)
        self.assertTrue(actions.wait_idle(self.jid, 300))
        self.assertEqual(self.steps()["animatic"]["shots"][1]["frames"], 117)

    def test_rebuilds_waiting_join(self):
        from unittest import mock
        from studio import actions, jobs, store
        j = jobs.load(self.jid)
        with mock.patch("studio.actions.start_local"):                        # nothing runs: both wait in the queue
            first = actions.create(j, "animatic", "animatic-draft", {"shots": "S2"}, None, "t")
            second = actions.create(j, "animatic", "animatic-draft", {"shots": "S6,S2"}, None, "t")
            self.assertEqual(second["id"], first["id"])
            self.assertEqual(store.doc_get("action", first["id"])["args"]["shots"], "S2,S6")
            actions.create(j, "animatic", "animatic-draft", {}, None, "t")    # the whole film
            self.assertEqual(store.doc_get("action", first["id"])["args"]["shots"], "")
            self.assertEqual(len(actions.queued(self.jid)), 1)
        self.assertEqual(self.steps()["animatic"]["building"], {"shots": ["all"], "running": False})

    def test_in_browser(self):
        env = {**os.environ, "STUDIO_ROOT": str(self.p.dir)}
        for k in ("STUDIO_JOB", "STUDIO_PROXY"):
            env.pop(k, None)
        r = subprocess.run(["sh", str(REPO / "bin" / "studio"), "ae", "draft", "anim", "--dir", str(self.film)],
                           capture_output=True, text=True, env=env, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        summary = self.p.dir / "s.md"
        summary.write_text("Animatic ready")
        self.p.cli("review", "request", self.jid, "--kind", "animatic", "--film", "anim", "--summary", str(summary))
        base = self.url.split("URL: ", 1)[1].split("/#", 1)[0] if "URL: " in self.url else ""
        if not base:
            self.skipTest("no page URL")
        r = subprocess.run(["node", str(Path(__file__).with_name("browser_animatic.cjs")), base, self.jid,
                            os.environ.get("ANIM_SHOT", "")], capture_output=True, text=True, timeout=240,
                           env={**os.environ, "NODE_PATH": str(REPO / "lib" / "lemo-opuscar" / "node_modules")})
        if r.returncode == 77:
            self.skipTest("no browser")
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(o["errors"], [])
        self.assertIn("Animatic", o["rail"])
        self.assertIn("Sound", o["rail"])
        self.assertIn("Final render", o["rail"])
        self.assertNotIn("Shots", o["rail"])
        self.assertEqual(o["gate"], 1)
        self.assertEqual((o["silence"], o["silenceWarn"]), ("Silence 33% · limit 20%", 1))
        self.assertEqual((o["shots"], o["lines"], o["cards"], o["pictures"], o["player"]), (9, 14, 9, 9, 1))
        self.assertEqual(o["gaps"], 3)
        self.assertEqual(o["suggestions"], 9)
        self.assertEqual(o["impact"], ["↻ Sound", "↻ Final render", "↻ Self-check", "↻ Publish"])
        self.assertTrue(o["approveDisabled"])                                 # silence over the limit: tick "anyway"
        self.assertEqual(o["anyway"], 1)
        self.assertEqual(o["afterAccept"]["suggestions"], 8)
        self.assertEqual(o["afterAccept"]["undo"], 1)
        self.assertIn("animatic/clips/S2.mp4", o["clip"])
        self.assertTrue(o["narrow"])
        from filmcheck import animatic
        self.assertTrue(animatic.draft_current(self.film))                  # the page rebuilt S2
        self.assertEqual(json.loads((self.film / "animatic" / "draft.json").read_text())["shots_built"], ["S2"])


if __name__ == "__main__":
    unittest.main()
