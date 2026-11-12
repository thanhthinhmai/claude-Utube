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
    qcj = Path(root) / "my-styles" / "test-style" / "qc.json"     # the sample's shots run up to 9.4 s (specs/020 shot_long)
    qcj.parent.mkdir(parents=True, exist_ok=True)
    if not qcj.exists():
        qcj.write_text(json.dumps({"shot_max": 10}), encoding="utf-8")
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


# ---------- publish packs (specs/011) ----------
PUB_PARAS = [
    ("P01", ["Archaeologists found honey in an Egyptian tomb.", "It was 3,000 years old, and it was still good to eat.",
             "Ten thousand jars of food had turned to dust around it."]),
    ("P02", ["So what makes honey so stubborn?", "The answer starts with water, or rather the lack of it.",
             "Honey is mostly sugar and very little else."]),
    ("P03", ["Germs need water to live.", "Honey pulls water out of anything that lands in it, like a sponge.",
             "A germ that falls in simply dries out."]),
    ("P04", ["Then there is acid.", "Honey is about as sour as orange juice, which most germs cannot stand.",
             "And bees add one more trick of their own."]),
    ("P05", ["An enzyme from the bees makes a little hydrogen peroxide.", "So every jar carries its own cleaner.",
             "Seal it well, and it may outlast us all."]),
]
PUB_SOURCES = ('- [P01] "3,000 years old": Smithsonian Magazine, 2013, https://example.org/honey\n'
               '- [P04] "as sour as orange juice": National Honey Board, 2020, https://example.org/acid\n'
               '- [P05] "hydrogen peroxide": National Honey Board, 2020, https://example.org/acid\n')
PUB_PAGE = """<!doctype html><html><body style="margin:0;background:#000">
<div id="bg" style="position:fixed;inset:0"></div>
<div id="t" style="position:fixed;left:0;right:0;top:7%;text-align:center;font:700 60px sans-serif;color:#fff"><span>Honey</span></div>
<script>
window.DUR = DURATION;
window.render = (t) => { document.getElementById('bg').style.background = `hsl(${(t * 7) % 360},60%,30%)`; };
window.TEXTS = (t) => { const r = document.querySelector('#t span').getBoundingClientRect();
  return [{id: 't', text: 'Honey', x0: r.left, y0: r.top, x1: r.right, y1: r.bottom}]; };
render(0); window.READY = true;
</script></body></html>
"""


def pub_pack() -> dict:
    return {"language": "en",
            "titles": [{"angle": "curiosity", "text": "Why Honey From a Tomb Was Still Good to Eat",
                        "thumb": {"t": 5, "text": "Still sweet"}},
                       {"angle": "number", "text": "3,000 Years Old and Still Fine: The Secret of Honey",
                        "thumb": {"t": 20, "text": "Bees did this", "position": "center"}},
                       {"angle": "question", "text": "Can Honey Really Last Forever?",
                        "thumb": {"t": 35, "text": "Forever food?", "color": "#ffd23f", "plate": "#1a1a1a",
                                  "plate_opacity": 0.75}}],
            "hook": ["Archaeologists found honey in an Egyptian tomb.", "It was still good to eat."],
            "summary": "A short look at why honey resists germs: little water, a lot of acid, and an enzyme from bees.",
            "chapters": [{"from": "P01", "title": "The tomb"}, {"from": "P03", "title": "Too dry for germs"},
                         {"from": "P05", "title": "The bees' secret"}],
            "hashtags": ["#honey", "#science", "#food"]}


