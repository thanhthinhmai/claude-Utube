"""specs/025: the parts of a film already done, on the job page (local mode)."""
import json
import os
import shutil
import subprocess
import time
import unittest
import wave
from pathlib import Path

from helpers import REPO, Project, client, jpg

NODE_MODULES = REPO / "lib" / "lemo-opuscar" / "node_modules"
BROWSER = Path(__file__).with_name("browser_done.cjs")


def wav(path: Path, seconds: float):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\0\0" * int(8000 * seconds))


def make_film(d: Path):
    """A small film half way: script passed, voices passed, mix, shots; render running."""
    paras = "\n".join(f"[P{i:02d}] Sentence number {i} has five words." for i in range(1, 13))
    (d / "SCRIPT.md").write_text(f"Title: Demo film\nTarget: 90s\nLanguage: en\n\n> A1 HOOK: a note for the director.\n{paras}\n")
    (d / "SOURCES.md").write_text('- [P01] "x": Site A, 2026, https://a.example/1\n- [P02] "y": Site A, 2026, https://a.example/1\n'
                                  '- [P03] "z": Site B, 2026, https://b.example/2\n- [P04] "w": fiction\n')
    lines = [{"id": f"l00{i}", "para": f"P0{i}", "text": f"Line {i}.", "voice": "am_michael", "speed": 1.1} for i in range(1, 6)]
    lines[2]["say"] = "Line three, read slowly."
    (d / "lines.json").write_text(json.dumps(lines))
    for x in lines:
        wav(d / "voices" / f"{x['id']}.wav", 0.4)
    (d / "voices" / "dur.json").write_text(json.dumps({x["id"]: 0.4 for x in lines}))
    (d / "checks.json").write_text(json.dumps({
        "script": {"verdict": "pass", "fix_rounds": 1, "machine": [{"round": 1, "score": 9.5}],
                   "editor": [{"round": 1, "score": 8.5, "model": "claude-opus-5-5"}]},
        "tiers": {"voice": {"pass": True}, "plan": {"pass": True},
                  "shots": {"pass": True, "issues": [{"severity": "warn"}, {"severity": "block"}], "style_accept": {"reason": "ok"}}}}))
    (d / ".check").mkdir(exist_ok=True)
    (d / ".check" / "review-r1.json").write_text(json.dumps({"score": 8.5, "issues": [{"level": "P3", "para": "P02", "reason": "r"}]}))
    sh = d / ".check" / "shots"
    for n in (1, 2):
        jpg(sh / f"sheet-{n}.jpg")
    for s in ("S001", "S002", "S003"):
        jpg(sh / f"{s}.jpg")
    jpg(sh / "S002~S002.bubble.jpg")
    (d / ".check" / "labels.json").write_text(json.dumps({"labels": {"S001": {"scale": "cu", "place": "kitchen"}}}))
    wav(d / "out" / "mix.wav", 2.0)
    old = time.time() - 60
    os.utime(d / "out" / "mix.wav", (old, old))
    (d / "out" / "render.log").write_text("render: gpu · ANGLE · 600 frames · 4 chunks (0 already done) · 2 workers · x\n"
                                          "1/4 chunks  3s\n")
    (d / "channel.json").write_text("{}")


