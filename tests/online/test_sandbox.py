"""The job container cannot see other jobs, the real key or the internet (specs/007 tasks T025).
Skipped without Docker or without the studio-job image (docker build -f deploy/job.Dockerfile -t studio-job:latest .).
The test makes its own internal network with a stand-in `proxy` service, and removes both at the end."""
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

DOCKER = shutil.which("docker")
IMAGE = "studio-job:latest"
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2] / "tools" / "runner"))
sys.path.insert(0, str(HERE.parents[2] / "tools" / "studio"))

# a stand-in for the API proxy: answers 200 on /health
PROXY = ("import http.server as h\n"
         "class H(h.BaseHTTPRequestHandler):\n"
         "    def do_GET(self):\n"
         "        self.send_response(200); self.end_headers(); self.wfile.write(b'ok')\n"
         "h.HTTPServer(('0.0.0.0', 8780), H).serve_forever()\n")


def have_image() -> bool:
    try:
        return bool(DOCKER) and subprocess.run([DOCKER, "image", "inspect", IMAGE], capture_output=True,
                                               timeout=20).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def docker(*args, check=True):
    return subprocess.run([DOCKER, *args], capture_output=True, text=True, check=check, timeout=120)


@unittest.skipUnless(have_image(), "needs Docker and the studio-job:latest image")
class Sandbox(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.net = f"studio-test-{secrets.token_hex(3)}"
        cls.proxy = f"{cls.net}-proxy"
        docker("network", "create", "--internal", cls.net)
        docker("run", "-d", "--name", cls.proxy, "--network", cls.net, "--network-alias", "proxy",
               "--entrypoint", "python3", IMAGE, "-c", PROXY)
        cls.data = Path(tempfile.mkdtemp(prefix="sandbox."))
        cls.old = {k: os.environ.get(k) for k in ("STUDIO_DATA", "STUDIO_JOB_NETWORK", "STUDIO_JOB_CPUS", "STUDIO_JOB_MEMORY")}
        os.environ.update(STUDIO_DATA=str(cls.data), STUDIO_JOB_NETWORK=cls.net, STUDIO_JOB_CPUS="1",
                          STUDIO_JOB_MEMORY="1g")
        import worker
        cls.runner = worker.DockerRunner()

    @classmethod
    def tearDownClass(cls):
        docker("rm", "-f", cls.proxy, check=False)
        docker("network", "rm", cls.net, check=False)
        for k, v in cls.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(cls.data, ignore_errors=True)

    def job(self, name: str) -> Path:
        d = self.data / "jobs" / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def sh(self, work: Path, script: str):
        return self.runner.exec(work, lambda root, lib: ["sh", "-c", script], timeout=120, network=self.net)

    def test_isolation(self):
        mine, other = self.job("j-mine"), self.job("j-other")
        (other / "secret.txt").write_text("other customer")
        rc, out = self.sh(mine, "cat /work/../j-other/secret.txt; ls /data; id -u; env")
        self.assertNotIn("other customer", out)                    # only its own job folder is mounted
        self.assertIn("\n1000\n", "\n" + out)                      # never root
        self.assertNotIn("sk-ant-", out)                           # no real key in the environment
        rc, out = self.sh(mine, "python3 -c \"import urllib.request as u; u.urlopen('https://example.com', timeout=5)\"")
        self.assertNotEqual(rc, 0, out)                            # no internet
        rc, out = self.sh(mine, "touch /studio/x")
        self.assertNotEqual(rc, 0, out)                            # read-only root
        rc, out = self.sh(mine, "touch /work/ok && echo wrote")
        self.assertEqual((rc, out.strip()), (0, "wrote"))          # its own folder is writable
        rc, out = self.sh(mine, "python3 -c \"import urllib.request as u; print(u.urlopen('http://proxy:8780/health',"
                                " timeout=5).status)\"")
        self.assertEqual((rc, out.strip()), (0, "200"), out)       # the proxy is the one thing it can reach

    def test_tools_inside(self):
        rc, out = self.sh(self.job("j-tools"), "ffmpeg -version | head -1; node --version; "
                                               "/studio/tools/.venv/bin/python -c 'import claude_agent_sdk; print(\"sdk ok\")'; "
                                               "test -f /studio/lib/lemo-opuscar/AGENTS.md && echo lib ok")
        self.assertEqual(rc, 0, out)
        self.assertIn("ffmpeg version 7", out)
        self.assertIn("sdk ok", out)
        self.assertIn("lib ok", out)


if __name__ == "__main__":
    unittest.main()
