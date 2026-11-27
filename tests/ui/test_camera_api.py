"""specs/039 US3: the Camera panel's data, its edits through actions, "Send notes to Claude" and the approval
(local mode, API), plus the page in a browser."""
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
import test_camsuggest as ts  # noqa: E402

NODE_MODULES = REPO / "lib" / "lemo-opuscar" / "node_modules"


def camera_film(root: Path, name: str) -> Path:
    """An AE film with camera options, a still for every option and a reference frame for each library shot."""
    from filmcheck import camsuggest
    from PIL import Image
    d = ts.make_film(root, name=name, plan=ts.PLAN)
    st = root / "my-styles" / "camstyle"
    (st / "camera").mkdir(exist_ok=True)
    for r in ts.SHOTS:
        for e in r["evidence"] or []:
            Image.new("RGB", (160, 90), (80, 60, 40)).save(st / e)
    camsuggest.suggest(d)
    o = camsuggest.load(d)
    (d / "camera" / "stills").mkdir(parents=True, exist_ok=True)
    for s, row in o["shots"].items():
        for x in row["options"]:
            rel = f"camera/stills/{s}-o{x['n']}.jpg"
            Image.new("RGB", (480, 270), (60, 90, 120 + 40 * x["n"])).save(d / rel)
            x["still"] = rel
    (d / "camera" / "options.json").write_bytes(camsuggest._dump(o))
    return d


