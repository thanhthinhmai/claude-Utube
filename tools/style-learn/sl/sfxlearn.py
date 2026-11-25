"""Learning the sound effects of a reference video (specs/037 R8; `learn sfx`).

1. Split the audio into layers with htdemucs (CPU): `fx` = drums + bass + other (everything but the voice); `vocal_off_words` = the vocals layer with
   the narrator's words (±80 ms) muted, because a crowd cheering or a gasp lands in the vocals layer.
2. Events in each layer: RMS in 20 ms frames and spectral flux over a MAD threshold (like soundcraft.sfx_onsets);
   an event lasts 0.1–8 s; events closer than 150 ms are one.
3. Each event is named by two classifiers that do not share anything: AST (AudioSet, top 5) and CLAP zero-shot on a
   closed list ("the sound of {label}", sound events and non-word human sounds only). It is trusted (`agree`) only
   when CLAP's top label is in AST's top 5 (AST p ≥ 0.10), or both top labels have the same level-2 ancestor in the
   AudioSet tree. Otherwise `unsure`: kept in sfx.json, never in the style's rules.
4. Each event is tied to the nearest word (≤ 1.0 s) and to its shot; chosen silences (≤ −50 dBFS for ≥ 0.4 s right
   after a word); how a sound ends at a cut (hard: drops ≥ 20 dB within 50 ms of the cut; fade; over).

Only numbers, labels and times are written (FR-022); the separated layers stay in references/<set>/stems/ and are
deleted with the videos. The models are injected (`Models`), so tests run without torch.
"""
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from . import audioset
from . import soundcraft as sc

SR = sc.SR                      # 16 kHz analysis
HI = 48000                      # classification rate (CLAP wants 48 kHz)
FRAME = 0.02                    # RMS frames
PAD = 0.08                      # words muted ±80 ms in the vocals layer
MIN_LEN, MAX_LEN, MERGE = 0.1, 8.0, 0.15
FLOOR_DB = -55.0                # nothing quieter than this is an event
END_DROP = 20.0                 # an event ends 20 dB under its peak
RISE_DB = 3.0                   # an onset rises at least 3 dB over the 60 ms before it
AST_MIN = 0.10
NEAR_WORD = 1.0
SIL_DB, SIL_LEN = -50.0, 0.4
HARD_DB, HARD_WIN = 20.0, 0.05
OVER_S = 1.0                    # still sounding 1 s after the cut → over
MODELS = {"separator": "htdemucs (demucs 4)", "ast": "MIT/ast-finetuned-audioset-10-10-0.4593",
          "clap": "laion/larger_clap_general"}


CLIP_PRE, CLIP_MAX = 0.1, 1.0   # classify a fixed window around the onset: the first second, a long event is mostly
                                # the music bed under it and a short one is too short for AST
SIL_UNDER = 15.0                # a chosen silence is also 15 dB under the layer's level around it (±5 s)
_SOUND = set(audioset.SOUND_LABELS)


class MissingDeps(RuntimeError):
    pass


# ---------------------------------------------------------------- words, shots
def load_words(obj) -> list:
    """[{word, start, end}] from words.json ({"words": [...]}) or from sentence segments [{t, d, text}] (the words of a
    sentence spread evenly over it)."""
    if isinstance(obj, dict):
        obj = obj.get("words", [])
    out = []
    for w in obj or []:
        if "start" in w:
            out.append({"word": w.get("word", ""), "start": float(w["start"]), "end": float(w["end"])})
        elif "t" in w and "d" in w:
            toks = (w.get("text") or "").split() or [""]
            step = float(w["d"]) / len(toks)
            for i, tok in enumerate(toks):
                a = float(w["t"]) + i * step
                out.append({"word": tok, "start": round(a, 3), "end": round(a + step, 3)})
    return sorted(out, key=lambda w: w["start"])


def load_cuts(obj) -> list:
    """Cut times from a list of times, rows [t0, t1, …], {"shots": [{t0, t1}]} (craft.json) or [{t0, t1}]."""
    if isinstance(obj, dict):
        obj = obj.get("shots", obj.get("cuts", []))
    starts = []
    for s in obj or []:
        if isinstance(s, (int, float)):
            starts.append(float(s))
        elif isinstance(s, dict) and "t0" in s:
            starts.append(float(s["t0"]))
        elif isinstance(s, (list, tuple)) and s:
            starts.append(float(s[0]))
    starts = sorted(set(starts))
    return [t for t in starts if t > 0.05] if starts and starts[0] <= 0.05 else starts


