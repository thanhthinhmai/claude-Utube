"""Bring reference videos into references/<set>/videos/ (research.md §1)."""
import re
import shutil
from pathlib import Path

from . import refset
from .refset import StepError, UsageError

NOTICE = ("Lưu ý: video tham chiếu chỉ để học phong cách trong máy này. Không đăng lại, không gửi đi. "
          "Bạn chịu trách nhiệm về quyền sử dụng nội dung tải về.")


def audio_original(info: dict, afmt: dict):
    """True when the chosen audio is the original track: marked "original", or the video has only one audio
    language (nothing was dubbed). None when there are several languages and none is marked."""
    if "original" in (afmt.get("format_note") or "").lower():
        return True
    langs = {f.get("language") for f in (info.get("formats") or [])
             if f.get("vcodec") == "none" and f.get("acodec") not in (None, "none") and f.get("language")}
    return True if len(langs) <= 1 else None


VIDEO_ID = re.compile(r"(?:v=|/shorts/|youtu\.be/|/live/)([A-Za-z0-9_-]+)")


def video_id(url: str):
    m = VIDEO_ID.search(url or "")
    return m.group(1) if m else None


def list_videos(ydl, url: str, limit: int) -> list:
    """Video URLs of a channel or playlist, in listing order, at most `limit`. Tabs and nested playlists
    (a channel home page lists Videos, then Shorts…) are opened in order until enough videos are found."""
    out = []

    def walk(info, depth=0):
        for e in (info or {}).get("entries") or []:
            if len(out) >= limit or not e:
                return
            nested = e.get("_type") == "playlist" or e.get("ie_key") == "YoutubeTab" or "entries" in e
            if nested and depth < 3:
                walk(e if "entries" in e else ydl.extract_info(e.get("url") or e.get("webpage_url"), download=False), depth + 1)
            else:
                u = e.get("webpage_url") or e.get("url")
                if u and u not in out:
                    out.append(u)
    walk(ydl.extract_info(url, download=False))
    return out


def check_count(n: int) -> int:
    if not 3 <= n <= 30:
        raise UsageError("--count phải trong khoảng 3–30")
    return n


def _open(name: str, kind: str, inputs, max_seconds, deny) -> dict:
    try:
        data = refset.load(name)
        data["deny"] = sorted(set(data.get("deny", [])) | set(deny))
        data["source"]["inputs"] += [str(i) for i in inputs]
        if data["source"]["kind"] != kind:
            data["source"]["kind"] = "mixed"
    except StepError:
        data = refset.new_set(name, kind, [str(i) for i in inputs], max_seconds, deny)
    (refset.set_dir(name) / "videos").mkdir(parents=True, exist_ok=True)
    return data


def fetch_files(name: str, files, max_seconds: float = 180, deny=(), log=print) -> dict:
    files = [Path(f) for f in files]
    for f in files:
        if not f.is_file():
            raise UsageError(f"không thấy file: {f}")
    data = _open(name, "files", [], max_seconds, deny)
    vdir = refset.set_dir(name) / "videos"
    known = {(v.get("src_name"), v.get("src_size")) for v in data["videos"]}
    for f in files:
        key = (f.name, f.stat().st_size)
        if key in known:
            log(f"= đã có {f.name}")
            continue
        vid = refset.next_id(data)
        dst = vdir / f"{vid}{f.suffix.lower() or '.mp4'}"
        if f.resolve() != dst.resolve():
            shutil.copy2(f, dst)
        data["videos"].append({"id": vid, "file": dst.name, "origin": "local", "src_name": f.name, "src_size": key[1],
                               "title": None, "channel": None, "audio_language": "unknown", "state": "fetched",
                               "source_sig": refset.source_sig(dst)})
        known.add(key)
        log(f"✓ {vid} ← {f.name}")
    refset.save(name, data)
    return data


