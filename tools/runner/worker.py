"""Worker: runs queued jobs, one container per run (specs/007 contracts/runner.md, research R4, R5, R13, R14).

Every tick (2 s):
1. Check the runs it started: finished, stopped by the customer, silent for too long, or over the run limit.
2. Put jobs whose review was answered back in the queue, to resume the same agent session.
3. Start the oldest queued job whose owner has nothing running, while fewer than N jobs run.

RUNNER=docker (default) starts `studio-job` containers; RUNNER=local runs the agent as a plain process
(tests, or a machine without Docker; no sandbox). Run: STUDIO_MODE=online python tools/runner/worker.py"""
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "studio"))
sys.path.insert(0, str(HERE))

from studio import accounts, db, jobs, mail, quotas, reviews, store  # noqa: E402
from studio.store import StudioError  # noqa: E402

import proxy  # noqa: E402

log = logging.getLogger("studio.worker")
EXIT_REVIEW = 10
LUFS, LUFS_TOL, PEAK_MAX = -14.0, 1.0, -1.0


def env_seconds(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


# ---------- runners ----------
class LocalRunner:
    """The agent as a child process in the job folder. No sandbox: only for tests and trusted machines."""
    name = "local"

    def __init__(self):
        self.cmd = shlex.split(os.environ.get("STUDIO_AGENT_CMD") or f"{shlex.quote(sys.executable)} {HERE / 'agent.py'}")
        self.lib = store.project_root() / "lib" / "lemo-opuscar"

    def start(self, job_id: str, work: Path, env: dict):
        base = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL", "TZ") if k in os.environ}
        env = {**base, **env, "STUDIO_WORK": str(work), "HOME": str(work / ".home")}
        with open(work / ".agent.log", "ab") as out:       # the child keeps its own copy of the file
            return subprocess.Popen(self.cmd, cwd=work, env=env, stdout=out, stderr=subprocess.STDOUT,
                                    start_new_session=True)

    def poll(self, handle):
        return handle.poll()

    def kill(self, handle):
        if handle.poll() is None:
            try:
                os.killpg(handle.pid, 9)
            except ProcessLookupError:
                pass
            handle.wait()

    def exec(self, work: Path, make_cmd, timeout: float = 900):
        """Run a check (ffmpeg, readcheck) on the job folder; `make_cmd(root, lib)` builds the command."""
        p = subprocess.run(make_cmd(str(work), str(self.lib)), cwd=work, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr


class DockerRunner:
    """A locked-down container per run (contracts/runner.md: Limits, Network)."""
    name = "docker"
    lib = "/studio/lib/lemo-opuscar"

    def __init__(self):
        self.docker = os.environ.get("DOCKER_BIN", "docker")
        self.image = os.environ.get("STUDIO_JOB_IMAGE", "studio-job:latest")
        if not self.image.startswith("studio-job:"):
            raise SystemExit("STUDIO_JOB_IMAGE must be a studio-job:* image")
        self.network = os.environ.get("STUDIO_JOB_NETWORK", "jobnet")
        self.cpus = os.environ.get("STUDIO_JOB_CPUS", "4")
        self.memory = os.environ.get("STUDIO_JOB_MEMORY", "8g")
        self.host_data = os.environ.get("STUDIO_HOST_DATA")        # /data as the Docker host sees it

    def _mount(self, work: Path) -> str:
        host = Path(self.host_data) / work.relative_to(db.data_dir()) if self.host_data else work
        return f"{host}:/work"

    def _flags(self, work: Path, network: str = None) -> list:
        return ["--user", "1000:1000", "--read-only", "--tmpfs", "/tmp:rw,size=2g", "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges", "--pids-limit", "512", "--cpus", self.cpus,
                "--memory", self.memory, "--network", network or self.network, "-v", self._mount(work), "-w", "/work"]

    def start(self, job_id: str, work: Path, env: dict):
        name = f"studio-{job_id}-{int(time.time())}"
        env = {**env, "STUDIO_WORK": "/work", "HOME": "/work/.home"}
        cmd = [self.docker, "run", "-d", "--name", name, "--label", f"studio.job={job_id}", *self._flags(work)]
        for k, v in env.items():
            cmd += ["-e", f"{k}={v}"]
        subprocess.run(cmd + [self.image], check=True, capture_output=True, text=True)
        return name

    def poll(self, name):
        p = subprocess.run([self.docker, "inspect", "-f", "{{.State.Status}} {{.State.ExitCode}}", name],
                           capture_output=True, text=True)
        if p.returncode != 0:
            return -1                      # the container is gone
        status, code = p.stdout.split()
        if status in ("exited", "dead"):
            logs = subprocess.run([self.docker, "logs", "--tail", "400", name], capture_output=True, text=True)
            try:
                with open(self._work_of(name) / ".agent.log", "a") as fh:
                    fh.write(logs.stdout + logs.stderr)
            except OSError:
                pass
            subprocess.run([self.docker, "rm", "-f", name], capture_output=True)
            return int(code)
        return None

    def _work_of(self, name: str) -> Path:
        job_id = name[len("studio-"):].rsplit("-", 1)[0]
        return db.data_dir() / "jobs" / job_id

    def kill(self, name):
        subprocess.run([self.docker, "rm", "-f", name], capture_output=True)

    def exec(self, work: Path, make_cmd, timeout: float = 900, network: str = "none"):
        """A check in a throw-away container with the same limits; no network unless asked."""
        cmd = make_cmd("/work", self.lib)
        p = subprocess.run([self.docker, "run", "--rm", *self._flags(work, network),
                            "--entrypoint", cmd[0], self.image, *cmd[1:]], capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr


def make_runner():
    return LocalRunner() if os.environ.get("RUNNER", "docker") == "local" else DockerRunner()


# ---------- quality check (R14) ----------
def loudness(text: str):
    """(integrated LUFS, true peak dB) from the summary of ffmpeg's ebur128 filter."""
    i = re.findall(r"I:\s+(-?[\d.]+|-inf) LUFS", text)
    pk = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", text)
    num = lambda s: float("-inf") if s == "-inf" else float(s)     # noqa: E731
    return (num(i[-1]) if i else None), (num(pk[-1]) if pk else None)


def quality(runner, work: Path, film: str) -> dict:
    d = work / "films" / film
    mp4 = d / f"{film}.mp4"
    if not mp4.is_file():
        return {"pass": False, "problems": [f"films/{film}/{film}.mp4 was not made"]}
    rel = f"films/{film}/{film}.mp4"
    rc, text = runner.exec(work, lambda root, lib: ["ffmpeg", "-nostats", "-hide_banner", "-i", f"{root}/{rel}",
                                                    "-af", "ebur128=peak=true", "-f", "null", "-"])
    lufs, peak = loudness(text)
    qa = {"lufs": lufs, "peak_db": peak, "readcheck": "not_checked", "problems": []}
    if rc != 0 or lufs is None:
        qa["problems"].append("the sound could not be measured")
    else:
        if not (LUFS - LUFS_TOL <= lufs <= LUFS + LUFS_TOL):
            qa["problems"].append(f"loudness is {lufs:.1f} LUFS; it must be {LUFS:.0f} ± {LUFS_TOL:.0f} LUFS")
        if peak is not None and peak > PEAK_MAX:
            qa["problems"].append(f"true peak is {peak:.1f} dB; it must be at most {PEAK_MAX:.0f} dB")
    has_lib = runner.name == "docker" or (Path(runner.lib) / "core/render/readcheck.mjs").is_file()
    if (d / "index.html").is_file() and has_lib:
        rc, text = runner.exec(work, lambda root, lib: ["node", f"{lib}/core/render/readcheck.mjs", f"{root}/films/{film}"])
        qa["readcheck"] = {0: "pass", 1: "fail"}.get(rc, "not_checked")
        if rc == 1:
            qa["problems"].append("some on-screen text is not shown long enough to read: " + text.strip()[-400:])
    qa["pass"] = not qa["problems"]
    return qa


# ---------- the worker ----------
class Run:
    def __init__(self, handle, started: float):
        self.handle, self.started = handle, started


class Worker:
    def __init__(self, runner=None, proxy_url: str = None):
        self.runner = runner or make_runner()
        self.proxy_url = proxy_url or os.environ.get("STUDIO_PROXY", "http://proxy:8780")
        self.runs = {}
        self.watchdog = env_seconds("STUDIO_WATCHDOG_S", 1800)      # no answer from Claude for 30 min
        self.run_limit = env_seconds("STUDIO_RUN_LIMIT_S", 3600)    # one run at most 60 min

    # ----- helpers -----
    def work_dir(self, job_id: str) -> Path:
        return db.data_dir() / "jobs" / job_id

    def notify(self, j: dict, template: str, **data) -> None:
        a = accounts.get(j["owner"])
        if a and a["email_notify"]:
            mail.queue(a["email"], template, {"name": j["name"], "job": j["id"], **data})

    def failed(self, job_id: str, error: str, by: str = "studio") -> None:
        j = quotas.fail(job_id, error, by)
        refund = ("Your credit was given back." if by == "studio" and not j.get("charged")
                  else "This job used one credit.")
        self.notify(j, "job_failed", error=error, refund=refund)
        log.info("job %s failed (%s): %s", job_id, by, error)

    # ----- start -----
    def recover(self) -> None:
        """After a worker restart: jobs marked running have no process any more. Run each again once."""
        for j in jobs.all_jobs():
            if j["status"] != "running" or j["id"] in self.runs or "charged" not in j:
                continue
            proxy.revoke(j["id"])
            if j.get("restarts", 0) < 1:
                def f(x):
                    x["status"], x["step"], x["restarts"] = "queued", "Queued", x.get("restarts", 0) + 1
                    x["log"].append(jobs._line("Restarted after a studio restart"))
                jobs.update(j["id"], f)
            else:
                self.failed(j["id"], "The studio restarted twice during this job.")

    def claim(self):
        """The next job to run, already marked running (one transaction: never more than N, one per customer)."""
        n = quotas.settings()["concurrency"]
        with db.tx() as con:
            busy = [r[0] for r in con.execute("SELECT owner FROM docs WHERE kind = 'job' AND status = 'running'")]
            if len(busy) >= n:
                return None
            rows = con.execute("SELECT id, owner, data FROM docs WHERE kind = 'job' AND status = 'queued' "
                               "ORDER BY json_extract(data, '$.queue_seq'), id").fetchall()
            pick = next((r for r in rows if r["owner"] not in busy), None)
            if not pick:
                return None
            j = json.loads(pick["data"])
            j["status"], j["step"] = "running", "Starting"
            j["run_count"] = j.get("run_count", 0) + 1
            j["updated_at"] = store.now_iso()
            j["log"].append(jobs._line("Started" if j["run_count"] == 1 else "Resumed"))
            j["log"] = j["log"][-jobs.LOG_KEEP:]
            j.pop("reported", None)
            store.doc_insert(con, "job", j["id"], j)
        return j

    def start(self, j: dict) -> None:
        work = self.work_dir(j["id"])
        (work / ".home").mkdir(parents=True, exist_ok=True)
        for f in (".result.json", ".review_pending"):
            (work / f).unlink(missing_ok=True)
        s = quotas.settings()
        store.write_json(work / ".input.json", {"job": j["id"], "model": s["model"], **(j.get("input") or {})})
        resume = j.get("resume")
        if resume:
            store.write_json(work / ".resume.json", {"session": j.get("agent_session"), "message": resume})
        else:
            (work / ".resume.json").unlink(missing_ok=True)
        token = proxy.issue(j["id"])
        env = {"ANTHROPIC_BASE_URL": self.proxy_url, "ANTHROPIC_API_KEY": token, "STUDIO_MODE": "online",
               "STUDIO_JOB": j["id"], "STUDIO_PROXY": self.proxy_url, "STUDIO_MODEL": s["model"]}
        try:
            handle = self.runner.start(j["id"], work, env)
        except Exception as e:    # noqa: BLE001 - e.g. Docker is down: the studio's fault
            proxy.revoke(j["id"])
            self.failed(j["id"], f"The studio could not start the job ({type(e).__name__}).")
            return
        self.runs[j["id"]] = Run(handle, time.time())
        log.info("job %s started (run %s)", j["id"], j["run_count"])

    def resume_answered(self) -> None:
        """Jobs whose review got a decision go back in the queue; the agent session is resumed (R5)."""
        for j in [x for x in jobs.all_jobs() if x["status"] == "waiting_review" and x["id"] not in self.runs]:
            if "charged" not in j or not j["review_ids"]:
                continue
            r = reviews.load(j["review_ids"][-1])
            d = r["decision"]
            if not d:
                continue
            msg = (f"The customer answered the {reviews.KINDS[r['kind']]} ({r['id']}): {reviews.LABEL[d['value']]}."
                   + (f"\nTheir note: {d['note']}" if d.get("note") else "") + "\nContinue the job.")

            def f(x):
                if x["status"] == "waiting_review":
                    x["status"], x["step"], x["resume"] = "queued", "Queued", msg
                    x["log"].append(jobs._line(f"Resumed after {reviews.KINDS[r['kind']]}: {reviews.LABEL[d['value']]}"))
            jobs.update(j["id"], f)

    # ----- finish -----
    def finished(self, job_id: str, rc: int) -> None:
        proxy.revoke(job_id)
        work = self.work_dir(job_id)
        result = store.read_json(work / ".result.json") or {}
        j = jobs.load(job_id)
        if result.get("session"):
            jobs.update(job_id, lambda x: x.__setitem__("agent_session", result["session"]))
        if j["status"] in jobs.FINAL:
            return
        if rc == EXIT_REVIEW or (work / ".review_pending").exists() or j["status"] == "waiting_review":
            if j["status"] != "waiting_review":
                self.failed(job_id, "The agent ended its turn without asking the customer anything.")
                return
            self.notify(j, "review_needed")
            return
        rep = j.get("reported") or {}
        if rep.get("done") is False:
            self.failed(job_id, rep.get("error") or "The job could not finish.", rep.get("by", "studio"))
            return
        if not rep.get("done"):
            err = result.get("error") or f"The agent stopped without finishing (exit code {rc})."
            self.failed(job_id, err)
            return
        if j["kind"] == "film":
            film = rep.get("film") or (j.get("input") or {}).get("film")
            qa = quality(self.runner, work, film)
            jobs.update(job_id, lambda x: x.__setitem__("qa", qa))
            if not qa["pass"]:
                if j.get("qa_retries", 0) < 1:
                    msg = ("The studio's quality check failed: " + "; ".join(qa["problems"])
                           + ". Fix the film, render it again, check it, then run `job done` again.")

                    def f(x):
                        x["status"], x["step"], x["resume"] = "queued", "Queued", msg
                        x["qa_retries"] = x.get("qa_retries", 0) + 1
                        x["log"].append(jobs._line("Quality check failed: " + "; ".join(qa["problems"])[:200]))
                    jobs.update(job_id, f)
                    return
                self.failed(job_id, "The film did not pass the quality check: " + "; ".join(qa["problems"]))
                return
            dest = store.account_dir(j["owner"]) / "films" / film
            shutil.copytree(work / "films" / film, dest, dirs_exist_ok=True)
            j = jobs.finish(job_id, "done", links={"film": film})
        else:
            j = jobs.finish(job_id, "done", links={k: v for k, v in rep.items() if k in ("film", "style")})
        self.notify(j, "job_done")
        shutil.rmtree(work, ignore_errors=True)
        log.info("job %s done", job_id)

    def check_runs(self) -> None:
        now = time.time()
        for job_id, run in list(self.runs.items()):
            try:
                j = jobs.load(job_id)
            except StudioError:
                j = None
            if j is None or j["status"] in jobs.FINAL:           # stopped by the customer, over the cost cap…
                self.runner.kill(run.handle)
                proxy.revoke(job_id)
                del self.runs[job_id]
                continue
            rc = self.runner.poll(run.handle)
            if rc is None:
                quiet = now - max(run.started, proxy.last_ok(job_id))
                if quiet > self.watchdog:
                    self.runner.kill(run.handle)
                    del self.runs[job_id]
                    proxy.revoke(job_id)
                    self.failed(job_id, f"Claude did not answer for {int(self.watchdog // 60) or 1} minutes.")
                elif now - run.started > self.run_limit:
                    self.runner.kill(run.handle)
                    del self.runs[job_id]
                    proxy.revoke(job_id)
                    self.failed(job_id, f"One run of the job took longer than {int(self.run_limit // 60) or 1} minutes.")
                continue
            del self.runs[job_id]
            try:
                self.finished(job_id, rc)
            except Exception as e:    # noqa: BLE001 - never let one job stop the worker
                log.exception("job %s: finishing failed", job_id)
                self.failed(job_id, f"The studio could not finish the job ({type(e).__name__}).")

    # ----- loop -----
    def tick(self) -> None:
        self.check_runs()
        self.resume_answered()
        while True:
            j = self.claim()
            if not j:
                break
            self.start(j)
        try:
            mail.flush()
        except Exception:   # noqa: BLE001 - mail problems are retried next time
            log.exception("mail")

    def run_forever(self, interval: float = 2.0, stop=None) -> None:
        self.recover()
        while not (stop and stop.is_set()):
            try:
                self.tick()
            except Exception:   # noqa: BLE001
                log.exception("tick")
            if stop:
                stop.wait(interval)
            else:
                time.sleep(interval)
        for job_id, run in list(self.runs.items()):
            self.runner.kill(run.handle)


def main():
    os.environ.setdefault("STUDIO_MODE", "online")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    Worker().run_forever(env_seconds("STUDIO_TICK_S", 2.0))


if __name__ == "__main__":
    main()
