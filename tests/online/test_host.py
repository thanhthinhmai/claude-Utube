"""The whole studio on one machine without Docker (specs/014 T004–T015): `sh bin/studio app …` with real child
processes, the fake agent and the fake Claude API. Data folders and HOME are temporary, outside the project."""
import http.cookiejar
import json
import os
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from helpers import FAKE_AGENT, FAKE_CLAUDE, PASSWORD, REAL_KEY, REPO, Server, fake_upstream, first_library_style, samples

STUDIO = REPO / "bin" / "studio"


class Web:
    """A browser-like client: cookies, the X-Studio header."""

    def __init__(self, base):
        self.base = base
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self, method, path, body=None):
        req = urllib.request.Request(self.base + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"content-type": "application/json", "x-studio": "1"})
        try:
            with self.op.open(req, timeout=20) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")


def porcelain():
    return subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--untracked-files=all"],
                          capture_output=True, text=True).stdout


class _Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        samples()
        cls.upstream = Server(fake_upstream())

    @classmethod
    def tearDownClass(cls):
        cls.upstream.close()

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="studio-host."))
        self.data, self.home = self.tmp / "data", self.tmp / "home"
        self.home.mkdir()
        self.env = {**os.environ, "HOME": str(self.home), "STUDIO_AGENT_CMD": f"{sys.executable} {FAKE_AGENT}",
                    "STUDIO_CLAUDE_BIN": str(FAKE_CLAUDE), "STUDIO_MODERATION": "fake", "ANTHROPIC_API_KEY": REAL_KEY,
                    "ANTHROPIC_UPSTREAM": self.upstream.url, "STUDIO_TICK_S": "0.2"}
        for k in ("STUDIO_MODE", "STUDIO_DATA", "RUNNER"):
            self.env.pop(k, None)

    def tearDown(self):
        self.app("stop", "--force")
        shutil.rmtree(self.tmp, ignore_errors=True)

    def app(self, *args, env=None):
        return subprocess.run(["sh", str(STUDIO), "app", *args, "--data", str(self.data)], capture_output=True, text=True,
                              env=env or self.env, timeout=60)

    def studio(self, *args):
        return subprocess.run(["sh", str(STUDIO), *args], capture_output=True, text=True, env=self.env, timeout=60)

    def state(self):
        return json.loads((self.data / "host.json").read_text())

    def owner(self, st=None):
        w = Web(f"http://127.0.0.1:{(st or self.state())['web']}")
        code, _ = w.call("POST", "/api/v1/auth/setup", {"email": "me@example.com", "password": PASSWORD})
        self.assertEqual(code, 201)
        return w

    def film(self, w, idea="A fox and a lantern"):
        code, j = w.call("POST", "/api/v1/jobs", {"kind": "film", "style": first_library_style(), "idea": idea, "seconds": 20})
        self.assertEqual(code, 201, j)
        return j["id"]

    def wait(self, w, jid, statuses=("done", "failed", "stopped"), timeout=90):
        end = time.time() + timeout
        while time.time() < end:
            _, j = w.call("GET", f"/api/v1/jobs/{jid}")
            if j.get("status") in statuses:
                return j
            time.sleep(0.3)
        self.fail(f"job {jid} did not reach {statuses}: {j.get('status')}")


