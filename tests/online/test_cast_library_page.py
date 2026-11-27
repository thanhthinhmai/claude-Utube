"""The Cast page of the app (specs/034 T050) in a real browser: the list, a preview beside the approved sheet, Update, Approve."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from helpers import PASSWORD, REPO, OnlineProject, Server

NODE_MODULES = REPO / "lib" / "lemo-opuscar" / "node_modules"
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "tests" / "filmcheck"))
import castfilm  # noqa: E402


def jpg(path: Path, color: str):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=320x320", "-frames:v", "1", str(path)], check=True)


def sheet(d: Path, cid: str, color: str):
    s = d / "cast" / "sheets" / cid
    s.mkdir(parents=True, exist_ok=True)
    rows = []
    for k, label in (("front", "Front"), ("back", "Back"), ("34", "3/4 view")):
        jpg(s / f"{k}.jpg", color)
        rows.append({"key": k, "group": "turn", "label": label, "file": f"{k}.jpg"})
    (s / "sheet.json").write_text(json.dumps({"character": cid, "rig": "ball@1", "built_at": "x", "frames": rows}))


@unittest.skipUnless(__import__("shutil").which("node") and (NODE_MODULES / "playwright-core").is_dir(),
                     "needs node and playwright-core")
class CastLibraryPage(unittest.TestCase):
    def test_page(self):
        p = OnlineProject()
        try:
            from studio import accounts, store
            from studio.server import create_app
            from filmcheck import cast, castlib
            accounts.signup("owner@x.test", PASSWORD, True, role="admin", verified=True)
            u = accounts.add_user("m@x.test", PASSWORD)
            acc = store.account_dir(u["id"])
            d = castfilm.make(acc / "films" / "f1")
            sheet(d, "hero", "orange")
            cast.approve(d, ["hero"])
            castlib.save_approved(d, ["hero"])
            w = castfilm.make(acc / "work" / "films" / "cast-hero")
            sheet(w, "hero", "teal")
            self.assertEqual(castlib.store_result(acc, "default", "hero", w, "preview"), 2)
            web = Server(create_app())
            try:
                r = subprocess.run(["node", str(Path(__file__).with_name("browser_cast_lib.cjs")), web.url, "m@x.test", PASSWORD,
                                    os.environ.get("CAST_LIB_SHOT", "")],
                                   capture_output=True, text=True, timeout=120, env={**os.environ, "NODE_PATH": str(NODE_MODULES)})
                if r.returncode == 77:
                    self.skipTest("cannot start a browser")
                self.assertEqual(r.returncode, 0, r.stderr)
                res = json.loads(r.stdout.strip().splitlines()[-1])
            finally:
                web.close()
            self.assertEqual(res["errors"], [])
            self.assertEqual((res["cards1280"], res["cards400"]), (1, 1))
            self.assertEqual(res["chips1280"], ["New rig version: ball@2", "Preview ready"])   # specs/038: ball@2 is the newest rig
            self.assertEqual(res["compare"], ["Preview with the new rig"])
            self.assertEqual(res["afterUpdate"], ["Version 2 waits for your approval"])
            self.assertIn("version 2", res["head"])
            self.assertLessEqual(res["scroll400"], 0)
        finally:
            p.close()


if __name__ == "__main__":
    unittest.main()
