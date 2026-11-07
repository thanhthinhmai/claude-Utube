"""The job container cannot see other jobs, the real key or the internet (specs/007 tasks T025).
Skipped without Docker or without the studio-job image (docker build -f deploy/job.Dockerfile -t studio-job:latest .).
Needs the `jobnet` network with a `proxy` container on it: docker compose -f deploy/compose.yml up -d proxy"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

DOCKER = shutil.which("docker")


def have_image() -> bool:
    return bool(DOCKER) and subprocess.run([DOCKER, "image", "inspect", "studio-job:latest"],
                                           capture_output=True).returncode == 0


@unittest.skipUnless(have_image(), "needs Docker and the studio-job:latest image")
class Sandbox(unittest.TestCase):
    def run_in_job(self, script: str, work: Path, network: str = None):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "runner"))
        os.environ.setdefault("STUDIO_DATA", str(work.parent.parent))
        import worker
        r = worker.DockerRunner()
        return r.exec(work, lambda root, lib: ["sh", "-c", script], network=network or r.network)

    def test_isolation(self):
        data = Path(tempfile.mkdtemp(prefix="sandbox."))
        try:
            mine, other = data / "jobs" / "j-mine", data / "jobs" / "j-other"
            for d in (mine, other):
                d.mkdir(parents=True)
                os.chmod(d, 0o777)
            (other / "secret.txt").write_text("other customer")
            os.environ["STUDIO_DATA"] = str(data)
            rc, out = self.run_in_job("cat /work/../j-other/secret.txt; ls /data 2>&1; env", mine)
            self.assertNotIn("other customer", out)
            self.assertNotIn("sk-ant-", out)
            rc, out = self.run_in_job("python3 -c \"import urllib.request as u; u.urlopen('https://example.com', timeout=5)\"", mine)
            self.assertNotEqual(rc, 0)
            rc, _ = self.run_in_job("touch /studio/x", mine)
            self.assertNotEqual(rc, 0)                     # read-only root
            rc, out = self.run_in_job("python3 -c \"import urllib.request as u; print(u.urlopen('http://proxy:8780/health',"
                                      " timeout=5).status)\"", mine)
            self.assertEqual((rc, out.strip()), (0, "200"))   # the proxy is the only thing it can reach
        finally:
            shutil.rmtree(data, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