class Host(_Base):
    # ---------- US1 ----------
    def test_start_film_stop(self):
        before = porcelain()
        t0 = time.time()
        r = self.app("start")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("URL: http://127.0.0.1:", r.stdout)
        self.assertLess(time.time() - t0, 20)                                         # SC-001
        s = json.loads(self.app("status", "--json").stdout)
        self.assertTrue(s["running"])
        self.assertEqual(s["parts"], {"proxy": True, "worker": True, "web": True})
        w = self.owner()
        self.assertEqual(w.call("GET", "/api/v1/me")[1]["quota"]["films"]["limit"], 1000)   # the owner pays (R4)
        j = self.wait(w, self.film(w))
        self.assertEqual(j["status"], "done", j["log"][-6:])
        self.assertTrue(j["qa"]["film"] and j["qa"]["publish"])                       # SC-002
        pids = [self.state()["pid"], *self.state()["children"].values()]
        self.assertEqual(self.app("stop").returncode, 0)
        time.sleep(0.5)
        self.assertFalse(any(_alive(p) for p in pids))                               # SC-003
        self.assertEqual(subprocess.run(["pgrep", "-f", str(self.data)], capture_output=True).stdout, b"")
        self.assertFalse((self.home / ".config" / "claude-utube" / "host.json").exists())
        self.assertEqual(porcelain(), before)                                         # SC-006

    def test_missing_tool(self):
        env = {**self.env, "PATH": "/usr/bin:/bin"}                                  # ffmpeg lives in /usr/local/bin here
        if shutil.which("ffmpeg", path=env["PATH"]):
            self.skipTest("ffmpeg is in /usr/bin on this machine")
        r = self.app("start", env=env)
        self.assertEqual(r.returncode, 2)
        self.assertIn("✗ ffmpeg", r.stdout)

    def test_data_folder_inside_the_project_is_refused(self):
        r = subprocess.run(["sh", str(STUDIO), "app", "start", "--data", str(REPO / ".studio" / "x")], capture_output=True,
                           text=True, env=self.env)
        self.assertEqual(r.returncode, 2)
        self.assertIn("outside the project", r.stderr)

    # ---------- US2 ----------
    def test_twice_and_busy_port(self):
        sys.path.insert(0, str(REPO / "tools" / "studio"))
        from studio import host
        port = host.free_port(host.WEB_PORTS)                                       # the port the studio would take
        busy = socket.socket()
        busy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        busy.bind(("127.0.0.1", port))
        busy.listen()
        try:
            r = self.app("start")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertNotEqual(self.state()["web"], port)
            first = self.state()["pid"]
            r2 = self.app("start")
            self.assertEqual(r2.returncode, 0)
            self.assertIn(f"URL: http://127.0.0.1:{self.state()['web']}", r2.stdout)
            self.assertEqual(self.state()["pid"], first)                              # no second supervisor
        finally:
            busy.close()

    def test_stop_with_a_running_job(self):
        self.app("start")
        w = self.owner()
        jid = self.film(w, "A fox [slow 30]")
        self.wait(w, jid, ("running",), 30)
        r = self.app("stop")
        self.assertEqual(r.returncode, 1)
        self.assertIn(jid, r.stdout)
        r = self.app("stop", "--force")
        self.assertEqual(r.returncode, 0, r.stdout)
        con = sqlite3.connect(self.data / "studio.db")
        status = json.loads(con.execute("SELECT data FROM docs WHERE id = ?", (jid,)).fetchone()[0])["status"]
        self.assertEqual(status, "stopped")

    def test_crash_then_start_again(self):                                            # SC-004
        self.app("start")
        w = self.owner()
        jid = self.film(w, "A fox [slow 4]")
        self.wait(w, jid, ("running",), 30)
        st = self.state()
        for pidf in (self.data / "jobs").glob("*/.pid"):
            _killpg(int(pidf.read_text()))
        for p in st["children"].values():
            _killpg(p)
        os.kill(st["pid"], signal.SIGKILL)
        time.sleep(0.5)
        r = self.app("start")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        w2 = Web(f"http://127.0.0.1:{self.state()['web']}")
        self.assertEqual(w2.call("POST", "/api/v1/auth/login", {"email": "me@example.com", "password": PASSWORD})[0], 200)
        j = self.wait(w2, jid)
        self.assertEqual(j["status"], "done", j["log"][-6:])
        self.assertTrue(any("Restarted" in x["line"] for x in j["log"]))

    def test_logs_rotate(self):
        self.app("start", env={**self.env, "STUDIO_HOST_LOG_BYTES": "60"})
        w = Web(f"http://127.0.0.1:{self.state()['web']}")
        for _ in range(30):
            w.call("GET", "/api/v1/nope")
        self.app("stop")
        logs = sorted(p.name for p in (self.data / "logs").iterdir())
        self.assertTrue(any(n.endswith(".log.1") for n in logs), logs)
        self.assertLessEqual(sum(1 for n in logs if n.startswith("web.log")), 6)

    # ---------- US3 ----------
    def test_import(self):
        proj = self.tmp / "proj"
        (proj / "films" / "f1").mkdir(parents=True)
        (proj / "films" / "f1" / "f1.mp4").write_bytes(b"x")
        (proj / "my-styles" / "s1").mkdir(parents=True)
        (proj / "my-styles" / "s1" / "style.json").write_text("{}")
        (proj / "channels" / "c1").mkdir(parents=True)
        (proj / "channels" / "c1" / "topics.json").write_text('{"topics": []}')
        self.assertEqual(self.app("import", "--from", str(proj)).returncode, 2)       # no owner yet
        self.app("start")
        self.owner()
        listing = sorted(str(p.relative_to(proj)) for p in proj.rglob("*"))
        r = self.app("import", "--from", str(proj))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("copied 3", r.stdout)
        owner = _owner(self.data)
        self.assertTrue((self.data / "accounts" / owner / "channels" / "c1" / "topics.json").is_file())
        self.assertIn("copied 0, kept 3", self.app("import", "--from", str(proj)).stdout)
        self.assertEqual(sorted(str(p.relative_to(proj)) for p in proj.rglob("*")), listing)

    def test_chat_flow_goes_to_the_app(self):
        film = "test-host-chat-film"
        fdir = REPO / "films" / film
        fdir.mkdir(parents=True, exist_ok=True)
        try:
            self.app("start")
            w = self.owner()
            r = self.studio("job", "start", "--kind", "film", "--name", "chat film", "--film", film)
            self.assertEqual(r.returncode, 0, r.stderr)
            jid = r.stdout.splitlines()[0]
            self.assertIn(f"URL: http://127.0.0.1:{self.state()['web']}/#/jobs/{jid}", r.stdout)
            ids = [j["id"] for j in w.call("GET", "/api/v1/jobs")[1]["jobs"]]
            self.assertIn(jid, ids)
            summary = self.tmp / "q.md"
            summary.write_text("Orange or grey?")
            r = self.studio("review", "request", jid, "--kind", "question", "--summary", str(summary))
            self.assertEqual(r.returncode, 0, r.stderr)
            rid = r.stdout.splitlines()[0]
            self.assertEqual(w.call("POST", f"/api/v1/reviews/{rid}/decision", {"value": "approve", "note": "grey"})[0], 201)
            r = self.studio("review", "wait", rid, "--timeout", "10")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(self.studio("job", "done", jid, "--film", film).returncode, 0)
            self.assertEqual(w.call("GET", f"/api/v1/films/{film}")[0], 200)
            self.assertFalse((REPO / ".studio" / "jobs" / f"{jid}.json").exists())    # not in the old job book
        finally:
            shutil.rmtree(fdir, ignore_errors=True)