def make_publish_film(root: Path, name: str = "honey", *, narration=True, script=True, vertical=False, seconds=50.0,
                      pack=True, lines_file=True) -> Path:
    """A film for the publish pack: page, mp4, SCRIPT.md, SOURCES.md, voice files and pack.json (contracts/files.md).
    Paragraphs last about seconds/5 each, so chapters P01, P03, P05 are each at least 10 s at 50 s."""
    d = Path(root) / "films" / name
    (d / "voices").mkdir(parents=True, exist_ok=True)
    w, h = (1080, 1920) if vertical else (1920, 1080)
    lead, tail, para_gap, word_gap = 0.5, 1.2, 0.6, 0.05
    n_words = sum(len(s.split()) for _, ss in PUB_PARAS for s in ss)
    step = (seconds - lead - tail - para_gap * (len(PUB_PARAS) - 1)) / n_words
    words, durs, rows, lines, t, k = {}, {}, [], [], lead, 0
    for pi, (para, sents) in enumerate(PUB_PARAS):
        if pi:
            t += para_gap
        for s in sents:
            k += 1
            lid = f"l{k:02d}"
            ws, x = [], 0.0
            for tok in s.split():
                ws.append([tok, round(x, 3), round(x + step - word_gap, 3)])
                x += step
            words[lid], durs[lid] = ws, ws[-1][2]
            rows.append({"id": lid, "text": s})
            lines.append({"id": lid, "para": para, "at": round(t, 3)})
            t += x
    duration = round(t - word_gap + tail, 3)
    if narration:
        (d / "voices" / "words.json").write_text(json.dumps(words), encoding="utf-8")
        (d / "voices" / "dur.json").write_text(json.dumps(durs), encoding="utf-8")
        (d / "lines.json").write_text(json.dumps(rows), encoding="utf-8")
        narr = {"words_file": "voices/words.json", "durations_file": "voices/dur.json", "lines": lines, "cuts": [0.0]}
        if lines_file:
            narr["lines_file"] = "lines.json"
        (d / "narration.json").write_text(json.dumps(narr), encoding="utf-8")
    if script:
        body = "\n".join(f"[{p}] {' '.join(ss)}" for p, ss in PUB_PARAS)
        (d / "SCRIPT.md").write_text(f"Title: Honey Never Spoils\nTarget: {int(seconds)}s\nLanguage: en\n\n{body}\n",
                                     encoding="utf-8")
        (d / "SOURCES.md").write_text(PUB_SOURCES, encoding="utf-8")
    (d / "index.html").write_text(PUB_PAGE.replace("DURATION", str(duration)), encoding="utf-8")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x334455:s={w}x{h}:r=2:d={duration}",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(d / f"{name}.mp4")], check=True)
    if pack:
        (d / "publish").mkdir(exist_ok=True)
        (d / "publish" / "pack.json").write_text(json.dumps(pub_pack(), indent=1), encoding="utf-8")
    return d


def fake_thumbs(d: Path, rows=None, size=None) -> None:
    """Three plain thumbnails and a thumbs.json that passes, without a browser (contracts/files.md)."""
    pub = Path(d) / "publish"
    pub.mkdir(exist_ok=True)
    w, h = size or (1280, 720)
    out = []
    for i in (1, 2, 3):
        f = pub / f"thumbnail-{i}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x2255{i}0:s={w}x{h}",
                        "-frames:v", "1", str(f)], check=True)
        out.append({"file": f.name, "t": [5, 20, 35][i - 1], "w": w, "h": h, "bytes": f.stat().st_size, "text": "x",
                    "font": "sans-serif", "font_loaded": True, "text_height_ratio": 0.12, "contrast": 8.0,
                    "bg_luma": [0.05, 0.2], "missing_glyphs": []})
    for i, r in enumerate(rows or []):
        out[i].update(r)
    (pub / "thumbs.json").write_text(json.dumps(out), encoding="utf-8")


