"""Stands in for tools/runner/agent.py in tests (no Claude). Behaviour comes from tags in the idea:
[ask] ask a question first (exit 10), finish after the answer · [treatment] same, as a treatment review
[fail] / [fail-customer] job fail --by studio|customer · [loud] deliver a film at about −4 LUFS
[spend N] call the API N times through the proxy · [529] keep calling an API that is overloaded
[slow S] wait S seconds before finishing · [noreport] exit without job done · [crash] exit 3
Learn jobs: makes a reference set with videos, sheets, transcripts and proof frames, asks review 1, then
review 2 (exit 10 each time), then saves my-styles/<slug>/. A channel URL with "fail" in it fails the job,
one with "hang" waits until stopped."""
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SAMPLES = Path(__file__).resolve().parent / ".tmp"
WORK = Path(os.environ["STUDIO_WORK"])
JOB = os.environ["STUDIO_JOB"]


def studio(*args) -> str:
    """Like the agent's Bash tool: Claude Code does not pass CLAUDE_CODE_OAUTH_TOKEN on (first live run)."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_OAUTH_TOKEN"}
    p = subprocess.run(["sh", str(REPO / "bin" / "studio"), *args], capture_output=True, text=True, env=env)
    if p.returncode not in (0, 10):
        print(f"studio {args[:2]} → {p.returncode}: {p.stderr}", file=sys.stderr)
    return p.stdout


def call_api(model: str = "claude-opus-5-5") -> int:
    body = json.dumps({"model": model, "max_tokens": 16, "messages": [{"role": "user", "content": "hi"}]}).encode()
    req = urllib.request.Request(os.environ["ANTHROPIC_BASE_URL"].rstrip("/") + "/v1/messages", data=body, method="POST",
                                 headers={"authorization": "Bearer " + os.environ["CLAUDE_CODE_OAUTH_TOKEN"],
                                          "content-type": "application/json", "anthropic-version": "2023-06-01",
                                          "anthropic-beta": "oauth-2025-04-20,claude-code-20250219"})   # like Claude Code
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def result(status: str, error: str = None):
    (WORK / ".result.json").write_text(json.dumps({"status": status, "session": f"sess-{JOB}", "error": error}))


def make_set(name: str) -> Path:
    """What `learn fetch/measure/transcribe` and the proof step leave behind."""
    d = WORK / "references" / name
    frame = (SAMPLES / "frame.jpg").read_bytes()
    for sub in ("videos", "profile/v01/sheets", "transcripts", "proof/out", "style"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    (d / "videos" / "v01.mp4").write_bytes((SAMPLES / "good.mp4").read_bytes())
    (d / "videos" / "v01.m4a").write_bytes(b"audio")
    for i in range(1, 4):
        (d / "profile/v01/sheets" / f"v01_{i:04d}.jpg").write_bytes(frame)
    (d / "profile/v01/words.json").write_text('[{"w": "hello"}]')
    (d / "transcripts" / "v01.txt").write_text("hello world")
    (d / "profile/v01/video.json").write_text('{"orientation": "landscape", "duration": 3}')
    (d / "profile/summary.json").write_text('{"videos_measured": 1, "measured_seconds": 3, "by_orientation": {}}')
    (d / "set.json").write_text(json.dumps({"created": "2026-11-07", "source": {"inputs": ["x"]},
                                            "videos": [{"id": "v01", "state": "measured", "title": "Secret title",
                                                        "channel": "Secret channel"}]}))
    (d / "proof/out" / "ref.jpg").write_bytes(frame)
    for r in range(1, 9):
        (d / "proof/out" / f"ours_r{r}_0.5.jpg").write_bytes(frame)
    (d / "proof/compare.jpg").write_bytes(frame)
    (d / "proof/compare.json").write_text(json.dumps({"luma_diff": 0.01, "sat_median_diff": 0.02, "dark_diff_pp": 1,
                                                      "palette_matched": 4, "palette_needed": 3, "pass": True, "round": 1,
                                                      "ref": "proof/out/ref.jpg", "ours": "proof/out/ours_r1_0.5.jpg"}))
    return d


def learn(inp: dict, stage: int) -> int:
    name, src = inp["set"], inp.get("channel") or ""
    if os.environ.get("STUDIO_ROOT") != str(WORK):
        studio("job", "fail", JOB, "STUDIO_ROOT is not the job folder")
        return 0
    if stage == 0:
        studio("job", "step", JOB, "Fetch videos")
        if inp.get("source") == "upload" and not list((WORK / "uploads").glob("*.mp4")):
            studio("job", "fail", JOB, "no uploaded videos")
            return 0
        d = make_set(name)
        if "fail" in src:
            studio("job", "fail", JOB, "fetch failed")
            return 0
        if "hang" in src:
            while True:
                time.sleep(0.2)
        (d / "style" / "review-1.md").write_text("# Style draft\nDark, slow, warm.")
        studio("review", "request", JOB, "--kind", "style-1", "--set", name, "--summary", str(d / "style/review-1.md"))
        return 10
    d = WORK / "references" / name
    if stage == 1:
        (d / "style" / "review-2.md").write_text("# Proof frame\nAll 4 checks pass.")
        studio("review", "request", JOB, "--kind", "style-2", "--set", name, "--summary", str(d / "style/review-2.md"))
        return 10
    slug = f"warm-night-{JOB[-4:]}"
    m = WORK / "my-styles" / slug
    m.mkdir(parents=True)
    (m / "style.json").write_text(json.dumps({"slug": slug, "en": "Warm Night", "based_on": "art-deco", "source": "learned"}))
    (m / "STYLE.md").write_text("# Warm Night\n1. Palette …")
    (m / "EVIDENCE.md").write_text("# Evidence")
    (m / "styleframe.jpg").write_bytes((SAMPLES / "frame.jpg").read_bytes())
    readme = WORK / "my-styles" / "README.md"
    text = readme.read_text() if readme.exists() else "# Phong cách riêng\n\n| Slug | Tên | Dựa trên | Nguồn | Ngày lưu |\n|---|---|---|---|---|\n"
    readme.write_text(text + f"| {slug} | Warm Night | art-deco | learned (1 video) | 2026-11-07 |\n")
    studio("job", "done", JOB, "--style", slug)
    return 0


def main() -> int:
    inp = json.loads((WORK / ".input.json").read_text())
    if inp.get("kind") == "learn":
        stage_file = WORK / ".stage"
        stage = int(stage_file.read_text()) if stage_file.exists() else 0
        stage_file.write_text(str(stage + 1))
        rc = learn(inp, stage)
        result("waiting" if rc == 10 else "ended")
        return rc
    idea = inp.get("idea", "")
    resumed = (WORK / ".resume.json").exists()
    key = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")
    plain = "ANTHROPIC_API_KEY" not in os.environ
    studio("job", "log", JOB, f"key kind: {'job token' if key.startswith('sk-job-') and plain else 'OTHER'}")
    studio("job", "step", JOB, "Treatment")
    msg = json.loads((WORK / ".resume.json").read_text())["message"] if resumed else ""
    if resumed:
        studio("job", "log", JOB, "answer: " + msg[:160].replace("\n", " "))
    # questions: [ask] one, [ask N] up to N; a refused request (over the limit) is logged and the film goes on
    m = re.search(r"\[ask(?: (\d+))?\]", idea)
    asks, asked_file = (int(m.group(1) or 1) if m and not inp.get("revise_of") else 0), WORK / ".asked"
    asked = int(asked_file.read_text()) if asked_file.exists() else 0
    if asked < asks:
        asked_file.write_text(str(asked + 1))
        q = WORK / "question.md"
        q.write_text(f"Question {asked + 1}: should the fox be orange or grey?")
        studio("review", "request", JOB, "--kind", "question", "--summary", str(q))
        if (WORK / ".review_pending").exists():
            result("waiting")
            return 10
        studio("job", "log", JOB, "question refused")
    treat_ok = WORK / ".treatment_ok"
    if (inp.get("review_treatment") or "[treatment]" in idea) and not treat_ok.exists():
        if resumed and "treatment review" in msg and ": Approve." in msg:
            treat_ok.write_text("1")
        else:
            t = WORK / "treatment.md"
            t.write_text("# Treatment\nA fox finds a lantern." + (" (changed)" if "Their note" in msg else ""))
            studio("review", "request", JOB, "--kind", "treatment", "--summary", str(t))
            result("waiting")
            return 10
    m = re.search(r"\[spend (\d+)\]", idea)
    for _ in range(int(m.group(1)) if m else 0):
        studio("job", "log", JOB, f"api: {call_api()}")
    if "[529]" in idea:
        while True:
            call_api("overloaded")
            time.sleep(0.2)
    if "[crash]" in idea:
        return 3
    if "[fail-customer]" in idea:
        studio("job", "fail", JOB, "The idea cannot be filmed", "--by", "customer")
        result("ended")
        return 0
    if "[fail]" in idea:
        studio("job", "fail", JOB, "A tool broke")
        result("ended")
        return 0
    m = re.search(r"\[slow ([\d.]+)\]", idea)
    if m:
        time.sleep(float(m.group(1)))
    studio("job", "step", JOB, "Render")
    film = inp["film"]
    d = WORK / "films" / film
    d.mkdir(parents=True, exist_ok=True)
    loud = "[loud]" in idea and not (resumed and "quality check" in (WORK / ".resume.json").read_text() and "[loud-always]" not in idea)
    sample = SAMPLES / ("loud.mp4" if loud or "[loud-always]" in idea else "good.mp4")
    if inp.get("revise_of"):                       # a changed version starts from the old film, which stays as it is
        old = WORK / "films" / inp["revise_of"] / f"{inp['revise_of']}.mp4"
        if not old.is_file():
            studio("job", "fail", JOB, "the old film is missing")
            result("ended")
            return 0
        sample = old
        (d / "NOTE.txt").write_text(inp.get("note", ""))
    (d / f"{film}.mp4").write_bytes(sample.read_bytes())
    if "[noreport]" in idea:
        result("ended")
        return 0
    studio("job", "done", JOB, "--film", film)
    result("ended")
    return 0


if __name__ == "__main__":
    sys.exit(main())
