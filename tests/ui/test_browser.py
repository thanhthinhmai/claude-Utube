"""Optional: drive the real UI in Chromium (playwright-core from the library). Skipped when unavailable."""
import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path

from helpers import REPO, Project

NODE_MODULES = REPO / "lib" / "lemo-opuscar" / "node_modules"
SCRIPT = Path(__file__).with_name("browser_check.cjs")


@unittest.skipUnless(shutil.which("node") and (NODE_MODULES / "playwright-core").is_dir(), "không có node / playwright-core")
class Browser(unittest.TestCase):
    def test_approve_in_browser(self):  # US1, US2
        p = Project(ports="18810-18819")
        try:
            jid, url = p.cli("job", "start", "--kind", "learn", "--name", "demo", "--set", "demo-set").stdout.splitlines()[:2]
            summ = p.dir / "review-1.md"
            summ.write_text("# Tóm tắt", encoding="utf-8")
            rid = p.cli("review", "request", jid, "--kind", "style-1", "--set", "demo-set", "--summary", str(summ)).stdout.splitlines()[0]
            base = url.split("URL: ", 1)[1].split("/#", 1)[0]
            r = subprocess.run(["node", str(SCRIPT), base, jid, rid], capture_output=True, text=True, timeout=60,
                               env={**os.environ, "NODE_PATH": str(NODE_MODULES)})
            if r.returncode == 77:
                self.skipTest("không mở được trình duyệt")
            self.assertEqual(r.returncode, 0, r.stderr)
            got = json.loads(p.cli("review", "status", rid).stdout)
            self.assertEqual((got["decision"]["value"], got["decision"]["source"]), ("approve", "ui"))
        finally:
            p.close()


if __name__ == "__main__":
    unittest.main()
