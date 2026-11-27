"""specs/038 T022: tools/blender/uses.py finds shots by kit call, set, fx and the kit's import graph."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from blender import uses  # noqa: E402


class Uses(unittest.TestCase):
    def setUp(self):
        self.kit = Path(tempfile.mkdtemp())
        (self.kit / "sets").mkdir()
        for f, src in {"core.py": "import bpy\n", "entry.py": "from kit import core\n", "toon.py": "from kit import core\n",
                       "mesh.py": "from kit import toon\n", "camera.py": "from kit import core\n",
                       "fx.py": "from kit import toon, mesh\n",
                       "sets/hallway.py": "from kit import mesh, toon\n", "sets/classroom.py": "from kit import mesh\n"}.items():
            (self.kit / f).write_text(src)
        self.old = uses.KIT
        uses.KIT = self.kit
        self.film = Path(tempfile.mkdtemp())
        (self.film / "blender").mkdir()
        (self.film / "blender" / "S2.py").write_text('def shot(k):\n    k.set("hallway")\n    k.cam(size="wide")\n')
        (self.film / "blender" / "S5.py").write_text('def shot(k):\n    k.set("classroom")\n    k.cam()\n    k.fx("confetti", t0=1)\n')
        (self.film / "blender" / "S10.py").write_text("def shot(k):\n    k.cam()\n")

    def tearDown(self):
        uses.KIT = self.old

    def test_files_of_follows_imports(self):
        g = uses.kit_graph(self.kit)
        self.assertEqual(uses.files_of(self.film / "blender" / "S2.py", g),
                         ["camera.py", "core.py", "entry.py", "mesh.py", "sets/hallway.py", "toon.py"])
        self.assertIn("fx.py", uses.files_of(self.film / "blender" / "S5.py", g))

    def test_shots_using(self):
        self.assertEqual(uses.shots_using(self.film, ["toon"]), ["S2", "S5"])
        self.assertEqual(uses.shots_using(self.film, ["hallway"]), ["S2"])
        self.assertEqual(uses.shots_using(self.film, ["k.fx"]), ["S5"])
        self.assertEqual(uses.shots_using(self.film, ["confetti"]), ["S5"])
        self.assertEqual(uses.shots_using(self.film, ["cam"]), ["S2", "S5", "S10"])
        self.assertEqual(uses.shots_using(self.film, ["camera.py"]), ["S2", "S5", "S10"])
        self.assertEqual(uses.shots_using(self.film, ["auditorium"]), [])


if __name__ == "__main__":
    unittest.main()
