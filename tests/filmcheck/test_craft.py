"""specs/027 T012: craft rules of tier 1 (craftcheck.py) on a page's window.CRAFT."""
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import craftcheck, tiers  # noqa: E402

TPL = {"craft": {"source": "test", "action": {"min": 0.5, "rule": "error"},
                 "outdoor": {"range": [0.1, 0.4]}, "prop": {"range": [0.2, 0.6]}, "ots": {"range": [0.0, 0.25]}}}


def row(i, people=1, action=False, outdoor=False, prop=False, cam="mid-eye", card=False, dur=2.0, **x):
    return [i * 2.0, i * 2.0 + dur, f"S{i:02d}", {"people": people, "action": action, "outdoor": outdoor, "prop": prop,
                                                 "cam": cam, "card": card, **x}]


class Rules(unittest.TestCase):
    def test_action_under_min_is_an_error_with_shots_to_fix(self):
        craft = [row(1, action=True), row(2, dur=4.0), row(3), row(4), row(5, people=0), row(6, card=True, people=0)]
        issues, m, skipped = craftcheck.rules(TPL, craft)
        self.assertEqual(skipped, [])
        a = [i for i in issues if i["rule"] == "craft_action"][0]
        self.assertEqual(a["severity"], "block")
        self.assertEqual(a["measure"], 0.25)                      # 1 of 4 shots with people (S05 empty, S06 a card)
        self.assertTrue(a["fix"].endswith("S02, S03, S04"))       # longest first
        self.assertEqual(m["craft"]["people_shots"], 4)
        self.assertEqual(m["craft"]["shots"], 5)

    def test_passes_at_the_minimum(self):
        issues, m, _ = craftcheck.rules(TPL, [row(1, action=True, prop=True, outdoor=True), row(2)])
        self.assertEqual([i["rule"] for i in issues if i["severity"] == "block"], [])
        self.assertEqual(m["craft"]["action"], 0.5)

    def test_style_ranges_warn(self):
        craft = [row(i, action=True, outdoor=True, prop=True, cam="ots") for i in range(1, 5)]
        issues, _, _ = craftcheck.rules(TPL, craft)
        warn = sorted(i["rule"] for i in issues if i["severity"] == "warn")
        self.assertEqual(warn, ["craft_ots", "craft_outdoor", "craft_prop"])
        self.assertFalse(any(i["severity"] == "block" for i in issues))

    def test_item_default_warns_on_the_shot(self):
        issues, _, _ = craftcheck.rules(TPL, [row(1, action=True, prop=True, item_default=["throw"])])
        w = [i for i in issues if i["rule"] == "craft_item_default"][0]
        self.assertEqual((w["ref"], w["severity"], w["at"]), ("S01", "warn", 2.0))

    def test_an_excepted_shot_leaves_the_action_share(self):
        craft = [row(1, action=True), row(2)]
        self.assertTrue(any(i["rule"] == "craft_action" for i in craftcheck.rules(
            {"craft": {"action": {"min": 0.6}}}, craft)[0]))
        issues, m, _ = craftcheck.rules({"craft": {"action": {"min": 0.6}}}, craft,
                                        [{"shot": "S02", "rule": "craft_action", "reason": "a quiet beat"}])
        self.assertFalse(any(i["rule"] == "craft_action" for i in issues))
        self.assertEqual((m["craft"]["action"], m["craft"]["action_excepted"]), (1.0, ["S02"]))

    def test_skipped_without_template_or_page(self):
        self.assertIn("no template.json → craft", craftcheck.rules({}, [row(1)])[2][0])
        self.assertIn("no window.CRAFT", craftcheck.rules(TPL, None)[2][0])

    def test_craft_action_is_exceptable(self):
        self.assertIn("craft_action", tiers.EXCEPTABLE)
        d = Path(tempfile.mkdtemp())
        (d / ".check").mkdir()
        (d / ".check" / "plan-input.json").write_text('{"shots": [{"id": "S01", "t0": 0, "t1": 2}]}', encoding="utf-8")
        e = tiers.add_exception(d, "S01", "craft_action", "no one acts here on purpose")
        self.assertEqual(e["rule"], "craft_action")


if __name__ == "__main__":
    unittest.main()
