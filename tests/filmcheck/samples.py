"""Sample scripts and films for tests/filmcheck (specs/010). Nothing here is committed media: films are made with ffmpeg.

Scripts: GOOD_EN / GOOD_VI pass every rule; BAD maps a rule name to a script that breaks that rule (contracts/cli.md).
Films:   make_film(root, name, **change) writes films/<name>/ with an mp4, voices/words.json, voices/dur.json and
         narration.json. With no change the film passes every QC rule; each change breaks one rule."""
import json
import subprocess
from pathlib import Path

# ---------- scripts ----------
GOOD_EN = """Title: The Baker Who Wakes the Street
Target: 45s
Language: en

[P01] Hanoi has more than six million motorbikes. So why is one street silent at four in the morning?
[P02] Minh is a night baker. He lights his oven before the city wakes, and the first loaf is always for his mother.
[P03] He shapes each loaf by hand. The dough is soft, warm, and a little stubborn, like the man himself.
[P04] By five, the smell drifts out the door. Neighbours stop, half asleep, and leave with bread still too hot to hold.
[P05] Then the motorbikes return, and the street forgets it was ever quiet. But Minh is already planning tomorrow.
"""
GOOD_EN_SOURCES = '- [P01] "six million motorbikes": Hanoi Department of Transport, 2024, https://example.org/hanoi-motorbikes\n'
OPENED = [{"url": "https://example.org/hanoi-motorbikes", "final_url": "https://example.org/hanoi-motorbikes",
           "status": 200, "at": "2026-11-10T00:00:00Z"}]

GOOD_VI = """Title: Người làm bánh đánh thức con phố
Target: 30s
Language: vi

[P01] Hà Nội có hơn sáu triệu xe máy. Vậy tại sao một con phố lại im lặng lúc bốn giờ sáng?
[P02] Anh Minh làm bánh mì ca đêm. Anh nhóm lò trước khi thành phố thức dậy.
[P03] Đến năm giờ, mùi bánh lan ra cửa. Hàng xóm dừng lại, mang về những ổ bánh còn nóng hổi.
[P04] Rồi xe máy quay lại, và con phố quên mất nó từng yên tĩnh. Nhưng anh Minh đã nghĩ tới ngày mai.
"""
GOOD_VI_SOURCES = '- [P01] "sáu triệu xe máy": Sở Giao thông Hà Nội, 2024, https://example.org/hanoi-motorbikes\n'


def _swap(text, old, new):
    assert old in text, old
    return text.replace(old, new, 1)


# rule -> (script, sources); OPENED is used for all of them unless the rule is about it
BAD = {
    "format": (_swap(GOOD_EN, "Language: en\n", ""), GOOD_EN_SOURCES),
    "sources": (GOOD_EN, ""),
    "sources_unopened": (GOOD_EN, GOOD_EN_SOURCES.replace("hanoi-motorbikes", "never-opened")),
    "length": (_swap(GOOD_EN, "Target: 45s", "Target: 90s"), GOOD_EN_SOURCES),
    "long_sentence": (_swap(GOOD_EN, "Minh is a night baker.",
                            "Minh is a night baker who works alone in a narrow kitchen behind his parents' old shop "
                            "and has done so every single night for most of his adult life."), GOOD_EN_SOURCES),
    "no_hook": (_swap(GOOD_EN, "Hanoi has more than six million motorbikes. So why is one street silent at four in the morning?",
                      "Hanoi is a big city with a lot of streets. One street is calm early in the day."), ""),
    "intro_opening": (_swap(GOOD_EN, "[P01] Hanoi has", "[P01] Welcome to our channel. Hanoi has"), GOOD_EN_SOURCES),
    "cliche": (_swap(GOOD_EN, "But Minh is already planning tomorrow.",
                     "At the end of the day, Minh is a game changer."), GOOD_EN_SOURCES),
    "risky_number": (_swap(GOOD_EN, "By five,", "By 4:45,"), GOOD_EN_SOURCES),
    "punctuation": (_swap(GOOD_EN, "The dough is soft, warm, and a little stubborn, like the man himself.",
                          "The dough (soft) — warm (very) — and (a little) stubborn — like (him)."), GOOD_EN_SOURCES),
}


def long_script(seconds=200, gap_paragraphs=()):
    """A script of about `seconds` at 150 words/min. Paragraphs listed in gap_paragraphs carry no retention marker,
    so a long stretch of them makes a retention gap."""
    plain = "Minh walks along the street and looks at the shops and the people who pass him on the way to work."
    marked = "But why does nobody notice the small bakery at the corner of the street?"
    n = max(1, round(seconds * 150 / 60 / 20))
    paras = [f"[P{i:02d}] {plain if i in gap_paragraphs else marked} {plain}" for i in range(1, n + 1)]
    words = sum(len(p.split()) - 1 for p in paras)
    head = f"Title: A Long Walk\nTarget: {round(words / 150 * 60)}s\nLanguage: en\n\n"
    return head + "\n".join(paras) + "\n"


def write_script(film_dir: Path, script: str, sources: str, opened=OPENED) -> Path:
    film_dir.mkdir(parents=True, exist_ok=True)
    (film_dir / "SCRIPT.md").write_text(script, encoding="utf-8")
    (film_dir / "SOURCES.md").write_text(sources or "no factual claims\n", encoding="utf-8")
    if opened is not None:
        (film_dir / ".check").mkdir(exist_ok=True)
        (film_dir / ".check" / "opened.json").write_text(json.dumps(opened), encoding="utf-8")
    return film_dir