class DoneSoFar(unittest.TestCase):
    def setUp(self):
        self.p = Project(ports="18820-18829")
        self.film = self.p.dir / "films" / "half-done"
        make_film(self.film)
        out = self.p.cli("job", "start", "--kind", "film", "--name", "half-done", "--film", "half-done")
        self.jid, self.url = out.stdout.splitlines()[0], out.stdout.splitlines()[1]
        self.p.cli("job", "step", self.jid, "Render")
        self.c = client()

    def tearDown(self):
        self.p.close()

    def done(self):
        r = self.c.get(f"/api/v1/jobs/{self.jid}/done")
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_summary(self):                                       # FR-002–FR-007, SC-001
        d = self.done()
        st = {s["key"]: s for s in d["steps"]}
        self.assertEqual(d["film"], "half-done")
        self.assertEqual({k: v["state"] for k, v in st.items()}, {"script": "done", "voice": "done", "shots": "done",
                         "mix": "done", "render": "running", "selfcheck": "waiting", "publish": "waiting"})
        self.assertEqual(st["render"]["progress"], {"done": 1, "total": 4})
        s = d["sections"]
        self.assertEqual({k: s["script"][k] for k in ("title", "target_seconds", "paragraphs", "words", "sources", "machine", "rounds")},
                         {"title": "Demo film", "target_seconds": 90, "paragraphs": 12, "words": 72, "sources": 2,
                          "machine": 9.5, "rounds": [1]})
        self.assertEqual(s["script"]["editor"], {"score": 8.5, "fix_rounds": 1, "model": "claude-opus-5-5"})
        self.assertEqual(len([x for x in s["script"]["excerpt"] if x["kind"] == "para"]), 9)
        self.assertEqual(s["script"]["excerpt"][0], {"kind": "dir", "text": "A1 HOOK: a note for the director."})
        self.assertEqual({k: s["voice"][k] for k in ("lines", "voice", "speed", "pass", "respelled")},
                         {"lines": 5, "voice": "am_michael", "speed": 1.1, "pass": True, "respelled": 1})
        self.assertEqual({k: s["shots"][k] for k in ("shots", "extras", "sheets", "warnings", "accepted", "labels")},
                         {"shots": 3, "extras": 1, "sheets": 2, "warnings": 1, "accepted": "ok", "labels": True})
        self.assertEqual(s["mix"]["seconds"], 2.0)
        self.assertEqual({k: s["render"][k] for k in ("chunks_done", "chunks_total", "mode", "workers")},
                         {"chunks_done": 1, "chunks_total": 4, "mode": "gpu", "workers": 2})
        self.assertNotIn("film_dir", self.c.get(f"/api/v1/jobs/{self.jid}").json())     # never show a server path

    def test_render_done(self):
        (self.film / "half-done.mp4").write_bytes(b"\0" * 64)
        ch = json.loads((self.film / "checks.json").read_text())
        ch["tiers"]["render"] = {"pass": True}
        (self.film / "checks.json").write_text(json.dumps(ch))
        old = time.time() - 60
        os.utime(self.film / "out" / "render.log", (old, old))
        self.p.cli("job", "step", self.jid, "Self-check")
        st = {s["key"]: s for s in self.done()["steps"]}
        self.assertEqual(st["render"]["state"], "done")
        self.assertEqual(self.done()["sections"]["render"]["chunks_done"], 4)

    def test_files(self):                                         # FR-009, SC-004
        base = f"/api/v1/jobs/{self.jid}/files/"
        for path, ctype in (("SCRIPT.md", "text/markdown"), ("lines.json", "application/json"), ("voices/l001.wav", "audio/wav"),
                            ("out/mix.wav", "audio/wav"), (".check/shots/sheet-1.jpg", "image/jpeg"),
                            (".check/shots/S002~S002.bubble.jpg", "image/jpeg"), (".check/review-r1.json", "application/json")):
            r = self.c.get(base + path)
            self.assertEqual(r.status_code, 200, path)
            self.assertTrue(r.headers["content-type"].startswith(ctype), (path, r.headers["content-type"]))
        r = self.c.get(base + "out/mix.wav", headers={"Range": "bytes=0-99"})
        self.assertEqual(r.status_code, 206)
        (self.film / "voices" / "l009.wav").symlink_to(self.p.dir / "secret.txt")
        refused = {"channel.json": 404, "voices/l404.wav": 404, "voices/l009.wav": 400, "%2e%2e/secret.txt": 400,
                   "voices/%2e%2e/channel.json": 400, "%2Fetc%2Fpasswd": 400}
        for path, code in refused.items():
            r = self.c.get(base + path)
            self.assertEqual(r.status_code, code, path)
            self.assertNotIn("do not serve", r.text)

    def test_not_a_film_job(self):
        jid = self.p.cli("job", "start", "--kind", "learn", "--name", "x", "--set", "demo-set").stdout.splitlines()[0]
        self.assertEqual(self.c.get(f"/api/v1/jobs/{jid}/done").status_code, 404)
        self.assertEqual(self.c.get(f"/api/v1/jobs/{jid}/files/SCRIPT.md").status_code, 404)

    def test_old_job_without_film_dir(self):                      # a job made before 025: films/<film>
        p = self.p.dir / ".studio" / "jobs" / f"{self.jid}.json"
        j = json.loads(p.read_text())
        j.pop("film_dir")
        p.write_text(json.dumps(j))
        self.assertEqual(self.done()["film"], "half-done")

    @unittest.skipUnless(shutil.which("node") and (NODE_MODULES / "playwright-core").is_dir(), "no node / playwright-core")
    def test_in_browser(self):                                    # SC-001, SC-002 on the small film
        base = self.url.split("URL: ", 1)[1].split("/#", 1)[0]
        r = subprocess.run(["node", str(BROWSER), base, self.jid], capture_output=True, text=True, timeout=90,
                           env={**os.environ, "NODE_PATH": str(NODE_MODULES)})
        if r.returncode == 77:
            self.skipTest("no browser")
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(o["errors"], [])
        self.assertIn("Machine 9.5/10", o["script"])
        self.assertIn("2 sources", o["script"])
        self.assertGreater(o["fullScript"], 100)
        self.assertEqual((o["voiceRows"], o["respelledRows"], o["readAs"]), (5, 1, 1))
        self.assertIsNotNone(o["playing"])
        self.assertLess(o["playing"], 1000)
        self.assertEqual((o["sheetButtons"], o["thumbs"], o["lightbox"]), (2, 3, 1))
        self.assertIn("Length 0:02", o["mix"])
        self.assertEqual((o["chunks"], o["chunksDone"]), (4, 1))
        self.assertIn("GPU", o["render"])
        disabled = {s["text"].split()[0]: s["disabled"] for s in o["steps"]}
        self.assertTrue(disabled["Self-check"] and disabled["Publish"])

    @unittest.skipUnless(shutil.which("node") and (NODE_MODULES / "playwright-core").is_dir(), "no node / playwright-core")
    def test_live_update_keeps_the_open_section(self):           # FR-008, SC-003
        base = self.url.split("URL: ", 1)[1].split("/#", 1)[0]
        ready = self.p.dir / "ready"
        node = subprocess.Popen(["node", str(Path(__file__).with_name("browser_done_live.cjs")), base, self.jid, str(ready)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                env={**os.environ, "NODE_PATH": str(NODE_MODULES)})
        deadline = time.time() + 40
        while not ready.exists() and node.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if node.poll() == 77:
            self.skipTest("no browser")
        ch = json.loads((self.film / "checks.json").read_text())
        ch["tiers"]["final"] = {"pass": True}
        (self.film / "checks.json").write_text(json.dumps(ch))
        self.p.cli("job", "step", self.jid, "Self-check")
        out, err = node.communicate(timeout=40)
        self.assertEqual(node.returncode, 0, err)
        o = json.loads(out.strip().splitlines()[-1])
        self.assertEqual(o["errors"], [])
        self.assertIsNotNone(o["changed"])
        self.assertLess(o["changed"], 10000)
        self.assertEqual((o["kept"], o["step"]), (1, "Self-check"))


if __name__ == "__main__":
    unittest.main()
