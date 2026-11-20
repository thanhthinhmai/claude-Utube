"""Reading rhythm, music and sound effects of a reference video (specs/023 research R5, R6; `learn sound`).

Uses the word times of `learn transcribe` (profile/<v>/words.json) to know when the narrator speaks.
- speech_stats: words per minute in 10 s windows; pauses inside a sentence, after a sentence, between paragraphs
  (> PARA s); the pause just before a number.
- music_windows: per 5 s window, is there music in the pauses (tonal: spectral flatness < FLAT in ≥ 70 % of the
  pause frames) and how loud it is against the voice (dB).
- sfx_onsets: sharp energy onsets (spectral flux > median + 4·1.4826·MAD) outside words, or ≥ 6 dB over the speech.
- tempo: autocorrelation of the low-band (< 150 Hz) onset envelope over the whole film, 60–180 BPM, with a confidence.
"""
import json
import re

import numpy as np

SR = 16000
HOP = 512
NFFT = 1024
PARA = 0.6
FLAT = 0.3
MIN_PAUSE = 0.25
NUM_WORDS = {"zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
             "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty",
             "fifty", "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "million", "billion", "trillion",
             "half", "dozen"}


def is_number(word: str) -> bool:
    w = re.sub(r"[^\w%$.,-]", "", word.lower()).strip(".,")
    return bool(re.search(r"\d", w)) or w in NUM_WORDS


def ends_sentence(word: str) -> bool:
    return bool(re.search(r"[.?!…]['\"”’)]*$", word.strip()))


def _q(xs):
    return [round(float(x), 3) for x in np.percentile(xs, [25, 50, 75])] if len(xs) else None


def speech_stats(words: list) -> dict:
    if len(words) < 2:
        return {"wpm_10s": [], "pause_in": [], "pause_sent": [], "pause_para": [], "pre_number": []}
    end = words[-1]["end"]
    wpm = []
    for t in np.arange(0, end, 10.0):
        n = sum(1 for w in words if t <= w["start"] < t + 10)
        if n >= 5:
            wpm.append([round(float(t), 1), n * 6])
    pin, psent, ppara, pnum = [], [], [], []
    for a, b in zip(words[:-1], words[1:]):
        g = round(b["start"] - a["end"], 3)
        if g < 0.05:
            continue
        if g > PARA:
            ppara.append(g)
        elif ends_sentence(a["word"]):
            psent.append(g)
        else:
            pin.append(g)
        if is_number(b["word"]):
            pnum.append(g)
    return {"wpm_10s": wpm, "pause_in": pin, "pause_sent": psent, "pause_para": ppara, "pre_number": pnum}


