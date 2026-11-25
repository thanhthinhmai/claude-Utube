"""A fake ElevenLabs for tests (specs/036 T001): subscription, paged voices, with-timestamps (silent PCM), 401, quota.

    srv = FakeEleven(key="sk_test_…", left=500); srv.start(); os.environ["STUDIO_ELEVEN_URL"] = srv.url; …; srv.stop()
srv.calls lists (method, path, json body) of every call; srv.used counts the characters charged."""
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

VOICES = [
    {"voice_id": "v_narr", "name": "Adam", "category": "premade",
     "labels": {"gender": "male", "age": "middle_aged", "accent": "american", "description": "deep"},
     "preview_url": "https://example.invalid/adam.mp3"},
    {"voice_id": "v_girl", "name": "Lily", "category": "premade",
     "labels": {"gender": "female", "age": "young", "accent": "british"}, "preview_url": None},
    {"voice_id": "v_mine", "name": "My voice", "category": "cloned", "is_owner": True, "labels": {}, "preview_url": None},
    {"voice_id": "v_lib", "name": "Shared", "category": "professional", "is_owner": False,
     "sharing": {"original_voice_id": "x1"}, "labels": {"gender": "male"}, "preview_url": None},
]


class FakeEleven:
    def __init__(self, key="sk_test_0123456789abcdef", left=10000, tier="creator", page=2):
        self.key, self.limit, self.used, self.tier, self.page = key, left, 0, tier, page
        self.calls = []
        self.align = True
        self.cost = None
        self.busy = 0                                       # the next n speak calls answer 429 (too many at once)                                    # a ratio: the plan charges fewer than the letters                                   # False: like eleven_v3 at times, no alignment comes back
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def start(self):
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        return self

    def stop(self):
        self.srv.shutdown()
        self.srv.server_close()

    def _handler(self):
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def send(self, code, obj, headers=None):
                b = json.dumps(obj).encode()
                self.send_response(code)
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def handle_any(self, method):
                u = urlsplit(self.path)
                n = int(self.headers.get("content-length") or 0)
                body = json.loads(self.rfile.read(n)) if n else None
                fake.calls.append((method, u.path, body))
                if self.headers.get("xi-api-key") != fake.key:
                    return self.send(401, {"detail": {"status": "invalid_api_key", "message": "Invalid API key"}})
                if u.path == "/v1/user/subscription":
                    return self.send(200, {"tier": fake.tier, "character_count": fake.used,
                                           "character_limit": fake.limit, "next_character_count_reset_unix": 1767225600})
                if u.path == "/v2/voices":
                    q = parse_qs(u.query)
                    start = int((q.get("next_page_token") or ["0"])[0])
                    rows = VOICES[start:start + fake.page]
                    more = start + fake.page < len(VOICES)
                    return self.send(200, {"voices": rows, "has_more": more,
                                           "next_page_token": str(start + fake.page) if more else None})
                if u.path.startswith("/v1/text-to-speech/") and u.path.endswith("/with-timestamps"):
                    text = body["text"]
                    if fake.busy > 0:
                        fake.busy -= 1
                        return self.send(429, {"detail": {"status": "too_many_concurrent_requests",
                                                          "message": "Too many concurrent requests."}})
                    if fake.used + len(text) > fake.limit:
                        return self.send(401, {"detail": {"status": "quota_exceeded", "message": "quota"}})
                    cost = len(text) if fake.cost is None else int(len(text) * fake.cost)
                    fake.used += cost
                    secs = max(0.3, 0.06 * len(text))
                    pcm = b"\0\0" * int(24000 * secs)
                    step = secs / max(1, len(text))
                    return self.send(200, {"audio_base64": base64.b64encode(pcm).decode(), "alignment": {
                        "characters": list(text),
                        "character_start_times_seconds": [round(i * step, 3) for i in range(len(text))],
                        "character_end_times_seconds": [round((i + 1) * step, 3) for i in range(len(text))]}
                        if fake.align else None}, {"character-cost": str(cost)} if fake.cost is not None else None)
                return self.send(404, {"detail": "not found"})

            def do_GET(self):
                self.handle_any("GET")

            def do_POST(self):
                self.handle_any("POST")

        return H
