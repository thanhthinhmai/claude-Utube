"""Phase 2 of specs/010: checks.json / CHECKS.md (T004), safe page opening (T005), editor model setting (T006),
the fake editor (T007)."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import editor, report, webfetch  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"
FAKE = REPO / "tests/online/fake_claude"


def tmpdir() -> Path:
    TMP.mkdir(exist_ok=True)
    return Path(tempfile.mkdtemp(dir=TMP))


class Report(unittest.TestCase):
    def test_parts_are_kept_and_markdown_written(self):
        d = tmpdir()
        report.update(d, lambda x: x["script"]["machine"].append(
            {"round": 0, "score": 8.5, "hard": {"format": True, "sources": False}, "issues": [
                {"para": "P02", "sentence": 1, "rule": "long_sentence", "detail": "31 words"}]}))
        report.update(d, lambda x: x.update(film={"pass": False, "measures": {"tail_s": 3.0, "stills_bad": [], "texts_checked": False},
                                                  "problems": ["the film ends 3.0 s after the last word"]}))
        data = json.loads((d / "checks.json").read_text())
        self.assertEqual(data["script"]["machine"][0]["score"], 8.5)        # the second write kept the first
        self.assertEqual(data["script"]["verdict"], "pending")
        md = (d / "CHECKS.md").read_text()
        for s in ("failed: sources", "P02.1 long_sentence", "| tail_s | 3.00 | ≤ 1.5 s |", "not checked", "ends 3.0 s"):
            self.assertIn(s, md)
        self.assertFalse([p for p in d.iterdir() if p.name.startswith(".checks")])      # no temporary file left

    def test_broken_file_starts_empty(self):
        d = tmpdir()
        (d / "checks.json").write_text("{not json")
        self.assertEqual(report.load(d)["script"]["verdict"], "pending")


class Page(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        routes = {
            "/page": (200, "text/html; charset=utf-8", b"<html><head><style>x{}</style><script>evil()</script></head>"
                      b"<body><h1>Hanoi</h1><p>6.2 million motorbikes &amp; more</p></body></html>"),
            "/big": (200, "text/plain", b"x" * (webfetch.MAX_BYTES + 10)),
            "/img": (200, "image/png", b"\x89PNG"),
        }
        if self.path == "/moved":
            self.send_response(302)
            self.send_header("location", "/page")
            self.end_headers()
            return
        code, ctype, body = routes.get(self.path, (404, "text/plain", b"no"))
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except OSError:          # the client stops reading a page that is too large
            pass


class Fetch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), Page)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://localhost:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        self._blocked, self._resolve, self._ports = webfetch.blocked, webfetch.resolve, None

    def tearDown(self):
        webfetch.blocked, webfetch.resolve = self._blocked, self._resolve

    def allow_local(self):
        """The test server is on 127.0.0.1, which the real rules refuse; let it through and accept its port."""
        webfetch.blocked = lambda a: False
        orig = webfetch.check_url

        def check(url):
            from urllib.parse import urlsplit
            u = urlsplit(url)
            return u.scheme, u.hostname, u.port, (u.path or "/"), "127.0.0.1"
        webfetch.check_url = check
        self.addCleanup(setattr, webfetch, "check_url", orig)

    def test_text_without_scripts(self):
        self.allow_local()
        r = webfetch.fetch(self.base + "/page")
        self.assertEqual(r["status"], 200)
        self.assertIn("6.2 million motorbikes & more", r["text"])
        self.assertNotIn("evil", r["text"])
        self.assertLessEqual(len(webfetch.text_of(b"word " * 5000, "text/plain")), 8000)

    def test_redirect_is_followed(self):
        self.allow_local()
        r = webfetch.fetch(self.base + "/moved")
        self.assertTrue(r["final_url"].endswith("/page"))

    def test_limits(self):
        self.allow_local()
        for path, code in (("/big", "too_large"), ("/img", "unsupported_type")):
            with self.assertRaises(webfetch.FetchError) as e:
                webfetch.fetch(self.base + path)
            self.assertEqual(e.exception.code, code, path)

    def test_internal_addresses_are_refused(self):
        webfetch.resolve = lambda host: {"proxy": ["172.18.0.3"], "ten": ["10.0.0.1"], "meta": ["169.254.169.254"],
                                         "v6": ["fd00::1"], "cgnat": ["100.64.1.1"], "mapped": ["::ffff:127.0.0.1"],
                                         "public": ["93.184.216.34"]}[host]
        for url in ("http://127.0.0.1/", "http://proxy:8780/", "http://proxy/", "http://ten/", "http://meta/latest",
                    "https://v6/", "http://cgnat/", "http://mapped/", "ftp://public/", "file:///etc/passwd"):
            with self.assertRaises(webfetch.FetchError, msg=url) as e:
                webfetch.check_url(url)
            self.assertEqual(e.exception.code, "blocked_address", url)
        self.assertEqual(webfetch.check_url("https://public/a?b=1")[4], "93.184.216.34")


class EditorModel(unittest.TestCase):
    def setUp(self):
        self.root = tmpdir()
        self.env = {k: os.environ.get(k) for k in ("STUDIO_ROOT", "STUDIO_EDITOR_MODEL", "STUDIO_MODEL")}
        os.environ["STUDIO_ROOT"] = str(self.root)
        for k in ("STUDIO_EDITOR_MODEL", "STUDIO_MODEL"):
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_default_is_inherit(self):
        self.assertEqual((editor.editor_model(), editor.model_args()), ("inherit", []))
        os.environ["STUDIO_MODEL"] = "claude-opus-5-5"
        self.assertEqual(editor.model_args(), ["--model", "claude-opus-5-5"])

    def test_local_config_command(self):
        env = {**os.environ, "STUDIO_ROOT": str(self.root)}
        p = subprocess.run(["sh", str(REPO / "bin/studio"), "config", "editor-model", "sonnet"], env=env,
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads((self.root / ".studio/config.json").read_text())["editor_model"], "sonnet")
        self.assertEqual(editor.model_args(), ["--model", "sonnet"])
        bad = subprocess.run(["sh", str(REPO / "bin/studio"), "config", "editor-model", "gpt"], env=env,
                             capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)

    def test_online_setting_wins(self):
        editor.set_editor_model("sonnet")
        os.environ["STUDIO_EDITOR_MODEL"] = "haiku"
        self.assertEqual(editor.model_args(), ["--model", "haiku"])


class FakeEditor(unittest.TestCase):
    def ask(self, film: Path):
        p = subprocess.run([sys.executable, str(FAKE), "-p", "--json-schema", '{"checked_sources": {}}', "--output-format", "json"],
                           input=f"Review this script. Files:\n- {film}/SCRIPT.md\n", capture_output=True, text=True, check=True)
        return json.loads(p.stdout)["structured_output"]

    def test_p1_until_changed(self):
        d = tmpdir()
        (d / "SCRIPT.md").write_text("> [editor-p1 P02]\n[P01] One.\n[P02] Two.\n")
        self.assertEqual(self.ask(d)["issues"][0]["level"], "P1")
        self.assertEqual(self.ask(d)["issues"][0]["para"], "P02")
        (d / "SCRIPT.md").write_text("> [editor-p1 P02]\n[P01] One.\n[P02] Two, fixed.\n")
        self.assertEqual(self.ask(d), {"score": 9, "issues": [], "checked_sources": []})

    def test_low_and_bad(self):
        d = tmpdir()
        (d / "SCRIPT.md").write_text("> [editor-low]\n[P01] One.\n")
        self.assertEqual(self.ask(d)["score"], 6)
        (d / "SCRIPT.md").write_text("> [editor-bad-json]\n[P01] One.\n")
        self.assertNotIn("score", self.ask(d))


if __name__ == "__main__":
    unittest.main()