def shot_of(t: float, cuts: list) -> str:
    return f"S{1 + sum(1 for c in cuts if c <= t)}"


def nearest_word(t: float, words: list, limit: float = NEAR_WORD):
    best, bd = None, limit + 1e-9
    for w in words:
        d = 0.0 if w["start"] <= t <= w["end"] else min(abs(t - w["start"]), abs(t - w["end"]))
        if d <= bd:
            best, bd = w, d
    return {"text": best["word"].strip(".,!?;:\"'“”"), "t": round(best["start"], 3)} if best else None


# ---------------------------------------------------------------- signal
def db(x) -> float:
    return float(20 * np.log10(max(float(x), 1e-9)))


def rms_frames(audio: np.ndarray, sr: int = SR):
    n = int(sr * FRAME)
    k = len(audio) // n
    if k == 0:
        return np.zeros(0), np.zeros(0)
    r = np.sqrt((audio[:k * n].reshape(k, n).astype(np.float64) ** 2).mean(1))
    return 20 * np.log10(np.maximum(r, 1e-9)), (np.arange(k) + 0.5) * FRAME


def mute_words(audio: np.ndarray, words: list, pad: float = PAD, sr: int = SR) -> np.ndarray:
    out = audio.copy()
    for w in words:
        a, b = max(0, int((w["start"] - pad) * sr)), min(len(out), int((w["end"] + pad) * sr))
        if b > a:
            out[a:b] = 0
    return out


def find_events(audio: np.ndarray) -> list:
    """[(t, len)] of sound events in one layer. A new strong onset starts a new event (a glass hit right after a music
    hit is its own event); onsets closer than MERGE are one."""
    spec, ft = sc.frames(audio)
    rdb, rt = rms_frames(audio)
    if len(ft) < 3 or not len(rdb):
        return []
    mag = np.sqrt(spec)
    flux = np.concatenate([[0], np.maximum(mag[1:] - mag[:-1], 0).sum(1)])
    live = flux[flux > 0]
    if not len(live):
        return []
    med = np.median(live)
    thr = med + 4 * 1.4826 * np.median(np.abs(live - med))
    onsets = []
    for i in range(1, len(flux) - 1):
        if flux[i] > thr and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1]:
            k = max(0, int(ft[i] / FRAME) - 1)
            win = rdb[k:k + max(1, int(0.1 / FRAME))]
            if not len(win) or win.max() < FLOOR_DB:
                continue
            if k >= 3 and win.max() - rdb[k - 3:k].max() < RISE_DB:     # a decay or a bin wobble, not a new sound
                continue
            lim = max(FLOOR_DB, win.max() - END_DROP)
            k += int(np.argmax(win > lim))
            if onsets and k - onsets[-1][0] < MERGE / FRAME:
                continue
            onsets.append((k, lim))
    ev = []
    for n, (i, lim) in enumerate(onsets):
        stop = onsets[n + 1][0] if n + 1 < len(onsets) else len(rdb)
        j = i
        while j < stop and rdb[j] > lim and (j - i) * FRAME < MAX_LEN:
            j += 1
        if (j - i) * FRAME >= MIN_LEN:
            ev.append((round(i * FRAME, 3), round((j - i) * FRAME, 3)))
    return ev


def silences(mix: np.ndarray, words: list) -> list:
    """Chosen silences: ≤ SIL_DB for ≥ SIL_LEN starting within NEAR_WORD after a word ends."""
    rdb, rt = rms_frames(mix)
    out, i = [], 0
    while i < len(rdb):
        if rdb[i] > SIL_DB:
            i += 1
            continue
        j = i
        while j < len(rdb) and rdb[j] <= SIL_DB:
            j += 1
        a, ln = rt[i] - FRAME / 2, (j - i) * FRAME
        before = [w for w in words if w["end"] <= a + 0.05]
        around = rdb[max(0, i - int(5 / FRAME)):min(len(rdb), j + int(5 / FRAME))]
        level = float(np.percentile(around, 75)) if len(around) else 0.0
        if (ln >= SIL_LEN and before and a - before[-1]["end"] <= NEAR_WORD and j < len(rdb)
                and level - float(rdb[i:j].mean()) >= SIL_UNDER):
            out.append({"t": round(a, 3), "len": round(ln, 3), "db": round(float(rdb[i:j].mean()), 1),
                        "word": before[-1]["word"].strip(".,!?;:\"'“”")})
        i = j
    return out


