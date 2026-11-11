"""CLI for the studio UI, jobs and reviews. Called by: sh bin/studio ui | job | review …  (contracts/cli.md)
Exit codes: 0 ok · 1 failed / not found · 2 bad usage · 3 wait timed out · 4 already decided."""
import argparse
import collections
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
PROJECT = Path(os.environ.get("STUDIO_ROOT") or Path(__file__).resolve().parents[2])


def _host_for_chat():
    """The studio host running for this project (specs/014 R7): the chat flow's jobs and reviews go to its job book.
    Only for `job` and `review` outside a job container."""
    if os.environ.get("STUDIO_MODE") or len(sys.argv) < 2 or sys.argv[1] not in ("job", "review"):
        return None
    from studio import host
    return host.running_pointer(PROJECT)


HOST = _host_for_chat()
if HOST:
    os.environ.update(STUDIO_MODE="online", STUDIO_DATA=HOST["data"])

from studio import jobs, launcher, reviews  # noqa: E402
from studio.store import StudioError  # noqa: E402

EXIT = {"invalid": 2, "value_not_allowed": 2, "note_required": 2, "bad_name": 2, "already_decided": 4}


def out(*lines):
    """Print, but never fail when the reader went away (e.g. `JOB=$(sh bin/studio job start … | head -1)`)."""
    for line in lines:
        try:
            print(line, flush=True)
        except BrokenPipeError:
            try:
                sys.stdout = open(os.devnull, "w")
            except OSError:
                pass
            return


def ui_url(path: str = "/"):
    """URL of the running UI, starting it if needed; None (with a warning) if it cannot start."""
    if HOST:                                     # the app on this machine (specs/014)
        return f"http://127.0.0.1:{HOST['web']}{path}"
    try:
        return launcher.url(launcher.ensure()["port"], path)
    except StudioError as e:
        print(f"! {e.message}. Việc vẫn chạy; duyệt trong khung chat như cũ.", file=sys.stderr)
        return None


# ---------- ui ----------
def cmd_ui(a):
    if a.action == "stop":
        out("✓ đã tắt giao diện" if launcher.stop() else "= giao diện không chạy")
        return 0
    if a.action == "status":
        i = launcher.info()
        if launcher.alive(i):
            out(f"✓ đang chạy · cổng {i['port']} · pid {i['pid']}", f"URL: {launcher.url(i['port'])}")
            return 0
        out("✗ giao diện không chạy. Mở: sh bin/studio ui")
        return 1
    i = launcher.ensure()
    out(f"URL: {launcher.url(i['port'])}")
    return 0


# ---------- job ----------
def cmd_job(a):
    if a.action == "start":
        if HOST:                                 # into the host's job book, as the owner (specs/014 FR-017)
            from studio import host
            j = jobs.create(a.kind, a.name, {"set": a.set, "film": a.film}, owner=host.owner_id(Path(HOST["data"])) or "local",
                            extra={"source": "chat"})
        else:
            j = jobs.create(a.kind, a.name, {"set": a.set, "film": a.film})
        out(j["id"])
        u = ui_url(f"/#/jobs/{j['id']}")
        if u:
            out(f"URL: {u}")
        return 0
    if a.action == "step":
        jobs.step(a.id, a.text, jobs.parse_progress(a.progress) if a.progress else None)
        return 0
    if a.action == "log":
        jobs.log(a.id, a.text)
        return 0
    if a.action == "run":
        return job_run(a)
    if a.action == "done":
        jobs.finish(a.id, "done", links={"style": a.style, "film": a.film})
        if HOST and a.film:
            link_film(a.film)
        return 0
    if a.action == "fail":
        jobs.finish(a.id, "failed", error=a.text)
        return 0
    if a.action == "stop":
        jobs.finish(a.id, "stopped")
        return 0
    if a.action == "show":
        out(json.dumps(reviews.job_view(jobs.load(a.id)), ensure_ascii=False, indent=1))
        return 0
    return 2


def link_film(film: str) -> None:
    """The app shows a film made in the chat flow: a copy in the owner's films/, made of hard links where it can (no
    extra space). Not a symbolic link: the studio refuses paths that lead outside a person's folder."""
    from studio import host
    owner = host.owner_id(Path(HOST["data"]))
    src = PROJECT / "films" / film
    if not owner or not src.is_dir():
        return
    dest = Path(HOST["data"]) / "accounts" / owner / "films" / film
    if not dest.exists() and not dest.is_symlink():
        import shutil

        def link_or_copy(a, b):
            try:
                os.link(a, b)
            except OSError:
                shutil.copy2(a, b)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest, copy_function=link_or_copy, symlinks=True)


