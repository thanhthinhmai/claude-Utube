"""The style's depth block (specs/038 T033, data-model "Style depth block")."""
import unittest

from helpers import Project
from sl import refset, save


def row(i, scale, cam="eye", lens="normal", depth="mid", layers=("mid", "bg"), occ=False, vid="v01"):
    return {"id": f"S{i}", "_vid": vid, "scale": scale, "cam_height": cam, "lens": lens, "depth": depth,
            "layers": list(layers), "occluder": occ}


class DepthBlock(unittest.TestCase):
    def test_by_size(self):
        rows = [row(1, "wide", cam="high", lens="wide", depth="deep", layers=("fg", "mid", "bg", "far"), occ=True),
                row(2, "wide", depth="deep", layers=("mid", "bg", "far")),
                row(3, "wide"), row(4, "wide", cam="unknown"),
                row(5, "cu", depth="shallow", layers=("mid",)),
                {"id": "S6", "_vid": "v01", "scale": "wide"},                 # an older label: left out
                row(7, "insert")]
        b = save.depth_block(rows)
        self.assertEqual(b["version"], 1)
        self.assertEqual(set(b["by_size"]), {"wide", "cu"})
        w = b["by_size"]["wide"]
        self.assertEqual(w["n"], 4)
        self.assertEqual(w["cam_height"], {"eye": 0.67, "high": 0.33})       # unknown is not a share
        self.assertEqual(w["depth"], {"mid": 0.5, "deep": 0.5})
        self.assertEqual((w["layers_p25"], w["layers_p50"]), (2, 3))
        self.assertEqual(w["occluder_share"], 0.25)
        self.assertEqual(w["evidence"][0], "v01:S1")
        self.assertEqual(b["by_size"]["cu"]["layers_p50"], 1)

    def test_empty(self):
        self.assertEqual(save.depth_block([]), {})
        self.assertEqual(save.depth_block([{"id": "S1", "scale": "wide"}]), {})

    def test_reads_the_set(self):
        Project()
        data = refset.new_set("depth-set", "files", [])
        data["videos"] += [{"id": "v01", "file": "a.mp4", "state": "transcribed"},
                           {"id": "v02", "file": "b.mp4", "state": "transcribed"}]
        refset.save("depth-set", data)
        for vid, n in (("v01", 3), ("v02", 2)):
            refset.write_json(refset.profile_dir("depth-set", vid) / "shots.json",
                              {"shots": [row(i, "wide", vid=vid) for i in range(n)]})
        b = save.depth_refs("depth-set")
        self.assertEqual(b["by_size"]["wide"]["n"], 5)


if __name__ == "__main__":
    unittest.main()