def cut_kind(layer: np.ndarray, t: float, ln: float, cuts: list):
    """How an event that spans a cut ends there: hard / fade / over; None if it does not reach a cut."""
    end = t + ln
    for c in cuts:
        if not (t < c <= end + HARD_WIN):
            continue
        rdb, rt = rms_frames(layer)
        k = int(c / FRAME)
        w = max(1, int(HARD_WIN / FRAME))
        before = rdb[max(0, k - w):k]
        after = rdb[k:k + w]
        if len(before) and len(after) and before.mean() - after.mean() >= HARD_DB:
            return {"kind": "hard", "fade_s": 0.0}
        if end - c > OVER_S:
            return {"kind": "over", "fade_s": 0.0}
        return {"kind": "fade", "fade_s": round(max(0.0, end - c), 3)}
    return None


def agree(ast5, clap1):
    """(agree, label): CLAP's top label in AST's top 5 (p ≥ AST_MIN), or same level-2 ancestor as AST's top label."""
    use = [(l, p) for l, p in (ast5 or []) if p >= AST_MIN and l in _SOUND]   # Speech/Music never name an effect
    if not use or not clap1:
        return False, None
    cl = clap1[0]
    if cl in [l for l, _ in use]:
        return True, cl
    if audioset.ancestors(cl) & audioset.ancestors(use[0][0]):
        return True, cl
    return False, None


# ---------------------------------------------------------------- one video
def analyze(mix: np.ndarray, stems: dict, words: list, cuts: list, models, hi: dict = None) -> dict:
    """mix and stems ({"fx", "vocals"}) mono 16 kHz; hi: the same layers at 48 kHz for the classifiers (optional)."""
    hi = hi or {}
    voc = stems["vocals"]
    layers = {"fx": stems["fx"], "vocal_off_words": mute_words(voc, words)}
    hi_layers = {"fx": hi.get("fx"), "vocal_off_words": mute_words(hi["vocals"], words, sr=HI) if "vocals" in hi else None}
    vseg = np.concatenate([voc[int(w["start"] * SR):int(w["end"] * SR)] for w in words]) if words else np.zeros(0)
    vrms = float(np.sqrt((vseg.astype(np.float64) ** 2).mean())) if len(vseg) else 0.0
    have = getattr(models, "ast", None) is not None and getattr(models, "clap", None) is not None
    events, onto = [], {}
    for name, layer in layers.items():
        for t, ln in find_events(layer):
            src, sr = (hi_layers[name], HI) if hi_layers.get(name) is not None else (layer, SR)
            clip = src[int(max(0.0, t - CLIP_PRE) * sr):int((t + CLIP_MAX) * sr)]   # AST needs ~1 s to hear a sound
            a5 = [(l, round(float(p), 4)) for l, p in models.ast(clip, sr)][:5] if have else []
            c1 = models.clap(clip, sr, audioset.SOUND_LABELS) if have else None
            c1 = (c1[0], round(float(c1[1]), 4)) if c1 else None
            ok, label = agree(a5, c1) if have else (False, None)
            for l in [x for x, _ in a5] + ([c1[0]] if c1 else []):
                onto[l] = sorted(audioset.ancestors(l))
            seg = layer[int(t * SR):int((t + ln) * SR)]
            e = {"t": t, "len": ln, "layer": name, "ast": [list(x) for x in a5], "clap": list(c1) if c1 else None,
                 "agree": ok, "label": label,
                 "db_vs_voice": round(db(np.sqrt((seg.astype(np.float64) ** 2).mean())) - db(vrms), 1) if vrms else None}
            w = nearest_word(t, words)
            if w:
                e["word"] = w
            if cuts:
                e["shot"] = shot_of(t, cuts)
            ck = cut_kind(layer, t, ln, cuts)
            if ck:
                e["cut"] = ck
            events.append(e)
    events.sort(key=lambda e: e["t"])
    # chosen silences are heard on the layer without the voice: in the films the voice stays through them
    return {"models": dict(MODELS) if have else {**MODELS, "missing": True}, "seconds": round(len(mix) / SR, 2),
            "events": events, "silences": silences(stems["fx"], words), "ontology": onto}


# ---------------------------------------------------------------- summary → style
def _pct(xs):
    return [round(float(x), 1) for x in np.percentile(xs, [25, 50, 75])] if xs else None