class CameraApi(unittest.TestCase):
    def setUp(self):
        self.env = {k: os.environ.get(k) for k in ("STUDIO_DATA", "STUDIO_EDIT_NO_RUN")}
        os.environ.update(STUDIO_DATA=tempfile.mkdtemp(prefix="cam data."), STUDIO_EDIT_NO_RUN="1")
        self.p = Project(ports="18860-18869")
        self.film = camera_film(self.p.dir, "camfilm")
        self.c = client()
        out = self.p.cli("job", "start", "--kind", "film", "--name", "camfilm", "--film", "camfilm")
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

    def act(self, op, args, base=None):
        from studio import actions
        r = self.c.post(f"/api/v1/jobs/{self.jid}/actions", headers=W,
                        json={"point": "camera", "op": op, "args": args, "base": base})
        self.assertEqual(r.status_code, 202, r.text)
        self.assertTrue(actions.wait_idle(self.jid, 60))
        return self.c.get(f"/api/v1/jobs/{self.jid}/actions/{r.json()['id']}").json()

    def request(self):
        s = self.p.dir / "s.md"
        s.write_text("Camera options ready")
        out = self.p.cli("review", "request", self.jid, "--kind", "camera", "--film", "camfilm", "--summary", str(s))
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout.splitlines()[0]

    def test_block_files_and_refs(self):
        v = self.steps()
        cb = v["camera"]
        self.assertEqual([s["id"] for s in cb["shots"]], ["S1", "S2", "S3"])
        self.assertEqual(cb["missing"], [])
        self.assertEqual(cb["source"], "style:camstyle")
        self.assertIn("Camera", [s["name"] for s in v["steps"]])
        s1 = cb["shots"][0]
        self.assertEqual(s1["chosen"], s1["recommended"])
        self.assertTrue(2 <= len(s1["options"]) <= 3)
        o = s1["options"][0]
        r = self.c.get(f"/api/v1/jobs/{self.jid}/files/{o['still']}")
        self.assertEqual((r.status_code, r.headers["content-type"]), (200, "image/jpeg"))
        r = self.c.get(f"/api/v1/jobs/{self.jid}/camera-ref/{o['ref_frames'][0]}")
        self.assertEqual(r.status_code, 200, r.text)
        for bad in ("../camera.json", "camera.json", "camera/../../../films/camfilm/film.json"):
            self.assertEqual(self.c.get(f"/api/v1/jobs/{self.jid}/camera-ref/{bad}").status_code, 404, bad)

    def test_choose_and_notes_through_actions(self):
        n2 = self.steps()["camera"]["shots"][0]["options"][1]["n"]
        a = self.act("camera-choose", {"shot": "S1", "n": n2})
        self.assertEqual(a["status"], "done", a)
        self.assertEqual(self.steps()["camera"]["shots"][0]["chosen"], n2)
        base = self.steps()["camera"]["notes_base"]
        a = self.act("camera-note-add", {"shot": "S2", "option": 1, "x": 30, "y": 40, "text": "slower"}, base)
        self.assertEqual(a["status"], "done", a)
        self.assertEqual(self.act("camera-note-add", {"shot": "S2", "option": 1, "x": 1, "y": 1, "text": "x"},
                                  base)["status"], "conflict")
        cb = self.steps()["camera"]
        self.assertEqual(cb["shots"][1]["open_notes"], 1)
        self.assertEqual(cb["summary"], "1 camera note on: S2")
        self.assertEqual(self.c.post(f"/api/v1/jobs/{self.jid}/actions", headers=W,
                                     json={"point": "camera", "op": "mix", "args": {}}).status_code, 422)

    def test_send_notes_and_approve(self):
        from filmcheck import camnotes
        camnotes.add(self.film, "S3", 1, 50, 50, "wider")
        rid = self.request()
        r = self.c.post(f"/api/v1/reviews/{rid}/decision", headers=W, json={"value": "revise"})
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["note"], "1 camera note on: S3")
        lot = camnotes.NOTES.load(self.film).get("lot")
        self.assertEqual(lot["job"], self.jid)
        nid = lot["notes"][0]
        camnotes.reply(self.film, nid, "wider start", True)
        rid = self.request()                                   # back for review: the lot is over
        self.assertIsNone(camnotes.NOTES.load(self.film).get("lot"))
        self.assertEqual(self.steps()["camera"]["state"], "waiting")
        base = self.steps()["points"]["camera"]["fingerprint"]
        r = self.c.post(f"/api/v1/reviews/{rid}/decision", headers=W, json={"value": "approve", "base": base})
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(self.steps()["camera"]["state"], "approved")
        plan = json.loads((self.film / "film.json").read_text())["shot_plan"]
        self.assertTrue(all("camera" in plan[s] for s in ("S1", "S2", "S3")))

    def test_approve_refused_while_a_still_is_missing(self):
        (self.film / "camera" / "stills" / "S2-o1.jpg").unlink()
        self.assertEqual(self.steps()["camera"]["missing"], ["S2"])
        rid = self.request()
        base = self.steps()["points"]["camera"]["fingerprint"]
        r = self.c.post(f"/api/v1/reviews/{rid}/decision", headers=W, json={"value": "approve", "base": base})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "checks_not_passed"))

    @unittest.skipUnless(shutil.which("node") and (NODE_MODULES / "playwright-core").is_dir(), "no node / playwright-core")
    def test_in_browser(self):
        self.request()
        base = self.url.split("URL: ", 1)[1].split("/#", 1)[0]
        r = subprocess.run(["node", str(Path(__file__).with_name("browser_camera.cjs")), base, self.jid, *([os.environ["CAM_SHOT"]] if os.environ.get("CAM_SHOT") else [])],
                           capture_output=True, text=True, timeout=180, env={**os.environ, "NODE_PATH": str(NODE_MODULES)})
        if r.returncode == 77:
            self.skipTest("no browser")
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(o["errors"], [])
        self.assertEqual(o["shots"], ["S1", "S2", "S3"])
        self.assertTrue(2 <= o["options"] <= 3)
        self.assertTrue(o["star"])
        self.assertEqual(o["chosen"], 2)                       # "Use this" on option 2 of S1
        self.assertTrue(o["preview"])                          # ▶ animates the still
        self.assertEqual(o["noteShown"], 1)
        self.assertEqual(o["sendText"], "Send 1 note to Claude")
        self.assertTrue(o["approveDisabled"])                  # open notes block the approval
        self.assertFalse(o["wide"])                            # no sideways scroll at 400 px


if __name__ == "__main__":
    unittest.main()
