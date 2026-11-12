"""Tier 1: check the film's plan before any frame is rendered (specs/020 US1; FR-005 – FR-008; research R3, R4).

Reads window.SHOTS / DUR / CUES / CARDS from the page once (plan.mjs, no frames drawn) and caches them in
.check/plan-input.json under the source fingerprint, then runs the shared rhythm rules (rhythm.py) on the shot list,
the script sentences laid on the word stamps, the subtitles and the text cards."""
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

from filmcheck import qc, rhythm, stylerefs, tiers

HERE = Path(__file__).resolve().parent
FPS_TOL = 1 / 24 + 1e-3
LATIN_CPS, CJK_CPS, READ_PAD, READ_MIN = 15, 4.5, 1.5, 1.5        # core/render/readcheck.mjs defaults
CJK = re.compile(r"[぀-ヿ㐀-鿿가-힯豈-﫿]")
RC_LINE = re.compile(r"^(OK|BAD)\s+(\S+)\s+at ([\d.]+)s\s+\d+ chars\s+need ([\d.]+)s\s+got ([\d.]+)s\s+(\".*\")?")
RC_PARTIAL = re.compile(r"^BAD\s+(\S+)\s+at ([\d.]+)s\s+never fully visible.*?(\".*\")?\s*$")


class PlanError(Exception):
    """The plan cannot be read (exit code 2)."""


def read_need(text: str) -> float:
    cjk = len(CJK.findall(text))
    other = sum(1 for ch in text if not ch.isspace()) - cjk
    return max(READ_MIN, cjk / CJK_CPS + other / LATIN_CPS + READ_PAD)


def _node(args, timeout=600):
    if not shutil.which("node"):
        raise PlanError("node is not installed (sh bin/studio setup)")
    p = subprocess.run(["node", *map(str, args)], capture_output=True, text=True, timeout=timeout)
    return p


def norm_shots(rows, dur: float) -> tuple:
    """([{id, t0, t1, set}], warnings). Raises PlanError on a broken list (data-model "Shot")."""
    shots, warns, seen = [], [], set()
    for n, r in enumerate(rows, 1):
        if not isinstance(r, (list, tuple)) or len(r) < 2:
            raise PlanError(f"window.SHOTS row {n} is not [t0, t1, set, id]")
        t0, t1 = float(r[0]), float(r[1])
        sid = str(r[3]) if len(r) > 3 and r[3] not in (None, "") else ""
        if not sid:
            sid = f"S{n}"
            if not any("have no id" in w for w in warns):
                warns.append("some shots have no id in window.SHOTS: named S<n>")
        if sid in seen:
            raise PlanError(f"shot id {sid} appears twice in window.SHOTS")
        seen.add(sid)
        if not (0 <= t0 < t1 <= dur + FPS_TOL):
            raise PlanError(f"shot {sid} runs {t0:.3f}–{t1:.3f} s, outside 0–{dur:.3f} s or backwards")
        shots.append({"id": sid, "t0": round(t0, 4), "t1": round(min(t1, dur), 4), "set": str(r[2]) if len(r) > 2 else ""})
    shots.sort(key=lambda s: s["t0"])
    if shots and shots[0]["t0"] > FPS_TOL:
        raise PlanError(f"the first shot starts at {shots[0]['t0']:.3f} s, not 0")
    for a, b in zip(shots, shots[1:]):
        if abs(b["t0"] - a["t1"]) > FPS_TOL:
            raise PlanError(f"shots {a['id']} and {b['id']} do not meet ({a['t1']:.3f} s vs {b['t0']:.3f} s)")
    return shots, warns


def film_cues(d: Path, page_cues):
    """[[t0, t1, text]] and where they came from."""
    if page_cues:
        return [[float(c[0]), float(c[1]), str(c[2])] for c in page_cues], "window.CUES"
    p = d / "cues.json"
    if p.is_file():
        try:
            rows = json.loads(p.read_text(encoding="utf-8"))
            out = [[float(c["t0"]), float(c["t1"]), str(c["text"])] if isinstance(c, dict) else [float(c[0]), float(c[1]), str(c[2])]
                   for c in rows]
            return out, "cues.json"
        except (OSError, ValueError, KeyError, IndexError, TypeError) as e:
            raise PlanError(f"cues.json cannot be read: {e}") from None
    srt = d / f"{d.name}.srt"
    if srt.is_file():
        from filmcheck import publish
        return [[c["start"], c["end"], " ".join(c["lines"])] for c in publish.read_srt(srt)], srt.name
    return None, None


