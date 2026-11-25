"""The channel's cast in the app (specs/034 T044): preview a newer rig, update, approve, fix a character from notes."""
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
import castfilm  # noqa: E402

KEY = "c" * 43


def sheet(d: Path, cid: str, tag: str):
    s = d / "cast" / "sheets" / cid
    s.mkdir(parents=True, exist_ok=True)
    (s / "front.jpg").write_bytes(b"\xff\xd8" + tag.encode())
    (s / "sheet.json").write_text(json.dumps({"character": cid, "rig": "ball@1", "built_at": "x",
                                              "frames": [{"key": "front", "group": "turn", "label": "Front", "file": "front.jpg"}]}))


class CastFixJob(unittest.TestCase):
    def setUp(self):
        self.s = Studio()
        f = Path(tempfile.mkdtemp()) / "bridge.json"
        f.write_text(json.dumps({"key": KEY}))
        self.old = os.environ.get("STUDIO_AE_BRIDGE")
        os.environ["STUDIO_AE_BRIDGE"] = str(f)
        self.c = self.s.signup_verified("cast@example.com")
        from studio import store
        from filmcheck import cast, castlib
        self.acc = store.account_dir(account_id(self.c))
        d = castfilm.make(self.acc / "films" / "f1")
        sheet(d, "hero", "v1")
        cast.approve(d, ["hero"])
        self.assertEqual(castlib.save_approved(d, ["hero"]), ["✓ default/hero: v1 (new)"])
        self.lib = self.acc / "channels" / "default" / "cast" / "hero"

    def tearDown(self):
        if self.old is None:
            os.environ.pop("STUDIO_AE_BRIDGE", None)
        else:
            os.environ["STUDIO_AE_BRIDGE"] = self.old
        self.s.close()

    def hello(self):
        self.c.post("/api/v1/ae/bridge/hello", json={"found": True, "afterfx": "C:/AE/AfterFX.exe"}, headers={"x-cu-bridge": KEY})

    def run_job(self, jid, ok=True, tag="new"):
        """The worker prepares the small film, a fake agent draws the sheet (and answers notes), the worker finishes."""
        from studio import jobs
        w = self.s.worker
        j = jobs.load(jid)
        work = w.work_dir(jid)
        (work / ".home").mkdir(parents=True, exist_ok=True)
        w.prepare(j, work)
        wf = work / "films" / "cast-hero"
        self.assertTrue((wf / "film.json").is_file())
        if ok:
            sheet(wf, "hero", tag)
            from filmcheck import castnotes
            for cid, n in castnotes.all_notes(castnotes.load(wf)):
                castnotes.reply(wf, n["id"], "bigger hat", done=True)
        jobs.update(jid, lambda x: x.__setitem__("reported", {"done": True} if ok else {"done": False, "error": "AE crashed"}))
        w.finished(jid, 0)
        return jobs.load(jid), wf

    def test_preview_update_approve(self):
        r = self.c.post("/api/v1/cast-library/default/hero/preview", json={"rig": "ball@1"}, headers=W)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "ae_unavailable"))
        self.hello()
        r = self.c.post("/api/v1/cast-library/default/hero/preview", json={"rig": "ball@9"}, headers=W)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "bad_rig"))
        self.assertEqual(self.c.post("/api/v1/cast-library/default/nobody/preview", json={"rig": "ball@1"}, headers=W).status_code, 404)
        r = self.c.post("/api/v1/cast-library/default/hero/preview", json={"rig": "ball@1"}, headers=W)
        self.assertEqual(r.status_code, 201, r.text)
        from studio import jobs
        jid = r.json()["job"]
        j = jobs.load(jid)
        self.assertEqual((j["kind"], j["input"]["target"], j["input"]["mode"], j["input"]["rig"]), ("fix", "cast", "preview", "ball@1"))
        r = self.c.post("/api/v1/cast-library/default/hero/preview", json={"rig": "ball@1"}, headers=W)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "in_progress"))
        j, wf = self.run_job(jid)
        self.assertEqual(j["status"], "done", j.get("error"))
        self.assertTrue((self.lib / "v2.preview" / "sheet" / "front.jpg").is_file())
        g = self.c.get("/api/v1/cast-library/default/hero").json()
        self.assertEqual((g["v"], g["preview"]["v"]), (1, "2"))
        self.assertEqual(self.c.get("/api/v1/cast-library/default/hero/v2.preview/front.jpg").content, b"\xff\xd8new")
        r = self.c.post("/api/v1/cast-library/default/hero/update", headers=W)
        self.assertEqual(r.json(), {"v": 2})
        r = self.c.post("/api/v1/cast-library/default/hero/update", headers=W)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "no_preview"))
        lib = self.c.get("/api/v1/cast-library").json()["channels"][0]["characters"][0]
        self.assertEqual((lib["latest"], lib["pending"]), (1, 2))       # later films still use v1
        self.assertEqual(self.c.post("/api/v1/cast-library/default/hero/approve", headers=W).json(), {"v": 2})
        lib = self.c.get("/api/v1/cast-library").json()["channels"][0]["characters"][0]
        self.assertEqual((lib["latest"], lib["pending"]), (2, None))
        r = self.c.post("/api/v1/cast-library/default/hero/approve", headers=W)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "nothing_to_approve"))

    def test_fix_from_notes(self):
        self.hello()
        self.assertEqual(self.c.post("/api/v1/cast-library/default/hero/fix", json={"notes": []}, headers=W).status_code, 422)
        r = self.c.post("/api/v1/cast-library/default/hero/fix", json={"notes": ["make the hat bigger"]}, headers=W)
        self.assertEqual(r.status_code, 201, r.text)
        jid = r.json()["job"]
        j, wf = self.run_job(jid)
        self.assertEqual(j["status"], "done", j.get("error"))
        notes = json.loads((self.lib / "v2" / "notes.json").read_text())
        n = notes["characters"]["hero"]["notes"][0]
        self.assertEqual((n["text"], n["reply"], n["done"]), ("make the hat bigger", "bigger hat", True))
        self.assertIsNone(json.loads((self.lib / "v2" / "character.json").read_text())["approved"])
        self.assertEqual(self.c.get("/api/v1/cast-library").json()["channels"][0]["characters"][0]["pending"], 2)

    def test_failed_leaves_the_library(self):
        self.hello()
        jid = self.c.post("/api/v1/cast-library/default/hero/fix", json={"notes": ["x"]}, headers=W).json()["job"]
        j, _ = self.run_job(jid, ok=False)
        self.assertEqual(j["status"], "failed")
        self.assertEqual(sorted(p.name for p in self.lib.iterdir()), ["v1"])

    def test_agent_prompt(self):
        sys.path.insert(0, str(REPO / "tools" / "runner"))
        import agent
        p = agent.prompt_for({"kind": "fix", "target": "cast", "mode": "library", "channel": "default", "character": "hero",
                              "notes": ["x"]})
        for want in ("ae sheet cast-hero", "cast notes reply", "--done", "job done", "Never change the shared kit"):
            self.assertIn(want, p)
        p = agent.prompt_for({"kind": "fix", "target": "cast", "mode": "preview", "channel": "default", "character": "hero",
                              "rig": "ball@2"})
        self.assertIn("ball@2", p)
        self.assertNotIn("cast notes reply", p)


if __name__ == "__main__":
    unittest.main()
