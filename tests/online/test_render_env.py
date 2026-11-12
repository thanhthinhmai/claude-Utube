"""GPU rendering in the desktop app's core (specs/019 T026): the host applies the probe result to every part, the
local worker forwards it to jobs, `app status` and Settings → Worker show it. No GPU needed."""
import os
import tempfile
import time
import unittest
from pathlib import Path

from helpers import PASSWORD, W, Studio

RENDER = {"mode": "gpu", "renderer": "ANGLE (Test, D3D12 (Fake GPU), OpenGL 4.1)", "reason": None, "fix": None,
          "source": "auto", "chrome": "/x/tools/render/chrome-gpu.sh"}
KEYS = ("STUDIO_RENDER_MODE", "STUDIO_RENDER_RENDERER", "STUDIO_RENDER_REASON", "PLAYWRIGHT_CHROME", "DISPLAY",
        "LD_LIBRARY_PATH", "GALLIUM_DRIVER")


class HostRender(unittest.TestCase):
    def test_apply_render_gpu_and_software(self):
        from studio import host
        env = host.apply_render({"PLAYWRIGHT_CHROME": "stale", "PATH": "/bin"}, RENDER)
        self.assertEqual(env["STUDIO_RENDER_MODE"], "gpu")
        self.assertEqual(env["PLAYWRIGHT_CHROME"], RENDER["chrome"])
        self.assertEqual(env["PATH"], "/bin")
        env = host.apply_render(env, {"mode": "software", "renderer": None, "reason": "no display", "chrome": None})
        self.assertEqual((env["STUDIO_RENDER_MODE"], env["STUDIO_RENDER_REASON"]), ("software", "no display"))
        self.assertNotIn("PLAYWRIGHT_CHROME", env)
        self.assertNotIn("STUDIO_RENDER_RENDERER", env)

    def test_probe_failure_is_software(self):
        from studio import host
        r = host.render_probe({"PATH": "/nonexistent"}, Path(tempfile.mkdtemp()))
        self.assertEqual(r["mode"], "software")
        self.assertTrue(r["reason"].startswith("probe failed"))

    def test_status_line(self):
        import studio_cli
        self.assertEqual(studio_cli.render_line(RENDER), "  ✓ dựng hình   GPU · ANGLE (Test, D3D12 (Fake GPU), OpenGL 4.1)")
        self.assertEqual(studio_cli.render_line({"mode": "software", "reason": "full Chromium missing", "fix": "sh bin/studio deps gpu"}),
                         "  ✗ dựng hình   phần mềm · thiếu Chromium đầy đủ → sh bin/studio deps gpu")
        self.assertEqual(studio_cli.render_line({"mode": "software", "reason": "no display"}), "  · dựng hình   phần mềm · không có màn hình đồ hoạ")
        self.assertEqual(studio_cli.render_line(None), "  · dựng hình   chưa kiểm")


class LocalRunnerForwards(unittest.TestCase):
    def test_render_env_reaches_the_job(self):
        work = Path(tempfile.mkdtemp())
        old = {k: os.environ.get(k) for k in (*KEYS, "STUDIO_AGENT_CMD")}
        try:
            os.environ.update(STUDIO_RENDER_MODE="gpu", STUDIO_RENDER_RENDERER=RENDER["renderer"], STUDIO_RENDER_REASON="",
                              PLAYWRIGHT_CHROME=RENDER["chrome"], DISPLAY=":0", LD_LIBRARY_PATH="/usr/lib/wsl/lib",
                              GALLIUM_DRIVER="d3d12", STUDIO_AGENT_CMD="sh -c 'env > envdump'")
            import sys
            from helpers import REPO
            sys.path.insert(0, str(REPO / "tools" / "runner"))
            import worker
            r = worker.LocalRunner()
            p = r.start("j-test", work, {})
            for _ in range(100):
                if r.poll(p) is not None:
                    break
                time.sleep(0.05)
            got = dict(line.split("=", 1) for line in (work / "envdump").read_text().splitlines() if "=" in line)
            for k in ("STUDIO_RENDER_MODE", "PLAYWRIGHT_CHROME", "DISPLAY", "LD_LIBRARY_PATH", "GALLIUM_DRIVER"):
                self.assertEqual(got.get(k), os.environ[k], k)
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


class WorkerTab(unittest.TestCase):
    def setUp(self):
        self.s = Studio()
        from studio import accounts
        accounts.signup("boss@x.test", PASSWORD, True, role="admin", verified=True)
        self.a = self.s.client()
        assert self.a.post("/api/v1/auth/login", json={"email": "boss@x.test", "password": PASSWORD}, headers=W).status_code == 200

    def tearDown(self):
        self.s.close()
        for k in ("STUDIO_RENDER_MODE", "STUDIO_RENDER_RENDERER", "STUDIO_RENDER_REASON"):
            os.environ.pop(k, None)

    def test_render_in_worker_status(self):
        self.assertIsNone(self.a.get("/api/v1/admin/worker").json()["render"])      # VPS: no host, no line
        os.environ.update(STUDIO_RENDER_MODE="gpu", STUDIO_RENDER_RENDERER=RENDER["renderer"])
        self.assertEqual(self.a.get("/api/v1/admin/worker").json()["render"],
                         {"mode": "gpu", "renderer": RENDER["renderer"], "reason": None})


if __name__ == "__main__":
    unittest.main()
