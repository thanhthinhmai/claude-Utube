"""Blender set files (specs/040 T011): each set has build(k, light, seed), imports only kit/bpy/stdlib math, and fills
the k.objects keys the shot scripts rely on. Reads the source; Blender is not needed."""
import ast
import unittest
from pathlib import Path

SETS = Path(__file__).resolve().parents[2] / "tools" / "blender" / "kit" / "sets"
NEW = ("kitchen", "livingroom")
ALLOWED = {"kit", "bpy", "mathutils", "math", "random"}
KEYS = {"look", "cam_dir", "floor", "walk"}


class Sets(unittest.TestCase):
    def tree(self, name):
        return ast.parse((SETS / f"{name}.py").read_text())

    def test_new_sets_exist_with_build(self):
        for name in NEW:
            fn = [n for n in self.tree(name).body if isinstance(n, ast.FunctionDef) and n.name == "build"]
            self.assertEqual(len(fn), 1, name)
            args = [a.arg for a in fn[0].args.args]
            self.assertEqual(args, ["k", "light", "seed"], name)

    def test_imports_only_kit_and_bpy(self):
        for name in NEW:
            for n in ast.walk(self.tree(name)):
                mods = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""] if isinstance(n, ast.ImportFrom) else []
                for m in mods:
                    self.assertIn(m.split(".")[0], ALLOWED, f"{name}: {m}")

    def test_objects_keys(self):
        for name in NEW:
            src = (SETS / f"{name}.py").read_text()
            for key in KEYS:
                self.assertIn(f'"{key}"', src, f"{name}: {key}")

    def test_at_least_eight_kinds_of_things(self):
        for name in NEW:
            names = set()
            for n in ast.walk(self.tree(name)):
                if isinstance(n, ast.Call) and getattr(n.func, "attr", "") in ("box", "sphere", "tube", "torus", "plane") \
                        and n.args and isinstance(n.args[0], ast.Constant):
                    names.add(n.args[0].value)
            self.assertGreaterEqual(len(names), 8, name)


if __name__ == "__main__":
    unittest.main()
