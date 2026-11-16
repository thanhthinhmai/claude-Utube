"""The craft template of a style (specs/023 contracts/template-format.md; research R8, R10).

check_template / check_numbers / check_style_tags: what `learn template-check <slug>` checks.
Each problem is one line "<file> <where>: <why>"; an empty list means the template passes."""
import json
import re
from pathlib import Path

from . import refset

COMPONENTS = [
    "Khuôn mặt và biểu cảm", "Thân và trang phục", "Bố cục theo cỡ cảnh", "Độ sâu theo cỡ cảnh", "Ánh sáng",
    "Bối cảnh và đạo cụ kể chuyện", "Đám đông", "Thẻ số liệu", "Thẻ tiêu đề và thẻ câu hỏi cuối", "Cảnh không khí",
    "Diễn xuất nhân vật", "Chuyển động máy", "Chuyển cảnh", "Âm thanh", "Nhịp đọc lời",
]
BEATS = ["hook", "explain", "benefit", "scale", "cost", "crisis", "ending", "sting", "end-card"]
BEAT_ROWS = ["độ dài cảnh", "chuỗi cỡ cảnh", "máy động", "diễn xuất", "đồ hoạ", "chuyển cảnh", "tiếng động", "nhạc",
             "từ mỗi phút"]
MIN_EVIDENCE, MIN_VIDEOS = 3, 2

EV_SHEET = re.compile(r"^(v\d{2})_shots_\d+\.jpg#(S\d{3,4}|\d{1,2})$")   # a shot id or a cell number (as shots.json writes it)
EV_STRIP = re.compile(r"^(v\d{2})/strips/(S\d{3,4})\.jpg#[0-7]$")
EV_FILE = re.compile(r"^(v\d{2})/evidence/[\w.-]+\.jpg$")
STYLE_TAG = re.compile(r"\[(xưởng|bằng chứng:\s*[^\]]+)\]")
STYLE_CITE = re.compile(r"\.jpg#\S+|→|§\s*\d+(\.\d+)?")
NUM = re.compile(r"-?\d+(?:[.,]\d+)?")


def _num(tok: str) -> float:
    return float(tok.replace(",", "."))


def _decimals(tok: str) -> int:
    m = re.search(r"[.,](\d+)$", tok)
    return len(m.group(1)) if m else 0


def style_dir(slug: str) -> Path:
    return refset.root() / "my-styles" / slug


