"""Type check of the UI script (specs/006-app-ts-check). Needs npx; TypeScript is fetched once into the npm cache."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "tools" / "studio" / "studio" / "web" / "app.js"
TSC = ["npx", "-y", "-p", "typescript@5.6.3", "tsc", "--noEmit", "--allowJs", "--checkJs",
       "--target", "es2022", "--lib", "es2022,dom,dom.iterable"]


class TypeCheck(unittest.TestCase):
    def test_app_js_has_no_type_errors(self):  # FR-003, FR-004
        if not shutil.which("npx"):
            self.skipTest("không có npx")
        with tempfile.TemporaryDirectory() as tmp:          # no config or files read from / written to the repo
            try:
                r = subprocess.run(TSC + [str(APP)], cwd=tmp, capture_output=True, text=True, timeout=180)
            except subprocess.TimeoutExpired:
                self.skipTest("tải TypeScript quá lâu")
        out = r.stdout + r.stderr
        if r.returncode == 0:
            return
        errors = [l for l in out.splitlines() if "error TS" in l]
        if not errors:
            self.skipTest(f"không tải được TypeScript: {out.strip()[-200:]}")
        self.fail(f"{len(errors)} lỗi kiểu trong app.js:\n" + "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