def sfx_summary(results: list) -> dict:
    """sound.sfx of a style from the sfx.json of its videos: numbers, labels and times only."""
    mins = sum(r.get("seconds", 0) for r in results) / 60 or 1
    ok = [(r.get("video", "?"), e) for r in results for e in r["events"] if e["agree"]]
    by = defaultdict(list)
    for v, e in ok:
        by[e["label"]].append((v, e))
    actions = []
    for label, xs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        words = Counter(e["word"]["text"].lower() for _, e in xs if e.get("word"))
        actions.append({"action": words.most_common(1)[0][0] if words else label, "label": label, "n": len(xs),
                        "evidence": [[v, e["t"]] for v, e in xs[:5]]})
    sil = [(r.get("video", "?"), s) for r in results for s in r["silences"]]
    cuts = [(v, e) for v, e in ok if e.get("cut")]
    kinds = Counter(e["cut"]["kind"] for _, e in cuts)
    kind = kinds.most_common(1)[0][0] if kinds else None
    fades = [e["cut"]["fade_s"] for _, e in cuts if e["cut"]["kind"] == "fade"]
    return {
        "per_min": round(len(ok) / mins, 1),
        "gain_db": _pct([e["db_vs_voice"] for _, e in ok if e.get("db_vs_voice") is not None]),
        "actions": actions,
        "silences": {"db": round(float(np.median([s["db"] for _, s in sil])), 1) if sil else None,
                     "len_s": round(float(np.median([s["len"] for _, s in sil])), 2) if sil else None,
                     "evidence": [[v, s["t"], s["word"]] for v, s in sil[:5]]},
        "cut": {"kind": kind, "fade_s": round(float(np.median(fades)), 2) if fades else None,
                "evidence": [[v, e["t"], e["cut"]["kind"]] for v, e in cuts[:5]]},
        "unsure_n": sum(1 for r in results for e in r["events"] if not e["agree"]),
    }


def style_paragraph(s: dict, set_name: str) -> str:
    acts = ", ".join(f"{a['action']} → {a['label']} ×{a['n']}" for a in s["actions"][:6]) or "none"
    g = s["gain_db"]
    sil = s["silences"]
    return (f"<!-- sfx (learn sfx, specs/037) -->\n**Sound effects** (measured on `{set_name}`, two classifiers agreeing): "
            f"{s['per_min']} sounds a minute; gain against the voice {g[1] if g else '—'} dB (p25–p75 "
            f"{g[0] if g else '—'}…{g[2] if g else '—'}); actions: {acts}. Chosen silences: "
            f"{sil['db'] if sil['db'] is not None else '—'} dB for {sil['len_s'] if sil['len_s'] is not None else '—'} s. "
            f"At a cut sounds end `{s['cut']['kind'] or '—'}`. Unsure events left out: {s['unsure_n']}.\n<!-- end sfx -->")