# ---------- channels and lessons (specs/012) ----------
def make_channel(root: Path, slug: str = "honey-facts", **over) -> dict:
    """A valid channel profile under root/channels/ (and the style it names under root/my-styles/)."""
    from filmcheck import channels
    style = over.get("style", "test-style")
    (Path(root) / "my-styles" / style).mkdir(parents=True, exist_ok=True)
    (Path(root) / "my-styles" / style / "style.json").write_text("{}", encoding="utf-8")
    ch = {"slug": slug, "name": "Honey Facts", "niche": "food science", "audience": "curious adults",
          "language": "en", "seconds": 50, "style": style, "voice": "af_bella", "speed": 1.0,
          "title_rules": "Lead with the surprise.", "thumbnail_rules": "Two to four words.", "title_max": 70,
          "hashtags": ["#honey"], "banned": ["shocking"], "decisions": [{"date": "2026-11-11", "text": "No songs with lyrics."}]}
    ch.update(over)
    return channels.save(root, ch, new=not (channels.channel_dir(root, slug) / "channel.json").exists())


def make_lesson(root: Path, scope: str, rule=None, status="active", what="A mistake", stop="Do not do it") -> dict:
    from filmcheck import channels
    return channels.add_lesson(channels.lessons_file(root, scope), what=what, why="Nothing checked it", stop=stop,
                               rule=rule, status=status)


# ---------- films for the QC tiers (specs/020) ----------
TIER_PAGE = r"""<!doctype html>
<html><head><meta charset="utf-8">
<style>html,body{margin:0;background:#000;overflow:hidden}canvas{display:block}
#card{position:fixed;left:0;right:0;text-align:center;color:#f2e6c8;font:700 64px sans-serif;opacity:0}
#sub{position:fixed;left:0;right:0;bottom:4%;text-align:center;color:#fff;font:600 40px sans-serif}</style>
</head><body><canvas id="c"></canvas><div id="card"></div><div id="sub"></div>
<script>
// Test film for the QC tiers (tests/filmcheck/samples.py make_tier_film): one look per shot on a 2D canvas.
const F = FILM_JSON;
const c = document.getElementById('c'); c.width = innerWidth; c.height = innerHeight;
const g = c.getContext('2d');
window.DUR = F.dur;
window.SHOTS = F.shots.map(s => [s.t0, s.t1, s.set || 'x', s.id]);
if (F.cues) window.CUES = F.cues;
if (F.cards) window.CARDS = F.cards.map(k => [k.t0, k.t1, k.id, k.text]);
let rnd = 1;
const R = () => (rnd = (rnd * 16807) % 2147483647) / 2147483647;
function look(s, t) {
  const W = c.width, H = c.height, k = s.look || 'good', moving = k !== 'still';
  const lt = moving ? t - s.t0 : 0;
  if (k === 'flat') { g.fillStyle = '#3a2f55'; g.fillRect(0, 0, W, H); return; }
  if (k === 'blown') { g.fillStyle = '#fff'; g.fillRect(0, 0, W, H); g.fillStyle = '#ddd'; g.fillRect(W * .4, H * .4, W * .1, H * .1); return; }
  if (k === 'cardbg') { g.fillStyle = '#120c1c'; g.fillRect(0, 0, W, H); return; }
  const dim = k === 'dark' ? 0.04 : (s.dim || 1);
  rnd = 1 + Math.round(s.t0 * 1000);
  const hue = s.hue ?? Math.round(R() * 360);
  const grd = g.createLinearGradient(0, 0, W, H);
  grd.addColorStop(0, `hsl(${hue},45%,${40 * dim}%)`); grd.addColorStop(1, `hsl(${(hue + 60) % 360},45%,${18 * dim}%)`);
  g.fillStyle = grd; g.fillRect(0, 0, W, H);
  for (let i = 0; i < 40; i++) {
    const x = R() * W + Math.sin(lt * 2 + i) * 40, y = R() * H, w = 40 + R() * 220, h = 40 + R() * 220;
    g.fillStyle = `hsl(${Math.round(R() * 360)},${30 + R() * 40}%,${(15 + R() * 55) * dim}%)`; g.fillRect(x, y, w, h);
  }
}
window.render = (t) => {
  if (window.CLEAN_SEEN !== undefined) window.CLEAN_SEEN = !!window.CLEAN;
  const s = F.shots.find(s => t >= s.t0 && t < s.t1) || F.shots[F.shots.length - 1];
  look(s, t);
  const card = document.getElementById('card'), k = (F.cards || []).find(k => t >= k.t0 && t < k.t1);
  card.textContent = k ? k.text : '';
  card.style.opacity = k && !window.CLEAN ? 1 : 0;
  card.style.top = k && k.pos === 'bottom' ? '84%' : '40%';
  const cue = (F.cues || []).find(q => t >= q[0] && t < q[1]);
  document.getElementById('sub').textContent = cue && !window.CLEAN ? cue[2] : '';
};
window.TEXTS = (t) => {
  const e = document.getElementById('card');
  if (+e.style.opacity < .5 || !e.textContent) return [];
  const r = e.firstChild ? (() => { const rg = document.createRange(); rg.selectNodeContents(e); return rg.getBoundingClientRect(); })() : e.getBoundingClientRect();
  return [{ id: 'card', text: e.textContent, x0: r.left, y0: r.top, x1: r.right, y1: r.bottom }];
};
window.render(0); window.READY = true;
</script></body></html>
"""


