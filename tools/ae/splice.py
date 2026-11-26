"""Splice rebuilt shots into a film's video, frame-exact, in one encode (specs/032 R5; from fixshots.sh).

marks: the film's shots.json rows [t0, t1, set, id]. pieces: {shot id: (clip, start second in the clip)}; a build
of several shots renders them back to back in one MASTER, so each piece is an offset into that clip. Every frame
outside the rebuilt shots is copied from the old video at the same frame number; the audio is copied as it is."""
import json
import subprocess
from pathlib import Path


class SpliceError(Exception):
    pass


def probe(video) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate,nb_frames:format=duration", "-of", "json", str(video)],
                       capture_output=True, text=True)
    if r.returncode:
        raise SpliceError(f"cannot read video {video}: {r.stderr.strip()[:200]}")
    j = json.loads(r.stdout)
    s = j["streams"][0]
    n, dd = s["r_frame_rate"].split("/")
    return {"w": s["width"], "h": s["height"], "fps": float(n) / float(dd), "fps_text": s["r_frame_rate"],
            "duration": float(j["format"]["duration"])}


def has_audio(video) -> bool:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0",
                        str(video)], capture_output=True, text=True)
    return bool(r.stdout.strip())


def plan(marks: list, pieces: dict, fps: float, total_frames: int) -> list:
    """Segments in film order: ("old", f0, f1) or ("new", shot, clip index, frames offset, frame count)."""
    rows = sorted(marks, key=lambda r: r[0])
    ids = [r[3] for r in rows]
    missing = [s for s in pieces if s not in ids]
    if missing:
        raise SpliceError(f"shot not in shots.json: {', '.join(missing)}")
    segs, cur = [], 0
    clips = {}
    for r in rows:
        if r[3] not in pieces:
            continue
        f0, f1 = round(r[0] * fps), round(r[1] * fps)
        if f0 > cur:
            segs.append(("old", cur, f0))
        clip, off = pieces[r[3]]
        ci = clips.setdefault(str(clip), len(clips) + 1)
        segs.append(("new", r[3], ci, round(off * fps), f1 - f0))
        cur = f1
    if cur < total_frames:
        segs.append(("old", cur, total_frames))
    return segs, clips


def splice(video, marks: list, pieces: dict, out, crf: int = 21) -> dict:
    v = probe(video)
    fps, ft = v["fps"], v["fps_text"]
    total = round(v["duration"] * fps)
    segs, clips = plan(marks, pieces, fps, total)
    parts, labels = [], []
    for i, s in enumerate(segs):
        lab = f"s{i}"
        if s[0] == "old":
            parts.append(f"[0:v]trim=start_frame={s[1]}:end_frame={s[2]},setpts=N/({ft})/TB[{lab}]")
        else:
            _, shot, ci, off, n = s
            parts.append(f"[{ci}:v]scale={v['w']}:{v['h']},fps={ft},setsar=1,tpad=stop_mode=clone:stop_duration=10,trim=start_frame={off}:end_frame={off + n},"
                         f"setpts=N/({ft})/TB[{lab}]")
        labels.append(f"[{lab}]")
    parts.append(f"{''.join(labels)}concat=n={len(labels)}:v=1:a=0,fps={ft}[v]")
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(video)]
    for clip in clips:
        cmd += ["-i", clip]
    cmd += ["-filter_complex", ";".join(parts), "-map", "[v]"]
    if has_audio(video):
        cmd += ["-map", "0:a", "-c:a", "copy"]
    cmd += ["-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast", "-pix_fmt", "yuv420p", str(out)]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SpliceError(f"ffmpeg failed: {r.stderr.strip()[-400:]}")
    return {"out": str(out), "frames": total, "replaced": [s[1] for s in segs if s[0] == "new"]}


def pieces_from_master(master, master_marks: list, shots: list) -> dict:
    """Offsets of each built shot inside the MASTER clip, from the build's own shots_<proj>.json rows."""
    by = {r[3]: r for r in master_marks}
    lost = [s for s in shots if s not in by]
    if lost:
        raise SpliceError(f"the build did not make: {', '.join(lost)}")
    return {s: (str(master), by[s][0]) for s in shots}



def segment(clip, start_s: float, frames: int, out, size=(480, 270), fps_text: str = None, crf: int = 23) -> Path:
    """specs/035 R7: one shot of a built clip as its own video segment (no sound), encoded once, so a draft made of
    segments copies a shot that was not rebuilt bit for bit."""
    src = probe(clip)
    ft = fps_text or src["fps_text"]
    o = round(start_s * src["fps"])
    w, h = size
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    part = out.with_name(out.stem + ".part.mp4")
    seek = max(0.0, (o - 0.5) / src["fps"])        # start decoding at the shot (half a frame early: frame o is the first)
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{seek:.6f}", "-i", str(clip), "-vf",
           f"scale={w}:{h},fps={ft},setsar=1,tpad=stop_mode=clone:stop_duration=10,trim=end_frame={frames},"
           f"setpts=N/({ft})/TB", "-an", "-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast", "-pix_fmt", "yuv420p",
           "-r", ft, "-video_track_timescale", "15360", str(part)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SpliceError(f"ffmpeg failed: {r.stderr.strip()[-400:]}")
    part.replace(out)
    return out


