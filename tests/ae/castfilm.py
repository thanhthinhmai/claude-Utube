"""A small AE film with a cast (specs/034) shared by the cast tests."""
import json
from pathlib import Path

HERO = {"id": "hero", "name": "You (hero)", "role": "hero", "kind": "one", "rig": "ball@1",
        "spec": {"hoodie": "#e8604c", "pants": "#262a3d", "shoes": "#f4f2ee", "hat": {"kind": "beanie", "color": "#4f7a4a"},
                 "headColor": "#141418", "stripe": None, "tie": None, "hood": True, "brows": False},
        "needs": {"expressions": [{"key": "wide", "label": "Wide-eyed", "para": "P01"}],
                  "poses": [{"key": "guitar", "label": "Guitar", "para": "P02"}, {"key": "zzz", "label": "Unknown pose"}],
                  "walk": True},
        "from_library": None, "approved": None}
FRIEND = {"id": "friend", "name": "Friend", "role": "support", "kind": "one", "rig": "ball@1",
          "spec": {"hoodie": "#5aa064", "hat": {"kind": "curly", "color": "#2a1c14"}},
          "needs": {"expressions": [], "poses": [], "walk": False}, "from_library": None, "approved": None}
CLASS = {"id": "classmates", "name": "Classmates ×2", "role": "background", "kind": "group", "rig": "ball@1",
         "members": [{"hoodie": "#4f7fc8", "hat": {"kind": "cap", "color": "#d9a640"}}, {"hoodie": "#c8a24f"}],
         "needs": {"expressions": [], "poses": [], "walk": False}, "from_library": None, "approved": None}


def make(d: Path, characters=(HERO, FRIEND, CLASS), channel="default") -> Path:
    (d / "ae").mkdir(parents=True, exist_ok=True)
    (d / "ae" / "shots.jsx").write_text('CU.shot1 = function () { return CU.char("hero", {dur: 2}).comp; };\n')
    (d / "film.json").write_text(json.dumps({"engine": "ae", "fps": 30, "shots": ["S1"], "ae_files": ["shots.jsx"]}))
    (d / "cast").mkdir(exist_ok=True)
    (d / "cast" / "cast.json").write_text(json.dumps({"version": 1, "channel": channel, "save_to_library": True,
                                                      "characters": [json.loads(json.dumps(c)) for c in characters]}, indent=2))
    return d
