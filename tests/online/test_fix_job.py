"""Fix with Claude on an After Effects film (specs/031 T026): the lot, the fix job, and what the worker puts back."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from helpers import W, Studio, account_id

KEY = "f" * 43


def video(path: Path, seconds: float, color="gray"):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=160x90:r=30:d={seconds}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)


def ae_film(d: Path, n_shots=12):
    (d / "ae").mkdir(parents=True)
    (d / "ae" / "shots.jsx").write_text("CU.shot1 = function () { return CU.comp('S01', 1); };\n")
    (d / "film.json").write_text(json.dumps({"engine": "ae", "shots": [f"S{i}" for i in range(1, n_shots + 1)], "ae_files": ["shots.jsx"]}))
    video(d / f"{d.name}.mp4", n_shots)
    (d / "shots.json").write_text(json.dumps({"version": 1, "video": f"{d.name}.mp4", "duration": n_shots, "fps": 30, "source": "ae",
                                              "shots": [[i, i + 1, "", f"S{i + 1}"] for i in range(n_shots)]}))


class FixJob(unittest.TestCase):
    def setUp(self):
        self.s = Studio()
        f = Path(tempfile.mkdtemp()) / "bridge.json"
        f.write_text(json.dumps({"key": KEY}))
        self.old = os.environ.get("STUDIO_AE_BRIDGE")
        os.environ["STUDIO_AE_BRIDGE"] = str(f)
        self.c = self.s.signup_verified("fix@example.com")
        from studio import store
        self.lib = store.account_dir(account_id(self.c)) / "films" / "ae-one"
        ae_film(self.lib)

    def tearDown(self):
        if self.old is None:
            os.environ.pop("STUDIO_AE_BRIDGE", None)
        else:
            os.environ["STUDIO_AE_BRIDGE"] = self.old
        self.s.close()

    def hello(self):
        self.c.post("/api/v1/ae/bridge/hello", json={"found": True, "afterfx": "C:/AE/AfterFX.exe"}, headers={"x-cu-bridge": KEY})

    def notes(self, per_shot):
        """Write one note per (shot, text) through the API, like the page does."""
        g = self.c.get("/api/v1/films/ae-one/notes").json()
        doc = g["doc"]
        for sid, text in per_shot:
            doc["shots"].setdefault(sid, {"notes": []})["notes"].append({"text": text, "at": 0.5})
        r = self.c.put("/api/v1/films/ae-one/notes", json={"base": g["base"], "doc": doc}, headers=W)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def fix(self):
        return self.c.post("/api/v1/films/ae-one/fix", json={}, headers=W)

    def test_refusals(self):
        r = self.fix()
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "ae_unavailable"))     # no desktop app
        self.hello()
        r = self.fix()
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "no_open_notes"))
        (self.lib.parent / "web-one").mkdir()
        video(self.lib.parent / "web-one" / "web-one.mp4", 1)
        r = self.c.post("/api/v1/films/web-one/fix", json={}, headers=W)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "not_ae"))
        f = self.c.get("/api/v1/films/ae-one").json()
        self.assertEqual((f["engine"], f["ae_ready"], f["lot"]), ("ae", True, None))

    def test_lot_of_ten_in_film_order_and_one_job(self):              # FR-011, US3 scenario 4
        self.hello()
        self.notes([(f"S{i}", f"note {i}") for i in range(12, 0, -1)])    # written last shot first
        r = self.fix()
        self.assertEqual(r.status_code, 201, r.text)
        body = r.json()
        self.assertEqual((len(body["notes"]), body["left"]), (10, 2))
        from studio import jobs
        j = jobs.load(body["job"])
        self.assertEqual((j["kind"], j["status"], j["charged"], j["links"]["film"]), ("fix", "queued", False, "ae-one"))
        doc = self.c.get("/api/v1/films/ae-one/notes").json()["doc"]
        texts = {n["id"]: n["text"] for sh in doc["shots"].values() for n in sh["notes"]}
        self.assertEqual([texts[i] for i in body["notes"]], [f"note {i}" for i in range(1, 11)])
        r = self.fix()
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "in_progress"))     # no second job
        self.assertEqual(self.c.get("/api/v1/films/ae-one").json()["lot"]["job"], body["job"])
        self.notes([("S2", "added while fixing")])                                     # saved, not in the lot
        doc = self.c.get("/api/v1/films/ae-one/notes").json()["doc"]
        self.assertEqual(doc["lot"]["notes"], body["notes"])
        from studio import jobs as J
        J.finish(body["job"], "stopped")                                               # a dead job frees the notes
        self.assertIsNone(self.c.get("/api/v1/films/ae-one").json()["lot"])
        self.assertEqual(self.fix().status_code, 201)

    def run_fix(self, finish_ok=True):
        self.hello()
        self.notes([("S2", "hair is wrong"), ("S5", "logo is wrong"), ("S8", "table cut")])
        jid = self.fix().json()["job"]
        from studio import jobs
        w = self.s.worker
        j = jobs.load(jid)
        work = w.work_dir(jid)
        (work / ".home").mkdir(parents=True, exist_ok=True)
        w.prepare(j, work)
        wf = work / "films" / "ae-one"
        self.assertTrue((wf / "film.json").is_file() and (wf / "ae-one.mp4").is_file())
        self.assertEqual(os.stat(wf / "ae-one.mp4").st_ino, os.stat(self.lib / "ae-one.mp4").st_ino)    # hard link
        self.notes([("S9", "a new note during the run")])
        return jid, work, wf

    def test_done_puts_video_answers_and_code_back(self):             # FR-011, FR-014, US3 scenario 3
        jid, work, wf = self.run_fix()
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
        from filmcheck import shotnotes
        lot = shotnotes.read_notes(wf)["doc"]["lot"]["notes"]
        base = shotnotes.read_notes(wf)["base"]
        base = shotnotes.reply(wf, lot[0], "redrew the hair", done=True, base=base)["base"]
        shotnotes.reply(wf, lot[1], "the logo file is not in the film; left open", done=False, base=base)   # lot[2]: no answer
        (wf / "out").mkdir()
        video(wf / "out" / "fix.mp4", 12, "red")
        shutil.copy2(wf / "shots.json", wf / "out" / "fix-shots.json")
        (wf / "ae" / "shots.jsx").write_text("// fixed\n")
        old_ino = os.stat(self.lib / "ae-one.mp4").st_ino
        from studio import jobs
        jobs.update(jid, lambda x: x.__setitem__("reported", {"done": True, "film": "ae-one"}))
        self.s.worker.finished(jid, 0)
        j = jobs.load(jid)
        self.assertEqual(j["status"], "done", j.get("error"))
        self.assertTrue((self.lib / "ae-one.prev.mp4").is_file())
        self.assertNotEqual(os.stat(self.lib / "ae-one.mp4").st_ino, old_ino)
        self.assertEqual((self.lib / "ae" / "shots.jsx").read_text(), "// fixed\n")
        doc = shotnotes.read_notes(self.lib)["doc"]
        self.assertNotIn("lot", doc)
        by = {n["id"]: n for sh in doc["shots"].values() for n in sh["notes"]}
        self.assertEqual((by[lot[0]]["done"], by[lot[0]]["reply"]), (True, "redrew the hair"))
        self.assertFalse(by[lot[1]]["done"])
        self.assertIn("no answer", by[lot[2]]["reply"])                 # no note is left without a word
        new = [n for n in by.values() if n["text"] == "a new note during the run"][0]
        self.assertNotIn("reply", new)
        self.assertFalse(work.exists())
        self.assertIn("cost_usd", j)                                     # FR-013: the job carries its usage

    def test_failed_keeps_the_film_and_frees_the_notes(self):          # FR-014
        jid, work, wf = self.run_fix()
        old = (self.lib / "ae-one.mp4").read_bytes()
        from studio import jobs
        jobs.update(jid, lambda x: x.__setitem__("reported", {"done": False, "error": "AE crashed"}))
        self.s.worker.finished(jid, 0)
        self.assertEqual(jobs.load(jid)["status"], "failed")
        self.assertEqual((self.lib / "ae-one.mp4").read_bytes(), old)
        self.assertFalse((self.lib / "ae-one.prev.mp4").exists())
        self.assertIsNone(self.c.get("/api/v1/films/ae-one").json()["lot"])
        doc = self.c.get("/api/v1/films/ae-one/notes").json()["doc"]
        self.assertNotIn("lot", doc)

    def test_a_chat_job_left_running_does_not_hold_the_queue(self):
        self.hello()
        self.notes([("S1", "x")])
        from studio import jobs
        jobs.create("film", "chat film", {"film": "ae-one"}, owner=account_id(self.c))     # `job start` of the chat flow
        jid = self.fix().json()["job"]
        got = self.s.worker.claim()
        self.assertEqual(got and got["id"], jid)

    def test_agent_prompt(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "runner"))
        import agent
        p = agent.prompt_for({"kind": "fix", "film": "ae-one", "notes": ["n-0000aaaa", "n-0000bbbb"]})
        for want in ("n-0000aaaa", "ae fix ae-one", "notes reply ae-one", "--done", "job done", "kit_fixes.jsx", "ae uses"):
            self.assertIn(want, p)
        self.assertNotIn("ae render ae-one", p.replace("do not run `ae render`", ""))


class AeFilmJob(unittest.TestCase):
    """US5 (T034): a new film drawn by After Effects."""

    def setUp(self):
        self.s = Studio()
        f = Path(tempfile.mkdtemp()) / "bridge.json"
        f.write_text(json.dumps({"key": KEY}))
        self.old = os.environ.get("STUDIO_AE_BRIDGE")
        os.environ["STUDIO_AE_BRIDGE"] = str(f)
        self.c = self.s.signup_verified("aefilm@example.com")

    def tearDown(self):
        if self.old is None:
            os.environ.pop("STUDIO_AE_BRIDGE", None)
        else:
            os.environ["STUDIO_AE_BRIDGE"] = self.old
        self.s.close()

    def test_needs_the_desktop_app_then_marks_the_job(self):          # FR-018
        from helpers import film_job
        r = film_job(self.c, engine="ae")
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "ae_unavailable"))
        self.assertFalse(self.c.get("/api/v1/me").json()["ae"]["ready"])
        self.c.post("/api/v1/ae/bridge/hello", json={"found": True}, headers={"x-cu-bridge": KEY})
        self.assertTrue(self.c.get("/api/v1/me").json()["ae"]["ready"])
        r = film_job(self.c, engine="ae")
        self.assertEqual(r.status_code, 201, r.text)
        from studio import jobs
        j = jobs.load(r.json()["id"])
        self.assertEqual(j["input"]["engine"], "ae")
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "runner"))
        import agent
        p = agent.prompt_for(j["input"])
        self.assertIn(f"ae new {j['input']['film']}", p)
        self.assertIn("ae render", p)
        self.assertNotIn("ae new", agent.prompt_for({**j["input"], "engine": None}))
        r = film_job(self.c)                                              # web page films are unchanged
        self.assertEqual(r.status_code, 201, r.text)
        self.assertNotIn("engine", jobs.load(r.json()["id"])["input"])

    def test_new_ae_film_holds_no_kit_file(self):                       # SC-008
        root = Path(tempfile.mkdtemp())
        env = {**os.environ, "STUDIO_ROOT": str(root)}
        env.pop("STUDIO_JOB", None)
        repo = Path(__file__).resolve().parents[2]
        p = subprocess.run(["sh", str(repo / "bin" / "studio"), "ae", "new", "fox-1"], env=env, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        d = root / "films" / "fox-1"
        self.assertEqual(json.loads((d / "film.json").read_text())["engine"], "ae")
        kit = {f.name for f in (repo / "tools" / "ae" / "kit").glob("*.jsx")}
        self.assertFalse(kit & {f.name for f in d.rglob("*.jsx")})


if __name__ == "__main__":
    unittest.main()