def job_run(a, remote: bool = False) -> int:
    cmd = a.cmd
    if not cmd:
        raise StudioError("invalid", "thiếu lệnh sau --", 422)
    if remote:
        step = lambda text: proxy_call("POST", f"/internal/jobs/{a.id}/step", {"text": text})   # noqa: E731
        add_log = lambda *lines: proxy_call("POST", f"/internal/jobs/{a.id}/log", {"lines": list(lines)})  # noqa: E731
        beat_fn = (lambda: step(a.step)) if a.step else (lambda: None)   # same step again only marks it alive  # noqa: E731
    else:
        jobs.load(a.id)
        step = lambda text: jobs.step(a.id, text)     # noqa: E731
        add_log = lambda *lines: jobs.log(a.id, *lines)   # noqa: E731
        beat_fn = lambda: jobs.heartbeat(a.id)         # noqa: E731
    if a.step:
        step(a.step)
    tail = collections.deque(maxlen=50)
    beat = float(os.environ.get("STUDIO_HEARTBEAT", "30"))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    done = threading.Event()

    def heartbeat():
        while not done.wait(beat):
            try:
                beat_fn()
            except StudioError:
                pass
    threading.Thread(target=heartbeat, daemon=True).start()
    # online, the agent reads only the end (every line it reads is paid again on every later turn); locally all of it
    quiet = remote
    for line in p.stdout:
        if not quiet:
            sys.stdout.write(line)
            sys.stdout.flush()
        text = line.rstrip("\n")
        # the log keeps the command's output, not tool notes ("[note] WebGL …") or a line repeated right after itself
        if text.startswith("[note] ") or (tail and tail[-1] == text):
            continue
        tail.append(text)
    rc = p.wait()
    done.set()
    if quiet:
        shown = list(tail)[-20:]
        if len(tail) > 20:
            print(f"… ({len(tail) - 20}+ earlier lines are in the job log)")
        print("\n".join(shown), flush=True)
    add_log(*tail, f"(command exited with code {rc})")
    return rc


# ---------- inside a job container (online mode, specs/007 contracts/runner.md) ----------
REVIEW_PENDING = ".review_pending"     # tells agent.py to end the turn with exit code 10


def in_container() -> bool:
    return os.environ.get("STUDIO_MODE") == "online" and bool(os.environ.get("STUDIO_JOB"))


def proxy_call(method: str, path: str, body: dict = None):
    """Call the API proxy with this job's token. Raises StudioError on an error answer."""
    import urllib.error
    import urllib.request
    base = os.environ.get("STUDIO_PROXY", "http://proxy:8780").rstrip("/")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={"content-type": "application/json",
                                          "x-api-key": os.environ.get("STUDIO_JOB_TOKEN")
                                          or os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
                                          or os.environ.get("ANTHROPIC_API_KEY", "")})     # the job's own token
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read())["error"]
        except Exception:      # noqa: BLE001
            err = {"code": "proxy", "message": f"proxy answered {e.code}"}
        raise StudioError(err.get("code") or err.get("type") or "proxy", err.get("message", ""), e.code) from None
    except urllib.error.URLError as e:
        raise StudioError("proxy", f"không gọi được bộ chuyển tiếp: {e.reason}", 503) from None


def _own(job_id: str) -> str:
    if job_id != os.environ["STUDIO_JOB"]:
        raise StudioError("invalid", "trong container chỉ ghi được việc của chính nó (STUDIO_JOB)", 422)
    return job_id


def remote_job(a) -> int:
    if a.action == "start":
        raise StudioError("invalid", "việc đã có sẵn: dùng mã trong STUDIO_JOB", 422)
    i = _own(a.id)
    if a.action == "step":
        prog = jobs.parse_progress(a.progress) if a.progress else None
        proxy_call("POST", f"/internal/jobs/{i}/step", {"text": a.text, "progress": prog})
    elif a.action == "log":
        proxy_call("POST", f"/internal/jobs/{i}/log", {"lines": [a.text]})
    elif a.action == "run":
        return job_run(a, remote=True)
    elif a.action == "done":
        proxy_call("POST", f"/internal/jobs/{i}/done", {"film": a.film, "style": a.style})
    elif a.action == "fail":
        proxy_call("POST", f"/internal/jobs/{i}/fail", {"text": a.text, "by": a.by or "studio"})
    else:
        raise StudioError("invalid", f"job {a.action} không dùng trong container", 422)
    return 0