def readcheck_cards(d: Path, lib) -> list:
    """Cards measured by the library's readcheck (slow: it draws the film) when the page has no window.CARDS."""
    p = subprocess.run(["node", "core/render/readcheck.mjs", str(d)], cwd=str(lib), capture_output=True, text=True,
                       timeout=7200)
    if p.returncode == 2:
        return []
    out = []
    for ln in p.stdout.splitlines():
        m = RC_LINE.match(ln.strip())
        if m:
            out.append({"id": m.group(2), "t0": float(m.group(3)), "need": float(m.group(4)), "got": float(m.group(5)),
                        "text": json.loads(m.group(6)) if m.group(6) else ""})
            continue
        m = RC_PARTIAL.match(ln.strip())          # a card never fully on screen cannot be read: got 0 s
        if m:
            text = json.loads(m.group(3)) if m.group(3) else ""
            out.append({"id": m.group(1), "t0": float(m.group(2)), "need": round(read_need(text), 2), "got": 0.0,
                        "text": text, "partial": True})
    return out


def read_input(d: Path, lib, fp: str) -> dict:
    cache = d / ".check" / "plan-input.json"
    try:
        c = json.loads(cache.read_text(encoding="utf-8"))
        if c.get("fingerprint") == fp:
            return c
    except (OSError, ValueError):
        pass
    if not (d / "index.html").is_file():
        raise PlanError(f"films/{d.name}/index.html is not there")
    if not lib or not Path(lib, "core/render/page.mjs").is_file():
        raise PlanError("the library is not installed (sh bin/studio deps)")
    p = _node([HERE / "plan.mjs", d, lib])
    try:
        page = json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise PlanError(f"the page could not be read: {(p.stderr or p.stdout).strip()[-300:]}") from None
    if not isinstance(page.get("dur"), (int, float)) or page["dur"] <= 0:
        raise PlanError("the page has no window.DUR")
    dur = float(page["dur"])
    warns = []
    shots = None
    if page.get("shots"):
        shots, warns = norm_shots(page["shots"], dur)
    cues, cues_from = film_cues(d, page.get("cues"))
    if page.get("cards") is not None:
        cards = [{"id": str(k[2]), "t0": float(k[0]), "t1": float(k[1]), "text": str(k[3]),
                  "need": round(read_need(str(k[3])), 2), "got": round(float(k[1]) - float(k[0]), 2)} for k in page["cards"]]
        cards_from = "window.CARDS"
    else:
        cards, cards_from = readcheck_cards(d, lib), "readcheck"
    c = {"fingerprint": fp, "dur": dur, "shots": shots, "cues": cues, "cues_from": cues_from, "cards": cards,
         "cards_from": cards_from, "warnings": warns}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    return c


def run(film_dir: Path, lib) -> dict:
    t0 = time.time()
    d = Path(film_dir)
    fp = tiers.fingerprint(d)
    inp = read_input(d, lib, fp)
    dur, shots = inp["dur"], inp["shots"]
    style = stylerefs.load(d)
    skipped = list(inp.get("warnings") or [])
    if not shots:
        skipped.append("no shot list (window.SHOTS): shot rules skipped")
    if inp["cards_from"] == "readcheck":
        skipped.append("cards via readcheck (the page has no window.CARDS)")
    try:
        nar = qc.load_narration(d)
    except qc.QcError as e:
        raise PlanError(str(e)) from None
    sents, words = [], []
    if nar:
        words = sorted((s, e, ln["para"]) for ln in nar["lines"] for (_, s, e) in ln["words"])
        sents = rhythm.sentences(nar["lines"], qc.line_texts(d, nar))
        last = max(e for _, e, _ in words)
        if last > dur + rhythm.EPS:
            raise PlanError(f"the last word ends at {last:.2f} s, after the film ({dur:.2f} s)")
    cards = [{"id": k["id"], "at": k["t0"], "need": k["need"], "got": k["got"], "text": k["text"]} for k in inp["cards"] or []]
    if nar:
        m, issues = rhythm.measure(sents, words, dur, shots=shots, cuts=None if shots else [], cues=inp["cues"],
                                   cards=cards, style=style)
    else:                                   # US1 AC6: no narration → shot lengths, tail after the last shot, cards
        m, issues = rhythm.measure([], [], dur, shots=shots, cards=cards, style=style)
    if not shots:                           # without a shot list, no shot rule applies
        issues = [i for i in issues if i["rule"] not in ("cut_in_sentence", "cut_too_soon", "key_shot_short",
                                                         "shot_short", "shot_long")]
    m["sentences"] = sents
    m["shots"] = len(shots or [])
    if shots and sents:                      # data-model "Shot.para": the paragraph of the first sentence in the shot
        for s in shots:
            x = next((x for x in sents if s["t0"] - 1e-6 <= x["start"] < s["t1"] - 1e-6), None) \
                or next((x for x in sents if x["start"] < s["t0"] < x["end"]), None)
            s["para"] = x["para"] if x else None
        inp["shots"] = shots
        (d / ".check" / "plan-input.json").write_text(json.dumps(inp, ensure_ascii=False), encoding="utf-8")
    m["narration"] = bool(nar)
    exc = tiers.load_exceptions(d)
    tiers.apply_exceptions(issues, exc)
    res = tiers.result("plan", issues, m, skipped, time.time() - t0, fp, exceptions=exc,
                       sources={"cues": inp["cues_from"], "cards": inp["cards_from"]})
    tiers.save_tier(d, "plan", res)
    return res
