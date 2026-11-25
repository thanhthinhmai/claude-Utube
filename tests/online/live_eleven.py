"""specs/036 T043 (SC-003): a real ElevenLabs run, only with ELEVENLABS_API_KEY (in the environment or .env).
Reads 3 short lines of a temporary film with the account's first voice and checks that the characters charged
(`character_count` before and after) match usage.json within 1 % and stay under the estimate. Spends about 100 characters."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import eleven  # noqa: E402

LINES = ["The kettle clicked off at midnight.", "Nobody in the house was awake.", "Except, of course, the cat."]


def main() -> int:
    os.environ.update({k: v for k, v in eleven.load_env(REPO).items() if k not in os.environ})
    if not os.environ.get("ELEVENLABS_API_KEY"):
        print("= no ELEVENLABS_API_KEY: the ElevenLabs run is skipped")
        return 0
    voice = next((v["id"] for v in eleven.list_voices()), None)
    if not voice:
        print("✗ the account has no voice")
        return 1
    root = Path(tempfile.mkdtemp(prefix="live-eleven."))
    d = root / "films" / "live-eleven"
    d.mkdir(parents=True)
    (d / "lines.json").write_text(json.dumps([{"id": f"l{i + 1}", "para": "P01", "text": t, "voice": voice}
                                              for i, t in enumerate(LINES)]))
    before = eleven.subscription()["used"]
    env = {**os.environ, "STUDIO_ROOT": str(root)}
    for k in ("STUDIO_JOB_TOKEN", "STUDIO_PROXY", "STUDIO_TTS_DRY", "STUDIO_TTS_FAKE"):
        env.pop(k, None)
    r = subprocess.run(["sh", str(REPO / "bin" / "studio"), "voice", "make", "live-eleven", "--yes"], env=env,
                       capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode:
        print(r.stderr.strip())
        return 1
    after = eleven.subscription()["used"]
    u = json.loads((d / "voices" / "usage.json").read_text())
    est, mine = u["runs"][-1]["chars_estimated"], u["runs"][-1]["chars"]
    for _ in range(12):                    # the account's count catches up a few seconds later
        charged = after - before
        if charged >= mine:
            break
        time.sleep(10)
        after = eleven.subscription()["used"]
    gap = abs(charged - mine) / max(1, charged)
    print(f"estimate {est} (ceiling) · usage.json {mine} · account {charged} · gap {gap:.1%}")
    ok = gap <= 0.01 and mine <= est and all((d / "voices" / f"l{i}.wav").is_file() for i in (1, 2, 3))
    print("✓ SC-003" if ok else "✗ SC-003: usage.json and the account differ by more than 1 %")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
