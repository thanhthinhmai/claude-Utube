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