# ---------- films ----------
WORD, GAP = 0.39, 0.01      # one spoken word and the gap after it (silence ratio about 0.15 for the good film)


def _line(lid, para, at, n, word=WORD, gap=GAP):
    words, t = [], 0.0
    for i in range(n):
        words.append([f"w{i}" + ("." if i == n - 1 else ""), round(t, 3), round(t + word, 3)])
        t += word + gap
    return {"id": lid, "para": para, "at": at, "words": words}


def layout(word=WORD, gap=GAP, pause_in_p01=0.0):
    """The good film's lines: P01 two lines, P02 two lines, P03 two lines (cuts after P01 and after P02)."""
    step = word + gap
    lines, t = [], 0.5
    for lid, para, n, before in (("l01", "P01", 8, 0), ("l02", "P01", 6, 0.06 + pause_in_p01), ("l03", "P02", 10, 0.8),
                                 ("l04", "P02", 7, 0.06), ("l05", "P03", 5, 0.8), ("l06", "P03", 4, 0.54)):
        t += before
        lines.append(_line(lid, para, round(t, 3), n, word, gap))
        t += n * step - gap
    return lines


def _end(line):
    return line["at"] + line["words"][-1][2]


def make_film(root: Path, name: str, *, word=WORD, gap=GAP, pause_in_p01=0.0, extra_cuts=(), move_cut=None,
              tail=1.1, still_shot=None, write_cuts=True, srt=None, script=False, lines_text=None) -> Path:
    """Write films/<name>/ under root. Cuts fall 0.5 s after the last word of P01 and of P02."""
    d = Path(root) / "films" / name
    (d / "voices").mkdir(parents=True, exist_ok=True)
    lines = layout(word, gap, pause_in_p01)
    cuts = [0.0, round(_end(lines[1]) + 0.5, 3), round(_end(lines[3]) + 0.5, 3)]
    if move_cut:
        cuts[move_cut[0]] = move_cut[1]
    cuts = sorted(set(cuts) | set(extra_cuts))
    duration = round(_end(lines[-1]) + tail, 3)
    (d / "voices" / "words.json").write_text(json.dumps({L["id"]: L["words"] for L in lines}), encoding="utf-8")
    (d / "voices" / "dur.json").write_text(json.dumps({L["id"]: L["words"][-1][2] for L in lines}), encoding="utf-8")
    narr = {"words_file": "voices/words.json", "durations_file": "voices/dur.json",
            "lines": [{"id": L["id"], "para": L["para"], "at": L["at"]} for L in lines]}
    if write_cuts:
        narr["cuts"] = cuts
    if script:            # a SCRIPT.md and the lines.json the voice was made from (T035)
        said = {L["id"]: " ".join(w[0] for w in L["words"]) for L in lines}
        paras = {}
        for L in lines:
            paras.setdefault(L["para"], []).append(said[L["id"]])
        (d / "SCRIPT.md").write_text("Title: Test\nTarget: 20s\nLanguage: en\n\n"
                                     + "\n".join(f"[{p}] {' '.join(t)}" for p, t in paras.items()) + "\n", encoding="utf-8")
        rows = [{"id": k, "text": (lines_text or {}).get(k, v)} for k, v in said.items()]
        (d / "lines.json").write_text(json.dumps(rows), encoding="utf-8")
        narr["lines_file"] = "lines.json"
    (d / "narration.json").write_text(json.dumps(narr), encoding="utf-8")
    (d / "TREATMENT.md").write_text("Style: test-style\n", encoding="utf-8")
    if srt is not None:
        (d / f"{name}.srt").write_text(srt, encoding="utf-8")
    _render(d / f"{name}.mp4", cuts, duration, still_shot)
    return d


def _render(mp4: Path, cuts, duration, still_shot):
    """One moving test picture per shot, different for neighbouring shots, so scene cuts are clear; `still_shot`
    (an index) is a flat colour that never moves."""
    bounds = list(cuts) + [duration]
    inputs, chains = [], []
    for i in range(len(bounds) - 1):
        length = round(bounds[i + 1] - bounds[i], 3)
        if i == still_shot:
            inputs += ["-f", "lavfi", "-i", f"color=c=0x3366aa:s=320x180:r=24:d={length}"]
            chains.append(f"[{i}:v]format=yuv420p,setsar=1[v{i}]")
        else:                           # three clearly different moving pictures, so scene detection finds each cut
            src, post = [("testsrc2=s=320x180:r=24", ""), ("mandelbrot=s=320x180:r=24", ""),
                         ("testsrc2=s=320x180:r=24", "negate,")][i % 3]
            inputs += ["-f", "lavfi", "-t", str(length), "-i", src]
            chains.append(f"[{i}:v]{post}format=yuv420p,setsar=1[v{i}]")
    n = len(bounds) - 1
    inputs += ["-f", "lavfi", "-i", f"sine=frequency=330:sample_rate=48000:duration={duration}"]
    graph = ";".join(chains) + ";" + "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]"
    cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[v]", "-map", f"{n}:a",
           "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-shortest", str(mp4)]
    subprocess.run(cmd, check=True)
