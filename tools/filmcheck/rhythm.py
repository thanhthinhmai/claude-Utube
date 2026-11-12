"""One set of rhythm rules for the plan check (tier 1) and the finished-film qc (tier 4) — specs/020 FR-006, FR-010.

Sentences come from the passed script (the voice lines' own text), laid on the speech recogniser's word stamps; the
recogniser's punctuation never decides where a sentence ends (FR-003). Word stamps are clamped to [0, line length]
(FR-004). The recogniser model is chosen in tools/asr.json (research R1: small.en). Python standard library only."""
import difflib
import re

SILENCE_MAX, LONG_PAUSE, CUT_AFTER, KEY_SHOT, TAIL_MAX = 0.20, 0.8, 0.4, 2.5, 1.5
SHOT_MIN, SHOT_MAX, CUE_MIN, CUE_PAD = 1.1, 6.0, 1.8, 0.6
EPS = 0.05
SENT_END = re.compile(r"[.?!…。？！][\"'”’)]*$")
SPLIT = re.compile(r"(?<=[.?!…。？！])[\"'”’)]*\s+|(?<=[。？！])")


def norm(w: str) -> str:
    return re.sub(r"[^\w]", "", w.lower().replace("’", "'").replace("'", ""))


def clamp_words(words, length=None):
    """[(w, s, e)] relative to a line, each stamp inside [0, length] (FR-004)."""
    out = []
    for w, s, e in words:
        s, e = max(0.0, float(s)), max(0.0, float(e))
        if length is not None:
            s, e = min(s, length), min(e, length)
        out.append((str(w), s, max(s, e)))
    return out


def split_sentences(text: str) -> list:
    return [x.strip() for x in SPLIT.split(text or "") if x and x.strip()]