class Check(_Base):                                                                     # specs/015 T003
    def test_check_and_job_names(self):
        r = self.app("check", "--json")
        c = json.loads(r.stdout)
        self.assertEqual(set(c), {"ok", "missing", "data_default"})
        self.assertTrue(c["ok"], c)
        r = self.app("check", "--json", env={**self.env, "PATH": "/usr/bin:/bin"})
        if not shutil.which("ffmpeg", path="/usr/bin:/bin"):
            self.assertFalse(json.loads(r.stdout)["ok"])
        self.app("start")
        w = self.owner()
        jid = self.film(w, "A fox [slow 20]")
        self.wait(w, jid, ("running",), 30)
        s = json.loads(self.app("status", "--json").stdout)
        self.assertEqual([(j["id"], j["name"]) for j in s["jobs"]], [(jid, "A fox [slow 20]")])


class Upgrade(unittest.TestCase):                                                      # T004, FR-006
    def test_backup_before_upgrade(self):
        tmp = Path(tempfile.mkdtemp(prefix="studio-upg."))
        old = os.environ.get("STUDIO_DATA")
        os.environ["STUDIO_DATA"] = str(tmp)
        try:
            from studio import db
            db.connect().close()
            con = sqlite3.connect(tmp / "studio.db")
            con.execute("UPDATE meta SET value = '2' WHERE key = 'schema'")
            con.commit()
            con.close()
            db._ready.discard(str(db.path()))
            db._ready.discard(db.path())
            db.connect().close()
            backups = list((tmp / "backup").glob("studio-2-*.db"))
            self.assertEqual(len(backups), 1)
            con = sqlite3.connect(tmp / "studio.db")
            self.assertEqual(con.execute("SELECT value FROM meta WHERE key = 'schema'").fetchone()[0], str(db.SCHEMA_VERSION))
        finally:
            if old is None:
                os.environ.pop("STUDIO_DATA", None)
            else:
                os.environ["STUDIO_DATA"] = old
            shutil.rmtree(tmp, ignore_errors=True)


