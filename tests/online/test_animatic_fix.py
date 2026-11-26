"""specs/035 T041, T042: "Send notes to Claude" on the Animatic outside a waiting film job: the fix job with target
"animatic", what the worker puts back (code, draft, answers) and a failed round that keeps the notes open (FR-022)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import W, Studio, account_id

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "tests" / "filmcheck"))
import animfilm  # noqa: E402

KEY = "f" * 43


class AnimaticFix(unittest.TestCase):
    def setUp(self):
        self.s = Studio()
        f = Path(tempfile.mkdtemp()) / "bridge.json"
        f.write_text(json.dumps({"key": KEY}))
        self.old = os.environ.get("STUDIO_AE_BRIDGE")
        os.environ["STUDIO_AE_BRIDGE"] = str(f)
        self.c = self.s.signup_verified("anim@example.com")
        from studio import store
        from filmcheck import timing
        self.lib = store.account_dir(account_id(self.c)) / "films" / "anim"
        animfilm.make(self.lib)
        timing.start(self.lib)
        animfilm.fake_draft(self.lib)

    def tearDown(self):
        if self.old is None:
            os.environ.pop("STUDIO_AE_BRIDGE", None)
        else:
            os.environ["STUDIO_AE_BRIDGE"] = self.old
        self.s.close()

    def fix(self):
        return self.c.post("/api/v1/films/anim/animatic/fix", json={}, headers=W)

    def start(self):
        from filmcheck import animatic
        self.c.post("/api/v1/ae/bridge/hello", json={"found": True, "afterfx": "C:/AE/AfterFX.exe"}, headers={"x-cu-bridge": KEY})
        a = animatic.note_add(self.lib, "S6", "slower", at=1.0, x=40, y=30)
        b = animatic.note_add(self.lib, "S2", "the cup")
        r = self.fix()
        self.assertEqual(r.status_code, 201, r.text)
        body = r.json()
        self.assertEqual((body["shots"], sorted(body["notes"])), (["S6", "S2"], sorted([a["id"], b["id"]])))
        from studio import jobs
        j = jobs.load(body["job"])
        self.assertEqual((j["input"]["target"], j["charged"]), ("animatic", False))
        self.assertEqual((self.fix().status_code, self.fix().json()["error"]["code"]), (409, "in_progress"))
        work = self.s.worker.work_dir(j["id"])
        (work / ".home").mkdir(parents=True, exist_ok=True)
        self.s.worker.prepare(j, work)
        wf = work / "films" / "anim"
        self.assertNotEqual(os.stat(wf / "animatic" / "draft.mp4").st_ino, os.stat(self.lib / "animatic" / "draft.mp4").st_ino)
        return j["id"], wf, a, b

    def test_refusals(self):
        r = self.fix()
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "ae_unavailable"))
        self.c.post("/api/v1/ae/bridge/hello", json={"found": True, "afterfx": "C:/AE/AfterFX.exe"}, headers={"x-cu-bridge": KEY})
        r = self.fix()
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "no_notes"))

    def test_done_puts_code_draft_and_answers_back(self):
        from filmcheck import animatic
        jid, wf, a, b = self.start()
        late = animatic.note_add(self.lib, "S3", "written during the run")
        animatic.note_reply(wf, a["id"], "slowed the walk", done=True)
        (wf / "ae" / "fixed.jsx").write_text("// fixed\n")
        (wf / "animatic" / "draft.mp4").write_bytes(b"new draft")
        from studio import jobs
        jobs.update(jid, lambda x: x.__setitem__("reported", {"done": True, "film": "anim"}))
        self.s.worker.finished(jid, 0)
        self.assertEqual(jobs.load(jid)["status"], "done", jobs.load(jid).get("error"))
        self.assertEqual((self.lib / "ae" / "fixed.jsx").read_text(), "// fixed\n")
        self.assertEqual((self.lib / "animatic" / "draft.mp4").read_bytes(), b"new draft")
        doc = animatic.notes_load(self.lib)
        self.assertNotIn("lot", doc)
        by = {n["id"]: n for _, n in animatic.NOTES.all_notes(doc)}
        self.assertEqual((by[a["id"]]["done"], by[a["id"]]["reply"]), (True, "slowed the walk"))
        self.assertFalse(by[b["id"]]["done"])
        self.assertIsNone(by[late["id"]]["reply"])                        # the next round's note is untouched
        self.assertEqual(animatic.open_notes(self.lib), {"S2": 1, "S3": 1})

    def test_failed_keeps_the_notes_open(self):
        from filmcheck import animatic
        jid, wf, a, b = self.start()
        from studio import jobs
        jobs.update(jid, lambda x: x.__setitem__("reported", {"done": False, "error": "AE crashed"}))
        self.s.worker.finished(jid, 0)
        self.assertEqual(jobs.load(jid)["status"], "failed")
        doc = animatic.notes_load(self.lib)
        self.assertNotIn("lot", doc)
        self.assertIn("AE crashed", doc["failed_lot"]["error"])
        self.assertEqual(animatic.open_notes(self.lib), {"S2": 1, "S6": 1})
        self.assertEqual(self.fix().status_code, 201)                      # "Send again"

    def test_agent_prompt(self):
        sys.path.insert(0, str(REPO / "tools" / "runner"))
        import agent
        p = agent.prompt_for({"kind": "fix", "target": "animatic", "film": "anim", "shots": ["S2", "S6"], "notes": ["n-1"]})
        for want in ("animatic notes", "ae draft anim", "--shots", "reply", "--done", "Never approve the animatic", "job done",
                     "kit_fixes.jsx"):
            self.assertIn(want, p)


if __name__ == "__main__":
    unittest.main()
