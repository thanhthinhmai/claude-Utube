"""specs/036 T008: the ElevenLabs client — direct with a key from the environment or .env, or through the proxy."""
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from filmcheck import eleven  # noqa: E402
from fake_eleven import VOICES, FakeEleven  # noqa: E402


class Direct(unittest.TestCase):
    def setUp(self):
        self.fake = FakeEleven(left=100, page=2).start()
        self.root = Path(tempfile.mkdtemp(prefix="el."))
        self.env = mock.patch.dict(os.environ, {"STUDIO_ELEVEN_URL": self.fake.url, "STUDIO_ROOT": str(self.root),
                                                "ELEVENLABS_API_KEY": self.fake.key}, clear=False)
        self.env.start()
        for k in ("STUDIO_JOB_TOKEN", "STUDIO_PROXY", "ELEVENLABS_MODEL"):
            os.environ.pop(k, None)
        eleven._cache.clear()

    def tearDown(self):
        self.env.stop()
        self.fake.stop()

    def test_subscription(self):
        s = eleven.subscription()
        self.assertEqual((s["tier"], s["left"], s["limit"]), ("creator", 100, 100))

    def test_voices_follow_every_page(self):
        rows = eleven.voices()
        self.assertEqual(len(rows), len(VOICES))
        self.assertEqual(sum(1 for c in self.fake.calls if c[1] == "/v2/voices"), 2)
        eleven.voices()                                  # cached for 10 minutes
        self.assertEqual(sum(1 for c in self.fake.calls if c[1] == "/v2/voices"), 2)

    def test_speak_returns_pcm_and_alignment(self):
        pcm, al, n = eleven.speak("el:v_narr", "Hello there.", settings={"speed": 1.5, "stability": 0.4})
        self.assertGreater(len(pcm), 24000 * 2 * 0.3 - 2)
        self.assertEqual(al["characters"], list("Hello there."))
        self.assertEqual(n, 12)
        body = self.fake.calls[-1][2]
        self.assertEqual(body["model_id"], eleven.DEFAULT_MODEL)
        self.assertEqual(body["voice_settings"], {"stability": 0.4, "speed": 1.2})     # speed clamped to 0.7–1.2
        self.assertIn("/v1/text-to-speech/v_narr/with-timestamps", self.fake.calls[-1][1])

    def test_bad_key(self):
        os.environ["ELEVENLABS_API_KEY"] = "sk_wrong_0000000000"
        with self.assertRaises(eleven.ElevenError) as e:
            eleven.subscription()
        self.assertEqual(e.exception.code, "invalid_key")
        self.assertNotIn("sk_wrong_0000000000", e.exception.message)

    def test_quota(self):
        with self.assertRaises(eleven.ElevenError) as e:
            eleven.speak("el:v_narr", "x" * 101)
        self.assertEqual(e.exception.code, "quota")

    def test_too_long(self):
        with self.assertRaises(eleven.ElevenError) as e:
            eleven.speak("el:v_narr", "x" * 1001)
        self.assertEqual(e.exception.code, "too_long")

    def test_key_from_dotenv_and_inline_comment(self):
        os.environ.pop("ELEVENLABS_API_KEY")
        (self.root / ".env").write_text(f"# keys\nELEVENLABS_API_KEY=\"{self.fake.key}\"\n"
                                        "ELEVENLABS_MODEL=eleven_v3   # a comment\n")
        self.assertEqual(eleven.model(), "eleven_v3")
        self.assertEqual(eleven.subscription()["left"], 100)

    def test_no_key(self):
        os.environ.pop("ELEVENLABS_API_KEY")
        with self.assertRaises(eleven.ElevenError) as e:
            eleven.subscription()
        self.assertEqual(e.exception.code, "no_key")


class ThroughProxy(unittest.TestCase):
    """Inside a job: every call goes to the proxy with the job token; .env and ELEVENLABS_API_KEY are not read."""
    def setUp(self):
        self.seen = []
        seen = self.seen

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["content-length"])))
                seen.append((self.path, self.headers.get("authorization"), body))
                if self.path.endswith("/subscription"):
                    out = {"tier": "x", "left": 7, "limit": 9, "used": 2, "reset_at": None}
                elif self.path.endswith("/voices"):
                    out = {"voices": [{"id": "el:a", "name": "A"}]}
                elif body.get("text") == "quota":
                    b = json.dumps({"error": {"code": "quota", "message": "no characters"}}).encode()
                    self.send_response(402); self.send_header("content-length", str(len(b))); self.end_headers()
                    self.wfile.write(b)
                    return
                else:
                    out = {"audio_base64": "AAAA", "alignment": None, "chars": len(body["text"])}
                b = json.dumps(out).encode()
                self.send_response(200); self.send_header("content-length", str(len(b))); self.end_headers()
                self.wfile.write(b)
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        root = Path(tempfile.mkdtemp(prefix="elp."))
        (root / ".env").write_text("ELEVENLABS_API_KEY=should_not_be_read\n")
        self.env = mock.patch.dict(os.environ, {"STUDIO_ROOT": str(root), "STUDIO_JOB_TOKEN": "job-token-1",
                                                "STUDIO_PROXY": f"http://127.0.0.1:{self.srv.server_address[1]}"})
        self.env.start()
        os.environ.pop("ELEVENLABS_API_KEY", None)
        eleven._cache.clear()

    def tearDown(self):
        self.env.stop()
        self.srv.shutdown()
        self.srv.server_close()

    def test_all_calls_go_to_the_proxy(self):
        self.assertEqual(eleven.subscription()["left"], 7)
        self.assertEqual(eleven.voices()[0]["id"], "el:a")
        pcm, al, n = eleven.speak("el:v1", "Hi.")
        self.assertEqual((pcm, n), (b"\0\0\0", 3))
        self.assertEqual([p for p, _, _ in self.seen], ["/internal/tts/elevenlabs/subscription",
                                                       "/internal/tts/elevenlabs/voices", "/internal/tts/elevenlabs/speak"])
        self.assertTrue(all(a == "Bearer job-token-1" for _, a, _ in self.seen))
        self.assertEqual(self.seen[-1][2]["voice_id"], "v1")
        self.assertNotIn("should_not_be_read", json.dumps(self.seen))

    def test_proxy_error_code(self):
        with self.assertRaises(eleven.ElevenError) as e:
            eleven.speak("el:v1", "quota")
        self.assertEqual(e.exception.code, "quota")


if __name__ == "__main__":
    unittest.main()
