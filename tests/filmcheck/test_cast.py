"""Cast of an AE film: cast.json rules, character states, the cast review point (specs/034 T011, T013)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from filmcheck import cast, edit, points, steps  # noqa: E402
import castfilm  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"


def fake_sheet(d: Path, cid: str, extra="") -> None:
    s = d / "cast" / "sheets" / cid
    s.mkdir(parents=True, exist_ok=True)
    (s / "front.jpg").write_bytes(b"\xff\xd8jpeg" + extra.encode())
    (s / "sheet.json").write_text(json.dumps({"character": cid, "rig": "ball@1", "built_at": "2026-11-25T00:00:00Z",
                                              "frames": [{"key": "front", "group": "turn", "label": "Front",
                                                          "file": "front.jpg"}], "x": extra}))


class Rules(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(exist_ok=True)
        self.d = castfilm.make(Path(tempfile.mkdtemp(dir=TMP)) / "f1")
        self.doc = cast.load(self.d)

    def codes(self, doc=None):
        return [(cid, code) for cid, code, _ in cast.validate(doc or self.doc)]

    def test_sample_is_valid(self):
        self.assertEqual(cast.validate(self.doc), [])

    def test_bad_specs(self):
        h = cast.find(self.doc, "hero")
        for k, v in (("hoodie", "red"), ("pupils", 3), ("scale", 2), ("brows", "happy"), ("hood", "yes"),
                     ("hat", {"kind": "crown"}), ("stripe", "blue")):
            spec = dict(h["spec"]); spec[k] = v
            doc = json.loads(json.dumps(self.doc)); cast.find(doc, "hero")["spec"] = spec
            self.assertIn(("hero", "bad_spec"), self.codes(doc), k)

    def test_ids_roles_rigs_groups(self):
        doc = json.loads(json.dumps(self.doc))
        doc["characters"][1]["id"] = "hero"                              # used twice
        doc["characters"][0]["role"] = "villain"
        doc["characters"][2]["members"] = [{}]                          # a group needs 2..8
        self.assertIn(("hero", "bad_id"), self.codes(doc))
        self.assertIn(("hero", "bad_role"), self.codes(doc))
        self.assertIn(("classmates", "bad_members"), self.codes(doc))
        doc = json.loads(json.dumps(self.doc)); doc["characters"][0]["rig"] = "ball@9"
        self.assertIn(("hero", "bad_rig"), self.codes(doc))
        doc = json.loads(json.dumps(self.doc)); doc["characters"][0]["id"] = "Hero One"
        self.assertIn((None, "bad_id"), self.codes(doc))
        doc = json.loads(json.dumps(self.doc)); doc["characters"] = [dict(self.doc["characters"][1], id=f"c{i}") for i in range(11)]
        self.assertIn((None, "too_many"), self.codes(doc))

    def test_catalog_warning(self):
        w = cast.catalog_warnings(self.d)
        self.assertEqual(len(w), 1)
        self.assertEqual(w[0][0], "hero")
        self.assertIn("zzz", w[0][1])

    def test_states(self):
        self.assertEqual(cast.states(self.d), {"hero": "new", "friend": "new", "classmates": "new"})
        why = cast.approve(self.d, ["hero"])
        self.assertIn("no cast sheet yet", why[0])                      # nothing written
        self.assertIsNone(cast.find(cast.load(self.d), "hero")["approved"])
        fake_sheet(self.d, "hero")
        self.assertEqual(cast.states(self.d)["hero"], "ready")
        self.assertEqual(cast.approve(self.d, ["hero"], "ui", "me"), [])
        self.assertEqual(cast.states(self.d)["hero"], "approved")
        doc = cast.load(self.d); cast.find(doc, "hero")["spec"]["hoodie"] = "#000000"; cast.save(self.d, doc)
        self.assertEqual(cast.states(self.d)["hero"], "changed")        # spec changed after approval
        cast.approve(self.d, ["hero"])
        fake_sheet(self.d, "hero", "redrawn")
        self.assertEqual(cast.states(self.d)["hero"], "changed")        # the sheet was redrawn
        self.assertTrue(cast.unapprove(self.d, "hero"))
        self.assertEqual(cast.states(self.d)["hero"], "ready")

    def test_fingerprint_ignores_approvals(self):
        for c in ("hero", "friend", "classmates"):
            fake_sheet(self.d, c)
        f = cast.fingerprint(self.d)
        cast.approve(self.d, ["hero"])
        self.assertEqual(cast.fingerprint(self.d), f)
        fake_sheet(self.d, "friend", "new")
        self.assertNotEqual(cast.fingerprint(self.d), f)


class Point(unittest.TestCase):
    def setUp(self):
        TMP.mkdir(exist_ok=True)
        self.d = castfilm.make(Path(tempfile.mkdtemp(dir=TMP)) / "f1")

    def test_on_for_ae_films(self):
        st = points.status(self.d)
        self.assertTrue(st["cast"]["on"])
        self.assertIn("cast", points.POINTS)
        self.assertEqual(points.POINTS.index("cast"), points.POINTS.index("script") + 1)

    def test_chosen_list_keeps_cast_off_before_ae(self):            # T060: FR-002, the form's list comes before `ae new`
        import shutil
        for chosen, on in ((True, False), (False, True)):
            d = Path(tempfile.mkdtemp(dir=TMP)) / "f2"
            shutil.copytree(self.d, d)
            (d / "film.json").rename(d / "film.later")
            points.set_on(d, ["script", "shots"], origin="this film", chosen=chosen)
            (d / "film.later").rename(d / "film.json")                     # the film becomes an AE film
            self.assertEqual(points.status(d)["cast"]["on"], on, chosen)

    def test_skipped_without_characters_or_for_page_films(self):
        doc = cast.load(self.d); doc["characters"] = []; cast.save(self.d, doc)
        self.assertEqual(points.cast_skip_reason(self.d), "no characters")
        self.assertEqual(points.state(self.d, "cast"), "skipped")
        page = Path(tempfile.mkdtemp(dir=TMP)) / "p1"
        page.mkdir()
        self.assertEqual(points.cast_skip_reason(page), "not an After Effects film")
        self.assertNotIn("Cast", [s["step"] if isinstance(s, dict) else s for s in steps.after("Script", page)])

    def test_gate_and_approve_all(self):
        why = points.gate(self.d, "cast")
        self.assertTrue(why and "characters not approved" in why[0])
        for c in ("hero", "friend", "classmates"):
            self.assertIn(c, why[0])
        code, _ = points.approve(self.d, "cast")
        self.assertEqual(code, 1)                                       # no sheets yet
        for c in ("hero", "friend", "classmates"):
            fake_sheet(self.d, c)
        code, why = points.approve(self.d, "cast", source="chat")
        self.assertEqual((code, why), (0, []))
        self.assertTrue(all(c["approved"]["source"] == "chat" for c in cast.load(self.d)["characters"]))
        self.assertEqual(points.state(self.d, "cast"), "approved")
        self.assertEqual(points.gate(self.d, "cast"), [])

    def test_note_after_approval_stops_the_voice(self):              # T056: FR-003, SC-002
        for c in ("hero", "friend", "classmates"):
            fake_sheet(self.d, c)
        self.assertEqual(points.approve(self.d, "cast", source="chat"), (0, []))
        from filmcheck import castnotes
        castnotes.add(self.d, "friend", text="bigger smile", b=castnotes.base(self.d))
        self.assertEqual(points.state(self.d, "cast"), "stale")
        why = points.gate(self.d, "cast")
        self.assertTrue(why and "friend" in why[0], why)

    def test_cast_change_makes_picture_stale_not_voice(self):
        hit = steps.impact("cast", self.d)
        self.assertIn("Shots", hit)
        self.assertIn("Render", hit)
        self.assertNotIn("Voice", hit)



class Cli(unittest.TestCase):
    """T013: cast check|status|approve, the voice gate (SC-002) and the cast edits of the job page."""

    def setUp(self):
        TMP.mkdir(exist_ok=True)
        self.root = Path(tempfile.mkdtemp(dir=TMP))
        self.d = castfilm.make(self.root / "films" / "f1")
        (self.d / "SCRIPT.md").write_text("# f1\n")
        (self.d / "lines.json").write_text("[]")
        self.env = {**os.environ, "STUDIO_ROOT": str(self.root)}
        for k in ("STUDIO_JOB", "STUDIO_PROXY", "STUDIO_MODE"):
            self.env.pop(k, None)

    def studio(self, *args):
        return subprocess.run(["sh", str(REPO / "bin" / "studio"), *args], capture_output=True, text=True, env=self.env,
                              cwd=self.root, timeout=120)

    def sheets(self):
        for c in ("hero", "friend", "classmates"):
            fake_sheet(self.d, c)

    def test_check_and_status(self):
        r = self.studio("cast", "check", "f1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("zzz", r.stdout)                                  # a need outside the catalog is a warning
        doc = cast.load(self.d); cast.find(doc, "hero")["spec"]["pupils"] = 1; cast.save(self.d, doc)
        r = self.studio("cast", "check", "f1")
        self.assertEqual(r.returncode, 2)
        self.assertIn("hero: bad_spec", r.stderr)
        r = self.studio("cast", "status", "f1", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        js = json.loads(r.stdout)
        self.assertEqual([c["state"] for c in js["characters"]], ["new", "new", "new"])
        r = self.studio("cast", "status", "f1")
        self.assertTrue(r.stdout.strip().splitlines()[-1].startswith("point cast: "))

    def test_approve(self):
        r = self.studio("cast", "approve", "f1", "hero")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no cast sheet yet", r.stderr)
        self.sheets()
        r = self.studio("cast", "approve", "f1", "hero", "--no-save")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(cast.states(self.d)["hero"], "approved")
        r = self.studio("cast", "approve", "f1", "--all", "--no-save", "--base", "0" * 16)
        self.assertEqual(r.returncode, 4)
        r = self.studio("cast", "approve", "f1", "--all", "--no-save", "--source", "ui")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(points.state(self.d, "cast"), "approved")
        self.assertEqual(cast.find(cast.load(self.d), "friend")["approved"]["source"], "ui")

    def test_voice_gate(self):
        r = self.studio("voice", "make", "f1", "--skip-review", "test film")
        self.assertEqual(r.returncode, 1)
        self.assertIn("characters not approved: hero, friend, classmates", r.stderr)

    def test_edits(self):
        self.sheets()
        base = points.fingerprint(self.d, "cast")
        r = edit.run(self.d, "cast-approve", {"character": "friend"}, base=base)
        self.assertEqual((r["code"], r["stale"]), (0, []), r)
        self.assertEqual(cast.states(self.d)["friend"], "approved")
        self.assertEqual(points.fingerprint(self.d, "cast"), base)       # approving changes no fingerprint
        r = edit.run(self.d, "cast-save", {"on": "false"}, base="0" * 16)
        self.assertEqual(r["code"], 4)
        r = edit.run(self.d, "cast-save", {"on": "false"}, base=base)
        self.assertEqual(r["code"], 0, r)
        self.assertFalse(cast.load(self.d)["save_to_library"])
        r = edit.run(self.d, "cast-approve", {"character": "nobody"})
        self.assertEqual(r["code"], 2)


if __name__ == "__main__":
    unittest.main()
