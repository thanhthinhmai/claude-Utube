"""specs/023 T007: learn template-check (contracts/template-format.md)."""
import json
import unittest

from helpers import Project
from sl import refset, template

SET, SLUG = "ref-set", "night-ink"


def good_template(n=15, beats=True):
    parts = [f"# Template: Night Ink\n\nBộ tham chiếu: {SET} · 2 video\n"]
    for i, name in enumerate(template.COMPONENTS[:n], 1):
        parts.append(f"""## {i}. {name}
Mô tả của xưởng cho thành phần này.

| Số đo | Giá trị | Khoảng | Nguồn |
|---|---|---|---|
| tỉ lệ máy đứng yên | 0,86 | 0,72–0,93 | template.json → motion.still_ratio |

Bằng chứng: v01_shots_1.jpg#S001, v01/strips/S002.jpg#3, v02/evidence/face.jpg
Nên làm: một điều.
Không nên làm: một điều khác.
Trong bộ dựng: `figure.face`
""")
    if beats:
        parts.append("## Công thức nhịp\n")
        for b in template.BEATS:
            rows = "\n".join(f"| {r} | x |" for r in template.BEAT_ROWS)
            parts.append(f"### {b}\n\n| Mục | Giá trị |\n|---|---|\n{rows}\n")
    return "\n".join(parts)


GOOD_STYLE = """# Night Ink — Style Prompt

> intro line without a label is fine

## 1. Essence
- violet grade [bằng chứng: summary.json → luma_p50]
- subtitles burned in [xưởng]

| Shot | Share |
|---|---|
| wide | 25 % [bằng chứng: v01_shots_1.jpg#S001] |

## 12. Extra
- not checked
"""


class TemplateCheck(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        prof = refset.refs_dir() / SET / "profile"
        for rel in ("v01/shot-sheets/v01_shots_1.jpg", "v01/strips/S002.jpg", "v02/evidence/face.jpg"):
            (prof / rel).parent.mkdir(parents=True, exist_ok=True)
            (prof / rel).write_bytes(b"jpg")
        refset.write_json(prof / "summary.json", {"luma_p50": 0.25})
        refset.write_json(prof / "craft-summary.json", {"person": {"active_share": {"p10": 0.09}}})
        self.d = self.p.dir / "my-styles" / SLUG
        self.d.mkdir()
        self.write(good_template(), GOOD_STYLE,
                   {"version": 1, "set": SET, "motion": {"still_ratio": [0.72, 0.93]},
                    "source": {"motion.still_ratio": "summary.json"}})

    def tearDown(self):
        self.p.close() if hasattr(self.p, "close") else None

    def write(self, md=None, style=None, tj=None):
        if md is not None:
            (self.d / "TEMPLATE.md").write_text(md, encoding="utf-8")
        if style is not None:
            (self.d / "STYLE.md").write_text(style, encoding="utf-8")
        if tj is not None:
            (self.d / "template.json").write_text(json.dumps(tj), encoding="utf-8")

    def problems(self, partial=None):
        return template.check_template(SLUG, partial) + template.check_numbers(SLUG) + template.check_style_tags(SLUG)

    def test_good_passes(self):
        self.assertEqual(self.problems(), [])
        self.assertEqual(template.cli(SLUG), 0)

    def one(self, partial=None):
        got = self.problems(partial)
        self.assertEqual(len(got), 1, got)
        return got[0]

    def test_missing_component(self):
        self.write(good_template().replace("## 7. Đám đông", "## 7. Đám đông người"))
        self.assertIn("§7", self.one())

    def test_too_little_evidence(self):
        md = good_template().replace(", v02/evidence/face.jpg", "", 1)       # §1 keeps 2 pieces from 1 video
        self.write(md)
        self.assertIn("≥ 3 bằng chứng", self.one())
        # a rare component may say so instead
        self.write(md.replace("v01/strips/S002.jpg#3\n", "v01/strips/S002.jpg#3\nÍt bằng chứng: 2 khung\n", 1))
        self.assertEqual(self.problems(), [])

    def test_one_video_only(self):
        md = good_template().replace("v02/evidence/face.jpg", "v01/evidence/face.jpg", 1)
        (refset.refs_dir() / SET / "profile" / "v01" / "evidence").mkdir()
        (refset.refs_dir() / SET / "profile" / "v01" / "evidence" / "face.jpg").write_bytes(b"jpg")
        self.write(md)
        self.assertIn("từ 1 video", self.one())

    def test_missing_evidence_file(self):
        self.write(good_template().replace("v02/evidence/face.jpg", "v02/evidence/gone.jpg", 1))
        self.assertIn("gone.jpg", self.one())

    def test_missing_dont_line(self):
        self.write(good_template().replace("Không nên làm: một điều khác.\n", "", 1))
        self.assertIn("Không nên làm", self.one())

    def test_missing_beat(self):
        self.write(good_template().replace("### sting", "### stinger"))
        self.assertIn("sting", self.one())

    def test_partial_skips_later_parts(self):
        self.write(good_template(n=10, beats=False))
        self.assertEqual(self.problems((1, 10)), [])
        self.assertTrue(any("§11" in x for x in self.problems()))

    def test_style_label_missing(self):
        self.write(style=GOOD_STYLE.replace("- subtitles burned in [xưởng]", "- subtitles burned in"))
        self.assertIn("dòng 7", self.one())

    def test_style_label_without_citation(self):
        self.write(style=GOOD_STYLE.replace("[bằng chứng: summary.json → luma_p50]", "[bằng chứng: see the report]"))
        self.assertIn("trích dẫn", self.one())

    def test_number_differs_from_source(self):
        self.write(good_template().replace("0,72–0,93", "0,70–0,93", 1))
        self.assertIn("nguồn là 0.72–0.93", self.one())

    def test_json_leaf_without_source(self):
        self.write(tj={"version": 1, "set": SET, "motion": {"still_ratio": [0.72, 0.93], "rise_s": [0.3, 0.6]},
                       "source": {"motion.still_ratio": "summary.json"}})
        self.assertIn("motion.rise_s", self.one())

    def test_bad_partial(self):
        with self.assertRaises(refset.UsageError):
            template.cli(SLUG, "3-99")


if __name__ == "__main__":
    unittest.main()
