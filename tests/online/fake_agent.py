"""Stands in for tools/runner/agent.py in tests (no Claude). Behaviour comes from tags in the idea:
[ask] ask a question first (exit 10), finish after the answer · [treatment] same, as a treatment review
[fail] / [fail-customer] job fail --by studio|customer · [loud] deliver a film at about −4 LUFS
[spend N] call the API N times through the proxy · [529] keep calling an API that is overloaded
[slow S] wait S seconds before finishing · [noreport] exit without job done · [crash] exit 3
[qc-bad] a 9 s still film first, fixed after the quality check · [qc-bad-always]
[narration] the Script step of specs/010 (SCRIPT.md, script check, script review, fixing flagged paragraphs; exit 3
of the review fails the job), then voice files and narration.json; editor tags such as [editor-p1 P02] go into
SCRIPT.md as a note
Every film ends with the Publish step of specs/011 (pack.json, three plain thumbnails, `publish --no-draw`);
[publish-bad] writes a 120-character title · [publish-cap] calls the API until the proxy stops it, then exits
without job done · [529-publish] keeps calling an overloaded API during Publish
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


def studio_rc(*args) -> int:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_OAUTH_TOKEN"}
    p = subprocess.run(["sh", str(REPO / "bin" / "studio"), *args], capture_output=True, text=True, env=env)
    if p.returncode not in (0, 1):
        print(f"studio {args[:2]} → {p.returncode}: {p.stdout[-300:]} {p.stderr[-500:]}", file=sys.stderr)
    return p.returncode


SCRIPT = """Title: A Fox and a Lantern
Target: 20s
Language: en
{tags}
[P01] Why does a small fox walk alone at night? She is looking for light.
[P02] She finds an old lantern in the snow. It still glows, warm and gold.
[P03] Now the whole forest is not dark anymore, and the little fox is never alone again.
"""


def script_step(idea: str, film: str) -> bool:
    """The Script step of JOB.md. False when the script did not pass (the job is failed)."""
    d = WORK / "films" / film
    d.mkdir(parents=True, exist_ok=True)
    studio("job", "step", JOB, "Script")
    if not (d / "SCRIPT.md").exists():
        tags = " ".join(re.findall(r"\[editor-[^\]]+\]", idea))
        (d / "SCRIPT.md").write_text(SCRIPT.format(tags=f"> {tags}\n" if tags else ""))
        (d / "SOURCES.md").write_text("no factual claims\n")
    customer = ["--customer-round"] if (WORK / ".customer_round").exists() else []
    if (d / "checks.json").exists() and studio_rc("script", "status", film) == 0:
        return True                                   # passed before this turn and not changed since
    if studio_rc("script", "check", film, *customer) != 0:
        studio("job", "fail", JOB, "the script check did not pass", "--by", "studio")
        return False
    for _ in range(6):
        rc = studio_rc("script", "review", film, *customer)
        if rc == 0:
            return True
        if rc != 1:
            studio("job", "fail", JOB, f"the script did not pass review (exit {rc})", "--by", "studio")
            return False
        checks = json.loads((d / "checks.json").read_text())
        flagged = {i["para"] for i in checks["script"]["editor"][-1]["issues"] if i["level"] in ("P1", "P2")}
        lines = []
        for ln in (d / "SCRIPT.md").read_text().splitlines():
            m = re.match(r"^\[(P\d+)\]", ln)
            lines.append(ln + " Truly." if m and m.group(1) in flagged else ln)
        (d / "SCRIPT.md").write_text("\n".join(lines) + "\n")
    return False


def voice_files(film: str) -> None:
    d = WORK / "films" / film
    (d / "voices").mkdir(parents=True, exist_ok=True)
    words = {f"l0{i}": [["word", 0.0, 0.3], ["end.", 0.32, 0.6]] for i in (1, 2, 3)}     # fits the 3 s sample film
    (d / "voices" / "words.json").write_text(json.dumps(words))
    (d / "voices" / "dur.json").write_text(json.dumps({k: 0.6 for k in words}))
    paras = [re.sub(r"^\[P\d+\]\s*", "", ln) for ln in (d / "SCRIPT.md").read_text().splitlines() if ln.startswith("[P")]
    (d / "lines.json").write_text(json.dumps([{"id": f"l0{i}", "text": t} for i, t in enumerate(paras, 1)]))
    (d / "narration.json").write_text(json.dumps({"words_file": "voices/words.json", "durations_file": "voices/dur.json",
                                                  "lines_file": "lines.json",
                                                  "lines": [{"id": f"l0{i}", "para": f"P0{i}", "at": round(0.2 + (i - 1) * 0.65, 2)}
                                                            for i in (1, 2, 3)]}))


def publish_step(idea: str, film: str):
    """The Publish step of JOB.md. Returns an exit code when the run ends here ([publish-cap]), else None."""
    studio("job", "step", JOB, "Publish")
    d = WORK / "films" / film
    sys.path.insert(0, str(REPO / "tests" / "filmcheck"))
    import samples
    samples.fake_thumbs(d)                       # no page to draw from: three plain pictures that pass
    pack = {"language": "en",
            "titles": [{"angle": "curiosity", "text": "The Fox Who Found a Lantern in the Snow",
                        "thumb": {"t": 0.5, "text": "Still glowing"}},
                       {"angle": "number", "text": "One Small Light Changed the Whole Forest",
                        "thumb": {"t": 1.5, "text": "Not dark anymore"}},
                       {"angle": "question", "text": "Why Does a Fox Walk Alone at Night?",
                        "thumb": {"t": 2.5, "text": "Looking for light"}}],
            "hook": ["A small fox walks alone at night.", "She is looking for light."],
            "summary": "A short story about a fox, a lantern and a forest that is not dark anymore.",
            "chapters": [], "hashtags": ["#fox", "#story", "#animation"]}
    if "[publish-bad]" in idea:
        pack["titles"][0]["text"] = "The Fox " + "x" * 112
    (d / "publish" / "pack.json").write_text(json.dumps(pack))
    if "[529-publish]" in idea:                   # Claude stops answering during Publish: the watchdog
        while True:
            call_api("overloaded")
            time.sleep(0.2)
    if "[publish-cap]" in idea:
        while call_api() == 200:
            pass
        result("ended")
        return 1
    studio_rc("publish", str(d), "--no-draw")
    return None


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
    if inp.get("kind") == "topics":              # specs/013: the real topic picker, through the proxy
        sys.path.insert(0, str(REPO / "tools"))
        from filmcheck import topics
        r = topics.run_job(WORK)
        result("ended")
        return 0 if r else 1
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
    narration = "[narration]" in idea and not inp.get("revise_of")
    if narration:
        if resumed and "Their note" in msg and "treatment review" in msg:
            (WORK / ".customer_round").write_text("1")
            d = WORK / "films" / inp["film"]
            (d / "SCRIPT.md").write_text((d / "SCRIPT.md").read_text().replace("warm and gold.", "warm and bright gold."))
        if not script_step(idea, inp["film"]):
            result("ended")
            return 0
    treat_ok = WORK / ".treatment_ok"
    if (inp.get("review_treatment") or "[treatment]" in idea) and not treat_ok.exists():
        if resumed and "treatment review" in msg and ": Approve." in msg:
            treat_ok.write_text("1")
        else:
            t = WORK / "treatment.md"
            t.write_text("# Treatment\nA fox finds a lantern." + (" (changed)" if "Their note" in msg else ""))
            film_arg = ["--film", inp["film"]] if narration else []
            studio("review", "request", JOB, "--kind", "treatment", "--summary", str(t), *film_arg)
            result("waiting")
            return 10
    if narration:
        studio("job", "step", JOB, "Voice")
        voice_files(inp["film"])
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
        if inp.get("lesson"):                      # specs/012: the note becomes a draft lesson for the channel
            (d / "LESSON_DRAFT.json").write_text(json.dumps({"what": inp.get("note", "")[:400], "why": "No rule caught it",
                                                             "stop": "Check this before delivery", "rule": None}))
        src = old.parent
        if (src / "SCRIPT.md").exists():          # as the revise prompt says: the script and its review come along
            import shutil
            for name in ("SCRIPT.md", "SOURCES.md", "checks.json", "narration.json", "lines.json"):
                if (src / name).exists():
                    shutil.copy2(src / name, d / name)
            for sub in (".check", "voices"):
                if (src / sub).exists():
                    shutil.copytree(src / sub, d / sub, dirs_exist_ok=True)
    still = "[qc-bad-always]" in idea or ("[qc-bad]" in idea and not (resumed and "quality check" in msg))
    if still:                              # 9 s of a still picture: the studio's qc finds it (specs/010 T027)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-stream_loop", "2", "-i", str(sample), "-c", "copy",
                        str(d / f"{film}.mp4")], check=True)
    else:
        (d / f"{film}.mp4").write_bytes(sample.read_bytes())
    if "[noreport]" in idea:
        result("ended")
        return 0
    rc = publish_step(idea, film)
    if rc is not None:
        return rc
    studio("job", "done", JOB, "--film", film)
    result("ended")
    return 0


if __name__ == "__main__":
    sys.exit(main())
