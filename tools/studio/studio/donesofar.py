"""The parts of a film already done, for the job page (specs/025). Read only, from the job's film folder; files only by
an allow list. Python standard library only."""
import json
import re
import time
import wave
from pathlib import Path

from . import store
from .store import StudioError

STEPS = [("script", "Script"), ("voice", "Voice"), ("shots", "Shots"), ("mix", "Mix"), ("render", "Render"),
         ("selfcheck", "Self-check"), ("publish", "Publish")]
ALLOWED = re.compile(r"^(SCRIPT\.md|SOURCES\.md|lines\.json|checks\.json|CHECKS\.md|voices/[lL]\d{2,4}\.wav|voices/dur\.json"
                     r"|out/mix\.wav|out/render\.mp4|\.check/review-r\d+\.json|\.check/labels\.json"
                     r"|\.check/shots/(sheet|label-sheet)-\d+\.jpg|\.check/shots/S\d{2,4}(~[A-Za-z0-9._~-]+)?\.jpg"
                     r"|scenes\.json|mix\.json|publish/pack\.json|publish/thumbnail-[123]\.(png|jpg)"
                     r"|cast/sheets/[a-z0-9-]{1,32}(\.prev)?/([a-z0-9-]{1,40}\.jpg|walk\.mp4|sheet\.json)"
                     r"|cast/voices/[a-z0-9-]{1,32}/[123]\.wav"
                     r"|animatic/(draft(\.prev)?\.mp4|clips/S\d{1,4}\.mp4|frames/S\d{1,4}\.jpg))$")   # 035: the animatic   # 036: voice samples of a character   # 034: cast sheets       # 026: scene table, mix settings, publish pack
# Never listed nor served, even if the allow list grows (specs/029 contracts/files.md): shot notes' pictures, the
# small-picture cache, the previous video and its shot marks
EXCLUDED = re.compile(r"^(shot-notes/|\.shots/|shots\.prev\.json$|[^/]*\.prev\.mp4$)")
TYPES = {".md": "text/markdown; charset=utf-8", ".json": "application/json", ".wav": "audio/wav", ".jpg": "image/jpeg",
         ".png": "image/png", ".mp4": "video/mp4"}
SHOT = re.compile(r"^S\d{2,4}\.jpg$")
EXTRA = re.compile(r"^S\d{2,4}~.+\.jpg$")
SHEET = re.compile(r"^sheet-(\d+)\.jpg$")
PARA = re.compile(r"^\[(P\d+)\]\s*(.*)$")
RENDER_HEAD = re.compile(r"^render: (\w+) · .*?(\d+) chunks .*?(\d+) workers")
RENDER_DONE = re.compile(r"^(\d+)/(\d+) chunks\b")
STILL_FOR = 5.0          # a mix file not touched for 5 s is finished
EXCERPT = 9


# ---------- where the film is ----------
def film_dir(job: dict):
    """The job's film folder (plan R1): film_dir written by the CLI or the worker, else films/<film>; None if missing."""
    if job.get("kind") != "film":
        return None
    d = job.get("film_dir")
    if d and Path(d).is_dir():
        return Path(d)
    name = (job.get("links") or {}).get("film")
    if not (name and re.fullmatch(r"[a-z0-9-]{1,60}", name)):
        return None
    # online a finished film is in its owner's folder (the studio owner may be the one looking); locally the project
    base = store.account_dir(job["owner"]) if store.mode() == "online" and job.get("owner") else store.root()
    p = base / "films" / name
    return p if p.is_dir() else None


def safe_path(base: Path, rel: str) -> Path:
    """A file of the film folder by its relative path; refuses .., absolute paths, links out and unlisted files."""
    if not rel or rel.startswith("/") or "\\" in rel or ".." in rel.split("/"):
        raise StudioError("bad_name", "đường dẫn không hợp lệ", 400)
    if EXCLUDED.match(rel) or not ALLOWED.match(rel):
        raise StudioError("not_found", "không xem được tệp này", 404)
    root = base.resolve()
    p = (base / rel).resolve()
    if not p.is_relative_to(root):
        raise StudioError("bad_name", "đường dẫn không hợp lệ", 400)
    if not p.is_file():
        raise StudioError("not_found", "không có tệp", 404)
    return p


def content_type(rel: str) -> str:
    return TYPES[Path(rel).suffix]


# ---------- reading ----------
def _json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _mtime(*ps) -> str:
    m = 0.0
    for p in ps:
        try:
            m = max(m, p.stat().st_mtime)
        except OSError:
            pass
    return f"{m:.3f}"


def _wav_seconds(p: Path):
    try:
        with wave.open(str(p)) as w:
            return round(w.getnframes() / float(w.getframerate()), 2)
    except (OSError, wave.Error, EOFError, ZeroDivisionError):
        return None