def with_script(summary: str, a) -> str:
    """A treatment review shows the passed script and its scores too (specs/010 FR-019)."""
    if a.kind != "treatment" or not getattr(a, "film", None):
        return summary
    d = Path(a.film) if os.sep in a.film else Path(os.environ.get("STUDIO_WORK") or Path.cwd()) / "films" / a.film
    if not (d / "SCRIPT.md").is_file():
        d = Path(os.environ.get("STUDIO_ROOT") or Path(__file__).resolve().parents[2]) / "films" / a.film
    if not (d / "SCRIPT.md").is_file():
        return summary
    parts = [summary.rstrip(), "## Script", (d / "SCRIPT.md").read_text(encoding="utf-8").strip()]
    try:
        sc = json.loads((d / "checks.json").read_text(encoding="utf-8"))["script"]
        m = sc["machine"][-1]["score"] if sc.get("machine") else "–"
        e = sc["editor"][-1] if sc.get("editor") else {}
        parts += ["## Scores", f"- Machine check: {m}/10", f"- Editor: {e.get('score', '–')}/10 "
                  f"(P1 {e.get('p1', 0)}, P2 {e.get('p2', 0)}, P3 {e.get('p3', 0)}) · fix rounds: {sc.get('fix_rounds', 0)}"]
    except (OSError, ValueError, KeyError, IndexError):
        pass
    return "\n\n".join(parts) + "\n"


def remote_review(a) -> int:
    if a.action == "request":
        summary = with_script(Path(a.summary).read_text(encoding="utf-8"), a)
        r = proxy_call("POST", "/internal/reviews/request",
                       {"kind": a.kind, "set": a.set, "summary": summary, "final_round": a.final_round})
        Path(os.environ.get("STUDIO_WORK", ".")).joinpath(REVIEW_PENDING).write_text(r["id"])
        out(r["id"], "Review sent to the customer. End your turn now: the job resumes with their answer.")
        return 0
    if a.action == "wait":
        out("kết thúc lượt: thoát mã 10. The customer answers on the web; this session is resumed with the decision.")
        return 10
    if a.action == "status":
        out(json.dumps(proxy_call("GET", f"/internal/reviews/{a.id}"), ensure_ascii=False, indent=1))
        return 0
    raise StudioError("invalid", f"review {a.action} không dùng trong container", 422)


# ---------- the studio on this machine (specs/014) ----------
def cmd_app(a):
    from studio import host
    try:
        if a.action == "start":
            return host.start(a.data, a.web_port, a.proxy_port, a.foreground, out=out)
        if a.action == "status":
            s = host.status(a.data)
            if a.json:
                out(json.dumps(s, ensure_ascii=False))
            elif s["running"]:
                out(f"✓ running · {s['url']} · jobs running {s['jobs_running']}, queued {s['jobs_queued']}",
                    "  parts: " + ", ".join(f"{p} {'up' if ok else 'down'}" for p, ok in s["parts"].items()),
                    f"  data {s['data']} · logs {s['logs']}", f"URL: {s['url']}")
            else:
                out(f"✗ not running · data {s['data']}. Start: sh bin/studio app start")
            return 0 if s["running"] else 1
        if a.action == "stop":
            return host.stop(a.data, a.force, out=out)
        if a.action == "import":
            return host.import_project(a.data, Path(a.source).resolve() if a.source else PROJECT, out=out)
    except host.HostError as e:
        print(f"✗ {e}", file=sys.stderr)
        return e.code
    return 2


# ---------- admin (online mode, specs/007) ----------
def cmd_admin(a):
    from studio import accounts, store
    if store.mode() != "online":
        print("✗ chỉ dùng ở chế độ online: đặt STUDIO_MODE=online và STUDIO_DATA=<thư mục dữ liệu>", file=sys.stderr)
        return 1
    password = os.environ.get("STUDIO_ADMIN_PASSWORD")
    if not password:
        import getpass
        password = getpass.getpass("Mật khẩu quản trị (≥ 10 ký tự): ")
        if getpass.getpass("Nhập lại: ") != password:
            print("✗ hai lần nhập không khớp", file=sys.stderr)
            return 2
    accounts.signup(a.email, password, True, role="admin", verified=True)
    out(f"✓ đã tạo tài khoản quản trị {a.email.strip().lower()}")
    return 0


