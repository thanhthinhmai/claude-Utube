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


def job_run(a) -> int:
    cmd = a.cmd
    if not cmd:
        raise StudioError("invalid", "thiếu lệnh sau --", 422)
    jobs.load(a.id)
    if a.step:
        jobs.step(a.id, a.step)
    tail = collections.deque(maxlen=50)
    beat = float(os.environ.get("STUDIO_HEARTBEAT", "30"))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    done = threading.Event()

    def heartbeat():
        while not done.wait(beat):
            try:
                jobs.heartbeat(a.id)
            except StudioError:
                pass
    threading.Thread(target=heartbeat, daemon=True).start()
    for line in p.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        text = line.rstrip("\n")
        # the log keeps the command's output, not tool notes ("[note] WebGL …") or a line repeated right after itself
        if text.startswith("[note] ") or (tail and tail[-1] == text):
            continue
        tail.append(text)
    rc = p.wait()
    done.set()
    jobs.log(a.id, *tail, f"(command exited with code {rc})")
    return rc


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
        summary = Path(a.summary).read_text(encoding="utf-8")
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
    s = js.add_parser("stop"); s.add_argument("id")
    s = js.add_parser("show"); s.add_argument("id")
    j.set_defaults(fn=cmd_job)

    r = sub.add_parser("review", help="yêu cầu duyệt")
    rs = r.add_subparsers(dest="action", required=True)
    s = rs.add_parser("request"); s.add_argument("job"); s.add_argument("--kind", required=True, choices=sorted(reviews.KINDS))
    s.add_argument("--set", required=True); s.add_argument("--summary", required=True); s.add_argument("--final-round", action="store_true")
    s = rs.add_parser("wait"); s.add_argument("id"); s.add_argument("--timeout", type=float, default=540)
    s = rs.add_parser("decide"); s.add_argument("id"); s.add_argument("--value", required=True)
    s.add_argument("--note"); s.add_argument("--source", default="chat", choices=sorted(reviews.SOURCES))
    s = rs.add_parser("status"); s.add_argument("id")
    r.set_defaults(fn=cmd_review)

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
