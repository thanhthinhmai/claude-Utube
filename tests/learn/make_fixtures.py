"""Make synthetic test videos with known properties (cuts, pans, brightness, silences).
   python make_fixtures.py OUT_DIR [--perf]
Frames are drawn with numpy and encoded with ffmpeg (libx264), so every property is exact."""
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

FPS = 30


def encode(path: Path, frames, w: int, h: int, fps: int = FPS, audio: Path = None) -> None:
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-"]
    if audio:
        cmd += ["-i", str(audio), "-c:a", "aac", "-b:a", "128k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "10", "-pix_fmt", "yuv420p", str(path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(np.ascontiguousarray(f, np.uint8).tobytes())
    p.stdin.close()
    if p.wait():
        raise SystemExit(f"ffmpeg failed for {path}")


def scene(seed: int, w: int = 640, h: int = 360) -> np.ndarray:
    """A blocky picture with its own colour family, so histograms differ between scenes."""
    r = np.random.default_rng(seed)
    base = r.integers(30, 225, 3)
    blocks = r.integers(-40, 40, (h // 40 + 1, w // 40 + 1, 3))
    img = np.repeat(np.repeat(blocks, 40, 0), 40, 1)[:h, :w] + base
    return np.clip(img, 0, 255).astype(np.uint8)


def cuts(out: Path) -> None:
    """7 scenes of 30 frames: 5 hard cuts, a 4-frame white flash in scene 3, a 12-frame dissolve 4→5."""
    S = [scene(s) for s in (11, 22, 33, 44, 55, 66, 77)]
    frames = []
    frames += [S[0]] * 30 + [S[1]] * 30                       # cut 1 at frame 30
    s3 = [S[2]] * 30
    for i in range(10, 14):
        s3[i] = np.full_like(S[2], 250)                       # flash, not a cut
    frames += s3                                              # cut 2 at 60
    frames += [S[3]] * 30                                     # cut 3 at 90
    for k in range(1, 13):                                    # dissolve 120..131
        a = k / 13
        frames.append((S[3] * (1 - a) + S[4] * a).astype(np.uint8))
    frames += [S[4]] * 30                                     # (soft transition)
    frames += [S[5]] * 30                                     # cut 4 at 162
    frames += [S[6]] * 30                                     # cut 5 at 192
    encode(out, frames, 640, 360)


def texture(w: int, h: int, seed: int = 5, block: int = 16) -> np.ndarray:
    r = np.random.default_rng(seed)
    t = r.integers(0, 255, (h // block + 2, w // block + 2, 3)).astype(np.float32)
    t = np.repeat(np.repeat(t, block, 0), block, 1)[:h, :w]
    # smooth so sub-pixel shifts look like real motion
    for ax in (0, 1):
        t = (np.roll(t, 1, ax) + 2 * t + np.roll(t, -1, ax)) / 4
    return t


def pan(out: Path, px_per_frame_at_640: float, n: int = 60) -> None:
    T = texture(640 + int(px_per_frame_at_640 * n) + 4, 360)
    frames = []
    for k in range(n):
        x = k * px_per_frame_at_640
        i, f = int(x), x - int(x)
        frames.append(T[:, i:i + 640] * (1 - f) + T[:, i + 1:i + 641] * f)
    encode(out, frames, 640, 360)


def flat(out: Path) -> None:
    encode(out, [np.full((360, 640, 3), (100, 150, 200), np.uint8)] * 30, 640, 360)


def black_white(out: Path) -> None:
    img = np.zeros((360, 640, 3), np.uint8)
    img[:, 320:] = 255
    encode(out, [img] * 30, 640, 360)


def stripes(out: Path) -> None:
    img = np.zeros((360, 640, 3), np.uint8)
    img[:, :213] = (200, 30, 30)
    img[:, 213:426] = (30, 170, 40)
    img[:, 426:] = (30, 40, 200)
    encode(out, [img] * 30, 640, 360)


def rainbow(out: Path) -> None:
    x = np.linspace(0, 1, 640, endpoint=False)
    hue = np.stack([np.clip(np.abs(x * 6 - 3) - 1, 0, 1),
                    np.clip(2 - np.abs(x * 6 - 2), 0, 1),
                    np.clip(2 - np.abs(x * 6 - 4), 0, 1)], -1)
    img = np.repeat((hue * 230 + 15)[None], 360, 0).astype(np.uint8)
    encode(out, [img] * 30, 640, 360)


def long_video(out: Path) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=160x90:r=30:d=300",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(out)], check=True)


def portrait(out: Path) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=30:d=1",
                    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(out)], check=True)


def tone(out: Path, tmp: Path) -> None:
    """5 s, 1 kHz at -12 dBFS, silent 1.0–1.5 s and 3.0–4.0 s."""
    sr = 48000
    t = np.arange(5 * sr) / sr
    a = 0.25 * np.sin(2 * np.pi * 1000 * t)
    a[(t >= 1.0) & (t < 1.5)] = 0
    a[(t >= 3.0) & (t < 4.0)] = 0
    wav = tmp / "tone.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((a * 32767).astype("<i2").tobytes())
    encode(out, [np.full((90, 160, 3), 128, np.uint8)] * (5 * FPS), 160, 90, audio=wav)


def perf_set(out: Path) -> None:
    """About 18 minutes in 20 videos of 54 s, with motion and colour change."""
    for i in range(20):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=s=1280x720:r=30:d=54",
                        "-f", "lavfi", "-i", f"sine=frequency={300 + 20 * i}:duration=54",
                        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac",
                        "-shortest", str(out / f"perf{i + 1:02d}.mp4")], check=True)


def main() -> None:
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    if "--perf" in sys.argv:
        perf_set(out); return
    cuts(out / "cuts.mp4")
    pan(out / "pan_fast.mp4", 4.0)                      # 2 px/frame at 320 wide
    pan(out / "pan_slow.mp4", 0.3 * 640 / 720)         # 0.3 px/frame at 720 wide
    flat(out / "flat.mp4")
    black_white(out / "bw.mp4")
    stripes(out / "stripes.mp4")
    rainbow(out / "rainbow.mp4")
    long_video(out / "long.mp4")
    portrait(out / "portrait.mp4")
    tone(out / "tone.mp4", out)
    (out / "broken.mp4").write_bytes(np.random.default_rng(1).integers(0, 255, 5000, np.uint8).tobytes())


if __name__ == "__main__":
    main()
