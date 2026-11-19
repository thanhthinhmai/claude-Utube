"""specs/023 T026: time measures gathered by shot scale, by beat and for the set; beats.json checks."""
import json
import unittest

from helpers import Project
from sl import refset, template, timesummary as ts


def shot(i, t0, t1, scale, cam="still", spans=(), trans="cut", person=True, px=0.0, zoom=0.0):
    return {"id": f"S{i:03d}", "t0": t0, "t1": t1, "scale": scale, "person": person,
            "cam": {"type": cam, "px_s": px, "zoom_pct_s": zoom},
            "inner": {"active_share": 0.5 if spans else 0.0, "spans": [list(s) for s in spans],
                      "rise_s": [round(s[1] - s[0], 3) for s in spans]},
            "trans_in": {"type": trans, "dur": 0.15 if trans != "cut" else 0.0}}


class TimeSummary(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        data = refset.new_set("t-set", "videos", [])
        for vid in ("v01", "v03"):
            data["videos"].append({"id": vid, "file": f"{vid}.mp4", "duration": 20.0, "state": "transcribed"})
        refset.save("t-set", data)
        shots = [shot(1, 0, 4, "cu", spans=[(1.0, 1.4, 0.05, [0.5, 0.5])]),
                 shot(2, 4, 8, "wide", cam="push", zoom=2.5),
                 shot(3, 8, 12, "med", spans=[]),
                 shot(4, 12, 16, "insert", person=False, trans="streak"),
                 shot(5, 16, 20, "wide", cam="drift-h", px=20)]
        for vid in ("v01", "v03"):
            prof = refset.profile_dir("t-set", vid)
            prof.mkdir(parents=True)
            refset.write_json(prof / "craft.json", {"video": vid, "shots": shots})
            refset.write_json(prof / "sound.json", {"video": vid,
                "speech": {"wpm_10s": [[0, 150], [10, 170]], "pause_in": [0.1, 0.2], "pause_sent": [0.4],
                           "pause_para": [0.9], "pre_number": [0.3]},
                "music": {"windows": [[0, 5, True, -14.0], [5, 10, True, -12.0], [10, 15, False, None], [15, 20, None, None]],
                          "tempo": 92.0, "tempo_conf": "ok"},
                "sfx": {"onsets": [2.0, 13.0], "per_min": 6.0}})
        refset.write_json(refset.set_dir("t-set") / "profile" / "summary.json", {"by_orientation": {"landscape": {"metrics": {
            "motion720_p50": {"min": 0.01, "max": 0.17}}}}})
        self.beats = [{"video": "v01", "beats": [["hook", 0, 8], ["explain", 8, 20]]}]
        refset.write_json(ts.beats_file("t-set"), self.beats)

    def tearDown(self):
        self.p.close()

    def test_motion_from_3d_films_only(self):
        s = ts.build("t-set")
        m = s["motion"]
        self.assertEqual(m["films"], ["v01"])                       # v03 is a flat film
        self.assertEqual(m["still_ratio"], [0.6, 0.6])              # 12 of 20 s still
        self.assertEqual(m["shift_still_ratio"], [0.8, 0.8])        # the push does not shift
        self.assertEqual(m["person_still_cam"]["n"], 2)             # cu and med: still camera, person
        self.assertEqual(m["person_still_cam"]["none_share"], 0.5)
        self.assertEqual(m["by_scale"]["wide"]["moving"], 1.0)
        self.assertEqual(m["motion720_p50"], [0.01, 0.17])

    def test_transitions_voice_sound(self):
        s = ts.build("t-set")
        self.assertEqual(s["transitions"]["count"]["streak"], 2)
        self.assertEqual(s["voice"]["pause_para"], [0.9, 0.9, 0.9])
        self.assertEqual(s["sound"]["music_share"], 0.667)
        self.assertEqual(s["sound"]["music_under_voice_db"], [-14.0, -13.0, -12.0])

    def test_beats(self):
        b = ts.build("t-set")["beats"]
        self.assertEqual(set(b), {"hook", "explain"})
        self.assertEqual(b["hook"]["shots"], 2)
        self.assertEqual(b["hook"]["cam_moving"], 0.5)
        self.assertEqual(b["explain"]["insert_share"], 0.333)
        self.assertEqual(b["hook"]["sfx_per_min"], 7.5)            # 1 onset in 8 s
        self.assertEqual(b["explain"]["trans"], {"streak": 1})

    def test_check_beats(self):
        self.assertEqual(ts.check_beats("t-set"), [])
        bad = [{"video": "v01", "beats": [["explain", 0, 8], ["hook", 8.5, 18]]}]
        refset.write_json(ts.beats_file("t-set"), bad)
        got = " | ".join(ts.check_beats("t-set"))
        self.assertIn("thứ tự", got)
        self.assertIn("bắt đầu 8.5", got)
        self.assertIn("kết thúc 18", got)

    def test_craft_summary_time_part(self):
        template.craft_summary("t-set", parts=("time",))
        s = json.loads((refset.set_dir("t-set") / "profile" / "craft-summary.json").read_text())
        self.assertIn("motion", s)
        self.assertIn("beats", s)


if __name__ == "__main__":
    unittest.main()
