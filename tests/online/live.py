"""Live run of the online studio with real Claude (specs/007 tasks T048, SC-002, SC-006). Costs money.

Brings the stack up on this machine (DOMAIN=localhost in deploy/.env), makes 3 films of 30 seconds and, when
--videos is given, learns one style from up to 3 of your own videos. Reviews and questions are answered
automatically. Prints the time, cost and quality checks of each job. Run it through tests/online/live.sh."""
import argparse
import http.cookiejar
import json
import mimetypes
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADMIN, CUSTOMER, PASSWORD = "live-admin@example.com", "live-customer@example.com", "live run password 2026"
IDEAS = [
    "A night-shift baker in Hanoi shapes the first loaf of the day while the street is still asleep.",
    "A paper boat travels down a rainy gutter and reaches a wide, quiet river at dawn.",
    "An old lighthouse keeper teaches a young cat to watch for ships.",
]


class Client:
    def __init__(self, base: str):
        self.base = base.rstrip("/")
        ctx = ssl.create_default_context()
        ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE        # Caddy's own certificate for localhost
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
                                              urllib.request.HTTPSHandler(context=ctx))

    def call(self, method, path, body=None, raw=None, ctype="application/json"):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(self.base + "/api/v1" + path, data=data, method=method,
                                     headers={"X-Studio": "1", "Content-Type": ctype, "Origin": self.base})
        try:
            with self.op.open(req, timeout=120) as r:
                return r.status, (json.loads(r.read() or b"{}") if "json" in r.headers.get("content-type", "") else r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def ok(self, method, path, body=None, **kw):
        code, out = self.call(method, path, body, **kw)
        if code >= 300:
            sys.exit(f"✗ {method} {path} → {code}: {out}")
        return out

    def login(self, email):
        self.ok("POST", "/auth/login", {"email": email, "password": PASSWORD})

    def upload(self, path: Path) -> str:
        b = uuid.uuid4().hex
        body = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\n"
                f"Content-Type: {mimetypes.guess_type(path.name)[0] or 'video/mp4'}\r\n\r\n").encode() + path.read_bytes() \
            + f"\r\n--{b}--\r\n".encode()
        return self.ok("POST", "/uploads", raw=body, ctype=f"multipart/form-data; boundary={b}")["upload_id"]


def compose(*args, check=True):
    return subprocess.run(["docker", "compose", "-f", str(REPO / "deploy/compose.yaml"), "--env-file",
                           str(REPO / "deploy/.env"), *args], check=check, capture_output=True, text=True)


def make_account(email, role):
    code = (f"from studio import accounts\ntry:\n    accounts.signup({email!r}, {PASSWORD!r}, True, role={role!r}, verified=True)\n"
            f"except Exception as e:\n    print('exists', e)\n")
    compose("exec", "-T", "web", "/studio/tools/.venv/bin/python", "-c",
            f"import sys; sys.path.insert(0, '/studio/tools/studio')\n{code}")


def loudness(mp4: Path):
    p = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-i", str(mp4), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    import re
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr)
    pk = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", p.stderr)
    return (float(i[-1]) if i else None), (float(pk[-1]) if pk else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://localhost")
    ap.add_argument("--videos", help="folder with up to 3 of your own videos to learn a style from")
    ap.add_argument("--films", type=int, default=3)
    ap.add_argument("--seconds", type=int, default=30)
    ap.add_argument("--no-up", action="store_true", help="the stack is already running")
    a = ap.parse_args()
    if not a.no_up:
        print("↑ sh bin/studio online up …")
        subprocess.run(["sh", str(REPO / "bin/studio"), "online", "up"], check=True)
        time.sleep(5)
    make_account(ADMIN, "admin")
    make_account(CUSTOMER, "customer")
    admin, cust = Client(a.base), Client(a.base)
    admin.login(ADMIN)
    cust.login(CUSTOMER)
    me = cust.ok("GET", "/me")
    admin.ok("PUT", f"/admin/accounts/{me['id']}", {"quota_films": a.films + 2, "quota_learns": 2})
    styles = [s["slug"] for s in cust.ok("GET", "/library")["styles"]][: a.films]
    started, ids = {}, []
    for idea, style in zip(IDEAS, styles):
        j = cust.ok("POST", "/jobs", {"kind": "film", "style": style, "idea": idea, "seconds": a.seconds})
        ids.append(j["id"])
        started[j["id"]] = time.time()
        print(f"→ film {j['id']} · {style}")
    if a.videos:
        files = sorted(p for p in Path(a.videos).iterdir() if p.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm"))[:3]
        ups = [cust.upload(f) for f in files]
        j = cust.ok("POST", "/jobs", {"kind": "learn", "source": "upload", "uploads": ups})
        ids.append(j["id"])
        started[j["id"]] = time.time()
        print(f"→ learn {j['id']} · {len(ups)} videos")
    done = {}
    while len(done) < len(ids):
        for jid in ids:
            if jid in done:
                continue
            j = admin.ok("GET", f"/jobs/{jid}")
            open_ = [r for r in j.get("reviews", []) if not r["decision"]]
            if j["status"] == "waiting_review" and open_:
                r = open_[0]
                body = {"value": "approve", "note": "Your choice; keep it simple." if r["kind"] == "question" else ""}
                cust.ok("POST", f"/reviews/{r['id']}/decision", body)
                print(f"  {jid}: answered {r['kind']}")
            if j["status"] in ("done", "failed", "stopped"):
                done[jid] = (j, time.time() - started[jid])
                print(f"  {jid}: {j['status']} in {done[jid][1] / 60:.1f} min, ${j.get('cost_usd', 0):.2f}")
        time.sleep(10)
    print("\n| Job | Kind | Status | Minutes | Cost (USD) | LUFS | Peak dB | Readcheck |\n|---|---|---|---|---|---|---|---|")
    out = REPO / "tests/online/.tmp/live"
    out.mkdir(parents=True, exist_ok=True)
    for jid in ids:
        j, secs = done[jid]
        lufs = peak = None
        rc = (j.get("qa") or {}).get("readcheck", "–")
        if j["status"] == "done" and j["kind"] == "film":
            code, data = cust.call("GET", f"/films/{j['links']['film']}/download")
            if code == 200:
                f = out / f"{j['links']['film']}.mp4"
                f.write_bytes(data)
                lufs, peak = loudness(f)
        print(f"| {jid} | {j['kind']} | {j['status']} | {secs / 60:.1f} | {j.get('cost_usd', 0):.2f} | "
              f"{lufs if lufs is not None else '–'} | {peak if peak is not None else '–'} | {rc} |")
    films = [done[i][0] for i in ids if done[i][0]["kind"] == "film"]
    print(f"\nFilms done: {sum(f['status'] == 'done' for f in films)}/{len(films)} · total cost "
          f"${sum(done[i][0].get('cost_usd', 0) for i in ids):.2f} · films saved in {out}")


if __name__ == "__main__":
    main()
