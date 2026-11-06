import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools" / "style-learn"))
FX = Path(os.environ.get("LEARN_FIXTURES", ""))


def need_fixtures(test):
    if not (FX / "cuts.mp4").exists():
        test.skipTest("LEARN_FIXTURES chưa có: chạy qua sh tests/learn/run.sh")


class Project:
    """A throwaway project root (STUDIO_ROOT) with references/, my-styles/ and a fake library."""

    def __init__(self):
        self.dir = Path(tempfile.mkdtemp(prefix="learn proj."))
        (self.dir / "references").mkdir()
        (self.dir / "my-styles").mkdir()
        (self.dir / "my-styles" / "README.md").write_text(
            "# Phong cách riêng\n\n| Slug | Tên | Dựa trên | Nguồn | Ngày lưu |\n|---|---|---|---|---|\n", encoding="utf-8")
        for s in ("watercolor", "ink-wash", "_template"):
            (self.dir / "lib" / "lemo-opuscar" / "styles" / s).mkdir(parents=True)
            (self.dir / "lib" / "lemo-opuscar" / "styles" / s / "STYLE.md").write_text("x")
        self.old = os.environ.get("STUDIO_ROOT")
        os.environ["STUDIO_ROOT"] = str(self.dir)

    def close(self):
        if self.old is None:
            os.environ.pop("STUDIO_ROOT", None)
        else:
            os.environ["STUDIO_ROOT"] = self.old
        shutil.rmtree(self.dir, ignore_errors=True)
