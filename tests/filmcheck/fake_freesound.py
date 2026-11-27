"""A fake Freesound APIv2 for tests (specs/037 T008): text search (records the filter), HQ Ogg previews, 401.

    srv = FakeFreesound(key="fs_test_…").start(); os.environ["STUDIO_FREESOUND_URL"] = srv.url; …; srv.stop()
srv.calls lists (path, query dict, Authorization header). The search answer includes one non-CC0 sound on purpose:
the client must drop it even though the server sent it."""
import json
import struct
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

CC0 = "http://creativecommons.org/publicdomain/zero/1.0/"
BY = "https://creativecommons.org/licenses/by/4.0/"


def ogg_bytes(secs=0.5, rate=44100) -> bytes:
    """A minimal Ogg stream with a Vorbis identification header and a final page granule (no real audio)."""
    ident = b"\x01vorbis" + struct.pack("<IBIiii", 0, 1, rate, 0, 128000, 0) + b"\xb8\x01"
    def page(body, granule, seq, flag):
        return b"OggS\x00" + bytes([flag]) + struct.pack("<qIIIB", granule, 1, seq, 0, 1) + bytes([len(body)]) + body
    return page(ident, 0, 0, 2) + page(b"\x00" * 30, int(secs * rate), 1, 4)


class FakeFreesound:
    def __init__(self, key="fs_test_0123456789abcdef"):
        self.key = key
        self.calls = []
        self.sounds = [
            {"id": 101, "name": "Aquarium bubbles office", "tags": ["aquarium", "bubbles", "water"], "description": "pump",
             "license": CC0, "username": "alice", "duration": 4.0, "url": "https://freesound.org/s/101/"},
            {"id": 102, "name": "Fish tank bubbling", "tags": ["fish", "tank", "bubbles"], "description": "",
             "license": BY, "username": "bob", "duration": 3.0, "url": "https://freesound.org/s/102/"},
            {"id": 103, "name": "Bubbles small", "tags": ["bubbles"], "description": "", "license": "Creative Commons 0",
             "username": "carol", "duration": 1.0, "url": "https://freesound.org/s/103/"},
        ]
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

            def do_GET(self):
                u = urlsplit(self.path)
                q = {k: v[0] for k, v in parse_qs(u.query).items()}
                auth = self.headers.get("authorization") or ""
                fake.calls.append((u.path, q, auth))
                if u.path.startswith("/previews/"):
                    b = ogg_bytes()
                    self.send_response(200)
                    self.send_header("content-type", "audio/ogg")
                    self.send_header("content-length", str(len(b)))
                    self.end_headers()
                    self.wfile.write(b)
                    return
                if auth != f"Token {fake.key}":
                    return self.send(401, {"detail": "Invalid token."})
                if u.path == "/apiv2/search/text/":
                    words = set((q.get("query") or "").lower().split())
                    res = [dict(s, previews={"preview-hq-ogg": f"{fake.url}/previews/{s['id']}-hq.ogg"})
                           for s in fake.sounds if words & set((s["name"] + " " + " ".join(s["tags"])).lower().split())]
                    return self.send(200, {"count": len(res), "results": res[: int(q.get("page_size") or 15)]})
                self.send(404, {"detail": "Not found."})

            def send(self, code, obj):
                b = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)
        return H
