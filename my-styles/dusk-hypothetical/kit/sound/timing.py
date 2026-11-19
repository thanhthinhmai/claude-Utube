"""Line timing by the style's reading rhythm (specs/023 FR-017, TEMPLATE.md §15). Pure Python.

schedule(lines, spoken, template) → ({id: start}, end): each line starts after the one before has been spoken plus
a pause from template.json → voice (middle of the measured p25–p75): inside a sentence, after a sentence, between
paragraphs, and a longer pause before a line that opens with a number."""
import re

NUM_WORDS = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen "
             "eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand million billion half dozen")
NUM = re.compile(r"^\W*(\d|(" + "|".join(NUM_WORDS.split()) + r")\b)", re.I)
DEFAULT = {"pause_in": [0.28, 0.44], "pause_sent": [0.42, 0.54], "pause_para": [0.64, 0.74], "pre_number": [0.46, 0.64]}


def mid(r):
    return round((r[0] + r[1]) / 2, 3)


def gap(cur: dict, nxt: dict, voice: dict) -> float:
    v = {**DEFAULT, **(voice or {})}
    if nxt.get("para") != cur.get("para"):
        g = mid(v["pause_para"])
    elif re.search(r"[.?!…]['\"”’)]*\s*$", cur.get("text", "")):
        g = mid(v["pause_sent"])
    else:
        g = mid(v["pause_in"])
    if NUM.match(nxt.get("text", "")):
        g = max(g, mid(v["pre_number"]))
    return g


def schedule(lines: list, spoken: dict, template: dict = None, extra: dict = None):
    """lines: [{id, para, text}]; spoken: {id: seconds of speech}; extra: {id: seconds added before that line}."""
    voice = (template or {}).get("voice") or {}
    at, t = {}, 0.0
    for i, ln in enumerate(lines):
        if i:
            t += gap(lines[i - 1], ln, voice) + (extra or {}).get(ln["id"], 0.0)
        at[ln["id"]] = round(t, 3)
        t += spoken[ln["id"]]
    return at, round(t, 3)


def fit(lines: list, spoken: dict, template: dict = None, extra: dict = None, silence_max: float = 0.19, tail: float = 1.45):
    """schedule() with the style's pauses shrunk together (their order kept) until the voice gaps fit the studio's silence
    rule (specs/020: ≤ 20 % of the film; 0.19 leaves a margin). The measured pauses come from whisper word times and run
    long, and films with many short lines have many gaps. Returns (starts, end, factor); the story's extra beats stay."""
    voice = {**DEFAULT, **((template or {}).get("voice") or {})}
    talk = sum(spoken[ln["id"]] for ln in lines)
    k = 1.0
    while True:
        tpl = {**(template or {}), "voice": {key: [v[0] * k, v[1] * k] for key, v in voice.items() if isinstance(v, list) and len(v) == 2}}
        at, end = schedule(lines, spoken, tpl, extra)
        if (end + tail - talk) / (end + tail) <= silence_max or k <= 0.2:
            return at, end, round(k, 2)
        k -= 0.05
