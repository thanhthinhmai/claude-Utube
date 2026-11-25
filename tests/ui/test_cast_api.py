"""specs/034 T025: the Cast panel's data and edits on the film job page (local mode, API)."""
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from helpers import REPO, Project, W, client

sys.path.insert(0, str(REPO / "tests" / "filmcheck"))
sys.path.insert(0, str(REPO / "tools"))
import castfilm  # noqa: E402
import samples  # noqa: E402
from test_cast import fake_sheet  # noqa: E402


class CastApi(unittest.TestCase):
    def setUp(self):
        self.p = Project(ports="18840-18849")
        self.film = samples.review_film(self.p.dir, "aefilm", kit=False)
        castfilm.make(self.film)
        samples.review_film(self.p.dir, "pagefilm", kit=False)
        self.c = client()
        self.jid = self.job("aefilm")

    def tearDown(self):
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

    def wait_action(self, aid):
        from studio import actions
        self.assertTrue(actions.wait_idle(self.jid, 60))
        return self.c.get(f"/api/v1/jobs/{self.jid}/actions/{aid}").json()

    def test_cast_block(self):
        v = self.steps()
        self.assertIn("Cast", [s["name"] for s in v["steps"]])
        self.assertIn("cast", v["points"])
        cb = v["cast"]
        self.assertEqual([c["id"] for c in cb["characters"]], ["hero", "friend", "classmates"])
        self.assertEqual(cb["characters"][0]["state"], "new")
        self.assertIsNone(cb["characters"][0]["sheet"])
        self.assertIn("members", cb["characters"][2])
        self.assertIn("spec", cb["characters"][0])
        self.assertFalse(cb["library_available"])
        from filmcheck import script                                         # T061: the passages hero plays in
        want = script.para_map(script.read_script(self.film / "SCRIPT.md"))
        self.assertEqual(cb["passages"], {k: want[k] for k in ("P01", "P02")})
        page = self.steps(self.job("pagefilm"))
        self.assertNotIn("Cast", [s["name"] for s in page["steps"]])
        self.assertIsNone(page["cast"])

    def test_sheet_files_and_approve(self):
        for c in ("hero", "friend", "classmates"):
            fake_sheet(self.film, c)
        (self.film / "cast" / "sheets" / "hero.prev").mkdir()
        (self.film / "cast" / "sheets" / "hero.prev" / "front.jpg").write_bytes(b"\xff\xd8old")
        v = self.steps()
        self.assertEqual(v["cast"]["characters"][0]["sheet"]["frames"][0]["file"], "front.jpg")
        r = self.c.get(f"/api/v1/jobs/{self.jid}/files/cast/sheets/hero/front.jpg")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content[:2], b"\xff\xd8")
        self.assertEqual(self.c.get(f"/api/v1/jobs/{self.jid}/files/cast/sheets/hero.prev/front.jpg").status_code, 200)
        self.assertEqual(self.c.get(f"/api/v1/jobs/{self.jid}/files/cast/cast.json").status_code, 404)
        self.assertEqual(self.c.get(f"/api/v1/jobs/{self.jid}/files/cast/sheets/../cast.json").status_code, 404)
        base = v["points"]["cast"]["fingerprint"]
        r = self.c.post(f"/api/v1/jobs/{self.jid}/actions", headers=W, json={
            "point": "cast", "op": "cast-approve", "args": {"character": "friend"}, "base": base})
        self.assertEqual(r.status_code, 202, r.text)
        a = self.wait_action(r.json()["id"])
        self.assertEqual(a["status"], "done", a)
        self.assertEqual(next(c for c in self.steps()["cast"]["characters"] if c["id"] == "friend")["state"], "approved")
        r = self.c.post(f"/api/v1/jobs/{self.jid}/actions", headers=W, json={
            "point": "cast", "op": "cast-save", "args": {"on": False}, "base": base})
        self.assertEqual(self.wait_action(r.json()["id"])["status"], "done")
        self.assertFalse(json.loads((self.film / "cast" / "cast.json").read_text())["save_to_library"])
        self.assertEqual(self.c.post(f"/api/v1/jobs/{self.jid}/actions", headers=W, json={
            "point": "cast", "op": "shot", "args": {}}).status_code, 422)

    def test_approve_cast_review_saves_and_failed_job_ends_round(self):    # Phase 9: T055 and T059 through the app
        from unittest import mock
        from filmcheck import castnotes
        from studio import jobs
        for c in ("hero", "friend", "classmates"):
            fake_sheet(self.film, c)
        summary = self.p.dir / "s.md"
        summary.write_text("Cast ready")
        self.assertEqual(self.p.cli("review", "request", self.jid, "--kind", "cast", "--film", "aefilm",
                                    "--summary", str(summary)).returncode, 0)
        rid = next(r["id"] for r in self.c.get("/api/v1/reviews?status=pending").json()["reviews"] if r["kind"] == "cast")
        base = self.steps()["points"]["cast"]["fingerprint"]
        with mock.patch("filmcheck.castlib.save_if_wanted", return_value=[]) as saved:
            r = self.c.post(f"/api/v1/reviews/{rid}/decision", headers=W, json={"value": "approve", "base": base})
            self.assertEqual(r.status_code, 201, r.text)
        saved.assert_called_once()
        self.assertEqual(Path(saved.call_args[0][0]).name, "aefilm")
        castnotes.add(self.film, "hero", text="bigger hair")
        castnotes.start_lot(self.film, self.jid)
        jobs.finish(self.jid, "failed", "AE crashed")
        doc = castnotes.load(self.film)
        self.assertNotIn("lot", doc)
        self.assertIn("AE crashed", doc["failed_lot"]["error"])
        self.assertEqual(castnotes.open_counts(self.film), {"hero": 1})

    def test_cast_library(self):
        """T036: /cast-library is off outside the app; inside an account it lists and serves the saved characters."""
        r = self.c.get("/api/v1/cast-library")
        self.assertEqual(r.json(), {"available": False, "channels": []})
        self.assertEqual(self.c.get("/api/v1/cast-library/default/hero").status_code, 404)
        self.assertEqual(self.c.get("/api/v1/cast-library/default/hero/v1/front.jpg").status_code, 404)
        for p, body in (("/api/v1/cast-library/default/hero/preview", {"rig": "ball@1"}), ("/api/v1/cast-library/default/hero/fix", {"notes": ["x"]}),
                        ("/api/v1/cast-library/default/hero/update", {}), ("/api/v1/cast-library/default/hero/approve", {})):
            r = self.c.post(p, json=body, headers=W)
            self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "app_only"), p)   # changes run in the app
        from studio import castapi, store
        from filmcheck import cast, castlib
        acc = self.p.dir / "data" / "accounts" / "u1"
        d = castfilm.make(acc / "films" / "f1")
        fake_sheet(d, "hero")
        cast.approve(d, ["hero"])
        self.assertEqual(castlib.save_approved(d, ["hero"]), ["✓ default/hero: v1 (new)"])
        tok = store._account_root.set(acc)
        try:
            lib = castapi.cast_library()
            self.assertTrue(lib["available"])
            self.assertEqual(lib["channels"][0]["characters"][0]["id"], "hero")
            g = castapi.cast_library_character("default", "hero")
            self.assertEqual((g["v"], g["sheet"]["frames"][0]["file"], g["preview"]), (1, "front.jpg", None))
            self.assertTrue(Path(castapi.cast_library_file("default", "hero", "v1", "front.jpg").path).is_file())
            for bad in (("default", "hero", "v1", "..%2Fcharacter.json"), ("default", "hero", "v1", "character.json"),
                        ("default", "hero", "x1", "front.jpg"), ("..", "hero", "v1", "front.jpg"), ("default", "hero", "v2", "front.jpg")):
                with self.assertRaises(store.StudioError, msg=bad):
                    castapi.cast_library_file(*bad)
            with self.assertRaises(store.StudioError):
                castapi.cast_library_character("default", "nobody")
        finally:
            store._account_root.reset(tok)

    @unittest.skipUnless(shutil.which("node") and (REPO / "lib" / "lemo-opuscar" / "node_modules" / "playwright-core").is_dir(),
                         "no node / playwright-core")
    def test_in_browser(self):
        env = {**os.environ, "STUDIO_AE_FAKE": "1", "STUDIO_AE_CONFIG": str(self.p.dir / "ae.json"),
               "STUDIO_AE_WORK": str(self.p.dir / "aework"), "STUDIO_ROOT": str(self.p.dir)}
        for k in ("STUDIO_JOB", "STUDIO_PROXY"):
            env.pop(k, None)
        r = subprocess.run(["sh", str(REPO / "bin" / "studio"), "ae", "sheet", "aefilm"], capture_output=True, text=True,
                           env=env, timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr)
        summary = self.p.dir / "s.md"
        summary.write_text("Cast ready")
        self.p.cli("review", "request", self.jid, "--kind", "cast", "--film", "aefilm", "--summary", str(summary))
        jid = self.jid
        base = self.url.split("URL: ", 1)[1].split("/#", 1)[0] if "URL: " in self.url else ""
        if not base:
            self.skipTest("no page URL")
        shot = os.environ.get("CAST_SHOT", "")
        r = subprocess.run(["node", str(Path(__file__).with_name("browser_cast.cjs")), base, jid, shot], capture_output=True,
                           text=True, timeout=180, env={**os.environ, "NODE_PATH": str(REPO / "lib" / "lemo-opuscar" / "node_modules")})
        if r.returncode == 77:
            self.skipTest("no browser")
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(o["errors"], [])
        self.assertEqual(o["castGate"], 1)
        self.assertEqual(o["characters"], 3)
        self.assertGreaterEqual(o["pictures"], 6)                       # hero: 3 views, wide, guitar, walk
        self.assertEqual(o["missing"], 1)                               # pose zzz is outside the catalog
        self.assertEqual(o["groups"], ["Turnaround", "Expressions", "Poses", "Walk loop", "Look"])
        self.assertFalse(o["approveCastDisabled"])
        self.assertEqual((o["saveBox"], o["toggleCast"]), (1, 1))
        self.assertTrue(o.get("friendApproved"))
        for k in ("pin1280", "pin400"):                                 # the pin sits where it was clicked
            self.assertEqual(o[k]["notes"], 1, k)
            self.assertLess(o[k]["off"], 0.02, k)
        self.assertEqual(o["askLabel"], "Undo")
        self.assertEqual(o["sendNotes"], "Send 1 note to Claude")
        self.assertLessEqual(o["scroll400"], 0)


if __name__ == "__main__":
    unittest.main()
