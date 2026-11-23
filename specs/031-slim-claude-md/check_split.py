"""specs/031: every line of the old CLAUDE.md is still somewhere, and the root file is small.
Exit 1 when a line is missing, a film-flow pointer is left in the root, or CLAUDE.md is over 9000 bytes."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NEW = ["CLAUDE.md", ".claude/skills/film-make/SKILL.md", "desktop/CLAUDE.md", "tools/CLAUDE.md"]
LIMIT = 9000
# Lines replaced by a pointer on purpose (why):
REPLACED = {
    "| Làm một bộ phim, video, clip (theo phong cách thư viện hoặc phong cách riêng) | **Làm phim** (bên dưới). Không tạo spec cho từng phim |":
        "row now points to the film-make skill",
    "4. Không sửa file nào trong `lib/` (hiến pháp VI). Muốn dùng phiên bản thư viện mới thì đổi `library.lock` theo quy trình spec-kit.":
        "kept as a bullet of Luật bắt buộc in the root and as step 4 in the skill",
}


def main() -> int:
    old = subprocess.run(["git", "show", "main:CLAUDE.md"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    new = "\n".join((ROOT / f).read_text(encoding="utf-8") for f in NEW)
    lines = [ln for ln in old.splitlines() if ln.strip() and not ln.startswith("#")]
    missing = [ln for ln in lines if ln not in new and ln not in REPLACED]
    for ln in REPLACED:
        if ln not in lines:
            print(f"stale exception: {ln[:80]}")
    size = (ROOT / "CLAUDE.md").stat().st_size
    root = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    pointer = "film-make/SKILL.md" in root and "(bên dưới)" not in root
    print(f"old CLAUDE.md: {len(old.encode())} bytes, {len(lines)} content lines")
    print(f"new CLAUDE.md: {size} bytes (limit {LIMIT}, {100 - size * 100 // len(old.encode())}% smaller)")
    print(f"missing lines: {len(missing)}")
    for ln in missing:
        print("  - " + ln[:120])
    print(f"root points to the film-make skill: {'yes' if pointer else 'NO'}")
    return 0 if not missing and size <= LIMIT and pointer else 1


if __name__ == "__main__":
    sys.exit(main())
