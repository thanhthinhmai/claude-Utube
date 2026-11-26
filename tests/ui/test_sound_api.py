"""specs/037 US3 (before 035): the Sound panel's data and edits on the film job page and on the finished film page
(local mode, API)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import REPO, Project, W, client

sys.path.insert(0, str(REPO / "tests" / "filmcheck"))
sys.path.insert(0, str(REPO / "tools"))
import samples  # noqa: E402
import soundfilm  # noqa: E402

NODE_MODULES = REPO / "lib" / "lemo-opuscar" / "node_modules"


def ae_sound_film(root: Path, name: str) -> Path:
    d = samples.review_film(root, name, kit=False)
    soundfilm.make(d)
    (d / "ae").mkdir(exist_ok=True)
    (d / "ae" / "shots.jsx").write_text("// test\n")
    soundfilm.tone(d / "out" / "mix.wav", 7.0, 220, rate=48000, channels=2)
    return d


class SoundApi(unittest.TestCase):
    def setUp(self):
        self.env = {k: os.environ.get(k) for k in ("STUDIO_DATA", "STUDIO_EDIT_NO_RUN", "FREESOUND_API_KEY")}
        os.environ.update(STUDIO_DATA=tempfile.mkdtemp(prefix="snd data."), STUDIO_EDIT_NO_RUN="1", FREESOUND_API_KEY="")
        self.p = Project(ports="18850-18859")
        self.film = ae_sound_film(self.p.dir, "aefilm")
        samples.review_film(self.p.dir, "pagefilm", kit=False)
        self.c = client()
        out = self.p.cli("job", "start", "--kind", "film", "--name", "aefilm", "--film", "aefilm")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.jid, self.url = out.stdout.splitlines()[:2]

    def tearDown(self):
        self.p.close()
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def steps(self):
        r = self.c.get(f"/api/v1/jobs/{self.jid}/steps")
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def act(self, op, args, base):
        from studio import actions
        r = self.c.post(f"/api/v1/jobs/{self.jid}/actions", headers=W, json={"point": "mix", "op": op, "args": args,
                                                                               "base": base})
        self.assertEqual(r.status_code, 202, r.text)
        self.assertTrue(actions.wait_idle(self.jid, 60))
        return self.c.get(f"/api/v1/jobs/{self.jid}/actions/{r.json()['id']}").json()

    def test_sound_block_and_files(self):
        sb = self.steps()["sound"]
        self.assertEqual([s["id"] for s in sb["shots"]], ["S1", "S2", "S3"])
        self.assertEqual((sb["shots"][1]["t0"], sb["shots"][1]["t1"]), (2.0, 5.0))
        self.assertEqual(sb["mix"]["url"], "out/mix.wav")
        self.assertEqual((len(sb["plan_base"]), len(sb["notes_base"])), (16, 16))
        self.assertEqual(sb["impact"], ["Render", "Self-check", "Publish"])          # specs/037 T056 "If you change this"
        self.assertIsNone(sb["shots"][0]["clip_url"])                                 # no Animatic draft yet
        self.assertIsNone(sb["draft"])
        clips = self.film / "animatic" / "clips"
        clips.mkdir(parents=True)
        (clips / "S2.mp4").write_bytes(b"x")
        (self.film / "animatic" / "draft.mp4").write_bytes(b"x")
        sb = self.steps()["sound"]
        self.assertTrue(sb["shots"][1]["clip_url"].startswith("animatic/clips/S2.mp4?v="))
        self.assertTrue(sb["draft"].startswith("animatic/draft.mp4?v="))
        r = self.c.get(f"/api/v1/jobs/{self.jid}/files/out/mix.wav", headers={"Range": "bytes=0-99"})
        self.assertEqual((r.status_code, len(r.content)), (206, 100))
        out = self.p.cli("job", "start", "--kind", "film", "--name", "pagefilm", "--film", "pagefilm")
        page = self.c.get(f"/api/v1/jobs/{out.stdout.splitlines()[0]}/steps").json()
        self.assertIsNone(page["sound"])

    def test_edits_through_actions(self):
        sb = self.steps()["sound"]
        a = self.act("cue-add", {"shot": "S2", "action": "window breaks", "query": "glass break", "at": "1.5"}, sb["plan_base"])
        self.assertEqual(a["status"], "done", a)
        sb = self.steps()["sound"]
        cue = sb["shots"][1]["cues"][0]
        self.assertEqual((cue["action"], cue["anchor"]), ("window breaks", {"shot_at": 0.5}))
        a = self.act("cue-set", {"cue": cue["id"], "gain_db": -3}, sb["plan_base"])
        self.assertEqual(a["status"], "done", a)
        a = self.act("cue-set", {"cue": cue["id"], "gain_db": 0}, sb["plan_base"])   # the old base
        self.assertEqual(a["status"], "conflict", a)
        sb = self.steps()["sound"]
        self.assertEqual(self.act("shot-set", {"shot": "S2", "on": "no"}, sb["plan_base"])["status"], "done")
        self.assertFalse(self.steps()["sound"]["shots"][1]["on"])
        sb = self.steps()["sound"]
        a = self.act("sound-note-add", {"shot": "S3", "text": "The bubbles are too loud"}, sb["notes_base"])
        self.assertEqual(a["status"], "done", a)
        v = self.steps()
        self.assertEqual(v["sound"]["shots"][2]["notes_open"], 1)
        self.assertEqual(v["sound"]["notes"]["shots"]["S3"][0]["text"], "The bubbles are too loud")
        self.assertEqual(self.c.post(f"/api/v1/jobs/{self.jid}/actions", headers=W, json={
            "point": "mix", "op": "cast-approve", "args": {}}).status_code, 422)

    def test_film_page_notes(self):
        r = self.c.get("/api/v1/films/aefilm/sound")
        self.assertEqual(r.status_code, 200, r.text)
        base = r.json()["notes_base"]
        r = self.c.post("/api/v1/films/aefilm/sound/notes", headers=W, json={"shot": "S1", "text": "Too quiet", "base": base})
        self.assertEqual(r.status_code, 201, r.text)
        nid, nb = r.json()["note"]["id"], r.json()["notes_base"]
        r = self.c.post("/api/v1/films/aefilm/sound/notes", headers=W, json={"shot": "S1", "text": "x", "base": base})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "changed"))
        r = self.c.post("/api/v1/films/aefilm/sound/notes", headers=W, json={"shot": "S9", "text": "x"})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(self.c.get("/api/v1/films/pagefilm/sound").status_code, 422)
        self.assertEqual(self.c.get("/api/v1/films/nofilm/sound").status_code, 404)
        r = self.c.post("/api/v1/films/aefilm/sound/fix", headers=W, json={})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "app_only"))   # Claude runs in the app
        r = self.c.delete(f"/api/v1/films/aefilm/sound/notes/S1/{nid}?base={nb}", headers={**W, "Content-Type": "application/json"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(json.loads((self.film / "sound" / "notes.json").read_text())["shots"], {})

    @unittest.skipUnless(shutil.which("node") and (NODE_MODULES / "playwright-core").is_dir(), "no node / playwright-core")
    def test_in_browser(self):
        from filmcheck import soundplan
        soundplan.add_cue(self.film, "S3", "bubbles", {"span": "shot"}, "aquarium bubbles")
        summary = self.p.dir / "s.md"
        summary.write_text("Mix ready")
        self.assertEqual(self.p.cli("review", "request", self.jid, "--kind", "mix", "--film", "aefilm",
                                    "--summary", str(summary)).returncode, 0)
        base = self.url.split("URL: ", 1)[1].split("/#", 1)[0]
        r = subprocess.run(["node", str(Path(__file__).with_name("browser_sound.cjs")), base, self.jid, "aefilm"],
                           capture_output=True, text=True, timeout=180, env={**os.environ, "NODE_PATH": str(NODE_MODULES)})
        if r.returncode == 77:
            self.skipTest("no browser")
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(o["errors"], [])
        self.assertEqual(o["shots"], ["S1", "S2", "S3"])
        self.assertEqual(o["cues"], 1)
        self.assertFalse(o["wide"])                                  # no sideways scroll at 400 px
        self.assertTrue(o["send"], o)
        self.assertEqual(o["sendText"], "Send 1 note to Claude")
        self.assertTrue(o["approveDisabled"])                        # open notes block the approval
        self.assertEqual(o["noteShown"], 1)
        self.assertEqual(o["strip"], {"shots": 3, "fx": 1})                    # T056: shots and sounds on one timeline
        self.assertTrue(o["impact"].startswith("If you change this: Final render"))
        self.assertEqual((o["filmShots"], o["filmNotes"], o["filmEdits"]), (3, 1, 0))   # the film page: notes only


if __name__ == "__main__":
    unittest.main()