def _ranges(stoks: list, atoks: list) -> list:
    """For each script token, (lo, hi) indexes of the recogniser words it covers (hi < lo when it has none)."""
    out = [None] * len(stoks)
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, stoks, atoks, autojunk=False).get_opcodes():
        m, n = i2 - i1, j2 - j1
        for i in range(i1, i2):
            if op == "equal":
                out[i] = (j1 + i - i1, j1 + i - i1)
            elif op == "replace":                         # "seven" ↔ "7", "neighbours" ↔ "neighbors": share in proportion
                lo = j1 + (i - i1) * n // m
                hi = max(lo, j1 + -(-(i - i1 + 1) * n // m) - 1)
                out[i] = (lo, min(hi, j2 - 1))
            elif op == "delete":
                out[i] = (j1, j1 - 1)
    return out


def sentences(lines: list, texts=None) -> list:
    """[{para, line, n, start, end, text}] in film time. lines: [{id, para, at, words: [(w, s_abs, e_abs)]}] with
    stamps already clamped. texts: {line id: script text}; a line without text falls back to the words' own
    punctuation (films made before 010 have no lines.json)."""
    out = []
    for ln in lines:
        ws = ln["words"]
        if not ws:
            continue
        text = (texts or {}).get(ln["id"])
        if text:
            sents = split_sentences(text)
            stoks, first = [], []
            for s in sents:
                first.append(len(stoks))
                stoks += [norm(t) for t in s.split() if norm(t)] or [""]
            rng = _ranges(stoks, [norm(w[0]) for w in ws])
            last = len(ws) - 1
            for k, s in enumerate(sents):
                a = first[k]
                b = (first[k + 1] if k + 1 < len(sents) else len(stoks)) - 1
                lo = min(max(rng[a][0], 0), last)
                hi = min(max(rng[b][1], 0), last)
                start = ws[lo][1]
                end = max(ws[hi][2], start)
                out.append({"para": ln["para"], "line": ln["id"], "n": k, "start": round(start, 3),
                            "end": round(end, 3), "text": s[:30]})
        else:
            start, k = None, 0
            for i, (w, s, e) in enumerate(ws):
                start = s if start is None else start
                if SENT_END.search(w) or i == len(ws) - 1:
                    out.append({"para": ln["para"], "line": ln["id"], "n": k, "start": round(start, 3),
                                "end": round(e, 3), "text": ""})
                    start, k = None, k + 1
    out.sort(key=lambda x: (x["start"], x["end"]))
    for a, b in zip(out, out[1:]):          # a recogniser glitch must not make sentences overlap
        if b["start"] < a["end"]:
            b["start"] = a["end"]
            b["end"] = max(b["end"], b["start"])
    return out


def _issue(rule, ref, at, measure, limit, text="", fix="", severity="block"):
    return {"tier": None, "ref": ref, "at": round(at, 2) if at is not None else None, "rule": rule,
            "severity": severity, "measure": measure, "limit": limit, "text": text, "fix": fix, "excepted": None}


def shot_at(shots, t):
    """The shot that holds second t (a cut at t belongs to the shot it starts)."""
    for s in shots or []:
        if s["t0"] - 1e-6 <= t < s["t1"] - 1e-6:
            return s
    return shots[-1] if shots else None


def _ref(shots, t):
    s = shot_at(shots, t)
    return s["id"] if s else f"{t:.1f}s"


def speech_in(words, a, b) -> float:
    return sum(max(0.0, min(e, b) - max(s, a)) for s, e, _ in words)


def measure(sents, words, dur, *, shots=None, cuts=None, cues=None, cards=None, style=None):
    """(measures, issues). words: [(s, e, para)] in film time; shots: [{id, t0, t1}] (cuts come from them) or cuts
    alone (old films, cuts found in the picture); cues: [[t0, t1, text]]; cards: [{id, at, need, got, text}]."""
    style = style or {}
    shot_max = float(style.get("shot_max") or SHOT_MAX)
    m, issues = {}, []
    if shots:
        cuts = [s["t0"] for s in shots[1:]]
    cuts = sorted(cuts or [])
    words = sorted(words)
    if words:
        first, last = words[0][0], max(e for _, e, _ in words)
        covered, cs, ce = 0.0, None, None
        for s, e, _ in words:
            if ce is None or s > ce:
                covered += (ce - cs) if ce is not None else 0
                cs, ce = s, e
            else:
                ce = max(ce, e)
        covered += ce - cs
        m["silence_ratio"] = round(1 - covered / max(last - first, 1e-6), 3)
        if m["silence_ratio"] > SILENCE_MAX:
            issues.append(_issue("silence", "film", first, m["silence_ratio"], SILENCE_MAX,
                                 fix="tighten the gaps between lines"))
        m["long_pauses_bad"] = []
        for (s0, e0, p0), (s1, _, p1) in zip(words, words[1:]):
            gap = s1 - e0
            if gap >= LONG_PAUSE - 1e-9 and p0 == p1:
                m["long_pauses_bad"].append({"at": round(e0, 2), "length": round(gap, 2)})
                issues.append(_issue("pause_in_para", _ref(shots, e0), e0, round(gap, 2), LONG_PAUSE,
                                     fix="shorten the pause; long pauses belong between paragraphs"))
        # cuts: never inside a sentence, and not too soon after one ends
        m["cuts_bad"] = []
        for c in cuts:
            if c <= EPS or c >= dur - EPS:
                continue
            inside = [x for x in sents if x["start"] + EPS < c < x["end"] - EPS]
            if inside:
                x = inside[0]
                nxt = [y["start"] for y in sents if y["start"] >= x["end"] - 1e-6]
                ok_at = x["end"] + min(CUT_AFTER, (min(nxt) - x["end"]) if nxt else CUT_AFTER)
                m["cuts_bad"].append({"at": round(c, 2), "sentence_end": round(x["end"], 2)})
                issues.append(_issue("cut_in_sentence", _ref(shots, c), c, round(x["end"] - c, 2), 0.0,
                                     text=f"\"{x['text']}…\"" if x["text"] else "", fix=f"move the cut to ≥ {ok_at:.2f} s"))
                continue
            before = [x["end"] for x in sents if x["end"] <= c + EPS]
            after = [x["start"] for x in sents if x["start"] >= c - EPS]
            if before:
                gap = (min(after) - max(before)) if after else float("inf")
                need = min(CUT_AFTER, gap)
                if c - max(before) < need - EPS:
                    m["cuts_bad"].append({"at": round(c, 2), "sentence_end": round(max(before), 2)})
                    issues.append(_issue("cut_too_soon", _ref(shots, c), c, round(c - max(before), 2), round(need, 2),
                                         fix=f"move the cut to ≥ {max(before) + need:.2f} s"))
        # the shot holding each paragraph's last word
        bounds = sorted({0.0, dur, *[c for c in cuts if EPS < c < dur - EPS]})
        last_word = {}
        for s, e, p in words:
            last_word[p] = max(last_word.get(p, 0), e)
        m["key_shots_bad"] = []
        for p, t in sorted(last_word.items(), key=lambda kv: kv[1]):
            for a, b in zip(bounds, bounds[1:]):
                if a <= t - 1e-6 < b or (b == bounds[-1] and t <= b):
                    if b - a < KEY_SHOT - 1e-6:
                        m["key_shots_bad"].append({"para": p, "shot_length": round(b - a, 2)})
                        issues.append(_issue("key_shot_short", _ref(shots, a), a, round(b - a, 2), KEY_SHOT,
                                             text=p, fix=f"hold the shot with the last words of {p} for ≥ {KEY_SHOT} s"))
                    break
        m["tail_s"] = round(dur - last, 2)
    elif shots:
        m["tail_s"] = 0.0
    if "tail_s" in m and m["tail_s"] > TAIL_MAX:
        issues.append(_issue("tail", "film", dur, m["tail_s"], TAIL_MAX, fix="end the film sooner after the last word"))
    # shot lengths (020)
    m["shots_short"], m["shots_long"] = [], []
    for s in shots or []:
        L = round(s["t1"] - s["t0"], 3)
        if L < SHOT_MIN - 1e-6 and s["t1"] < dur - 1e-6:          # the very last shot may be a short tail
            m["shots_short"].append({"shot": s["id"], "length": L})
            issues.append(_issue("shot_short", s["id"], s["t0"], L, SHOT_MIN, fix=f"merge or lengthen to ≥ {SHOT_MIN} s"))
        if L > shot_max + 1e-6:
            m["shots_long"].append({"shot": s["id"], "length": L})
            issues.append(_issue("shot_long", s["id"], s["t0"], L, shot_max, fix=f"split the shot (≤ {shot_max:g} s)"))
    # subtitles: on screen ≥ max(1.8 s, the speech they carry + 0.6 s)
    m["cues_short"] = []
    for i, (a, b, text) in enumerate(cues or [], 1):
        need = max(CUE_MIN, speech_in(words, a, b) + CUE_PAD) if words else CUE_MIN
        if b - a < need - 1e-6:
            m["cues_short"].append({"cue": i, "at": round(a, 2), "length": round(b - a, 2), "need": round(need, 2)})
            issues.append(_issue("cue_short", f"cue {i}", a, round(b - a, 2), round(need, 2), text=str(text)[:30],
                                 fix="merge it with a neighbouring subtitle"))
    # text cards: the library's reading rule (need/got come from it)
    m["cards_short"] = []
    for k in cards or []:
        if k["got"] < k["need"] - 1e-6:
            m["cards_short"].append(k)
            issues.append(_issue("card_read", k.get("shot") or _ref(shots, k["at"]), k["at"], round(k["got"], 2),
                                 round(k["need"], 2), text=str(k.get("text", ""))[:30], fix="keep the card on screen longer"))
    return m, issues


MESSAGES = {   # the finished-film qc keeps its 010 wording
    "silence": lambda i: f"the narration is silent {i['measure']:.0%} of the time; at most {SILENCE_MAX:.0%}",
    "pause_in_para": lambda i: f"a {i['measure']:.1f} s pause at {i['at']:.1f} s inside one paragraph; long pauses belong between paragraphs",
    "cut_in_sentence": lambda i: f"a cut at {i['at']:.1f} s comes before the sentence ending at {i['at'] + i['measure']:.1f} s has settled "
                                 f"(cut at least {CUT_AFTER} s after a sentence, never inside one)",
    "cut_too_soon": lambda i: f"a cut at {i['at']:.1f} s comes before the sentence ending at {i['at'] - i['measure']:.1f} s has settled "
                              f"(cut at least {CUT_AFTER} s after a sentence, never inside one)",
    "key_shot_short": lambda i: f"the shot with the last words of {i['text']} lasts {i['measure']:.2f} s; at least {KEY_SHOT} s",
    "tail": lambda i: f"the film ends {i['measure']:.1f} s after the last word; at most {TAIL_MAX} s",
    "shot_short": lambda i: f"shot {i['ref']} lasts {i['measure']:.2f} s; at least {SHOT_MIN} s",
    "shot_long": lambda i: f"shot {i['ref']} lasts {i['measure']:.2f} s; at most {i['limit']:g} s",
    "cue_short": lambda i: f"{i['ref']} is on screen {i['measure']:.2f} s; at least {i['limit']:.2f} s",
    "card_read": lambda i: f"the card \"{i['text']}\" at {i['at']:.1f} s is on screen {i['measure']:.2f} s; reading needs {i['limit']:.2f} s",
}


def message(i: dict) -> str:
    f = MESSAGES.get(i["rule"])
    return f(i) if f else f"{i['rule']} at {i['ref']}: {i['measure']} (limit {i['limit']})"


def line(i: dict) -> str:
    """One report line (contracts/cli.md): ref, time, rule, measure vs limit, text, fix."""
    at = f"{i['at']:.2f} s" if isinstance(i.get("at"), (int, float)) else ""
    if i["rule"] == "cut_in_sentence":
        what = f"the sentence ends {i['measure']} s later"
    else:
        cmp_ = {"silence": ">", "tail": ">", "shot_long": ">", "pause_in_para": "≥", "pause_in_line": "≥",
                "tail_mismatch": ">"}.get(i["rule"], "<")
        what = f"{i['measure']} {cmp_} {i['limit']}"
    s = f"{i['ref']} {at}  {i['rule']} {what}"
    if i.get("text"):
        s += f"  {i['text']}"
    if i.get("fix"):
        s += f"  → {i['fix']}"
    if i.get("excepted"):
        s += f"  (excepted: {i['excepted']['reason']})"
    return s
