"""The chosen camera of a Blender shot (specs/039 R7): shot_plan.<S>.camera → k.cam() lens-zoom parameters.

Blender only draws the backgrounds with a still camera (decision 2026-11-27), so a camera block never moves the camera:
the lens grows (a 2D zoom about the picture centre, no parallax) and the frame shifts.
  start {scale, cx, cy}  the lens starts `scale` times longer, the frame centred on (cx, cy) % of the picture
  zoom_pct               the lens grows by (1 + zoom_pct/100) more by the end
  drift_px [x, y]        the window moves that many 1080p screen pixels by the end
  ease_ae [in, out]      After Effects' influences; k.cam's ease is (out, in)
No bpy here, so the tests run it without Blender."""


def from_block(c: dict, aspect: float = 16 / 9) -> dict:
    st = c.get("start") or {}
    s = float(st.get("scale") or 1.0)
    cx, cy = float(st.get("cx", 50.0)), float(st.get("cy", 50.0))
    z = 1 + float(c.get("zoom_pct") or 0) / 100
    se = s * z
    dx, dy = (c.get("drift_px") or [0, 0])[:2]
    ex, ey = cx + float(dx) / 1920 * 100 / se, cy + float(dy) / 1080 * 100 / se

    def shift(x, y, m):                    # Blender shift is in frame widths (horizontal sensor fit), y up
        return (round((x - 50) / 100 * m, 4), round(-(y - 50) / 100 * m / aspect, 4))

    ea = c.get("ease_ae")
    return {"move": "zoom", "size": c.get("size"), "lens_scale": s, "zoom": round(z, 4),
            "shift0": shift(cx, cy, s), "shift": shift(ex, ey, se),
            "ease": (float(ea[1]), float(ea[0])) if ea and c.get("move") != "static" else (0.0, 0.0),
            "parallax": 0.0}
