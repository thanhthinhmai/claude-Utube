"""The mix of an After Effects film from its sound plan (specs/037 US1, research R7).

Two halves:
- `run(film_dir)` (tools venv, no numpy): resolve the plan, make sure every chosen sound is copied into
  sound/cache/, refuse any sound that is not from the library (R11), write a JSON job, call the other half with the
  library's Python, write the film's CREDITS block and put the sound back on a rendered film (no new picture);
- `python soundmix.py <job.json>` (the library's venv: numpy + soundfile; nothing of lib/ is imported): voice lines at
  their times, out/music.wav ducked under the voice (50 ms window), each cue at its time with its gain against the voice,
  its cut rule at the shot end, the chosen silences, one gain for the whole film from the voice and the music only
  (−14 LUFS, BS.1770), and a true-peak limiter (−2.5 dBTP, 5 ms look-ahead). The gain does not depend on cues or
  silences and the limiter only reaches 7.5 ms, so changing one cue changes only the samples within
  [its time − 60 ms, its end + 60 ms] (FR-026, SC-006).
Writes out/mix.wav (48 kHz stereo), sound/stems/fx.wav and sound/stems/voice.wav."""
import json
import os
import subprocess
import sys
from pathlib import Path

SR = 48000
FADE_IN = 0.005
HARD = 0.010                     # a hard cut is silent 10 ms after the cut
TAIL = 0.005
RAMP = 0.030                     # silence ramps
DUCK = 0.5                       # music under the voice: −6 dB at most
CEIL_DBTP = -2.5                 # true-peak ceiling (4× oversampled, 5 ms look-ahead); AAC adds ~1 dB on top
LOOK = 0.005
END_FADE = 0.8
TARGET_LUFS = -14.0              # the studio's delivery check: −14 ± 1 LUFS, true peak ≤ −1 dB (runner/worker.py)
MAX_GAIN_DB = 20.0
MARK_BEGIN, MARK_END = "# sound effects (studio, 037)", "# end sound effects"


# ====================================================================== tools side
def lib_python() -> str:
    from filmcheck import edit
    py = edit.lib_path() / ".venv" / "bin" / "python"
    return str(py) if py.is_file() else sys.executable


def _cache_file(d: Path, entry: str):
    from filmcheck import soundlib
    folder = d / "sound" / "cache"
    for p in sorted(folder.glob(f"{soundlib.safe(entry)}.*")) if folder.is_dir() else []:
        if p.suffix != ".json":
            return p
    return None


def _forbidden(d: Path, p: Path) -> bool:
    from filmcheck import soundlib
    return bool(soundlib.forbidden(p)) or bool(soundlib.forbidden(Path(os.path.realpath(p))))


def job(d: Path, plan: dict) -> dict:
    """The JSON the mixer reads. Raises PlanError when a sound is not from the library."""
    from filmcheck import soundlib, soundplan
    d = Path(d)
    idx = soundplan._read(d / "sound" / "cache" / "index.json", {}) or {}
    lines = soundplan.narration(d)
    voices = []
    for lid, ln in lines.items():
        f = d / "voices" / f"{lid}.wav"
        if f.is_file():
            voices.append({"file": str(f), "at": float(ln.get("at", 0))})
    cues, used = [], {}
    for c in plan["cues"]:
        if c.get("state") != "placed":
            continue
        meta = idx.get(c["entry"]) or {}
        if meta.get("source") not in soundplan.SOURCES:
            raise soundplan.PlanError("bad", f"{c['id']}: sound {c['entry']} is not from the library (source "
                                             f"{meta.get('source')!r})")
        f = _cache_file(d, c["entry"])
        if f is None:
            try:
                f = soundlib.cache(c["entry"], d)
            except soundlib.LibraryError as e:
                raise soundplan.PlanError("missing", f"{c['id']}: {e.message}") from None
        if _forbidden(d, f):
            raise soundplan.PlanError("bad", f"{c['id']}: reference audio never goes into a film")
        end = plan["t1"][c["shot"]]
        length = c.get("len_s")
        if length is None and (c.get("anchor") or {}).get("span") == "shot":
            length = end - c["at"]
        cues.append({"id": c["id"], "file": str(f), "at": c["at"], "len": length, "gain_db": c["gain_db"],
                     "cut": c["cut"], "fade_s": c.get("fade_s", 0.15), "shot_end": end})
        used[c["entry"]] = meta
    music = d / "out" / "music.wav"
    return {"length": plan["length"], "voices": voices, "music": str(music) if music.is_file() else None,
            "cues": cues, "silences": [s for s in plan["silences"] if "at" in s],
            "out": str(d / "out" / "mix.wav"), "stems": str(d / "sound" / "stems"), "_used": used}