class WriteGuard(unittest.TestCase):                                                   # T009, R5
    def test_only_the_job_folder(self):
        tmp = Path(tempfile.mkdtemp(prefix="studio-work."))
        os.environ["STUDIO_WORK"] = str(tmp)
        sys.path.insert(0, str(REPO / "tools" / "runner"))
        import importlib
        import agent
        importlib.reload(agent)
        try:
            self.assertEqual(agent.write_allowed("Write", {"file_path": str(tmp / "films" / "a.txt")})[0], True)
            self.assertEqual(agent.write_allowed("Edit", {"file_path": "films/a.txt"})[0], True)
            for bad in (str(REPO / "tools" / "x.py"), str(Path.home() / ".bashrc"), str(tmp / ".." / "escape")):
                ok, why = agent.write_allowed("Write", {"file_path": bad})
                self.assertFalse(ok, bad)
                self.assertIn("job folder", why)
            self.assertEqual(agent.write_allowed("Bash", {"command": "rm -rf /"})[0], True)   # Bash is not this guard's job
        finally:
            os.environ.pop("STUDIO_WORK", None)
            shutil.rmtree(tmp, ignore_errors=True)


class Gate(_Base):                                                                      # specs/017 T012, SC-002
    def write_gate(self, **over):
        sys.path.insert(0, str(REPO / "tools" / "license"))
        import signing
        now = int(time.time())
        payload = {"v": 1, "lid": "l1", "did": "d" * 64, "label": "An", "iat": now, "exp": now + 7 * 86400, "keyExp": None}
        payload.update(over.pop("payload", {}))
        doc = {"deviceId": "d" * 64, "lease": signing.sign_lease(self.priv, payload), "clock": now, "refused": None, **over}
        tmp = self.gate.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc))
        tmp.replace(self.gate)

    def test_locked_and_open(self):
        sys.path.insert(0, str(REPO / "tools" / "license"))
        import signing
        self.priv, pub = signing.new_keypair()
        self.gate = self.tmp / "gate.json"
        self.env["CU_LICENSE_PUBLIC_KEY"] = pub
        self.write_gate()
        self.assertEqual(self.app("start", "--gate", str(self.gate)).returncode, 0)
        w = self.owner()
        a = self.film(w, "A fox [slow 20]")
        self.wait(w, a, ("running",), 30)
        b = self.film(w, "A second fox")                                           # waits: one job per person
        for bad in ({"refused": "revoked"}, {"payload": {"exp": int(time.time()) - 5}}, {"deviceId": "e" * 64},
                    {"clock": int(time.time()) + 3600}, {"lease": "forged.lease"}):
            self.write_gate(**bad)
            code, j = w.call("GET", "/api/v1/jobs")
            self.assertEqual((code, j["error"]["code"]), (423, "license_locked"), bad)
            r = urllib.request.urlopen(f"http://127.0.0.1:{self.state()['web']}/api/v1/health", timeout=10)
            self.assertEqual(r.status, 200)
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{self.state()['web']}/", timeout=10)
                self.fail("the page opened while locked")
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 423)
                self.assertIn(b"claude-Utube is locked", e.read())
        # the running film finishes; the queued one does not start while locked
        con = lambda: sqlite3.connect(self.data / "studio.db")                     # noqa: E731
        status = lambda jid: json.loads(con().execute("SELECT data FROM docs WHERE id = ?", (jid,)).fetchone()[0])["status"]   # noqa: E731
        end = time.time() + 90
        while status(a) == "running" and time.time() < end:
            time.sleep(0.5)
        self.assertEqual(status(a), "done")
        time.sleep(2)
        self.assertEqual(status(b), "queued")
        self.write_gate()
        self.assertEqual(self.wait(w, b)["status"], "done")


