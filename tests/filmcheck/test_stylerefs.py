"""A style's measured ranges (specs/020 T022; FR-013; research R6)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import stylerefs  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"


class StyleRefs(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(exist_ok=True)
        self.root = Path(tempfile.mkdtemp(dir=TMP))
        self.film = self.root / "films" / "f"
        self.film.mkdir(parents=True)

    def style(self, slug, evidence=None, qc=None):
        d = self.root / "my-styles" / slug
        d.mkdir(parents=True, exist_ok=True)
        if evidence is not None:
            (d / "EVIDENCE.md").write_text(evidence)
        if qc is not None:
            (d / "qc.json").write_text(json.dumps(qc))
        (self.film / "TREATMENT.md").write_text(f"Style: {slug}\n")

    @unittest.skipUnless((REPO / "my-styles" / "dusk-hypothetical" / "EVIDENCE.md").is_file(), "needs the learned style")
    def test_dusk_hypothetical(self):
        ev = (REPO / "my-styles" / "dusk-hypothetical" / "EVIDENCE.md").read_text()
        got = stylerefs.from_evidence(ev)
        self.assertEqual(got, {"luma_p50": [0.198, 0.299], "saturation_p50": [0.319, 0.504], "cuts_per_min": [16, 26],
                               "loudness_range": [2.4, 3.3]})

    def test_qc_json_overrides(self):
        self.style("s", "| Metric | Median | Range |\n|---|---|---|\n| luma p50 | 0.2 | 0.1–0.3 |\n"
                        "| loudness | −14 LUFS | −14.4 to −13.8 |\n", {"luma_p50": [0.15, 0.25], "shot_max": 8})
        got = stylerefs.load(self.film)
        self.assertEqual(got["luma_p50"], [0.15, 0.25])
        self.assertEqual(got["shot_max"], 8)
        self.assertNotIn("loudness_range", got)
        self.assertTrue(stylerefs.has_ranges(got))

    def test_no_measurements(self):
        self.style("plain")
        self.assertEqual(stylerefs.load(self.film), {})
        self.assertFalse(stylerefs.has_ranges({}))


if __name__ == "__main__":
    unittest.main()