def credits(d: Path, used: dict) -> None:
    """Replace the film's sound-effects block in CREDITS: one line per library sound used (FR-016)."""
    f = Path(d) / "CREDITS"
    text = f.read_text(encoding="utf-8") if f.is_file() else ""
    if MARK_BEGIN in text:
        head, _, rest = text.partition(MARK_BEGIN)
        _, _, tail = rest.partition(MARK_END)
        text = head.rstrip("\n") + ("\n" if head.strip() else "") + tail.lstrip("\n")
    rows = sorted({(f"{m.get('credit') or e} · {m.get('name') or e} — {m.get('license') or '?'}"
                    + (f" — {m['url']}" if m.get("url") else "")) for e, m in used.items()})
    if rows:
        block = "\n".join([MARK_BEGIN] + rows + [MARK_END])
        text = (text.rstrip("\n") + "\n\n" if text.strip() else "") + block + "\n"
    f.write_text(text, encoding="utf-8")


def remux(d: Path) -> dict:
    """Put the new mix back on a rendered film without a new picture (like edit.mix_edit)."""
    d = Path(d)
    mix = d / "out" / "mix.wav"
    out = {}
    film = json.loads((d / "film.json").read_text(encoding="utf-8")) if (d / "film.json").is_file() else {}
    audio = film.get("audio")
    if audio and audio.endswith((".m4a", ".aac")):
        dst = d / audio
        dst.parent.mkdir(parents=True, exist_ok=True)
        p = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mix), "-c:a", "aac", "-b:a", "192k", str(dst)],
                           capture_output=True, text=True)
        out["audio"] = p.returncode == 0
    render = d / "out" / "render.mp4"
    if render.is_file():
        tmp = render.with_name("render.remux.mp4")
        p = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(render), "-i", str(mix), "-map", "0:v", "-map", "1:a",
                            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(tmp)], capture_output=True, text=True)
        if p.returncode == 0:
            os.replace(tmp, render)
            final = d / f"{d.name}.mp4"
            if final.is_file():                  # a new file, never written in place: a fix job's copy is a hard link
                import shutil
                part = final.with_name(final.name + ".part")
                shutil.copyfile(render, part)
                os.replace(part, final)
            out["muxed"] = True
        else:
            out["muxed"] = False
    return out


def run(d: Path, mux: bool = True) -> dict:
    from filmcheck import soundplan
    d = Path(d)
    plan = soundplan.resolve(d, save=True)
    j = job(d, plan)
    used = j.pop("_used")
    (d / "sound").mkdir(parents=True, exist_ok=True)
    jf = d / "sound" / ".mix-job.json"
    jf.write_text(json.dumps(j), encoding="utf-8")
    p = subprocess.run([lib_python(), str(Path(__file__).resolve()), str(jf)], capture_output=True, text=True, timeout=1800)
    if p.returncode:
        raise soundplan.PlanError("bad", "the mix failed: " + (p.stderr or p.stdout).strip()[-400:])
    credits(d, used)
    states = [c["state"] for c in plan["cues"]]
    r = {"placed": states.count("placed"), "dropped": states.count("dropped"), "missing": states.count("missing"), "off": states.count("off"),
         "mix": str(d / "out" / "mix.wav"), "base": soundplan.base(d)}
    if mux:
        r.update(remux(d))
    return r