class Cert(unittest.TestCase):                                                          # specs/018 T001
    def test_made_once_then_reused(self):
        tmp = Path(tempfile.mkdtemp(prefix="studio-cert."))
        try:
            run = lambda: subprocess.run(["sh", str(STUDIO), "app", "cert", "--data", str(tmp)], capture_output=True,   # noqa: E731
                                         text=True, timeout=60)
            a = json.loads(run().stdout)
            self.assertIn("BEGIN CERTIFICATE", a["cert"])
            self.assertIn("PRIVATE KEY", a["key"])
            self.assertRegex(a["fingerprint"], r"^[0-9a-f]{64}$")
            self.assertEqual(json.loads(run().stdout), a)
            self.assertEqual((tmp / "share" / "key.pem").stat().st_mode & 0o777, 0o600)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class Packaged(unittest.TestCase):                                                     # specs/016 T007
    def run_cli(self, *args, env=None):
        return subprocess.run(["sh", str(STUDIO), "app", *args], capture_output=True, text=True, timeout=60,
                              env={**os.environ, **(env or {})})

    def test_models(self):
        r = self.run_cli("models", env={"CU_MODELS_FAKE": "1"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.split(), ["✓", "base.en", "✓", "base"])
        r = self.run_cli("models", env={"CU_MODELS_FAKE": "fail"})
        self.assertEqual(r.returncode, 1)
        self.assertIn("✗ base.en: network is unreachable", r.stdout)

    def test_sandbox_env(self):
        from studio import host
        tmp = Path(tempfile.mkdtemp(prefix="studio-sbx."))
        try:
            real = shutil.which
            host.shutil.which = lambda t, *a, **k: f"/usr/bin/{t}"
            self.assertEqual(host.part_env(tmp, REPO, 1, 2).get("STUDIO_AGENT_SANDBOX"), "1")
            host.shutil.which = lambda t, *a, **k: None if t == "bwrap" else f"/usr/bin/{t}"
            expect = "1" if sys.platform == "darwin" else None
            self.assertEqual(host.part_env(tmp, REPO, 1, 2).get("STUDIO_AGENT_SANDBOX"), expect)
        finally:
            host.shutil.which = real
            shutil.rmtree(tmp, ignore_errors=True)

    def test_agent_sandbox_options(self):
        sys.path.insert(0, str(REPO / "tools" / "runner"))
        import agent
        old = {k: os.environ.get(k) for k in ("STUDIO_AGENT_SANDBOX", "TMPDIR")}
        try:
            os.environ.pop("STUDIO_AGENT_SANDBOX", None)
            self.assertIsNone(agent.sandbox_options())
            os.environ.update(STUDIO_AGENT_SANDBOX="1", TMPDIR="/data/tmp")
            o = agent.sandbox_options()
            self.assertTrue(o["enabled"])
            self.assertFalse(o["allowUnsandboxedCommands"])
            self.assertEqual(o["network"]["allowedDomains"], ["127.0.0.1", "localhost"])
            self.assertEqual(o["filesystem"]["allowWrite"], ["/data/tmp"])
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def _alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def _killpg(pid):
    try:
        os.killpg(int(pid), signal.SIGKILL)
    except OSError:
        pass


def _owner(data):
    con = sqlite3.connect(Path(data) / "studio.db")
    return con.execute("SELECT id FROM accounts WHERE role = 'admin'").fetchone()[0]


if __name__ == "__main__":
    unittest.main()