def frames(audio: np.ndarray):
    """Power spectra (n, NFFT/2+1) and frame times."""
    n = max(0, 1 + (len(audio) - NFFT) // HOP)
    if n == 0:
        return np.zeros((0, NFFT // 2 + 1)), np.zeros(0)
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(n)[:, None]
    win = np.hanning(NFFT).astype(np.float32)
    spec = np.abs(np.fft.rfft(audio[idx] * win, axis=1)) ** 2
    return spec, (np.arange(n) * HOP + NFFT / 2) / SR


def speaking_mask(times: np.ndarray, words: list, pad: float = 0.03) -> np.ndarray:
    m = np.zeros(len(times), bool)
    if not words:
        return m
    st = np.array([w["start"] - pad for w in words])
    en = np.array([w["end"] + pad for w in words])
    k = np.searchsorted(st, times, side="right") - 1
    ok = k >= 0
    m[ok] = times[ok] <= en[k[ok]]
    return m


def _trimmed(r: np.ndarray, keep: float = 95) -> float:
    """rms of frames below the keep-th percentile (one loud transient does not count)."""
    r = r[r <= np.percentile(r, keep)] if len(r) > 5 else r
    return float(np.sqrt(np.mean(r ** 2))) if len(r) else 0.0


def inside_mask(times: np.ndarray, words: list, margin: float) -> np.ndarray:
    m = np.zeros(len(times), bool)
    for w in words:
        if w["end"] - w["start"] > 2 * margin:
            m |= (times >= w["start"] + margin) & (times <= w["end"] - margin)
    return m


def off_grid(onsets: list, bpm: float, tol: float = 0.05) -> list:
    """Onsets not on the music's beat grid (phase taken from the onsets themselves): music beats are not effects."""
    if not bpm or len(onsets) < 4:
        return onsets
    beat = 60 / bpm
    ph = np.array(onsets) % beat
    hist, edges = np.histogram(ph, bins=max(4, int(beat / tol)), range=(0, beat))
    k = int(np.argmax(hist))
    if hist[k] < max(8, 0.4 * len(onsets)):     # no clear grid (few onsets, or spread): keep everything
        return onsets
    c = (edges[k] + edges[k + 1]) / 2
    d = np.abs(((ph - c) + beat / 2) % beat - beat / 2)
    return [o for o, x in zip(onsets, d) if x > tol]


def _flatness(spec: np.ndarray) -> np.ndarray:
    f = np.fft.rfftfreq(NFFT, 1 / SR)
    band = spec[:, (f >= 100) & (f <= 4000)] + 1e-12
    return np.exp(np.log(band).mean(1)) / band.mean(1)


def music_windows(audio: np.ndarray, words: list, win: float = 5.0) -> list:
    spec, t = frames(audio)
    if not len(t):
        return []
    half = NFFT / 2 / SR
    speak = speaking_mask(t, words, pad=0.03 + half)          # a pause frame must not reach into a word
    inside = inside_mask(t, words, half)                      # a voice frame lies wholly inside a word
    rms = np.sqrt(spec.sum(1) / NFFT + 1e-20)
    flat = _flatness(spec)
    out = []
    for a in np.arange(0, t[-1], win):
        sel = (t >= a) & (t < a + win)
        gap, voc = sel & ~speak, sel & inside
        if gap.sum() * HOP / SR < MIN_PAUSE:
            out.append([round(float(a), 1), round(float(a + win), 1), None, None])
            continue
        g_rms = _trimmed(rms[gap])                 # the loudest 5 % left out: an effect in a pause does not lift the bed
        audible = 20 * np.log10(g_rms + 1e-12) > 20 * np.log10(np.max(rms) + 1e-12) - 50
        tonal = float((flat[gap] < FLAT).mean()) >= 0.7
        level = None
        if voc.any():
            level = round(20 * np.log10(g_rms / (_trimmed(rms[voc]) + 1e-12)), 1)
        out.append([round(float(a), 1), round(float(a + win), 1), bool(audible and tonal), level])
    return out


def sfx_onsets(audio: np.ndarray, words: list) -> list:
    spec, t = frames(audio)
    if len(t) < 3:
        return []
    mag = np.sqrt(spec)
    flux = np.maximum(mag[1:] - mag[:-1], 0).sum(1)
    flux = np.concatenate([[0], flux])
    med = np.median(flux)
    thr = med + 4 * 1.4826 * np.median(np.abs(flux - med))
    peaks = [i for i in range(1, len(flux) - 1) if flux[i] > thr and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]]
    speak = speaking_mask(t, words, pad=0.05 + NFFT / 2 / SR)   # a frame reaching into a word is speech
    energy = 10 * np.log10(spec.sum(1) + 1e-20)
    sp_level = np.median(energy[speak]) if speak.any() else -np.inf
    out = []
    for i in peaks:
        if not speak[i] or energy[i] > sp_level + 6:
            if not out or t[i] - out[-1] > 0.15:
                out.append(round(float(t[i]), 3))
    return out


def tempo(audio: np.ndarray):
    """(BPM, confidence) from the low band; ("none") when the film is too short."""
    spec, t = frames(audio)
    if len(t) < 200:
        return None, "none"
    f = np.fft.rfftfreq(NFFT, 1 / SR)
    low = np.sqrt(spec[:, (f >= 30) & (f <= 150)]).sum(1)
    env = np.maximum(np.diff(low, prepend=low[0]), 0)
    env = env - env.mean()
    fps = SR / HOP
    ac = np.correlate(env, env, mode="full")[len(env) - 1:]
    lo, hi = int(fps * 60 / 180), int(fps * 60 / 60)
    seg = ac[lo:hi + 1]
    if not len(seg) or ac[0] <= 0:
        return None, "none"
    k = int(np.argmax(seg)) + lo
    # parabola for a sub-frame lag
    if lo < k < hi:
        y0, y1, y2 = ac[k - 1], ac[k], ac[k + 1]
        d = y0 - 2 * y1 + y2
        k = k + (0.5 * (y0 - y2) / d if d != 0 else 0)
    bpm = 60 * fps / k
    strength = float(seg.max() / ac[0])
    return round(float(bpm), 1), ("ok" if strength > 0.3 else "low")


def _inside(t: float, segments) -> bool:
    return any(a <= t < b for a, b in segments)


def restrict(res: dict, segments) -> dict:
    """Keep only sound effects and music windows inside the measured segments (specs/028 R9). words.json covers only
    those segments, so outside them speech onsets looked like effects and inflated sfx.per_min."""
    if not segments:
        return res
    minutes = max(sum(b - a for a, b in segments) / 60, 1e-6)
    on = [x for x in res["sfx"]["onsets"] if _inside(x, segments)]
    wins = [w for w in res["music"]["windows"] if _inside(w[0], segments) and _inside(w[1] - 1e-3, segments)]
    out = dict(res)
    out["music"] = dict(res["music"], windows=wins)
    out["sfx"] = {"onsets": on, "per_min": round(len(on) / minutes, 2), "segments": [list(s) for s in segments]}
    return out


def analyze(audio: np.ndarray, words: list, segments=None) -> dict:
    sp = speech_stats(words)
    bpm, conf = tempo(audio)
    on = off_grid(sfx_onsets(audio, words), bpm if conf == "ok" else None)
    minutes = max(len(audio) / SR / 60, 1e-6)
    res = {"speech": sp, "music": {"windows": music_windows(audio, words), "tempo": bpm, "tempo_conf": conf},
           "sfx": {"onsets": on, "per_min": round(len(on) / minutes, 2)}}
    return restrict(res, segments)


def recompute_set(name: str, only=None, log=print) -> int:
    """Re-filter stored sound.json files to the measured segments, without the videos (specs/028 T037)."""
    from . import refset
    data, rates = refset.load(name), []
    for v in data["videos"]:
        if only and v["id"] not in only:
            continue
        prof = refset.profile_dir(name, v["id"])
        sf, vj = prof / "sound.json", prof / "video.json"
        if not sf.exists() or not vj.exists():
            log(f"= {v['id']}: không có sound.json hoặc video.json, bỏ qua")
            continue
        res = json.loads(sf.read_text(encoding="utf-8"))
        segs = json.loads(vj.read_text(encoding="utf-8")).get("segments")
        new = restrict(res, segs)
        refset.write_json(sf, new)
        rates.append(new["sfx"]["per_min"])
        log(f"✓ {v['id']}: tiếng động {res['sfx']['per_min']} → {new['sfx']['per_min']}/phút (trong đoạn đo)")
    if rates:
        log(f"trung vị: {float(np.median(rates)):.1f}/phút")
    return 0 if rates else 1


def sound_set(name: str, only=None, log=print) -> int:
    from . import refset, speech
    data = refset.load(name)
    done = 0
    for v in data["videos"]:
        if only and v["id"] not in only:
            continue
        prof = refset.profile_dir(name, v["id"])
        wf = prof / "words.json"
        path = refset.video_path(name, v)
        if not wf.exists():
            log(f"✗ {v['id']}: chưa có mốc từ (chạy learn transcribe trước)")
            return 3
        if not path.exists():
            log(f"= {v['id']}: không có video, bỏ qua")
            continue
        words = json.loads(wf.read_text(encoding="utf-8")).get("words", [])
        vj = prof / "video.json"
        segs = json.loads(vj.read_text(encoding="utf-8")).get("segments") if vj.exists() else None
        res = analyze(speech.decode_16k(path), words, segs)
        res["video"] = v["id"]
        refset.write_json(prof / "sound.json", res)
        mus = [w for w in res["music"]["windows"] if w[2] is not None]
        log(f"✓ {v['id']}: tiếng động {res['sfx']['per_min']}/phút, nhạc {sum(bool(w[2]) for w in mus)}/{len(mus)} cửa sổ, "
            f"tempo {res['music']['tempo']} ({res['music']['tempo_conf']})")
        done += 1
    return 0 if done else 1
