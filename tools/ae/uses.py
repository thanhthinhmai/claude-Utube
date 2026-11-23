"""Which shots use which functions of the shared kit (specs/031 R6, FR-005).

ES3 has no modules: a shot uses CU.<name> when its function body (CU.shot<id> = function …) calls it, directly or
through other CU functions (the film's own helpers and the kit's call graph). When in doubt a shot is listed: an
extra shot only costs a rebuild, a missing one leaves a bug in the film."""
import re
from pathlib import Path

from ae import bundle

DEF = re.compile(r"^\s*CU\.([A-Za-z_$][\w$]*)\s*=\s*function\b", re.M)
CALL = re.compile(r"\bCU\.([A-Za-z_$][\w$]*)\b")


def _bodies(text: str) -> dict:
    """{name: body text} for top-level CU.<name> = function definitions (body = up to the next definition)."""
    ms = list(DEF.finditer(text))
    out = {}
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        out[m.group(1)] = out.get(m.group(1), "") + text[m.end():end]
    return out


def graph(texts: list) -> dict:
    """{function: set of CU functions it calls}; later files add to (and in AE override) earlier ones."""
    g = {}
    for t in texts:
        for name, body in _bodies(t).items():
            g[name] = {c for c in CALL.findall(body) if c != name}
    return g


def reach(g: dict, start: str) -> set:
    seen, todo = set(), [start]
    while todo:
        f = todo.pop()
        for c in g.get(f, ()):
            if c not in seen:
                seen.add(c)
                todo.append(c)
    return seen


def shots_using(film_dir, funcs) -> list:
    d = Path(film_dir)
    kit = [(bundle.KIT / f).read_text(encoding="utf-8") for f in bundle.KIT_FILES]
    own = [p.read_text(encoding="utf-8") for p in sorted((d / "ae").glob("*.jsx"))]
    g = graph(kit + own)
    want = {f.replace("CU.", "") for f in funcs}
    try:
        from ae import film as filmdoc
        known = set(filmdoc.load(d).get("shots") or [])
    except Exception:
        known = set()
    out = []
    for name in g:
        m = re.fullmatch(r"shot([0-9]{1,3}[A-Z]?)", name)
        if m and (not known or "S" + m.group(1) in known) and (reach(g, name) & want or name in want):
            out.append("S" + m.group(1))
    def key(s):
        m = re.fullmatch(r"S([0-9]+)([A-Z]?)", s)
        return (int(m.group(1)), m.group(2))
    return sorted(set(out), key=key)
