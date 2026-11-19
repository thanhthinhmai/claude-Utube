"""Demo film of the Sketch Explainer style (specs/028 US5): line times, shots, narration.json, cues.json, index.html.
The page holds only the scene table; the kit (kit/, copied by `sh bin/studio kit use`) draws everything.
Shot rules of the studio (specs/020): 1.1–6 s, no cut inside a sentence, the last shot of a paragraph ≥ 2.5 s."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(f"{HERE}/lines.json"))
D = json.load(open(f"{HERE}/voices/dur.json"))
IN_GAP, PARA_GAP, KEY, START, CAP = 0.15, 0.38, 2.5, 0.2, 5.4

# group lines into shots: same paragraph, at most CAP seconds of speech
groups, cur, cd = [], [], 0.0
for l in L:
    d = D[l["id"]]
    if cur and (l["para"] != cur[-1]["para"] or cd + d + IN_GAP > CAP):
        groups.append(cur); cur, cd = [], 0.0
    cur.append(l); cd += d + IN_GAP
groups.append(cur)
# a short last shot of a paragraph would have to wait for the key-shot length: take a line from the shot before
for i in range(1, len(groups)):
    g, p = groups[i], groups[i - 1]
    last_of_para = i + 1 == len(groups) or groups[i + 1][0]["para"] != g[-1]["para"]
    if last_of_para and p[-1]["para"] == g[0]["para"] and len(p) >= 2 and sum(D[l["id"]] for l in g) < KEY - 0.3:
        g.insert(0, p.pop())

# line times: a short gap inside a paragraph, a longer one between paragraphs; a shot is cut just before the next
# group's first word (never inside a sentence, never right on a sentence end), and the last shot of a paragraph
# lasts at least KEY seconds (the following speech waits when it must)
at, shots, t, cut = {}, [], START, 0.0
for i, g in enumerate(groups):
    if i:
        newpara = g[0]["para"] != groups[i - 1][-1]["para"]
        t += PARA_GAP if newpara else IN_GAP
        prev_end = at[groups[i - 1][-1]["id"]] + D[groups[i - 1][-1]["id"]]
        if newpara and t - 0.12 - cut < KEY:
            t = cut + KEY + 0.12
        shots[-1]["t1"] = round(max(t - 0.12, prev_end + (0.42 if newpara else 0.22)), 3)
        t = max(t, shots[-1]["t1"])
        cut = shots[-1]["t1"]
    for j, l in enumerate(g):
        if j:
            t += IN_GAP
        at[l["id"]] = round(t, 3); t += D[l["id"]]
    shots.append({"t0": round(cut, 3), "t1": None, "lines": [l["id"] for l in g]})
shots[-1]["t1"] = round(t + 0.6, 3)
DUR = round(shots[-1]["t1"], 3)

# the scene table: one scene per shot (sets, people, boards from kit/catalog.json)
G, B, GOLD, GREY = "growth", "blue", "gold", "grey"
TABLE = [
    dict(set="custom:cafe", cam={"size": "med"}, cast=[{"who": "extra:3", "x": 760, "pose": "hold", "expr": "happy"}, {"who": "worker", "x": 1180, "pose": "palm", "expr": "happy"}],
         sign={"who": 0, "text": "$5", "sub": "a latte"}, cap=["a latte", "", 1500, 160]),
    dict(set="whiteboard-room", cam={"size": "med"}, cast=[{"who": "narrator", "x": 1520, "pose": "pointL", "expr": "happy"}],
         board={"k": "list", "title": "the cup", "rows": ["coffee", "milk", "cup", "≈ $1.20"], "hi": 3, "step": 0.45}),
    dict(set="custom:cafe", cam={"size": "cu", "on": 0}, cast=[{"who": "narrator", "x": 820, "pose": "shrug", "expr": "shocked"}, {"who": "worker", "x": 1260, "expr": "smug"}],
         bub=[[0, "$4?!", 0.3], [1, "Nope.", 1.9]]),
    dict(set="street-day", cam={"size": "huge"}, cast=[{"who": "narrator", "x": 1500, "s": 0.3, "pose": "palm", "expr": "happy"}, {"who": "extra:5", "x": 620, "s": 0.3, "walk": [380, 760, 0.2, 1.6]}]),
    dict(set="living-room", cam={"size": "wide"}, cast=[{"who": "narrator", "x": 960, "pose": "hold", "expr": "excited"}],
         sign={"who": 0, "text": "$30,000", "sub": "sales a month", "w": 420}),
    dict(set="chalk-room", cam={"size": "med"}, cast=[{"who": "narrator", "x": 1500, "pose": "pointL", "expr": "neutral"}],
         board={"k": "pie", "title": "where each dollar goes", "sl": [["ingredients 30%", 30, GOLD], ["staff 30%", 30, B]], "at": 0.2}),
    dict(set="chalk-room", cam={"size": "insert"},
         board={"k": "pie", "title": "where each dollar goes", "sl": [["ingredients 30%", 30, GOLD], ["staff 30%", 30, B], ["rent 12%", 12, GREY]], "at": -2}),
    dict(set="office", cam={"size": "med"}, cast=[{"who": "auditor", "x": 960, "seat": True, "s": 0.8, "expr": "deadpan"}],
         lab=[["power, ads, more", "", 1500, 200, 1150, 380, 0.3]]),
    dict(set="tv-room", cam={"size": "med"}, cast=[{"who": "narrator", "x": 1500, "pose": "pointL", "expr": "excited", "hop": 1.2}],
         board={"k": "num", "text": "~19%", "sub": "left over, a well-run café", "col": G, "size": 150}),
    dict(set="ots-office", cam={"size": "ots"}, cast=[{"who": "narrator", "x": 1000, "pose": "hold", "expr": "happy"}],
         sign={"who": 0, "text": "~95¢", "sub": "per $5 latte", "col": G}),
    dict(set="meeting", cam={"size": "wide"}, cast=[{"who": "extra:1", "x": 420}, {"who": "banker", "x": 760, "expr": "calm"}, {"who": "extra:6", "x": 1100}, {"who": "narrator", "x": 1460, "pose": "palm"}],
         lab=[["aim: 10–15%", "", 960, 160, 760, 420, 0.3]]),
    dict(set="custom:cafe", cam={"size": "huge"}, cast=[{"who": "worker", "x": 1000, "pose": "palm", "expr": "happy"}] +
         [{"who": f"extra:{i}", "x": 0, "walk": [1900 - i * 160, 1260 + i * 150, 0.2 + i * 0.3, 2.8 + i * 0.3]} for i in range(4)],
         props=[["coinstack", 1000, 860, 0.9, 12]]),
    dict(set="sunset-city", cam={"size": "wide"}, cast=[{"who": "narrator", "x": 760, "pose": "hold", "expr": "beam"}, {"who": "worker", "x": 1160, "pose": "up", "expr": "excited"}],
         sign={"who": 0, "text": "200 a day", "sub": "the café's example", "w": 420}),
]
assert len(TABLE) == len(shots), (len(TABLE), len(shots))
CUSTOM = {"cafe": {"parts": [["sky", {}], ["skyline", {"y": 640, "col": "#a9c7d1", "seed": 2}], ["ground", {"y": 660}], ["stall", {"x": 980, "y": 560}]], "floor": 1000}}
scenes = []
for i, (s, row) in enumerate(zip(shots, TABLE)):
    sc = {"id": f"S{i + 1:03d}", "dur": round(s["t1"] - s["t0"], 3)}
    sc.update(row)
    scenes.append(sc)

json.dump({"words_file": "voices/words.json", "durations_file": "voices/dur.json", "lines_file": "lines.json",
           "lines": [{"id": l["id"], "para": l["para"], "at": at[l["id"]]} for l in L], "cuts": [s["t0"] for s in shots]},
          open(f"{HERE}/narration.json", "w"), indent=1)
json.dump({"dur": DUR, "lines": [{"id": l["id"], "at": at[l["id"]]} for l in L], "shots": [dict(s, id=sc["id"], set=sc.get("set")) for s, sc in zip(shots, scenes)]},
          open(f"{HERE}/plan.json", "w"), indent=1)
page = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>The Five-Dollar Latte</title></head>
<body>
<script type="module">
// Demo film of the Sketch Explainer style (specs/028 US5). Built by build.py: only the scene table lives here.
import {{ film }} from './kit/film.js';
const SCENES = {json.dumps(scenes, ensure_ascii=False)};
await film({{ scenes: SCENES, custom: {json.dumps(CUSTOM)} }});
</script>
</body></html>
"""
open(f"{HERE}/index.html", "w").write(page)
print("dur", DUR, "shots", len(shots), [round(s["t1"] - s["t0"], 2) for s in shots])