def fetch_urls(name: str, kind: str, urls, count: int = 12, max_seconds: float = 180, deny=(), log=print) -> dict:
    try:
        import yt_dlp
    except ImportError:
        raise StepError("chưa cài yt-dlp. Chạy: sh bin/studio deps learn --extra\n"
                        f"  Hoặc tự đặt video vào references/{name}/videos/ rồi chạy: sh bin/studio learn fetch {name} --files <file…>")
    if kind == "channel":
        check_count(count)
    data = _open(name, kind, urls, max_seconds, deny)
    vdir = refset.set_dir(name) / "videos"
    have = {v.get("origin") for v in data["videos"]}
    have_ids = {v.get("source_id") or video_id(v.get("origin")) for v in data["videos"]} - {None}
    what = f"{count} video gần nhất của kênh" if kind == "channel" else f"{len(urls)} video"
    log(f"↓ sẽ tải {what} (≤ 720p, ưu tiên tiếng gốc) từ: {', '.join(urls)}")
    log(NOTICE)
    opts = {"outtmpl": str(vdir / "dl_%(id)s.%(ext)s"), "format": "bv*[height<=720]+ba/b[height<=720]/b",
            "merge_output_format": "mp4", "writeinfojson": False, "quiet": True, "no_warnings": True,
            "noprogress": True, "ignoreerrors": True}
    infos = []
    try:
        if kind == "channel":
            # List first, then download exactly `count` videos. A channel's home page is a playlist of tabs
            # (Videos, Shorts…): downloading it directly fetched `count` per tab and returned tabs, not videos.
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "ignoreerrors": True,
                                   "extract_flat": "in_playlist"}) as lister:
                urls = list_videos(lister, urls[0], count)
            if not urls:
                raise StepError("không liệt kê được video nào của kênh (link sai, kênh trống, hoặc bị chặn)")
            log(f"  chọn {len(urls)} video: " + ", ".join(urls))
        todo = [u for u in urls if video_id(u) not in have_ids]
        if len(todo) < len(urls):
            log(f"= {len(urls) - len(todo)} video đã có, bỏ qua")
        with yt_dlp.YoutubeDL(opts) as ydl:
            for u in todo:
                info = ydl.extract_info(u, download=True)
                if info:
                    infos += [e for e in (info.get("entries") or [info]) if e]
    except StepError:
        raise
    except Exception as e:  # network blocked, platform refused, …
        raise StepError(f"không tải được ({str(e).splitlines()[0][:160]}).\n"
                        f"  Nếu môi trường chặn nền tảng video: tải trên máy khác, đặt vào references/{name}/videos/ rồi dùng --files")
    if not infos and todo:
        raise StepError(f"không tải được video nào. Có thể đặt file vào references/{name}/videos/ rồi dùng --files")
    for info in infos:
        url = info.get("webpage_url") or info.get("original_url")
        if url in have:
            continue
        reqs = info.get("requested_downloads") or []
        src = Path(reqs[0]["filepath"]) if reqs and reqs[0].get("filepath") else None
        if not src or not src.exists():
            continue
        vid = refset.next_id(data)
        dst = vdir / f"{vid}{src.suffix}"
        src.rename(dst)
        afmt = next((f for f in (info.get("requested_formats") or []) if f.get("vcodec") == "none"), {}) or {}
        lang = afmt.get("language") or info.get("language") or "unknown"
        data["videos"].append({
            "id": vid, "file": dst.name, "origin": url, "source_id": info.get("id") or video_id(url), "title": info.get("title"),
            "channel": info.get("channel") or info.get("uploader"),
            "handle": info.get("uploader_id") or info.get("channel_id"),
            "audio_language": lang, "audio_original": audio_original(info, afmt),
            "state": "fetched", "source_sig": refset.source_sig(dst)})
        log(f"✓ {vid} ← {info.get('title', '')[:60]}")
    refset.save(name, data)
    return data


# ---------------------------------------------------------------- refetch (specs/023 research R1)

MATCH_S = 1.0          # a downloaded video matches a known one when their lengths differ by at most this
MATCH_DE = 12.0        # … and its mid-shot frames look like the kept shot-sheet cells (mean ΔE Lab)


def length_candidates(videos: list, dur: float) -> list:
    """Known videos whose length is within MATCH_S of dur and that have no file on disk."""
    return [v for v in videos if v.get("duration") and abs(float(v["duration"]) - dur) <= MATCH_S]