def speak(text: str, word=0.32, gap=0.04, sent_gap=0.3):
    """Word stamps [[word, start, end]] (relative to the line) for a line of text: sentence ends get a longer gap."""
    out, t = [], 0.0
    for w in text.split():
        out.append([w, round(t, 3), round(t + word, 3)])
        t += word + (sent_gap if w[-1] in ".?!" else gap)
    return out


def make_tier_film(root: Path, name: str, *, shots, lines=(), cues=None, cards=None, dur=None, style=None,
                   asr=None, script=True, export_shots=True) -> Path:
    """films/<name>/ for the 020 tiers. shots: [{id, t0, t1, look?, hue?, dim?}]; lines: [{id, para, at, text}]
    (stamps from speak(), or asr[id] when given: a different transcript of the same line); cues: [[t0, t1, text]];
    cards: [{id, t0, t1, text, pos?}]. No mp4: the page is the film."""
    d = Path(root) / "films" / name
    (d / "voices").mkdir(parents=True, exist_ok=True)
    words, durs = {}, {}
    for L in lines:
        ws = (asr or {}).get(L["id"]) or speak(L["text"])
        words[L["id"]] = ws
        durs[L["id"]] = round(max(w[2] for w in ws), 3)
    if lines:
        (d / "voices" / "words.json").write_text(json.dumps(words), encoding="utf-8")
        (d / "voices" / "dur.json").write_text(json.dumps(durs), encoding="utf-8")
        (d / "lines.json").write_text(json.dumps([{"id": L["id"], "para": L["para"], "text": L["text"]} for L in lines]),
                                      encoding="utf-8")
        (d / "narration.json").write_text(json.dumps({
            "words_file": "voices/words.json", "durations_file": "voices/dur.json", "lines_file": "lines.json",
            "lines": [{"id": L["id"], "para": L["para"], "at": L["at"]} for L in lines]}), encoding="utf-8")
        if script:
            paras = {}
            for L in lines:
                paras.setdefault(L["para"], []).append(L["text"])
            (d / "SCRIPT.md").write_text("Title: Test\nTarget: 60s\nLanguage: en\n\n"
                                         + "\n".join(f"[{p}] {' '.join(t)}" for p, t in paras.items()) + "\n", encoding="utf-8")
    total = dur if dur is not None else max(s["t1"] for s in shots)
    film = {"dur": total, "shots": shots, "cues": cues, "cards": cards}
    page = TIER_PAGE.replace("FILM_JSON", json.dumps(film))
    if not export_shots:
        page = page.replace("window.SHOTS = F.shots", "const NO_SHOTS = F.shots")
    (d / "index.html").write_text(page, encoding="utf-8")
    (d / "TREATMENT.md").write_text(f"Style: {style or 'test-style'}\n", encoding="utf-8")
    return d
