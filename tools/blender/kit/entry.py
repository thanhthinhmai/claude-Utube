"""Entry of a Blender run (specs/038 T011): blender -b --factory-startup -P kit/entry.py -- request.json

request.json (contracts/bridge-api.md):
  {"id", "kind": "render|plan|plate|probe", "film", "fps", "size": [w, h], "quarter": false,
   "shots": [{"id": "S3", "frames": 72, "script": "blender/S3.py", "layers": "layers/S3", "still": 36}]}
Paths in request.json are relative to its folder. For each shot: clear the scene, load the shot script, call
shot(k), then render frames (render), one still (plate, or render with "still"), or write plan.json (plan)."""
import json
import os
import re
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from kit import core  # noqa: E402

FORBIDDEN = re.compile(r"^\s*(import|from)\s+\S", re.M)


class K:
    """What a shot script may call (contracts/blender-kit.md). Each call goes to a module of the shared kit; a call
    the kit does not have yet is an error of the script, never something written inside a film."""

    def __init__(self, run_dir: str, req: dict, shot: dict):
        self.run_dir, self.req, self.shot = run_dir, req, shot
        self.id = shot["id"]
        self.fps = int(req.get("fps") or 24)
        self.frames = int(shot["frames"])
        self.size = tuple(req.get("size") or (1920, 1080))
        self.plan = shot.get("plan") or {}            # the shot's shot_plan from film.json (size, lens, depth…)
        self.layers_dir = os.path.join(run_dir, shot["layers"]) if shot.get("layers") else ""
        self.cards = []                               # cast cards placed in this shot (plan pass reads them)
        self.objects = {}                             # named things a set exposes (rows, doors…) for later calls

    def f(self, seconds: float) -> int:
        """Seconds from the shot start → frame number (1-based)."""
        return max(1, min(self.frames, 1 + int(round(seconds * self.fps))))

    def _call(self, module: str, func: str, *a, **kw):
        import importlib
        try:
            mod = importlib.import_module("kit." + module)
        except ModuleNotFoundError:
            raise KitError(f"the kit has no {module.replace('.', '/')}.py yet") from None
        fn = getattr(mod, func, None)
        if fn is None:
            raise KitError(f"kit/{module.replace('.', '/')}.py has no {func}()")
        return fn(self, *a, **kw)

    def set(self, name: str, **kw):
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name or ""):
            raise KitError(f"bad set name {name!r}")
        return self._call("sets." + name, "build", **kw)

    def cam(self, **kw):
        return self._call("camera", "cam", **kw)

    def cast(self, char: str, **kw):
        return self._call("cards", "cast", char, **kw)

    def crowd(self, **kw):
        return self._call("cards", "crowd", **kw)

    def fg(self, name: str, **kw):
        return self._call("layers", "fg", name, **kw)

    def fx(self, name: str, **kw):
        return self._call("fx", name, **kw)

    def light(self, preset: str, **kw):
        return self._call("light", "preset", preset, **kw)


class KitError(Exception):
    pass


def load_shot(path: str):
    src = open(path, encoding="utf-8").read()
    m = FORBIDDEN.search(src)
    if m:
        line = src[:m.start()].count("\n") + 1
        raise KitError(f"line {line}: shot scripts call k.* only, no imports")
    ns = {"__name__": "shot", "__file__": path}
    exec(compile(src, path, "exec"), ns)
    if not callable(ns.get("shot")):
        raise KitError("the script has no shot(k)")
    return ns["shot"]


def script_error(shot_id: str, path: str, e: Exception) -> str:
    line = ""
    for fr in reversed(traceback.extract_tb(e.__traceback__)):
        if os.path.abspath(fr.filename) == os.path.abspath(path):
            line = f" line {fr.lineno}"
            break
    return f"{shot_id}: {type(e).__name__}: {e}{line}"


def main(argv: list) -> None:
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    if not args:
        print("usage: blender -b --factory-startup -P kit/entry.py -- request.json", file=sys.stderr)
        sys.exit(2)
    req_path = os.path.abspath(args[0])
    run_dir = os.path.dirname(req_path)
    core.open_log(os.path.join(run_dir, "log.txt"))
    core.log("START")
    import bpy
    core.log(f"VERSION {bpy.app.version_string}")
    req = json.load(open(req_path, encoding="utf-8"))
    kind = req.get("kind") or "render"
    shots = req.get("shots") or []
    core.clear_scene()
    core.setup_scene(req.get("fps") or 24, req.get("size") or (1920, 1080), 1, quarter=True)
    core.gpu_guard(os.path.join(run_dir, "probe.png"))
    if kind == "probe":
        core.log("DONE")
        return
    for s in shots:
        sid = s["id"]
        out = os.path.join(run_dir, sid)
        os.makedirs(out, exist_ok=True)
        path = os.path.join(run_dir, s["script"])
        core.clear_scene()
        core.setup_scene(req.get("fps") or 24, req.get("size") or (1920, 1080), s["frames"], quarter=bool(req.get("quarter")))
        k = K(run_dir, req, s)
        try:
            load_shot(path)(k)
        except KitError as e:
            core.fail("script", f"{sid}: {e}")
        except Exception as e:     # noqa: BLE001 — any error of a shot script is reported, not raised
            core.fail("script", script_error(sid, path, e))
        if bpy.context.scene.camera is None:
            core.fail("script", f"{sid}: the shot has no camera; call k.cam(...)")
        if kind == "plan":
            angle = max([c.get("angle", 0) for c in k.cards] or [0])
            json.dump({"shot": sid, "frames": s["frames"], "chars": k.cards, "card_angle_max": angle},
                      open(os.path.join(out, "plan.json"), "w"), indent=1)
        elif kind == "plate" or s.get("still"):
            name = "plate.png" if kind == "plate" else f"still-{int(s.get('still') or 1):04d}.png"
            core.render_still(os.path.join(out, name), int(s.get("still") or (s["frames"] + 1) // 2))
        else:
            core.render_frames(out, sid, s["frames"])
        core.log(f"shot {sid} ok")
    core.log("DONE")


if __name__ == "__main__":
    try:
        main(sys.argv)
    except SystemExit:
        raise
    except Exception as e:         # noqa: BLE001
        core.fail("script", f"entry: {type(e).__name__}: {e}")