def set_of(slug: str):
    d = style_dir(slug)
    tj = d / "template.json"
    if tj.exists():
        try:
            s = json.loads(tj.read_text(encoding="utf-8")).get("set")
            if s:
                return s
        except ValueError:
            pass
    md = d / "TEMPLATE.md"
    if md.exists():
        m = re.search(r"Bộ tham chiếu:\s*`?([a-z0-9-]+)`?", md.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return None


# ---------------------------------------------------------------- markdown pieces

def sections(text: str, level: int = 2) -> list:
    """[(title, body_lines, first_line_no)] for headings of exactly `level` #; a heading of a higher level ends one."""
    out, cur = [], None
    for no, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^(#+)\s+(.*)$", line)
        if m and len(m.group(1)) <= level:
            cur = (m.group(2).strip(), [], no) if len(m.group(1)) == level else None
            if cur:
                out.append(cur)
        elif cur is not None:
            cur[1].append(line)
    return out


def table(lines: list):
    """(header cells, rows) of the first markdown table in lines, or (None, [])."""
    rows = [l for l in lines if l.strip().startswith("|")]
    if len(rows) < 2:
        return None, []
    cells = lambda l: [c.strip() for c in l.strip().strip("|").split("|")]
    head = cells(rows[0])
    body = [cells(r) for r in rows[1:] if not re.match(r"^\|?\s*:?-{3,}", r.strip())]
    return head, body


def field(lines: list, label: str):
    for l in lines:
        if l.strip().startswith(label):
            return l.strip()[len(label):].strip()
    return None


# ---------------------------------------------------------------- TEMPLATE.md

def evidence_problems(where: str, lines: list, prof: Path) -> list:
    out = []
    ev = field(lines, "Bằng chứng:")
    few = field(lines, "Ít bằng chứng:")
    if ev is None:
        return [f"{where}: thiếu dòng 'Bằng chứng:'"]
    refs = [t.strip().strip("`") for t in ev.split(",") if t.strip()]
    vids = set()
    for r in refs:
        m = EV_SHEET.match(r) or EV_STRIP.match(r) or EV_FILE.match(r)
        if not m:
            out.append(f"{where}: bằng chứng sai dạng '{r}' (dạng: vNN_shots_N.jpg#Sxxx hoặc #ô, vNN/strips/Sxxx.jpg#k, vNN/evidence/<tên>.jpg)")
            continue
        vid = m.group(1)
        vids.add(vid)
        if EV_SHEET.match(r):
            path = prof / vid / "shot-sheets" / r.split("#")[0]
        else:
            path = prof / r.split("#")[0]
        if not path.exists():
            out.append(f"{where}: không thấy tệp bằng chứng {path.relative_to(prof.parent.parent)}")
    if few is not None:
        m = re.match(r"(\d+)", few)
        if not m or int(m.group(1)) < 1 or not refs:
            out.append(f"{where}: 'Ít bằng chứng:' cần số khung và ít nhất một bằng chứng")
    elif len(refs) < MIN_EVIDENCE or len(vids) < MIN_VIDEOS:
        out.append(f"{where}: cần ≥ {MIN_EVIDENCE} bằng chứng từ ≥ {MIN_VIDEOS} video (có {len(refs)} từ {len(vids)} video), "
                   "hoặc ghi 'Ít bằng chứng: <n> khung'")
    return out


def check_template(slug: str, partial=None) -> list:
    d = style_dir(slug)
    md = d / "TEMPLATE.md"
    if not md.exists():
        return [f"TEMPLATE.md: chưa có ({md})"]
    text = md.read_text(encoding="utf-8")
    s = set_of(slug)
    if not s:
        return ["TEMPLATE.md: thiếu dòng 'Bộ tham chiếu: <set>' (hoặc khoá 'set' trong template.json)"]
    prof = refset.refs_dir() / s / "profile"
    lo, hi = partial or (1, len(COMPONENTS))
    want = [(i, COMPONENTS[i - 1]) for i in range(lo, hi + 1)]
    secs = {t: (body, no) for t, body, no in sections(text)}
    numbered = [t for t, _, _ in sections(text) if re.match(r"^\d+\.\s", t)]
    out = []
    expect_order = [f"{i}. {name}" for i, name in enumerate(COMPONENTS, 1)]
    present = [t for t in numbered if t in expect_order]
    if present != [t for t in expect_order if t in present]:
        out.append("TEMPLATE.md: các mục không đúng thứ tự của contracts/template-format.md")
    for i, name in want:
        title = f"{i}. {name}"
        if title not in secs:
            out.append(f"TEMPLATE.md §{i}: thiếu mục '## {title}'")
            continue
        body, no = secs[title]
        where = f"TEMPLATE.md §{i} (dòng {no})"
        prose = [l for l in body if l.strip() and not l.strip().startswith("|")
                 and not re.match(r"^(Bằng chứng|Ít bằng chứng|Nên làm|Không nên làm|Trong bộ dựng):", l.strip())]
        if not prose:
            out.append(f"{where}: thiếu đoạn mô tả")
        head, rows = table(body)
        if not head or not rows:
            out.append(f"{where}: thiếu bảng số đo (≥ 1 dòng)")
        else:
            low = [h.lower() for h in head]
            if "khoảng" not in low:
                out.append(f"{where}: bảng số đo thiếu cột 'Khoảng'")
            else:
                k = low.index("khoảng")
                if any(len(r) <= k or not r[k] for r in rows):
                    out.append(f"{where}: có dòng số đo để trống cột 'Khoảng'")
        out += evidence_problems(where, body, prof)
        for label in ("Nên làm:", "Không nên làm:", "Trong bộ dựng:"):
            v = field(body, label)
            if not v:
                out.append(f"{where}: thiếu dòng '{label}'")
    if partial is None:
        out += check_beats(text)
    return out


def check_beats(text: str) -> list:
    out = []
    top = {t: (body, no) for t, body, no in sections(text)}
    if "Công thức nhịp" not in top:
        return ["TEMPLATE.md: thiếu mục '## Công thức nhịp'"]
    body, no = top["Công thức nhịp"]
    subs = sections("\n".join(body), 3)
    names = [t for t, _, _ in subs]
    if names != BEATS:
        missing = [b for b in BEATS if b not in names]
        out.append(f"TEMPLATE.md Công thức nhịp: cần đúng 9 nhịp theo thứ tự {', '.join(BEATS)}"
                   + (f" (thiếu: {', '.join(missing)})" if missing else " (sai thứ tự hoặc thừa)"))
    for t, b, _ in subs:
        if t not in BEATS:
            continue
        head, rows = table(b)
        firsts = " | ".join(r[0].lower() for r in rows if r)
        lack = [r for r in BEAT_ROWS if r not in firsts]
        if lack:
            out.append(f"TEMPLATE.md nhịp {t}: bảng thiếu dòng {', '.join(lack)}")
    return out


# ---------------------------------------------------------------- numbers against their sources

def _lookup(obj, dotted: str):
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return None
    return cur


def _sources(slug: str) -> dict:
    d = style_dir(slug)
    s = set_of(slug)
    prof = refset.refs_dir() / s / "profile" if s else None
    files = {"template.json": d / "template.json"}
    if prof:
        files["craft-summary.json"] = prof / "craft-summary.json"
        files["summary.json"] = prof / "summary.json"
    out = {}
    for k, p in files.items():
        try:
            out[k] = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            out[k] = None
    return out


def _close(tok: str, v: float) -> bool:
    return abs(_num(tok) - v) <= max(0.01, 0.5 * 10 ** -_decimals(tok))


def check_numbers(slug: str) -> list:
    md = style_dir(slug) / "TEMPLATE.md"
    if not md.exists():
        return []
    src = _sources(slug)
    out = []
    for title, body, no in sections(md.read_text(encoding="utf-8")):
        head, rows = table(body)
        if not head:
            continue
        low = [h.lower() for h in head]
        if "nguồn" not in low:
            continue
        ki, gi = low.index("nguồn"), (low.index("giá trị") if "giá trị" in low else None)
        ri = low.index("khoảng") if "khoảng" in low else None
        for r in rows:
            if len(r) <= ki or "→" not in r[ki]:
                continue
            fname, _, key = (x.strip().strip("`") for x in r[ki].partition("→"))
            fname = fname.split("/")[-1]
            if fname not in src:
                continue
            if src[fname] is None:
                out.append(f"TEMPLATE.md {title}: nguồn {fname} chưa có")
                continue
            v = _lookup(src[fname], key)
            where = f"TEMPLATE.md {title}, dòng '{r[0]}'"
            if v is None:
                out.append(f"{where}: không thấy khoá {key} trong {fname}")
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                toks = NUM.findall(r[gi]) if gi is not None and gi < len(r) else []
                if toks and not _close(toks[0], float(v)):
                    out.append(f"{where}: ghi {toks[0]}, nguồn là {v}")
            elif isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v):
                toks = NUM.findall(r[ri]) if ri is not None and ri < len(r) else []
                if len(toks) >= 2 and not (_close(toks[0], float(v[0])) and _close(toks[1], float(v[1]))):
                    out.append(f"{where}: khoảng ghi {toks[0]}–{toks[1]}, nguồn là {v[0]}–{v[1]}")
    out += check_json_sources(slug, src)
    return out


def _leaves(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _leaves(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list) and obj and all(isinstance(x, (int, float)) for x in obj):
        yield path, obj
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        yield path, obj


def check_json_sources(slug: str, src=None) -> list:
    src = src or _sources(slug)
    tj = src.get("template.json")
    if tj is None:
        return [] if not (style_dir(slug) / "template.json").exists() else ["template.json: không đọc được"]
    sources = tj.get("source") or {}
    summ = src.get("summary.json") or {}
    out = []
    for path, _ in _leaves({k: v for k, v in tj.items() if k not in ("version", "source")}):
        parts = path.split(".")
        if any(".".join(parts[:i]) in sources for i in range(1, len(parts) + 1)):
            continue
        if parts[-1] in summ or parts[-1] + "_p50" in summ:
            continue
        out.append(f"template.json {path}: thiếu nguồn trong 'source'")
    return out


# ---------------------------------------------------------------- STYLE.md labels

def check_style_tags(slug: str) -> list:
    p = style_dir(slug) / "STYLE.md"
    if not p.exists():
        return [f"STYLE.md: chưa có ({p})"]
    out, sec, in_table, header_seen = [], 0, False, False
    for no, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        m = re.match(r"^##\s+(\d+)\.", line)
        if m:
            sec, in_table = int(m.group(1)), False
            continue
        if line.startswith("## "):
            sec = 0
            continue
        if not 1 <= sec <= 11:
            continue
        s = line.strip()
        if s.startswith("|"):
            if not in_table:
                in_table = True                       # the header row
                continue
            if re.match(r"^\|?\s*:?-{3,}", s):
                continue
        else:
            in_table = False
            if not re.match(r"^[-*]\s+\S", s):
                continue
        tag = STYLE_TAG.search(s)
        if not tag:
            out.append(f"STYLE.md dòng {no} (§{sec}): luật thiếu nhãn [bằng chứng: …] hoặc [xưởng]")
        elif tag.group(1).startswith("bằng chứng") and not STYLE_CITE.search(tag.group(1)):
            out.append(f"STYLE.md dòng {no} (§{sec}): [bằng chứng: …] cần trích dẫn dạng bảng#ô, tệp → khoá, hoặc báo cáo §n.m")
    return out


def cli(slug: str, partial: str = None) -> int:
    rng = None
    if partial:
        m = re.match(r"^(\d+)-(\d+)$", partial)
        if not m or not 1 <= int(m.group(1)) <= int(m.group(2)) <= len(COMPONENTS):
            raise refset.UsageError(f"--partial cần dạng a-b trong 1-{len(COMPONENTS)}")
        rng = (int(m.group(1)), int(m.group(2)))
    probs = check_template(slug, rng) + check_numbers(slug) + check_style_tags(slug)
    for x in probs:
        print(f"✗ {x}")
    if probs:
        print(f"→ {len(probs)} chỗ cần sửa")
        return 1
    print("✓ TEMPLATE.md, template.json và nhãn luật của STYLE.md đạt"
          + (f" (mục {rng[0]}–{rng[1]})" if rng else ""))
    return 0


# ---------------------------------------------------------------- look measures from what learning kept (R10, US1)

FLAT_FILMS = ("v03", "v08")       # EVIDENCE.md corrections #15: the look rules come from the 3D films
SKIP_SCALES = ("insert", "short", "unknown", None)
LETTERBOX = 0.07                  # top and bottom share of a sheet cell left out (2.04:1 bars inside 16:9)


def shot_rows(name: str, look_only: bool = False) -> list:
    """Every labelled shot of the set: shots.json rows with their video id."""
    out = []
    data = refset.load(name)
    for v in data["videos"]:
        if look_only and v["id"] in FLAT_FILMS:
            continue
        f = refset.profile_dir(name, v["id"]) / "shots.json"
        if not f.exists():
            continue
        for r in json.loads(f.read_text(encoding="utf-8")).get("shots", []):
            out.append(dict(r, video=v["id"]))
    return out


def cell(name: str, ref: str):
    """The picture of one shot-sheet cell ("v01_shots_3.jpg#7" or "…#S087"), caption left out, as a PIL image."""
    from PIL import Image
    from .shots import COLS, CW, CH, LAB
    sheet, _, n = ref.partition("#")
    vid = sheet.split("_")[0]
    path = refset.profile_dir(name, vid) / "shot-sheets" / sheet
    if n.startswith("S"):
        rows = [r for r in shot_rows(name) if r["video"] == vid and r["id"] == n]
        if not rows or "#" not in (rows[0].get("evidence") or ""):
            raise refset.StepError(f"không thấy ô của {vid}:{n} trong shots.json")
        n = rows[0]["evidence"].partition("#")[2]
    k = int(n) - 1
    x, y = 6 + (k % COLS) * (CW + 6), 6 + (k // COLS) * (CH + LAB + 6) + LAB
    return Image.open(path).convert("RGB").crop((x, y, x + CW, y + CH))


def light_of(img) -> dict:
    """Warm highlights, contrast and the side the light comes from, inside the picture (letterbox left out)."""
    import numpy as np
    a = np.asarray(img, np.float32) / 255.0
    h = a.shape[0]
    a = a[int(h * LETTERBOX):h - int(h * LETTERBOX)]
    lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    mx, mn = a.max(-1), a.min(-1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    d = np.maximum(mx - mn, 1e-6)
    hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    warm = (lum > 0.6) & (hue >= 20) & (hue <= 60) & (sat > 0.25)
    w = lum.shape[1]
    lr = float(lum[:, w // 2:].mean() - lum[:, :w // 2].mean())
    tb = float(lum[lum.shape[0] // 2:].mean() - lum[:lum.shape[0] // 2].mean())
    return {"warm_share": float(warm.mean()), "range": float(np.percentile(lum, 90) - np.percentile(lum, 10)),
            "side_lr": lr, "side_tb": tb}


def _q(vals, nd=3):
    import numpy as np
    if not vals:
        return None
    return [round(float(x), nd) for x in np.percentile(vals, [25, 50, 75])]


def look_summary(name: str) -> dict:
    """framing and light by shot scale, from shots.json and the shot sheets (8 3D films)."""
    rows = [r for r in shot_rows(name, look_only=True) if r.get("scale") not in SKIP_SCALES]
    by = {}
    for r in rows:
        by.setdefault(r["scale"], []).append(r)
    framing, light = {}, {}
    all_light = []
    for sc, rs in by.items():
        cols, rws, fs, fg = [0] * 4, [0] * 3, [], 0
        lights = []
        for r in rs:
            f = r.get("focus") or {}
            if f.get("sharpest_at"):
                c, w = f["sharpest_at"]
                cols[c] += 1
                rws[w] += 1
            if f.get("focused_share") is not None:
                fs.append(f["focused_share"])
            fg += bool(r.get("foreground_blur"))
            if r.get("evidence"):
                try:
                    lights.append(light_of(cell(name, f"{r['evidence']}")))
                except (OSError, refset.StepError, ValueError):
                    pass
        n = max(1, sum(cols))
        framing[sc] = {"n": len(rs), "col": [round(x / n, 3) for x in cols], "row": [round(x / n, 3) for x in rws],
                       "off_centre": round((cols[0] + cols[3]) / n, 3), "focused_share": _q(fs),
                       "foreground_blur": round(fg / len(rs), 3)}
        all_light += lights
        light[sc] = _light_stats(lights)
    return {"framing": {"by_scale": framing, "films": sorted({r["video"] for r in rows})},
            "light": {"by_scale": light, "all": _light_stats(all_light)}}


def _light_stats(ls: list) -> dict:
    if not ls:
        return {"n": 0}
    side = [abs(x["side_lr"]) for x in ls]
    return {"n": len(ls), "warm_share": _q([x["warm_share"] for x in ls], 4), "range": _q([x["range"] for x in ls]),
            "side_lr_abs": _q(side), "raking": round(sum(s > 0.03 for s in side) / len(side), 3),
            "lit_from_right": round(sum(x["side_lr"] > 0.03 for x in ls) / len(ls), 3),
            "lit_from_left": round(sum(x["side_lr"] < -0.03 for x in ls) / len(ls), 3)}


def craft_summary(name: str, parts=("look",)) -> dict:
    """Write references/<set>/profile/craft-summary.json; parts already there and not rebuilt are kept."""
    path = refset.set_dir(name) / "profile" / "craft-summary.json"
    cur = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    cur["set"] = name
    if "look" in parts:
        cur.update(look_summary(name))
    if "time" in parts:
        from . import timesummary
        cur.update(timesummary.build(name))
    refset.write_json(path, cur)
    return cur


def print_summary(s: dict) -> None:
    fr = s.get("framing", {}).get("by_scale", {})
    if fr:
        print("Cỡ cảnh | n | lệch tâm | cột 0–3 | focused_share p25/50/75 | tiền cảnh mờ")
        for sc, v in sorted(fr.items(), key=lambda kv: -kv[1]["n"]):
            print(f"{sc} | {v['n']} | {v['off_centre']} | {v['col']} | {v['focused_share']} | {v['foreground_blur']}")
    li = s.get("light", {})
    if li:
        a = li.get("all", {})
        print(f"Ánh sáng (cả bộ, {a.get('n')} ô): sáng ấm {a.get('warm_share')} · độ chênh {a.get('range')} · "
              f"xiên {a.get('raking')} (phải {a.get('lit_from_right')}, trái {a.get('lit_from_left')})")
