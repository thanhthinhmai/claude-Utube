import json
import os
import subprocess
import threading
import time
import unittest
import urllib.request

from helpers import CLI, PY, Project, client


class CliAndEvents(unittest.TestCase):
    def setUp(self):
        self.p = Project()

    def tearDown(self):
        self.p.close()

    def start_job(self):
        out = self.p.cli("job", "start", "--kind", "learn", "--name", "demo", "--set", "demo-set")
        self.assertEqual(out.returncode, 0, out.stderr)
        jid, url = out.stdout.splitlines()[:2]
        return jid, url

    def test_job_start_launches_ui_once(self):  # FR-020a, SC-001, SC-002
        t = time.time()
        jid, url = self.start_job()
        self.assertLess(time.time() - t, 5)
        self.assertRegex(url, r"^URL: http://localhost:188\d\d/#/jobs/" + jid)
        port = json.loads((self.p.dir / ".studio" / "server.json").read_text())["port"]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/jobs") as r:
            self.assertEqual(json.loads(r.read())["jobs"][0]["id"], jid)
        pid = json.loads((self.p.dir / ".studio" / "server.json").read_text())["pid"]
        self.start_job()
        self.assertEqual(json.loads((self.p.dir / ".studio" / "server.json").read_text())["pid"], pid)   # no second server
        self.assertEqual(self.p.cli("ui", "status").returncode, 0)
        self.assertEqual(self.p.cli("ui", "stop").returncode, 0)
        self.assertEqual(self.p.cli("ui", "status").returncode, 1)

    def test_ui_replaces_stale_servers(self):  # old server on the first port / code changed after git pull
        sj = self.p.dir / ".studio" / "server.json"
        self.assertEqual(self.p.cli("ui").returncode, 0)
        first = json.loads(sj.read_text())
        self.assertEqual(self.p.cli("ui").returncode, 0)
        self.assertEqual(json.loads(sj.read_text())["pid"], first["pid"])          # unchanged code: same server
        sj.write_text(json.dumps({**first, "code": "0"}))                          # pretend the code changed
        self.assertEqual(self.p.cli("ui").returncode, 0)
        second = json.loads(sj.read_text())
        self.assertNotEqual(second["pid"], first["pid"])
        self.assertEqual(second["port"], first["port"])                            # old one gone, port reused
        sj.unlink()                                                                # forgotten server (orphan)
        out = self.p.cli("ui")
        self.assertEqual(json.loads(sj.read_text())["port"], first["port"], out.stdout)
        third = json.loads(sj.read_text())["pid"]
        self.assertNotEqual(third, second["pid"])
        sj.unlink()
        self.assertIn("đã tắt", self.p.cli("ui", "stop").stdout)                   # stop finds it without server.json
        with self.assertRaises(OSError):
            os.kill(third, 0)

    def test_other_projects_server_left_alone(self):  # tests must never stop the user's real server
        self.assertEqual(self.p.cli("ui").returncode, 0)
        other = json.loads((self.p.dir / ".studio" / "server.json").read_text())
        b = Project(ports="18810-18819")                    # second project, same code folder
        try:
            t = time.time()
            self.assertEqual(b.cli("ui").returncode, 0)
            self.assertLess(time.time() - t, 5)
            self.assertEqual(b.cli("ui", "stop").returncode, 0)
        finally:
            b.close()                                       # also gives the env back to self.p
        os.kill(other["pid"], 0)                            # still running
        with urllib.request.urlopen(f"http://127.0.0.1:{other['port']}/api/v1/health") as r:
            self.assertEqual(json.loads(r.read())["root"], str(self.p.dir.resolve()))
        self.assertEqual(self.p.cli("ui", "stop").returncode, 0)

    def test_job_commands(self):
        jid, _ = self.start_job()
        self.assertEqual(self.p.cli("job", "step", jid, "Đo video", "--progress", "3/5").returncode, 0)
        self.assertEqual(self.p.cli("job", "step", jid, "Đo video", "--progress", "6/5").returncode, 2)
        self.assertEqual(self.p.cli("job", "show", "j-20990101-000000-ffff").returncode, 1)
        run = self.p.cli("job", "run", jid, "--step", "Render", "--", "sh", "-c",
                         "for i in 1 2 3 4 5 6; do echo dòng $i; sleep 0.15; done; exit 7")
        self.assertEqual(run.returncode, 7)                                    # child's exit code kept
        self.assertIn("dòng 6", run.stdout)                                    # output passed through
        job = json.loads(self.p.cli("job", "show", jid).stdout)
        self.assertEqual(job["step"], "Render")
        self.assertTrue(any("dòng 6" in l["line"] for l in job["log"]))
        self.assertTrue(any("mã 7" in l["line"] for l in job["log"]))
        # same step twice (job step, then job run --step) → one log line; tool notes and repeats stay out of the log
        self.assertEqual(self.p.cli("job", "step", jid, "Mix").returncode, 0)
        run = self.p.cli("job", "run", jid, "--step", "Mix", "--", "sh", "-c",
                         "echo '[note] WebGL runs on software'; echo trộn; echo trộn; echo xong")
        self.assertIn("[note] WebGL", run.stdout)                              # still printed in the terminal
        lines = [l["line"] for l in json.loads(self.p.cli("job", "show", jid).stdout)["log"]]
        self.assertEqual(lines.count("Mix"), 1)
        self.assertFalse(any(l.startswith("[note]") for l in lines))
        self.assertEqual(lines.count("trộn"), 1)
        self.assertIn("xong", lines)
        self.assertEqual(self.p.cli("job", "fail", jid, "hết dung lượng").returncode, 0)
        self.assertEqual(json.loads(self.p.cli("job", "show", jid).stdout)["status"], "failed")

    def test_job_run_heartbeat(self):  # research §8
        jid, _ = self.start_job()
        before = json.loads(self.p.cli("job", "show", jid).stdout)["updated_at"]
        self.p.cli("job", "run", jid, "--", "sleep", "1.5")
        log = json.loads(self.p.cli("job", "show", jid).stdout)
        self.assertGreater(log["updated_at"], before)

    def test_review_wait_and_decide(self):  # FR-008, FR-009, FR-011, SC-003
        jid, _ = self.start_job()
        summ = self.p.dir / "review-1.md"
        summ.write_text("# Tóm tắt", encoding="utf-8")
        out = self.p.cli("review", "request", jid, "--kind", "style-1", "--set", "demo-set", "--summary", str(summ))
        self.assertEqual(out.returncode, 0, out.stderr)
        rid = out.stdout.splitlines()[0]
        self.assertEqual(self.p.cli("review", "wait", rid, "--timeout", "0.5").returncode, 3)     # timeout
        waiter = subprocess.Popen([PY, CLI, "review", "wait", rid, "--timeout", "20"], stdout=subprocess.PIPE,
                                  text=True, env=os.environ.copy())
        time.sleep(0.5)
        t = time.time()
        r = client().post(f"/api/v1/reviews/{rid}/decision", json={"value": "revise", "note": "nền tối hơn"},
                          headers={"X-Studio": "1"})
        self.assertEqual(r.status_code, 201)
        got, _ = waiter.communicate(timeout=10)
        self.assertLess(time.time() - t, 3)
        self.assertEqual(waiter.returncode, 0)
        self.assertEqual(json.loads(got)["note"], "nền tối hơn")
        self.assertEqual(json.loads(self.p.cli("job", "show", jid).stdout)["status"], "running")
        # the second decision, from the chat, is refused
        self.assertEqual(self.p.cli("review", "decide", rid, "--value", "approve").returncode, 4)
        # a decision given while no session waits is kept and picked up later (FR-011)
        out = self.p.cli("review", "request", jid, "--kind", "style-2", "--set", "demo-set", "--summary", str(summ))
        rid2 = out.stdout.splitlines()[0]
        d = self.p.cli("review", "decide", rid2, "--value", "approve", "--source", "chat")
        self.assertEqual(d.returncode, 0)
        self.assertEqual(client().get(f"/api/v1/reviews/{rid2}").json()["decision"]["source"], "chat")
        w = self.p.cli("review", "wait", rid2, "--timeout", "5")
        self.assertEqual((w.returncode, json.loads(w.stdout)["value"]), (0, "approve"))
        self.assertEqual(self.p.cli("review", "decide", rid2, "--value", "revise").returncode, 2)  # no note → usage

    def test_events_stream(self):  # FR-004, SC-002
        jid, _ = self.start_job()
        port = json.loads((self.p.dir / ".studio" / "server.json").read_text())["port"]
        got = []

        def listen():
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/v1/events?interval=0.2")
            with urllib.request.urlopen(req, timeout=10) as r:
                for raw in r:
                    line = raw.decode().strip()
                    if line.startswith("event:") or line.startswith("data:"):
                        got.append(line)
                    if any(jid in g for g in got) and any(g == "event: job.updated" for g in got):
                        return
        th = threading.Thread(target=listen, daemon=True)
        th.start()
        time.sleep(0.6)
        t = time.time()
        self.p.cli("job", "step", jid, "Phân tích")
        th.join(timeout=5)
        self.assertIn("event: job.updated", got)
        self.assertLess(time.time() - t, 5)
        self.assertTrue(any(jid in g for g in got))


if __name__ == "__main__":
    unittest.main()