def _script(d: Path, checks: dict) -> dict:
    s = (checks or {}).get("script") or {}
    text = (d / "SCRIPT.md").read_text(encoding="utf-8", errors="replace") if (d / "SCRIPT.md").is_file() else ""
    title, target, paras, excerpt, pending = None, None, [], [], []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Title:"):
            title = line[6:].strip()
        elif line.startswith("Target:"):
            m = re.search(r"\d+", line)
            target = int(m.group()) if m else None
        elif line.startswith(">"):
            pending.append(line.lstrip("> ").strip())
        elif PARA.match(line):
            pid, body = PARA.match(line).groups()
            paras.append(body)
            if len([x for x in excerpt if x["kind"] == "para"]) < EXCERPT:
                excerpt += [{"kind": "dir", "text": t} for t in pending] + [{"kind": "para", "id": pid, "text": body}]
            pending = []
    src = (d / "SOURCES.md").read_text(encoding="utf-8", errors="replace") if (d / "SOURCES.md").is_file() else ""
    rounds = sorted(int(m.group(1)) for f in (d / ".check").glob("review-r*.json")
                    if (m := re.fullmatch(r"review-r(\d+)\.json", f.name)))
    machine = (s.get("machine") or [{}])[-1].get("score") if s.get("machine") else None
    ed = (s.get("editor") or [{}])[-1] if s.get("editor") else {}
    return {"version": _mtime(d / "SCRIPT.md", d / "SOURCES.md", d / "checks.json"),
            "title": title, "target_seconds": target, "paragraphs": len(paras),
            "words": sum(len(p.split()) for p in paras), "excerpt": excerpt,
            "sources": len(set(re.findall(r"https?://[^\s,)>\]]+", src))),     # distinct links (a line is one claim)
            "machine": machine, "editor": {"score": ed.get("score"), "fix_rounds": s.get("fix_rounds"), "model": ed.get("model")}
            if ed else None, "verdict": s.get("verdict"), "rounds": rounds}


def narrator_voice(d: Path, lines: list) -> dict:
    """{voice, speed} of the narrator as `voice make` reads it (specs/036 FR-041: the summary and the Voice picker show
    the same voice): the resolved speaker table, else the first narrator line as written."""
    rows = [x for x in lines if isinstance(x, dict) and x.get("id")]
    try:
        from filmcheck import speakers
        st = ((speakers.resolve(d, rows, store.root())["speakers"].get("narrator") or {}).get("setting")) or {}
    except Exception:                       # noqa: BLE001 — the page still opens with a damaged file
        st = {}
    first = next((x for x in rows if (x.get("speaker") or "narrator") == "narrator"), rows[0] if rows else {})
    voice = first.get("voice") or st.get("voice")
    speed = first.get("speed") if first.get("voice") else st.get("speed", first.get("speed"))
    return {"voice": voice, "speed": speed}


def _voice(d: Path, lines, tiers: dict) -> dict:
    lines = lines if isinstance(lines, list) else []
    first = narrator_voice(d, lines)
    paras = list(dict.fromkeys(x.get("para") for x in lines if x.get("para")))
    return {"version": _mtime(d / "lines.json", d / "voices" / "dur.json", d / "checks.json"),
            "lines": len(lines), "voice": first.get("voice"), "speed": first.get("speed"),
            "pass": (tiers.get("voice") or {}).get("pass"), "respelled": sum(1 for x in lines if x.get("say")),
            "paras": paras}


def _shots(d: Path, tiers: dict, checks: dict) -> dict:
    sd = d / ".check" / "shots"
    names = [f.name for f in sd.iterdir()] if sd.is_dir() else []
    sheets = sorted(int(m.group(1)) for n in names if (m := SHEET.match(n)))
    sh = tiers.get("shots") or {}
    return {"version": _mtime(sd / "sheet-1.jpg", d / ".check" / "labels.json", d / "checks.json"),
            "shots": sum(1 for n in names if SHOT.match(n)), "extras": sum(1 for n in names if EXTRA.match(n)),
            "sheets": len(sheets), "plan_pass": (tiers.get("plan") or {}).get("pass"), "shots_pass": sh.get("pass"),
            "accepted": (sh.get("style_accept") or {}).get("reason"),
            "warnings": sum(1 for i in sh.get("issues") or [] if i.get("severity") == "warn"),
            "labels": (d / ".check" / "labels.json").is_file()}


def _render(d: Path) -> dict:
    log = d / "out" / "render.log"
    mode = total = workers = None
    done = 0
    try:
        for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
            if m := RENDER_HEAD.match(line):
                mode, total, workers, done = m.group(1), int(m.group(2)), int(m.group(3)), 0
            elif (m := RENDER_DONE.match(line)) and total and int(m.group(2)) == total:
                done = int(m.group(1))
            elif line.startswith("video ") and total:
                done = total
    except OSError:
        pass
    return {"version": _mtime(log), "chunks_done": done, "chunks_total": total, "mode": mode, "workers": workers}


