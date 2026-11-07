"""Stands in for tools/runner/agent.py in tests (no Claude). Behaviour comes from tags in the idea:
[ask] ask a question first (exit 10), finish after the answer · [treatment] same, as a treatment review
[fail] / [fail-customer] job fail --by studio|customer · [loud] deliver a film at about −4 LUFS
[spend N] call the API N times through the proxy · [529] keep calling an API that is overloaded
[slow S] wait S seconds before finishing · [noreport] exit without job done · [crash] exit 3"""
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
    p = subprocess.run(["sh", str(REPO / "bin" / "studio"), *args], capture_output=True, text=True)
    if p.returncode not in (0, 10):
        print(f"studio {args[:2]} → {p.returncode}: {p.stderr}", file=sys.stderr)
    return p.stdout


def call_api(model: str = "claude-opus-5-5") -> int:
    body = json.dumps({"model": model, "max_tokens": 16, "messages": [{"role": "user", "content": "hi"}]}).encode()
    req = urllib.request.Request(os.environ["ANTHROPIC_BASE_URL"].rstrip("/") + "/v1/messages", data=body, method="POST",
                                 headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "content-type": "application/json",
                                          "anthropic-version": "2023-06-01"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def result(status: str, error: str = None):
    (WORK / ".result.json").write_text(json.dumps({"status": status, "session": f"sess-{JOB}", "error": error}))


def main() -> int:
    inp = json.loads((WORK / ".input.json").read_text())
    idea = inp.get("idea", "")
    resumed = (WORK / ".resume.json").exists()
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    studio("job", "log", JOB, f"key kind: {'job token' if key.startswith('sk-job-') else 'OTHER'}")
    studio("job", "step", JOB, "Treatment")
    for kind in ("ask", "treatment"):
        if f"[{kind}]" in idea and not resumed:
            q = WORK / "question.md"
            q.write_text("Should the fox be orange or grey?")
            studio("review", "request", JOB, "--kind", "question" if kind == "ask" else "treatment", "--summary", str(q))
            result("waiting")
            return 10
    if resumed:
        studio("job", "log", JOB, "answer: " + json.loads((WORK / ".resume.json").read_text())["message"][:120])
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
    (d / f"{film}.mp4").write_bytes(sample.read_bytes())
    if "[noreport]" in idea:
        result("ended")
        return 0
    studio("job", "done", JOB, "--film", film)
    result("ended")
    return 0


if __name__ == "__main__":
    sys.exit(main())