# ---------- review ----------
def cmd_review(a):
    if a.action == "request":
        summary = with_script(Path(a.summary).read_text(encoding="utf-8"), a)
        r = reviews.create(a.job, a.kind, a.set, summary, a.final_round)
        out(r["id"])
        u = ui_url(f"/#/reviews/{r['id']}")
        if u:
            out(f"URL: {u}")
        return 0
    if a.action == "wait":
        deadline = time.time() + a.timeout
        while True:
            d = reviews.poll(a.id)
            if d:
                reviews.resume(a.id, d)
                out(json.dumps(d, ensure_ascii=False))
                return 0
            if time.time() >= deadline:
                out("… chưa có quyết định; chạy lại lệnh này để chờ tiếp")
                return 3
            time.sleep(min(1.0, max(0.05, deadline - time.time())))
    if a.action == "decide":
        d = reviews.decide(a.id, a.value, a.note, a.source)
        out(json.dumps(d, ensure_ascii=False))
        return 0
    if a.action == "status":
        out(json.dumps(reviews.load(a.id), ensure_ascii=False, indent=1))
        return 0
    return 2


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="sh bin/studio")
    sub = p.add_subparsers(dest="group", required=True)

    u = sub.add_parser("ui", help="mở / xem / tắt giao diện")
    u.add_argument("action", nargs="?", default="open", choices=["open", "status", "stop"])
    u.set_defaults(fn=cmd_ui)

    j = sub.add_parser("job", help="sổ việc")
    js = j.add_subparsers(dest="action", required=True)
    s = js.add_parser("start"); s.add_argument("--kind", required=True, choices=sorted(jobs.KINDS))
    s.add_argument("--name", required=True); s.add_argument("--set"); s.add_argument("--film")
    s = js.add_parser("step"); s.add_argument("id"); s.add_argument("text"); s.add_argument("--progress")
    s = js.add_parser("log"); s.add_argument("id"); s.add_argument("text")
    s = js.add_parser("run"); s.add_argument("id"); s.add_argument("--step")
    s = js.add_parser("done"); s.add_argument("id"); s.add_argument("--style"); s.add_argument("--film")
    s = js.add_parser("fail"); s.add_argument("id"); s.add_argument("text")
    s.add_argument("--by", choices=["studio", "customer"], help="online: who caused the failure (FR-006a)")
    s = js.add_parser("stop"); s.add_argument("id")
    s = js.add_parser("show"); s.add_argument("id")
    j.set_defaults(fn=cmd_job)

    r = sub.add_parser("review", help="yêu cầu duyệt")
    rs = r.add_subparsers(dest="action", required=True)
    s = rs.add_parser("request"); s.add_argument("job"); s.add_argument("--kind", required=True, choices=sorted(reviews.KINDS))
    s.add_argument("--set", help="reference set (style-1, style-2)"); s.add_argument("--summary", required=True); s.add_argument("--final-round", action="store_true")
    s.add_argument("--film", help="treatment review: add the film's SCRIPT.md and its scores (specs/010)")
    s = rs.add_parser("wait"); s.add_argument("id"); s.add_argument("--timeout", type=float, default=540)
    s = rs.add_parser("decide"); s.add_argument("id"); s.add_argument("--value", required=True)
    s.add_argument("--note"); s.add_argument("--source", default="chat", choices=sorted(reviews.SOURCES))
    s = rs.add_parser("status"); s.add_argument("id")
    r.set_defaults(fn=cmd_review)

    ap = sub.add_parser("app", help="cả xưởng trên máy này, không cần Docker (specs/014)")
    aps = ap.add_subparsers(dest="action", required=True)
    s = aps.add_parser("start")
    s.add_argument("--data")
    s.add_argument("--web-port", type=int)
    s.add_argument("--proxy-port", type=int)
    s.add_argument("--foreground", action="store_true")
    s = aps.add_parser("status")
    s.add_argument("--data")
    s.add_argument("--json", action="store_true")
    s = aps.add_parser("stop")
    s.add_argument("--data")
    s.add_argument("--force", action="store_true")
    s = aps.add_parser("import")
    s.add_argument("--data")
    s.add_argument("--from", dest="source")
    ap.set_defaults(fn=cmd_app)

    ad = sub.add_parser("admin", help="tài khoản quản trị (chế độ online)")
    ads = ad.add_subparsers(dest="action", required=True)
    s = ads.add_parser("create"); s.add_argument("email")
    ad.set_defaults(fn=cmd_admin)

    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = []
    if "--" in argv:                       # job run <id> [--step …] -- <command…>
        i = argv.index("--")
        argv, cmd = argv[:i], argv[i + 1:]
    a = p.parse_args(argv)
    a.cmd = cmd
    if in_container() and a.group in ("job", "review"):
        a.fn = remote_job if a.group == "job" else remote_review
    try:
        return a.fn(a)
    except StudioError as e:
        print(f"✗ {e.message}", file=sys.stderr)
        return EXIT.get(e.code, 1)
    except FileNotFoundError as e:
        print(f"✗ không thấy tệp: {e.filename}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