# ---------- summary ----------
def summary(job: dict) -> dict:
    d = film_dir(job)
    if d is None:
        return {"film": None, "steps": [], "sections": {}}
    checks = _json(d / "checks.json") or {}
    tiers = checks.get("tiers") or {}
    lines = _json(d / "lines.json")
    step = job.get("step") or ""
    running_steps = {r.get("step") for r in (job.get("runs") or {}).values()} | ({step} if job.get("status") == "running" else set())
    name = d.name
    narr = (checks.get("script") or {}).get("verdict") != "skipped"
    st, sections = {}, {}

    sv = (checks.get("script") or {}).get("verdict")
    has_script = (d / "SCRIPT.md").is_file()
    st["script"] = "none" if not narr else "done" if sv == "pass" or (has_script and not checks.get("script")) else \
        "running" if "Script" in running_steps or has_script else "waiting"
    if narr and has_script:
        sections["script"] = _script(d, checks)

    voices = d / "voices"
    has_voices = voices.is_dir() and any(voices.glob("l*.wav"))
    st["voice"] = "none" if not narr else "done" if (tiers.get("voice") or {}).get("pass") else \
        "running" if "Voice" in running_steps or has_voices else "waiting"
    if narr and (lines or has_voices):
        sections["voice"] = _voice(d, lines, tiers)

    sheet = d / ".check" / "shots" / "sheet-1.jpg"
    st["shots"] = "done" if sheet.is_file() and tiers.get("shots") else \
        "running" if running_steps & {"Storyboard", "Picture"} or sheet.is_file() else "waiting"
    if sheet.is_file():
        sections["shots"] = _shots(d, tiers, checks)

    mix = d / "out" / "mix.wav"
    if mix.is_file():
        busy = "Mix" in running_steps and time.time() - mix.stat().st_mtime < STILL_FOR
        st["mix"] = "running" if busy else "done"
        if not busy:
            sections["mix"] = {"version": _mtime(mix), "seconds": _wav_seconds(mix)}
    else:
        st["mix"] = "running" if "Mix" in running_steps else "waiting"

    video = next((p for p in (d / f"{name}.mp4", d / "out" / "video.mp4") if p.is_file()), None)
    rlog = d / "out" / "render.log"
    r = _render(d) if rlog.is_file() else None
    log_newer = r and video and rlog.stat().st_mtime > video.stat().st_mtime + 1
    if video and (tiers.get("render") or {}).get("pass") and "Render" not in running_steps and not log_newer:
        st["render"] = "done"
    elif "Render" in running_steps or (r and r["chunks_total"]):
        st["render"] = "running"
    else:
        st["render"] = "waiting"
    if r:
        if st["render"] == "done" and r["chunks_total"]:
            r["chunks_done"] = r["chunks_total"]
        sections["render"] = r

    st["selfcheck"] = "done" if tiers.get("final") else "running" if "Self-check" in running_steps else "waiting"
    st["publish"] = "done" if (d / "publish" / "pack.json").is_file() and checks.get("publish") else \
        "running" if "Publish" in running_steps else "waiting"

    order = list(STEPS)
    try:                                           # specs/034: an AE film's characters, between Script and Voice
        from filmcheck import cast
        if cast.is_ae(d) and cast.exists(d) and cast.load(d)["characters"]:
            st["cast"] = "done" if cast.all_approved(d) else "running" if "Cast" in running_steps else "waiting"
            order.insert(1, ("cast", "Cast"))
            cst = cast.states(d)
            sections["cast"] = {"version": cast.fingerprint(d) + ":" + ",".join(f"{k}={v}" for k, v in sorted(cst.items()))
                                + ":" + ",".join(f"{k}={v}" for k, v in sorted(cast.open_notes(d).items())),
                                "characters": len(cst), "approved": sum(1 for v in cst.values() if v == "approved")}
    except Exception:                              # noqa: BLE001 — a broken cast.json shows on the Cast panel
        pass
    try:                                           # specs/035: an AE film's animatic, after Voice; no Shots step
        from filmcheck import cast, timing
        if cast.is_ae(d):
            order = [(k, {"mix": "Sound", "render": "Final render"}.get(k, l)) for k, l in order if k != "shots"]
            if timing.load(d) is not None:
                import hashlib
                a = d / "animatic"
                h = hashlib.sha256(timing.base(d).encode())
                for f in ("draft.json", "fit.json", "notes.json"):
                    h.update((a / f).read_bytes() if (a / f).is_file() else b"-")
                st["animatic"] = "done" if (a / "draft.mp4").is_file() else \
                    "running" if "Animatic" in running_steps else "waiting"
                order.insert([k for k, _ in order].index("voice") + 1, ("animatic", "Animatic"))
                sections["animatic"] = {"version": h.hexdigest()[:16]}
    except Exception:                              # noqa: BLE001 — a broken timing.json shows on the Animatic panel
        pass
    steps = []
    for key, label in order:
        s = {"key": key, "label": label, "state": st[key]}
        if key == "render" and st[key] == "running" and r and r["chunks_total"]:
            s["progress"] = {"done": r["chunks_done"], "total": r["chunks_total"]}
        steps.append(s)
    return {"film": name, "steps": steps, "sections": sections}


def file(job: dict, rel: str) -> Path:
    d = film_dir(job)
    if d is None:
        raise StudioError("not_found", "không có phim", 404)
    return safe_path(d, rel)

