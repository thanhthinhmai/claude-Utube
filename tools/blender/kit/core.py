"""Core of the shared Blender kit (specs/038 T010): scene setup, GPU guard, log.txt, frame render with resume.

Runs inside Blender (bpy). Rewritten from the 2026-11-26 Blender test without machine paths. Every line written to
log.txt follows contracts/bridge-api.md: START, VERSION, GPU <renderer> <backend>, frame S<n> i/N, shot S<n> ok,
ERR <code> <msg>, DONE."""
import math
import os
import re
import sys

import bpy

SOFTWARE = re.compile(r"llvmpipe|softpipe|swrast|swiftshader|microsoft basic render|\bsoftware\b", re.I)
_LOG = None


def open_log(path: str) -> None:
    global _LOG
    _LOG = open(path, "a", encoding="utf-8")


def log(line: str) -> None:
    """One event per line, flushed at once: the runner watches this file."""
    if _LOG:
        _LOG.write(line.rstrip("\n") + "\n")
        _LOG.flush()
    else:
        print(line, flush=True)


def fail(code: str, message: str, exit_code: int = 1) -> None:
    log(f"ERR {code} {message}".replace("\n", " ")[:2000])
    sys.stdout.flush()
    sys.exit(exit_code)


def hexc(h: str, a: float = 1.0) -> list:
    """#rrggbb → linear RGBA."""
    h = h.lstrip("#")
    return [(int(h[i:i + 2], 16) / 255) ** 2.2 for i in (0, 2, 4)] + [a]


def clear_scene() -> None:
    """Remove every object and the data left without users, so shots in one run do not leak into each other."""
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.curves,
                 bpy.data.worlds, bpy.data.images, bpy.data.particles, bpy.data.node_groups):
        for b in list(coll):
            if b.users == 0:
                coll.remove(b)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)


def setup_scene(fps: int, size, frames: int, quarter: bool = False, samples: int = 0):
    """EEVEE, frames 1..N, the film's size (a quarter of it for quick looks), Standard view transform (flat colours)."""
    sc = bpy.context.scene
    sc.render.fps = int(fps)
    sc.render.fps_base = 1.0
    sc.frame_start, sc.frame_end = 1, max(1, int(frames))
    w, h = int(size[0]), int(size[1])
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 25 if quarter else 100
    for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = name
            break
        except TypeError:
            continue
    sc.eevee.taa_render_samples = samples or (16 if quarter else 48)
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    return sc


def gpu_renderer() -> tuple:
    import gpu
    return gpu.platform.renderer_get(), gpu.platform.backend_type_get()


def gpu_guard(probe_png: str) -> str:
    """Stop before the first frame when Blender draws with a software renderer (constitution VII: GPU only).

    In background mode the GPU context may only exist after a first render, so a 16×16 still is drawn first when the
    renderer cannot be read yet."""
    try:
        name, backend = gpu_renderer()
    except Exception:            # noqa: BLE001 — no context yet
        sc = bpy.context.scene
        keep = (sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage, sc.render.filepath, sc.camera)
        if sc.camera is None:
            cd = bpy.data.cameras.new("probe")
            sc.camera = bpy.data.objects.new("probe", cd)
            sc.collection.objects.link(sc.camera)
        sc.render.resolution_x = sc.render.resolution_y = 16
        sc.render.resolution_percentage = 100
        sc.render.filepath = probe_png
        bpy.ops.render.render(write_still=True)
        probe_cam = sc.camera if keep[4] is None else None
        sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage, sc.render.filepath, sc.camera = keep
        if probe_cam is not None:
            bpy.data.objects.remove(probe_cam, do_unlink=True)
        try:
            name, backend = gpu_renderer()
        except Exception as e:   # noqa: BLE001
            fail("gpu_software", f"the GPU renderer cannot be read ({e}); renders must run on the GPU", 3)
    log(f"GPU {name} {backend}")
    if SOFTWARE.search(str(name)):
        fail("gpu_software", f"{name}: Blender is drawing without the GPU; renders must run on the GPU", 3)
    return name


def drop_placeholders(out_dir: str) -> int:
    """Empty f####.png files are placeholders of frames that were cut off: remove them so the next run draws them."""
    n = 0
    if os.path.isdir(out_dir):
        for f in os.listdir(out_dir):
            p = os.path.join(out_dir, f)
            if re.fullmatch(r"f\d{4}\.png", f) and os.path.getsize(p) == 0:
                os.remove(p)
                n += 1
    return n


def render_frames(out_dir: str, shot_id: str, frames: int) -> None:
    """Draw frames 1..N to out_dir/f####.png. Frames already there are kept (use_overwrite False + placeholders), so a
    run cut off mid-shot goes on from where it stopped (FR-008)."""
    os.makedirs(out_dir, exist_ok=True)
    drop_placeholders(out_dir)
    sc = bpy.context.scene
    sc.render.filepath = os.path.join(out_dir, "f####")
    sc.render.use_overwrite = False
    sc.render.use_placeholder = True
    sc.render.use_file_extension = True

    def done(scene, *_):
        log(f"frame {shot_id} {scene.frame_current}/{frames}")

    bpy.app.handlers.render_write.append(done)
    try:
        bpy.ops.render.render(animation=True)
    finally:
        bpy.app.handlers.render_write.remove(done)
    missing = [i for i in range(1, frames + 1)
               if not os.path.isfile(os.path.join(out_dir, f"f{i:04d}.png"))
               or os.path.getsize(os.path.join(out_dir, f"f{i:04d}.png")) == 0]
    if missing:
        fail("script", f"{shot_id}: {len(missing)} frame(s) were not written (first f{missing[0]:04d}.png)")


def render_still(path: str, frame: int) -> None:
    sc = bpy.context.scene
    sc.frame_set(max(sc.frame_start, min(sc.frame_end, int(frame))))
    sc.render.filepath = path
    sc.render.use_file_extension = False
    bpy.ops.render.render(write_still=True)


def ease_io(u: float) -> float:
    u = max(0.0, min(1.0, u))
    return 0.5 - 0.5 * math.cos(math.pi * u)