# ====================================================================== mixer side (library venv)
def _load(path: str):
    import numpy as np
    import soundfile as sf
    a, sr = sf.read(path, dtype="float32", always_2d=True)
    if a.shape[1] == 1:
        a = np.repeat(a, 2, axis=1)
    elif a.shape[1] > 2:
        a = a[:, :2]
    if sr != SR:
        n = int(round(len(a) * SR / sr))
        x = np.arange(n) * (sr / SR)
        a = np.stack([np.interp(x, np.arange(len(a)), a[:, ch]) for ch in (0, 1)], 1).astype(np.float32)
    return a


def _rms(a) -> float:
    import numpy as np
    m = np.abs(a).mean(1)
    loud = m[m > max(1e-4, m.max() * 0.05)] if len(m) else m
    return float(np.sqrt(np.mean(loud ** 2))) if len(loud) else 0.0


def _place(buf, a, at: float):
    i = int(round(at * SR))
    if i >= len(buf) or i + len(a) <= 0:
        return
    j0 = max(0, -i)
    n = min(len(a) - j0, len(buf) - max(0, i))
    buf[max(0, i):max(0, i) + n] += a[j0:j0 + n]


def _cue(c: dict, voice_rms: float):
    import numpy as np
    a = _load(c["file"])
    if c.get("len") is not None:
        a = a[:max(1, int(round(c["len"] * SR)))]
    r = _rms(a)
    if r > 0 and voice_rms > 0:
        a = a * (voice_rms * 10 ** (c["gain_db"] / 20) / r)
    n = len(a)
    env = np.ones(n, np.float32)
    k = min(n, int(FADE_IN * SR))
    env[:k] = np.linspace(0, 1, k, endpoint=False)
    k = min(n, int(TAIL * SR))
    if k:
        env[n - k:] *= np.linspace(1, 0, k)
    cut = int(round((c["shot_end"] - c["at"]) * SR))           # samples from the cue's start to the shot end
    if 0 < cut < n and c["cut"] in ("hard", "fade"):
        span = int(HARD * SR) if c["cut"] == "hard" else max(1, int(c.get("fade_s", 0.15) * SR))
        if c["cut"] == "hard":                                  # down to silence by the cut point
            s0 = max(0, cut - span)
            env[s0:cut] *= np.linspace(1, 0, cut - s0)
            env[cut:] = 0
        else:                                                   # fades from the cut over fade_s
            e = min(n, cut + span)
            env[cut:e] *= np.linspace(1, 0, span)[:e - cut]
            env[e:] = 0
    return a * env[:, None]


def lufs(x, sr: int = SR) -> float:
    """Integrated loudness (ITU-R BS.1770-4: K-weighting, 400 ms blocks, −70 LUFS and −10 LU gates); −inf when silent."""
    import numpy as np
    from scipy.signal import lfilter
    x = np.asarray(x, np.float64)
    x = x[:, None] if x.ndim == 1 else x
    b1, a1 = [1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585]
    b2, a2 = [1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621]
    y = lfilter(b2, a2, lfilter(b1, a1, x, axis=0), axis=0)
    blk, hop = int(0.4 * sr), int(0.1 * sr)
    if len(y) < blk:
        return float("-inf")
    c = np.cumsum(np.concatenate([np.zeros((1, y.shape[1])), y ** 2]), axis=0)
    st = np.arange(0, len(y) - blk + 1, hop)
    z = ((c[st + blk] - c[st]) / blk).sum(1)
    with np.errstate(divide="ignore"):
        lk = -0.691 + 10 * np.log10(z)
    z = z[lk > -70]
    if not len(z):
        return float("-inf")
    rel = -0.691 + 10 * np.log10(z.mean()) - 10
    z = z[-0.691 + 10 * np.log10(z) > rel]
    return float(-0.691 + 10 * np.log10(z.mean())) if len(z) else float("-inf")


