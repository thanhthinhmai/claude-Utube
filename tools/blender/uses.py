"""Which Blender shots use which parts of the shared kit (specs/038 T022, FR-006).

A shot script calls k.<name>(…) only (contracts/blender-kit.md). Each call maps to a kit module (k.set("hallway") →
sets/hallway.py, k.cam → camera.py …), and kit modules import each other (`from kit import toon`). A shot uses every
module it reaches, plus core.py and entry.py. When in doubt a shot is listed: an extra rebuild is cheap."""
import re
from pathlib import Path

KIT = Path(__file__).resolve().parent / "kit"
CALL = re.compile(r"\bk\.([a-z_][a-z0-9_]*)\s*\(")
SET = re.compile(r"\bk\.set\(\s*[\"']([a-z][a-z0-9_]*)[\"']")
FX = re.compile(r"\bk\.fx\(\s*[\"']([a-z][a-z0-9_]*)[\"']")
IMPORT = re.compile(r"^\s*(?:from\s+kit(?:\.(?P<pkg>[a-z_.]+))?\s+import\s+(?P<names>[a-z_, ]+)|import\s+kit\.(?P<mod>[a-z_.]+))", re.M)
ALWAYS = ("core.py", "entry.py")
CALL_MODULE = {"cam": "camera.py", "cast": "cards.py", "crowd": "cards.py", "fg": "layers.py", "fx": "fx.py",
               "light": "light.py"}


def _key(s: str):
    m = re.fullmatch(r"S([0-9]+)([A-Z]?)", s)
    return (int(m.group(1)), m.group(2)) if m else (10 ** 6, s)


def _module_file(dotted: str):
    p = KIT / (dotted.replace(".", "/") + ".py")
    return str(p.relative_to(KIT)) if p.is_file() else None


def kit_graph(kit: Path = None) -> dict:
    """{kit file: set of kit files it imports}."""
    kit = kit or KIT
    g = {}
    for p in sorted(kit.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        deps = set()
        for m in IMPORT.finditer(p.read_text(encoding="utf-8")):
            if m.group("mod"):
                f = _module_file(m.group("mod"))
                deps |= {f} if f else set()
                continue
            pkg = m.group("pkg")
            for name in (n.strip() for n in m.group("names").split(",")):
                f = _module_file(f"{pkg}.{name}" if pkg else name) or (_module_file(pkg) if pkg else None)
                if f:
                    deps.add(f)
        g[str(p.relative_to(kit))] = deps
    return g


def calls(src: str) -> dict:
    return {"calls": set(CALL.findall(src)), "sets": set(SET.findall(src)), "fx": set(FX.findall(src))}


def files_of(script: Path, g: dict = None) -> list:
    """Kit files a shot script uses (sorted), for the shot's version and for `ae uses`."""
    g = g if g is not None else kit_graph()
    c = calls(Path(script).read_text(encoding="utf-8"))
    start = set(ALWAYS) | {f"sets/{s}.py" for s in c["sets"]} | {CALL_MODULE[x] for x in c["calls"] if x in CALL_MODULE}
    seen, todo = set(), [f for f in start if f in g]
    while todo:
        f = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        todo.extend(g.get(f, ()))
    return sorted(seen)


def shots_using(film_dir, funcs) -> list:
    """Blender shots whose script calls k.<f>, uses set/fx <f>, or reaches kit module <f> (toon, sets/hallway…)."""
    d = Path(film_dir)
    g = kit_graph()
    want = {f.replace("k.", "").removesuffix(".py") for f in funcs}
    out = []
    for p in sorted((d / "blender").glob("S*.py")):
        sid = p.stem
        c = calls(p.read_text(encoding="utf-8"))
        mods = {f.removesuffix(".py") for f in files_of(p, g)} | {f.removesuffix(".py").split("/")[-1] for f in files_of(p, g)}
        if want & (c["calls"] | c["sets"] | c["fx"] | mods):
            out.append(sid)
    return sorted(out, key=_key)
