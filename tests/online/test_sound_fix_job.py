"""specs/037 US3 (before 035): "Send notes to Claude" on a finished AE film's Sound notes: a fix job with target sound,
the work copy keeps out/, Claude's answers come back, the customer's film is untouched until the job is done."""
import json
import os
import sys
import unittest
from pathlib import Path

from helpers import W, Studio, account_id

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "tests" / "filmcheck"))
import soundfilm  # noqa: E402


class SoundFixJob(unittest.TestCase):
    def setUp(self):
        self.s = Studio()
        self.c = self.s.signup_verified("sound@example.com")
        from studio import store
        self.acc = store.account_dir(account_id(self.c))
        d = soundfilm.make(self.acc / "films" / "f1")
        (d / "ae").mkdir()
        (d / "ae" / "shots.jsx").write_text("// test\n")
        soundfilm.tone(d / "out" / "mix.wav", 7.0, 220, rate=48000, channels=2)
        (d / "f1.mp4").write_bytes(b"old film")
        self.d = d

    def tearDown(self):
        self.s.close()

    def note(self, shot, text):
        base = self.c.get("/api/v1/films/f1/sound").json()["notes_base"]
        r = self.c.post("/api/v1/films/f1/sound/notes", json={"shot": shot, "text": text, "base": base}, headers=W)
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["note"]["id"]

    def run_job(self, jid, ok=True):
        from studio import jobs
        from filmcheck import soundnotes
        w = self.s.worker
        j = jobs.load(jid)
        work = w.work_dir(jid)
        (work / ".home").mkdir(parents=True, exist_ok=True)
        w.prepare(j, work)
        wf = work / "films" / "f1"
        self.assertTrue((wf / "out" / "mix.wav").is_file())             # a sound fix keeps out/
        if ok:
            for _, n in soundnotes.all_notes(soundnotes.load(wf)):
                soundnotes.reply(wf, n["id"], "Bubbles 4 dB quieter", done=True)
            (wf / "out" / "mix.wav").write_bytes(b"RIFF new mix")
            os.unlink(wf / "f1.mp4")                                        # the remux writes a new file
            (wf / "f1.mp4").write_bytes(b"new film")
        jobs.update(jid, lambda x: x.__setitem__("reported", {"done": True} if ok else {"done": False, "error": "AE crashed"}))
        w.finished(jid, 0)
        return jobs.load(jid)

    def test_fix_from_sound_notes(self):
        r = self.c.post("/api/v1/films/f1/sound/fix", json={}, headers=W)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "no_notes"))
        n1 = self.note("S3", "The bubbles are too loud")
        r = self.c.post("/api/v1/films/f1/sound/fix", json={}, headers=W)
        self.assertEqual(r.status_code, 201, r.text)
        jid = r.json()["job"]
        from studio import jobs
        j = jobs.load(jid)
        self.assertEqual((j["kind"], j["input"]["target"], j["input"]["notes"]), ("fix", "sound", [n1]))
        n2 = self.note("S1", "Written while Claude works")                  # waits for the next round
        r = self.c.post("/api/v1/films/f1/sound/fix", json={}, headers=W)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "busy"))
        j = self.run_job(jid)
        self.assertEqual(j["status"], "done", j.get("error"))
        doc = json.loads((self.d / "sound" / "notes.json").read_text())
        a = next(n for n in doc["shots"]["S3"] if n["id"] == n1)
        b = next(n for n in doc["shots"]["S1"] if n["id"] == n2)
        self.assertEqual((a["reply"], a["done"], b["reply"], b["done"]), ("Bubbles 4 dB quieter", True, None, False))
        self.assertNotIn("lot", doc)
        self.assertEqual((self.d / "out" / "mix.wav").read_bytes(), b"RIFF new mix")
        self.assertEqual((self.d / "f1.mp4").read_bytes(), b"new film")

    def test_failed_keeps_the_film(self):
        self.note("S2", "Crash is late")
        jid = self.c.post("/api/v1/films/f1/sound/fix", json={}, headers=W).json()["job"]
        j = self.run_job(jid, ok=False)
        self.assertEqual(j["status"], "failed")
        doc = json.loads((self.d / "sound" / "notes.json").read_text())
        self.assertNotIn("lot", doc)
        self.assertIn("AE crashed", doc["failed_lot"]["error"])
        self.assertEqual((self.d / "f1.mp4").read_bytes(), b"old film")
        self.assertFalse(doc["shots"]["S2"][0]["done"])

    def test_agent_prompt(self):
        sys.path.insert(0, str(REPO / "tools" / "runner"))
        import agent
        p = agent.prompt_for({"kind": "fix", "target": "sound", "film": "f1", "notes": ["n-1"]})
        for want in ("sound notes", "reply", "sound mix", "job done"):
            self.assertIn(want, p)


if __name__ == "__main__":
    unittest.main()
