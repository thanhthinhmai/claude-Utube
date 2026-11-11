"""Draw the app and tray icons with plain Python (specs/015 T002): a rounded square with a play triangle.
Run: python3 desktop/assets/make_icons.py  (writes the PNGs next to this file)."""
import struct
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent


def png(path, w, h, pixel):
    rows = b"".join(b"\x00" + b"".join(bytes(pixel(x, y)) for x in range(w)) for y in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)  # noqa: E731
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) \
        + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")
    Path(path).write_bytes(data)


def shape(n):
    """(inside rounded square, inside play triangle) for pixel x, y of an n × n icon, with 4× supersampling."""
    def cover(x, y):
        sq = tri = 0
        for sx in range(4):
            for sy in range(4):
                u, v = (x + (sx + 0.5) / 4) / n, (y + (sy + 0.5) / 4) / n
                r, m = 0.22, 0.04
                cx, cy = min(max(u, m + r), 1 - m - r), min(max(v, m + r), 1 - m - r)
                if (u - cx) ** 2 + (v - cy) ** 2 <= r * r and m <= u <= 1 - m and m <= v <= 1 - m:
                    sq += 1
                if 0.38 <= u and abs(v - 0.5) <= (0.74 - u) * 0.85 and u <= 0.74:
                    tri += 1
        return sq / 16, tri / 16
    return cover


def app_icon(n, path):
    cover = shape(n)

    def px(x, y):
        sq, tri = cover(x, y)
        if tri:
            a = int(255 * max(sq, tri))
            return (255, 255, 255, a) if tri >= sq else (32, 34, 52, a)
        return (32, 34, 52, int(255 * sq))
    png(path, n, n, px)


def template_icon(n, path, rgb=(0, 0, 0)):
    cover = shape(n)

    def px(x, y):
        sq, tri = cover(x, y)
        return (*rgb, int(255 * max(0.0, sq - tri)))      # the square with the triangle cut out
    png(path, n, n, px)


if __name__ == "__main__":
    app_icon(512, HERE / "icon.png")
    app_icon(32, HERE / "tray.png")
    template_icon(16, HERE / "trayTemplate.png")
    template_icon(32, HERE / "trayTemplate@2x.png")
    print("icons written to", HERE)
