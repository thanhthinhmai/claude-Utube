"""camera suggest|choose|retime (specs/039 T019): similarity order, 2–3 different options, ★ inside p25–p75, notes,
no moving camera, no similar shot, --keep-others, retime, choose → shot_plan, page films refused."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import camsuggest  # noqa: E402

Q = lambda a, b, c: [a, b, c]  # noqa: E731


def ref(i, size="med", people=1, move="push", rate=2.0, dur=3.0, reliable=True, card=False, action=False,
        outdoor=False, prop=False, ease=(0.15, 0.5, 0.85), drift=(0.0, 6.0), evidence=True, sh=60.0):
    return {"id": f"v01:S{i:03d}", "size": size, "people": people, "card": card, "action": action, "outdoor": outdoor,
            "prop": prop, "dur": dur, "move": move, "zoom_pct": rate * dur if move in ("push", "pull") else 0.0,
            "rate_pct_s": rate if move in ("push", "pull") else 0.0, "ease": list(ease) if move != "static" else None,
            "drift_px": list(drift), "subject_x": 50.0, "subject_y": 50.0, "subject_h": sh, "headroom": 10.0,
            "cam_height": "eye", "lens": "normal", "parallax": False, "parallax_px": 0.0, "transition": "cut",
            "reliable": reliable, "evidence": [f"camera/v01-S{i:03d}-a.jpg", f"camera/v01-S{i:03d}-b.jpg"] if evidence else None}


SIZE = {"n": 10, "thin": False, "dur": Q(2.0, 3.0, 4.0), "zoom_pct": Q(4.0, 6.0, 8.0), "rate_pct_s": Q(1.5, 2.0, 2.5),
        "push_share": 0.7, "pull_share": 0.1, "pan_share": 0.0, "static_share": 0.2, "drift_px": Q(2.0, 6.0, 12.0),
        "ease_q": [0.15, 0.5, 0.85], "subject_h": Q(50.0, 60.0, 70.0), "subject_x": Q(45.0, 50.0, 55.0),
        "subject_y": Q(45.0, 50.0, 55.0), "headroom": Q(5.0, 10.0, 15.0)}
SUMMARY = {"transition_main": "cut", "transition_share": {"cut": 1.0}, "parallax_share": 0.0, "shots_n": 6,
           "reliable_n": 6, "by_size": {"med": SIZE, "wide": {**SIZE, "static_share": 0.0}, "cu": SIZE}}
SHOTS = [ref(1, rate=2.0, dur=3.0), ref(2, size="wide", rate=3.0, dur=3.0), ref(3, people=2, action=True),
         ref(4, size="cu", move="pull", rate=-2.0), ref(5, rate=5.0, dur=3.0, reliable=False),
         ref(6, card=True, size="med")]


def make_film(root: Path, name="f1", plan=None, frames=None, page=False):
    d = root / "films" / name
    (d / "ae").mkdir(parents=True)
    (d / "ae" / "shots.jsx").write_text("// shots\n")
    if page:
        (d / "film.json").write_text(json.dumps({"engine": "page"}))
        return d
    shots = ["S1", "S2", "S3"]
    (d / "film.json").write_text(json.dumps({"engine": "ae", "style": "camstyle", "shots": shots,
                                             "ae_files": ["shots.jsx"], "shot_plan": plan or {}}))
    fr = frames or {"S1": 90, "S2": 90, "S3": 60}
    (d / "timing.json").write_text(json.dumps({"version": 1, "fps": 30, "frames": fr}))
    st = root / "my-styles" / "camstyle"
    st.mkdir(parents=True, exist_ok=True)
    (st / "camera.json").write_text(json.dumps({"version": 1, **SUMMARY, "shots": SHOTS}))
    return d


PLAN = {"S1": {"size": "med", "people": 1, "card": False, "action": False, "outdoor": False, "prop": False},
        "S2": {"size": "wide", "people": 1},
        "S3": {"size": "med", "people": 2, "action": True}}


class Base(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="camsug."))
        self.env = dict(os.environ, STUDIO_ROOT=str(self.root))
        os.environ["STUDIO_ROOT"] = str(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(REPO / "tools/filmcheck/cli.py"), *args], cwd=self.root,
                              env=self.env, capture_output=True, text=True)


class Similarity(unittest.TestCase):
    def test_order(self):
        shot = camsuggest.film_shot(PLAN["S1"], 3.0)
        got = [r["id"] for _, _, r in camsuggest.ranked(shot, SHOTS)]
        self.assertEqual(got[:2], ["v01:S001", "v01:S005"])          # same everything first
        self.assertNotIn("v01:S006", got)                             # a card shot is never like a non-card shot
        s, why = camsuggest.similarity(shot, SHOTS[1])
        self.assertEqual(why["size"], 0.5)                            # wide is next to med

    def test_duration_term(self):
        shot = camsuggest.film_shot({}, 9.0)
        _, why = camsuggest.similarity(shot, SHOTS[0])
        self.assertEqual(why["dur"], 0.0)                             # 3× longer: no match
        self.assertEqual(set(why), {"dur"})                           # only the fields the film has count

    def test_ease_table(self):
        ae = camsuggest.ease_ae([0.15, 0.5, 0.85])
        self.assertEqual(len(ae), 2)
        self.assertTrue(all(5 <= x <= 95 for x in ae))
        self.assertIsNone(camsuggest.ease_ae(None))
        self.assertIsNone(camsuggest.clean_ease([0.0, 0.0, 0.21]))    # all the move in the last quarter


class Options(Base):
    def setUp(self):
        super().setUp()
        self.d = make_film(self.root, plan=PLAN)
        self.o = camsuggest.suggest(self.d)

    def test_two_or_three_different_options(self):
        for sid, row in self.o["shots"].items():
            opts = row["options"]
            self.assertTrue(2 <= len(opts) <= 3, sid)
            self.assertEqual(sum(o["recommended"] for o in opts), 1)
            for i, a in enumerate(opts):
                for b in opts[i + 1:]:
                    self.assertFalse(camsuggest._same(a, b), f"{sid} {a['n']} {b['n']}")

    def test_star_inside_p25_p75(self):
        for sid, row in self.o["shots"].items():
            star = row["options"][0]
            if star["move"] in ("push", "pull"):
                self.assertTrue(4.0 - 0.01 <= abs(star["zoom_pct"]) <= 8.0 + 0.01, (sid, star["zoom_pct"]))

    def test_star_never_from_unreliable(self):
        self.assertEqual(self.o["shots"]["S1"]["options"][0]["ref"], "v01:S001")
        refs = {o["ref"] for row in self.o["shots"].values() for o in row["options"] if o["recommended"]}
        self.assertNotIn("v01:S005", refs)

    def test_rate_times_length(self):
        star = self.o["shots"]["S1"]["options"][0]
        self.assertAlmostEqual(star["zoom_pct"], 6.0, places=1)       # 2 %/s × 3 s

    def test_only_2d_moves_and_framing_inside(self):
        for row in self.o["shots"].values():
            for o in row["options"]:
                self.assertIn(o["move"], camsuggest.MOVES_2D)
                st = o["start"]
                h = 50 / st["scale"]
                self.assertTrue(h - 0.1 <= st["cx"] <= 100 - h + 0.1 and h - 0.1 <= st["cy"] <= 100 - h + 0.1)

    def test_note_outside_range(self):
        o = {"move": "push", "zoom_pct": 12.0, "drift_px": [0, 0], "dur": 3.0, "transition": "cut", "size": "med"}
        self.assertIn("ngoài p25–p75", camsuggest._note(o, SIZE, "cut"))
        o.update(zoom_pct=6.0)
        self.assertIsNone(camsuggest._note(o, SIZE, "cut"))
        o.update(transition="fade")
        self.assertIn("chuyển cảnh", camsuggest._note(o, SIZE, "cut"))

    def test_no_similar_shot(self):
        lib = {"summary": SUMMARY, "shots": [ref(9, size="huge", people=3, action=True, outdoor=True, prop=True, dur=0.5)]}
        row = camsuggest.options_for("S1", PLAN["S1"], 6.0, lib)
        self.assertIsNone(row["options"][0]["ref"])
        self.assertIn("không có shot mẫu giống", row["options"][0]["reason"])

    def test_film_camera_kept_as_option(self):
        cam = {"size": "med", "move": "pull", "start": {"scale": 1.3, "cx": 40, "cy": 50}, "zoom_pct": -12.0,
               "rate_pct_s": -4.0, "ease": None, "ease_ae": None, "drift_px": [0, 0], "transition": "cut"}
        row = camsuggest.options_for("S1", {**PLAN["S1"], "camera": cam}, 3.0,
                                     {"summary": SUMMARY, "shots": SHOTS})
        self.assertEqual(row["options"][-1]["ref"], "film")

    def test_keep_others_keeps_bytes(self):
        camsuggest.choose(self.d, "S2", 2)
        before = json.loads(camsuggest.opath(self.d).read_text())
        camsuggest.suggest(self.d, shots=["S1"], keep_others=True)
        after = json.loads(camsuggest.opath(self.d).read_text())
        for s in ("S2", "S3"):
            self.assertEqual(json.dumps(after["shots"][s]), json.dumps(before["shots"][s]))
        self.assertEqual(after["shots"]["S2"]["choice"]["n"], 2)

    def test_suggest_again_uses_the_recorded_library(self):
        """A Camera note on a film whose film.json names no style: the options' source is used again (T034)."""
        fj = json.loads((self.d / "film.json").read_text())
        fj.pop("style", None)
        (self.d / "film.json").write_text(json.dumps(fj))
        src = camsuggest.load(self.d)["source"]
        o = camsuggest.suggest(self.d, shots=["S1"], keep_others=True)
        self.assertEqual(o["source"], src)

    def test_choose_writes_shot_plan(self):
        r = camsuggest.choose(self.d, "S1", 2)
        fj = json.loads((self.d / "film.json").read_text())
        self.assertEqual(fj["shot_plan"]["S1"]["camera"], r["camera"])
        self.assertEqual(fj["shot_plan"]["S1"]["move"], r["camera"]["move"])
        self.assertEqual(camsuggest.load(self.d)["shots"]["S1"]["choice"]["source"], "user")
        with self.assertRaises(camsuggest.CameraError):
            camsuggest.choose(self.d, "S1", 7)

    def test_retime_keeps_rate(self):
        camsuggest.choose(self.d, "S1", 1)
        (self.d / "timing.json").write_text(json.dumps({"version": 1, "fps": 30, "frames": {"S1": 120, "S2": 90, "S3": 60}}))
        ch = camsuggest.retime(self.d)
        self.assertEqual([c["shot"] for c in ch], ["S1"])
        star = camsuggest.load(self.d)["shots"]["S1"]["options"][0]
        self.assertAlmostEqual(star["zoom_pct"], star["rate_pct_s"] * 4.0, places=1)
        fj = json.loads((self.d / "film.json").read_text())
        self.assertEqual(fj["shot_plan"]["S1"]["camera"]["zoom_pct"], star["zoom_pct"])
        self.assertEqual(camsuggest.retime(self.d), [])


class Cli(Base):
    def test_page_film_refused(self):
        make_film(self.root, name="pg", page=True)
        r = self.cli("camera", "suggest", "pg")
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_no_library(self):
        d = make_film(self.root, plan=PLAN)
        shutil.rmtree(self.root / "my-styles")
        r = self.cli("camera", "suggest", d.name)
        self.assertEqual(r.returncode, 2)
        self.assertIn("learn camera", r.stderr)

    def test_suggest_and_choose(self):
        d = make_film(self.root, plan=PLAN)
        r = self.cli("camera", "suggest", d.name)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertRegex(r.stdout, r"S1\s+1\* med\s+push\s+\+6\.0% ease \.15/\.50/\.85")
        r = self.cli("camera", "choose", d.name, "S1", "2")
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
