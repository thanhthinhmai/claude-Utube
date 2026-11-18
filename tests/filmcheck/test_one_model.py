"""specs/024: one Claude model for every call of the studio (models.py, the code scan, `config model`)."""
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import models  # noqa: E402

OPUS = "claude-opus-5-5"
# where the studio starts a Claude call (claude -p, the Agent SDK, the API) …
LAUNCH = re.compile(r'"-p"|ClaudeAgentOptions\(|messages\.create\(')
# … and what proves the model there comes from the one setting
FROM_SETTING = re.compile(r"model_args\(\)|models\.current\(\)|quotas\.model\(\)|STUDIO_MODEL")
NEAR = 12      # lines around a launch (agent.py: model= sits 9 lines into ClaudeAgentOptions)


def scan(files) -> list:
    """[(file, line)] of Claude launches with no model from the one setting within NEAR lines."""
    bad = []
    for f in files:
        lines = Path(f).read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.lstrip().startswith("#") or not LAUNCH.search(line):
                continue
            if not any(FROM_SETTING.search(x) for x in lines[max(0, i - NEAR):i + NEAR + 1]):
                bad.append((str(f), i + 1))
    return bad


def studio_code():
    return [p for p in (REPO / "tools").rglob("*.py") if ".venv" not in p.parts and "license" not in p.parts]


class Scan(unittest.TestCase):
    def test_every_launch_takes_the_one_model(self):              # SC-002
        files = studio_code()
        self.assertGreater(len(files), 20)
        self.assertEqual(scan(files), [])

    def test_scan_finds_a_launch_without_the_model(self):         # the scan itself works
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "bad.py"
            f.write_text('import subprocess\n\n\ndef ask():\n    return subprocess.run([claude_bin(), "-p", "hi"])\n')
            self.assertEqual(scan([f]), [(str(f), 5)])
            f.write_text('def ask():\n    args = [claude_bin(), "-p", "hi", *model_args()]\n')
            self.assertEqual(scan([f]), [])

    def test_the_launches_found(self):                            # the scan sees the studio's known calls
        hits = {Path(f).name for f in studio_code() for line in Path(f).read_text(encoding="utf-8").splitlines()
                if LAUNCH.search(line) and not line.lstrip().startswith("#")}
        self.assertTrue({"editor.py", "labeler.py", "topics_fit.py", "moderation.py", "agent.py"} <= hits, hits)


class Models(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.old = {k: os.environ.get(k) for k in ("STUDIO_ROOT", "STUDIO_MODEL", "STUDIO_EDITOR_MODEL")}
        os.environ["STUDIO_ROOT"] = str(self.root)
        os.environ.pop("STUDIO_MODEL", None)
        os.environ.pop("STUDIO_EDITOR_MODEL", None)

    def tearDown(self):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def config(self, data):
        (self.root / ".studio").mkdir(exist_ok=True)
        (self.root / ".studio/config.json").write_text(json.dumps(data))

    def test_list(self):                                          # FR-001
        self.assertEqual((models.allowed(), models.default()), ({OPUS: "Opus 5.5"}, OPUS))

    def test_sources_and_unknown_values(self):                    # FR-003, FR-009, FR-010
        self.assertEqual(models.current(), OPUS)
        os.environ["STUDIO_EDITOR_MODEL"] = "haiku"
        self.config({"editor_model": "sonnet"})
        self.assertEqual(models.current(), OPUS)
        for where in ("env", "config"):
            err = io.StringIO()
            if where == "env":
                os.environ["STUDIO_MODEL"] = "claude-haiku-5-5"
            else:
                os.environ.pop("STUDIO_MODEL", None)
                self.config({"model": "claude-haiku-5-5"})
            with redirect_stderr(err):
                self.assertEqual(models.current(), OPUS)
            self.assertIn("claude-haiku-5-5 is not allowed", err.getvalue())

    def test_set_model(self):
        self.config({"render": "auto"})
        models.set_model(OPUS)
        self.assertEqual(json.loads((self.root / ".studio/config.json").read_text()), {"render": "auto", "model": OPUS})
        with self.assertRaises(ValueError):
            models.set_model("claude-haiku-5-5")

    def test_helper_env_and_main_model(self):                     # FR-004, FR-005
        env = models.helper_env({})
        self.assertEqual(env, {"ANTHROPIC_DEFAULT_HAIKU_MODEL": OPUS, "ANTHROPIC_SMALL_FAST_MODEL": OPUS})
        used = {"modelUsage": {"claude-haiku-5-5": {"outputTokens": 779}, OPUS: {"outputTokens": 229}}}
        self.assertEqual(models.main_model(used, OPUS), OPUS)          # the asked one, not the first listed
        self.assertEqual(models.main_model({"modelUsage": {"a": {"outputTokens": 1}, "b": {"outputTokens": 9}}}, OPUS), "b")
        self.assertEqual(models.main_model({}, OPUS), OPUS)

    def test_config_model_command(self):                          # FR-008, SC-003
        env = {**os.environ}
        run = lambda *a: subprocess.run(["sh", str(REPO / "bin/studio"), "config", "model", *a], env=env,  # noqa: E731
                                        capture_output=True, text=True)
        p = run()
        self.assertEqual((p.returncode, p.stdout.strip()), (0, OPUS))
        p = run(OPUS)
        self.assertEqual((p.returncode, p.stdout.strip()), (0, f"model: {OPUS}"))
        before = (self.root / ".studio/config.json").read_text()
        p = run("claude-haiku-5-5")
        self.assertEqual(p.returncode, 2)
        self.assertIn(f"model must be one of: {OPUS}", p.stderr)
        self.assertEqual((self.root / ".studio/config.json").read_text(), before)
        self.assertEqual(subprocess.run(["sh", str(REPO / "bin/studio"), "config", "editor-model", "opus"], env=env,
                                        capture_output=True, text=True).returncode, 2)


if __name__ == "__main__":
    unittest.main()