def frame_at(path: Path, t: float, size=(200, 112)):
    import subprocess
    import numpy as np
    w, h = size
    out = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1",
                          "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(out, np.uint8).reshape(h, w, 3) if len(out) == w * h * 3 else None


def looks_like(name: str, vid: str, path: Path, n: int = 5):
    """Mean ΔE between frames of `path` at the middle of n shots of `vid` and their shot-sheet cells; None if the
    video has no kept shots to compare with."""
    import json
    import numpy as np
    from . import color, template
    f = refset.profile_dir(name, vid) / "shots.json"
    if not f.exists():
        return None
    shots = [s for s in json.loads(f.read_text(encoding="utf-8")).get("shots", []) if s.get("evidence") and s.get("mid")]
    if not shots:
        return None
    pick = [shots[int(i)] for i in np.linspace(0, len(shots) - 1, min(n, len(shots)))]
    des = []
    for s in pick:
        fr = frame_at(path, float(s["mid"]))
        if fr is None:
            continue
        ref = np.asarray(template.cell(name, s["evidence"]), np.uint8)
        des.append(float(np.mean(np.linalg.norm(color.to_lab(fr.reshape(-1, 3)) - color.to_lab(ref.reshape(-1, 3)), axis=1))))
    return round(float(np.mean(des)), 2) if des else None


def probe_duration(path: Path) -> float:
    import subprocess
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True).stdout.strip()
    return float(r) if r else 0.0


def place(name: str, data: dict, src: Path, url: str, log=print):
    """Put a downloaded file in place of the known video it matches. Returns the video id or None."""
    dur = probe_duration(src)
    vdir = refset.set_dir(name) / "videos"
    free = [v for v in data["videos"] if not (vdir / v["file"]).exists()]
    cands = length_candidates(free, dur)
    scored = [(looks_like(name, v["id"], src), v) for v in cands]
    framed = [(d, v) for d, v in scored if d is not None]
    if framed:                                   # kept shot frames decide: the closest one under MATCH_DE
        ok = sorted([(d, v) for d, v in framed if d <= MATCH_DE], key=lambda x: x[0])
        cands = [ok[0][1]] if ok else []
    elif len(cands) != 1:                        # nothing to compare with: only an unambiguous length will do
        cands = []
    if not cands:
        log(f"✗ {url}: {dur:.1f} s không khớp video nào của bộ (độ dài ±{MATCH_S:g} s, khung ΔE ≤ {MATCH_DE:g})")
        return None
    v = cands[0]
    dst = vdir / v["file"]
    src.rename(dst)
    v["url"] = v["origin"] = url
    v["source_sig"] = refset.source_sig(dst)
    log(f"✓ {v['id']} ← {url} ({dur:.1f} s)")
    return v["id"]


def refetch(name: str, urls, log=print) -> int:
    """Download reference videos again into the same vNN, so shot ids, labels and evidence stay valid."""
    data = refset.load(name)
    vdir = refset.set_dir(name) / "videos"
    vdir.mkdir(parents=True, exist_ok=True)
    try:
        import yt_dlp
    except ImportError:
        raise StepError("chưa cài yt-dlp. Chạy: sh bin/studio deps learn --extra")
    log(NOTICE)
    opts = {"outtmpl": str(vdir / "re_%(id)s.%(ext)s"), "format": "bv*[height<=720]+ba/b[height<=720]/b",
            "merge_output_format": "mp4", "quiet": True, "no_warnings": True, "noprogress": True, "ignoreerrors": True}
    missed = 0
    with yt_dlp.YoutubeDL(opts) as ydl:
        for u in urls:
            info = ydl.extract_info(u, download=True)
            reqs = (info or {}).get("requested_downloads") or []
            src = Path(reqs[0]["filepath"]) if reqs and reqs[0].get("filepath") else None
            if not src or not src.exists():
                log(f"✗ {u}: không tải được")
                missed += 1
                continue
            if not place(name, data, src, u, log):
                src.unlink(missing_ok=True)
                missed += 1
            refset.save(name, data)
    have = sum((vdir / v["file"]).exists() for v in data["videos"])
    log(f"→ {have}/{len(data['videos'])} video của bộ đã có trên máy")
    return 1 if missed else 0