def write_style(slug: str, set_name: str, s: dict, root: Path) -> list:
    d = root / "my-styles" / slug
    tj = d / "template.json"
    t = json.loads(tj.read_text(encoding="utf-8")) if tj.exists() else {}
    t.setdefault("sound", {})["sfx"] = s
    tj.parent.mkdir(parents=True, exist_ok=True)
    tj.write_text(json.dumps(t, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    out = [tj]
    md = d / "STYLE.md"
    if md.exists():
        txt = md.read_text(encoding="utf-8")
        para = style_paragraph(s, set_name)
        a, b = txt.find("<!-- sfx (learn sfx"), txt.find("<!-- end sfx -->")
        if a >= 0 and b > a:
            txt = txt[:a] + para + txt[b + len("<!-- end sfx -->"):]
        else:
            txt = txt.rstrip() + "\n\n" + para + "\n"
        md.write_text(txt, encoding="utf-8")
        out.append(md)
    return out


# ---------------------------------------------------------------- real models (deps sound)
def _ffmpeg(path_or_pcm, rate: int, ch: int, in_rate: int = None, in_ch: int = 1) -> np.ndarray:
    if isinstance(path_or_pcm, (str, Path)):
        cmd, inp = ["ffmpeg", "-v", "error", "-nostdin", "-i", str(path_or_pcm), "-vn"], None
    else:
        cmd = ["ffmpeg", "-v", "error", "-nostdin", "-f", "f32le", "-ar", str(in_rate), "-ac", str(in_ch), "-i", "-"]
        inp = np.ascontiguousarray(path_or_pcm, np.float32).tobytes()
    r = subprocess.run(cmd + ["-ac", str(ch), "-ar", str(rate), "-f", "f32le", "-"], input=inp, capture_output=True)
    x = np.frombuffer(r.stdout, np.float32)
    return x.reshape(-1, ch) if ch > 1 else x


def _emb(x):
    """Transformers 5 returns an output object (projected, normalised embeddings in pooler_output); 4.x a tensor."""
    return x.pooler_output if hasattr(x, "pooler_output") else x


class Models:
    """htdemucs + AST + CLAP on CPU. Imports torch only here; MissingDeps when `deps sound` is not installed."""

    def __init__(self):
        try:
            import torch  # noqa: F401
            import demucs.pretrained  # noqa: F401
            import transformers  # noqa: F401
        except ImportError as e:
            raise MissingDeps(str(e))
        self._sep = self._a = self._c = None
        self._text = None

    def separate(self, path) -> tuple:
        """({"fx", "vocals", "mix"} at 16 kHz, {"fx", "vocals"} at 48 kHz), mono."""
        import torch
        from demucs.apply import apply_model
        from demucs.pretrained import get_model
        if self._sep is None:
            self._sep = get_model("htdemucs").eval()
        m = self._sep
        wav = _ffmpeg(path, m.samplerate, 2)
        x = torch.from_numpy(wav.T.copy())
        ref = x.mean(0)
        x = (x - ref.mean()) / (ref.std() + 1e-8)
        with torch.no_grad():
            out = apply_model(m, x[None], device="cpu", split=True, overlap=0.25, progress=False)[0]
        out = out * (ref.std() + 1e-8) + ref.mean()
        st = {n: out[i].mean(0).numpy() for i, n in enumerate(m.sources)}
        fx = st["drums"] + st["bass"] + st["other"]          # everything but the voice
        lo = {"fx": _ffmpeg(fx, SR, 1, m.samplerate), "vocals": _ffmpeg(st["vocals"], SR, 1, m.samplerate),
              "mix": _ffmpeg(wav.mean(1), SR, 1, m.samplerate)}
        hi = {"fx": _ffmpeg(fx, HI, 1, m.samplerate), "vocals": _ffmpeg(st["vocals"], HI, 1, m.samplerate)}
        return lo, hi

    def ast(self, clip, sr):
        import torch
        from transformers import ASTFeatureExtractor, ASTForAudioClassification
        if self._a is None:
            self._a = (ASTFeatureExtractor.from_pretrained(MODELS["ast"]),
                       ASTForAudioClassification.from_pretrained(MODELS["ast"]).eval())
        fe, m = self._a
        if sr != 16000:
            clip = _ffmpeg(clip, 16000, 1, sr)
        with torch.no_grad():
            p = torch.sigmoid(m(**fe(clip, sampling_rate=16000, return_tensors="pt")).logits[0]).numpy()
        top = np.argsort(-p)[:5]
        return [(m.config.id2label[int(i)], float(p[i])) for i in top]

    def clap(self, clip, sr, labels):
        import torch
        from transformers import ClapModel, ClapProcessor
        if self._c is None:
            self._c = (ClapProcessor.from_pretrained(MODELS["clap"]), ClapModel.from_pretrained(MODELS["clap"]).eval())
        pr, m = self._c
        if self._text is None or self._text[0] != tuple(labels):
            with torch.no_grad():
                te = _emb(m.get_text_features(**pr(text=[f"the sound of {l}" for l in labels], return_tensors="pt",
                                                   padding=True)))
            self._text = (tuple(labels), te / te.norm(dim=-1, keepdim=True))
        if sr != 48000:
            clip = _ffmpeg(clip, 48000, 1, sr)
        with torch.no_grad():
            ae = _emb(m.get_audio_features(**pr(audio=[clip], sampling_rate=48000, return_tensors="pt")))
            ae = ae / ae.norm(dim=-1, keepdim=True)
            p = torch.softmax((ae @ self._text[1].T)[0] * m.logit_scale_a.exp(), 0).numpy()
        i = int(p.argmax())
        return labels[i], float(p[i])


def _save_stems(d: Path, lo: dict) -> None:
    d.mkdir(parents=True, exist_ok=True)
    try:
        import soundfile as sf
        for k in ("fx", "vocals"):
            sf.write(str(d / f"{k}.wav"), lo[k], SR, subtype="PCM_16")
    except ImportError:
        for k in ("fx", "vocals"):
            np.save(d / f"{k}.npy", lo[k].astype(np.float16))


def run_file(wav: Path, words: list, cuts: list, models, stems_dir: Path = None, video: str = None) -> dict:
    """Separation is the slow part (minutes on CPU): layers kept in stems_dir are reused while the source is the same."""
    sig = f"fx=dbo:{Path(wav).stat().st_size}:{Path(wav).stat().st_mtime_ns}"   # fx = drums + bass + other
    cache = stems_dir / "layers.npz" if stems_dir else None
    lo = hi = None
    if cache and cache.exists():
        z = np.load(cache)
        if str(z["sig"]) == sig:
            lo = {k: z[f"lo_{k}"].astype(np.float32) for k in ("fx", "vocals", "mix")}
            hi = {k: z[f"hi_{k}"].astype(np.float32) for k in ("fx", "vocals")}
    if lo is None:
        lo, hi = models.separate(wav)
        if stems_dir:
            _save_stems(stems_dir, lo)
            np.savez(cache, sig=sig, **{f"lo_{k}": v.astype(np.float16) for k, v in lo.items()},
                     **{f"hi_{k}": v.astype(np.float16) for k, v in hi.items()})
    res = analyze(lo["mix"], lo, words, cuts, models, hi)
    res["video"] = video or Path(wav).stem
    return res


def sfx_set(name: str, only=None, models=None, log=print) -> int:
    from . import refset
    data = refset.load(name)
    todo = []
    for v in data["videos"]:
        if only and v["id"] not in only:
            continue
        prof = refset.profile_dir(name, v["id"])
        if not (prof / "words.json").exists():
            log(f"✗ {v['id']}: chưa có mốc từ (chạy learn transcribe trước)")
            return 3
        todo.append(v)
    if models is None:
        try:
            models = Models()
        except MissingDeps:
            log("✗ chưa cài tầng học tiếng: sh bin/studio deps sound")
            return 3
    done = 0
    for v in todo:
        prof = refset.profile_dir(name, v["id"])
        path = refset.video_path(name, v)
        if not path.exists():
            log(f"= {v['id']}: không có video, bỏ qua")
            continue
        words = load_words(json.loads((prof / "words.json").read_text(encoding="utf-8")))
        cj = prof / "craft.json"
        cuts = load_cuts(json.loads(cj.read_text(encoding="utf-8"))) if cj.exists() else []
        res = run_file(path, words, cuts, models, refset.set_dir(name) / "stems" / v["id"], v["id"])
        refset.write_json(prof / "sfx.json", res)
        n_ok = sum(e["agree"] for e in res["events"])
        log(f"✓ {v['id']}: {len(res['events'])} sự kiện, {n_ok} hai bộ đồng ý, {len(res['silences'])} lặng chọn")
        done += 1
    return 0 if done else 1


def summarize_set(name: str, style: str = None, log=print) -> int:
    from . import refset, template
    data = refset.load(name)
    res = [refset.read_json(refset.profile_dir(name, v["id"]) / "sfx.json") for v in data["videos"]]
    res = [r for r in res if r]
    if not res:
        log("✗ chưa có sfx.json nào (chạy learn sfx trước)")
        return 3
    s = sfx_summary(res)
    if style:
        template.style_dir(style)  # validates the path shape
        for p in write_style(style, name, s, refset.root()):
            log(f"✓ {p.relative_to(refset.root())}")
    else:
        log(json.dumps(s, ensure_ascii=False, indent=1))
    return 0


def score(res: dict, expect: dict) -> dict:
    """SC-003: which expected events were found (agree, a matching level-2 group, inside the window)."""
    out = []
    for x in expect["events"]:
        a, b = x["window"]
        if x.get("kind") == "silence":
            hit = [s for s in res["silences"] if s["t"] <= b and s["t"] + s["len"] >= a     # overlaps the window
                   and s["db"] <= x["max_db"] and s["len"] >= x["min_len"]]
        else:
            g = set(x["groups"])
            hit = [e for e in res["events"] if e["agree"] and a <= e["t"] <= b
                   and (audioset.ancestors(e["label"]) & g or e["label"] in g)]
        out.append({"name": x["name"], "found": bool(hit), "at": [round(h["t"], 2) for h in hit[:3]]})
    return {"found": sum(o["found"] for o in out), "of": len(out), "events": out}