def by_shot(segments: list, out) -> dict:
    """specs/035 R7: the draft's picture as the shot segments back to back, copied (no new encode): a shot that was
    not rebuilt keeps its exact frames even when an earlier shot changed length. segments: [(shot, path)] in order."""
    missing = [s for s, p in segments if not Path(p).is_file()]
    if missing:
        raise SpliceError(f"no segment for {', '.join(missing)}: rebuild those shots")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    lst = out.with_name(out.stem + ".list.txt")
    lst.write_text("".join(f"file '{Path(p).resolve().as_posix()}'\n" for _, p in segments))
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                        "-an", str(out)], capture_output=True, text=True)
    lst.unlink(missing_ok=True)
    if r.returncode:
        raise SpliceError(f"ffmpeg failed: {r.stderr.strip()[-400:]}")
    return {"out": str(out), "shots": [s for s, _ in segments]}


def assemble(segments: list, out, fps: int, size, transitions: dict = None, crf: int = 18) -> dict:
    """specs/038 T016: a mixed film's picture from shot pieces of either engine, frame-exact, in one encode.

    segments: [{"shot", "clip", "start" (seconds into the clip), "frames"}] in film order (AE shots point into the
    MASTER at their offset, Blender shots into their own S<n>.mp4 at 0). Each piece gives exactly `frames` frames
    (a short clip holds its last frame). transitions: {shot: "cut"|"fade"|"dip"}, how that shot is entered:
    dip fades the end of the shot before it to black and the shot in from black; fade dissolves from the last frame of
    the shot before it. Neither changes a shot's length, so every shot keeps its timing.json frames."""
    if not segments:
        raise SpliceError("nothing to assemble")
    transitions = transitions or {}
    w, h = int(size[0]), int(size[1])
    ft = str(int(fps)) if float(fps).is_integer() else str(fps)
    td = max(2, round(0.4 * float(fps)))                # transition frames
    clips, parts = {}, []
    for i, s in enumerate(segments):
        if not Path(s["clip"]).is_file():
            raise SpliceError(f"{s['shot']}: clip not found {s['clip']}")
        ci = clips.setdefault(str(s["clip"]), len(clips))
        n = int(s["frames"])
        off = round(float(s.get("start") or 0) * float(fps))
        chain = (f"[{ci}:v]scale={w}:{h},fps={ft},setsar=1,format=yuv420p,tpad=stop_mode=clone:stop_duration=10,"
                 f"trim=start_frame={off}:end_frame={off + n},setpts=N/({ft})/TB")
        nxt = transitions.get(segments[i + 1]["shot"]) if i + 1 < len(segments) else None
        here = transitions.get(s["shot"]) if i else None
        k = min(td, max(1, n // 3))
        if here == "dip":
            chain += f",fade=t=in:st=0:d={k / float(fps):.4f}"
        if nxt == "dip":
            chain += f",fade=t=out:st={(n - k) / float(fps):.4f}:d={k / float(fps):.4f}"
        parts.append(chain + f"[p{i}]")
    cur = "p0"
    total = int(segments[0]["frames"])
    for i in range(1, len(segments)):
        n = int(segments[i]["frames"])
        lab = f"j{i}"
        if transitions.get(segments[i]["shot"]) == "fade":
            k = min(td, max(1, n // 3))
            # the shot before holds its last frame k frames longer and B dissolves over it: xfade's output is
            # (total + k) + n - k frames, so the film keeps the sum of the shots and B starts on its own frame
            parts.append(f"[{cur}]tpad=stop_mode=clone:stop={k},fps={ft},settb=1/{ft}[h{i}]")
            parts.append(f"[p{i}]fps={ft},settb=1/{ft}[q{i}]")
            parts.append(f"[h{i}][q{i}]xfade=transition=fade:duration={k / float(fps):.4f}:offset={total / float(fps):.4f}"
                         f"[{lab}]")
        else:
            parts.append(f"[{cur}][p{i}]concat=n=2:v=1:a=0,fps={ft}[{lab}]")
        cur, total = lab, total + n
    parts.append(f"[{cur}]fps={ft},setpts=N/({ft})/TB[v]")
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for c in clips:
        cmd += ["-i", c]
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd += ["-filter_complex", ";".join(parts), "-map", "[v]", "-frames:v", str(total), "-an", "-c:v", "libx264",
            "-crf", str(crf), "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", ft, str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SpliceError(f"ffmpeg failed: {r.stderr.strip()[-400:]}")
    marks, t = [], 0
    for s in segments:
        n = int(s["frames"])
        marks.append([round(t / float(fps), 4), round((t + n) / float(fps), 4), s.get("set") or "", s["shot"]])
        t += n
    return {"out": str(out), "frames": total, "duration": round(total / float(fps), 4), "marks": marks}
