"""Bring reference videos into references/<set>/videos/ (research.md §1)."""
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
    what = f"{count} video gần nhất của kênh" if kind == "channel" else f"{len(urls)} video"
    log(f"↓ sẽ tải {what} (≤ 720p, ưu tiên tiếng gốc) từ: {', '.join(urls)}")
    log(NOTICE)
    opts = {"outtmpl": str(vdir / "dl_%(id)s.%(ext)s"), "format": "bv*[height<=720]+ba/b[height<=720]/b",
            "merge_output_format": "mp4", "writeinfojson": False, "quiet": True, "no_warnings": True,
            "noprogress": True, "ignoreerrors": True}
    if kind == "channel":
        opts["playlistend"] = count
    infos = []
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            for u in urls:
                info = ydl.extract_info(u, download=True)
                if info is None:
                    continue
                infos += [e for e in (info.get("entries") or [info]) if e]
    except Exception as e:  # network blocked, platform refused, …
        raise StepError(f"không tải được ({str(e).splitlines()[0][:160]}).\n"
                        f"  Nếu môi trường chặn nền tảng video: tải trên máy khác, đặt vào references/{name}/videos/ rồi dùng --files")
    if not infos:
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
            "id": vid, "file": dst.name, "origin": url, "title": info.get("title"),
            "channel": info.get("channel") or info.get("uploader"),
            "handle": info.get("uploader_id") or info.get("channel_id"),
            "audio_language": lang, "audio_original": audio_original(info, afmt),
            "state": "fetched", "source_sig": refset.source_sig(dst)})
        log(f"✓ {vid} ← {info.get('title', '')[:60]}")
    refset.save(name, data)
    return data