def limit(x, sr: int = SR, ceil_db: float = CEIL_DBTP):
    """True-peak limiter: the gain each sample needs (peaks between samples found at 4× oversampling), the smallest of it
    within LOOK either side, smoothed over LOOK; a peak only pulls down its own few milliseconds. Two passes."""
    import numpy as np
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    from scipy.signal import resample_poly
    ceil = 10 ** (ceil_db / 20)
    w = max(1, int(LOOK * sr))
    for _ in range(2):
        tp = np.abs(resample_poly(x, 4, 1, axis=0)).max(1)[:len(x) * 4].reshape(-1, 4).max(1)
        need = np.minimum(1.0, ceil / np.maximum(tp, 1e-9))
        if need.min() >= 1.0:
            break
        g = uniform_filter1d(minimum_filter1d(need, 2 * w + 1, mode="nearest"), w + 1, mode="nearest")
        x = x * np.minimum(g, 1.0)[:, None]
    return x


def mix(j: dict) -> None:
    import numpy as np
    import soundfile as sf
    n = int(round(j["length"] * SR))
    voice = np.zeros((n, 2), np.float32)
    for v in j["voices"]:
        _place(voice, _load(v["file"]), v["at"])
    vr = _rms(voice[np.abs(voice).max(1) > 1e-4]) if np.any(voice) else 0.1
    music = np.zeros((n, 2), np.float32)
    if j.get("music"):
        m = _load(j["music"])[:n]
        music[:len(m)] = m
        w = int(0.05 * SR)
        env = np.convolve(np.abs(voice).mean(1), np.ones(w, np.float32) / w, "same")      # finite window, no memory
        ref = vr if vr > 0 else 1.0
        music *= (1 - DUCK * np.clip(env / (ref * 0.5), 0, 1))[:, None]
    fx = np.zeros((n, 2), np.float32)
    for c in j["cues"]:
        _place(fx, _cue(c, vr), c["at"])
    out = voice + music + fx
    # one gain for the whole film from the voice and the bed only, so a cue or a silence changes just its own stretch
    bed = lufs(voice + music)
    gain = 10 ** (min(MAX_GAIN_DB, TARGET_LUFS - bed) / 20) if np.isfinite(bed) else 1.0
    g = np.ones(n, np.float32)
    for s in j["silences"]:
        lvl = 10 ** (s["db"] / 20)
        a, b, r = int(s["at"] * SR), int((s["at"] + s["len_s"]) * SR), int(RAMP * SR)
        seg = np.ones(n, np.float32)
        lo, hi = max(0, a - r), min(n, b + r)
        t = np.arange(lo, hi)
        down = np.clip((t - (a - r)) / r, 0, 1)
        up = np.clip(((b + r) - t) / r, 0, 1)
        seg[lo:hi] = 1 - (1 - lvl) * np.minimum(down, up)
        g = np.minimum(g, seg)
    speaking = np.abs(voice).max(1) > 1e-4
    out = np.where(speaking[:, None], voice + (music + fx) * g[:, None], out * g[:, None])
    k = min(n, int(END_FADE * SR))
    if k:
        out[n - k:] *= np.linspace(1, 0, k)[:, None]
    out = limit(out * gain)
    Path(j["out"]).parent.mkdir(parents=True, exist_ok=True)
    Path(j["stems"]).mkdir(parents=True, exist_ok=True)
    tmp = j["out"] + ".tmp.wav"
    sf.write(tmp, out.astype(np.float32), SR, subtype="PCM_16")
    os.replace(tmp, j["out"])
    sf.write(str(Path(j["stems"]) / "fx.wav"), fx, SR, subtype="FLOAT")
    sf.write(str(Path(j["stems"]) / "voice.wav"), voice, SR, subtype="FLOAT")


if __name__ == "__main__":
    mix(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
