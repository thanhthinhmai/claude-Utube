"""specs/037 T007: the sound library is built from names and text only, re-indexes only what changed, refuses
reference folders, ranks hits, and a customer's scope sees CC0 sounds only."""
import os
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
sys.path.insert(0, str(HERE))

import soundfix  # noqa: E402
from filmcheck import soundlib, ucs  # noqa: E402


class LibCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"STUDIO_DATA": str(t / "data"), "STUDIO_ROOT": str(t / "repo")})
        self.env.start()
        (t / "repo" / "references").mkdir(parents=True)
        self.lib = soundfix.make(t / "Sonniss" / "GDC2024")
        self.t = t

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


class Index(LibCase):
    def test_entries_broken_and_metadata(self):
        soundlib.add_root(self.lib)
        r = soundlib.index()
        self.assertEqual((r["new"], r["broken"], r["entries"]), (12, 1, 11))
        c = soundlib.connect()
        rows = {x["name"]: dict(x) for x in c.execute("SELECT * FROM entry")}
        c.close()
        glass = rows["GLASBrk Window Shatter Large TEST"]
        self.assertEqual((glass["category"], glass["subcategory"]), ("GLASS", "BREAK"))
        self.assertIn("Large window pane shatters", glass["description"])                       # bext
        self.assertEqual((glass["source"], glass["license"]), ("sonniss", "sonniss-gdc-2.0"))
        self.assertTrue(glass["credit"].startswith("Sonniss GDC 2024 · GDC2024 Test Pack"), glass["credit"])
        self.assertAlmostEqual(glass["duration"], 0.8, places=2)
        self.assertEqual((glass["rate"], glass["channels"]), (22050, 1))
        whoosh = rows["WHSH Fast Pass By TEST"]
        self.assertIn("Fast whoosh pass by", whoosh["description"])                               # LIST/INFO INAM
        self.assertIn("swish", whoosh["keywords"])                                                # IKEY
        ball = rows["BALLBnce Rubber Ball Bounce Gym TEST"]
        self.assertEqual(ball["category"], "BALLS")                                                # iXML CATEGORY
        self.assertIn("Dodgeball bounce", ball["description"])
        broken = [x for x in rows.values() if not x["ok"]]
        self.assertEqual([x["name"] for x in broken], ["IMPCMetl Broken File TEST"])
        self.assertTrue(glass["id"].startswith("s:") and len(glass["id"]) == 14)

    def test_reindex_reads_only_new_or_changed_and_drops_gone(self):
        soundlib.add_root(self.lib)
        soundlib.index()
        calls = []
        real = soundlib.read_meta
        with mock.patch.object(soundlib, "read_meta", side_effect=lambda p: calls.append(p) or real(p)):
            r = soundlib.index()
            self.assertEqual((r["new"], r["changed"], r["gone"], len(calls)), (0, 0, 0, 0))
            f = next(self.lib.rglob("CRTNPop*.wav"))
            soundfix.wav(f, "pop", 0.4, seed=9)                                    # changed size
            os.utime(f, ns=(1, 1))
            (next(self.lib.rglob("PAPRScrbl*.wav"))).unlink()
            soundfix.wav(self.lib / "GDC2024 Test Pack" / "DOORWood_Door Slam_TEST.wav", "hit", 0.3)
            r = soundlib.index()
        self.assertEqual((r["new"], r["changed"], r["gone"]), (1, 1, 1))
        self.assertEqual(len(calls), 2)

    def test_reference_folders_are_refused(self):
        ref = self.t / "repo" / "references" / "voice-check"
        soundfix.make(ref)
        with self.assertRaises(soundlib.LibraryError) as e:
            soundlib.add_root(ref)
        self.assertEqual(e.exception.code, "forbidden")
        learn = self.t / "data" / "learn" / "x"
        learn.mkdir(parents=True)
        with self.assertRaises(soundlib.LibraryError):
            soundlib.add_root(learn)
        # a roots.json edited by hand still never indexes them
        soundlib._save_roots([{"path": str(ref), "kind": "sonniss", "added_at": "x"}])
        self.assertEqual(soundlib.index()["new"], 0)

    def test_no_audio_sample_is_ever_read(self):
        def boom(*a, **k):
            raise AssertionError("an audio sample was read")
        patches = [mock.patch.object(wave.Wave_read, "readframes", boom)]
        try:
            import soundfile
            patches += [mock.patch.object(soundfile, "read", boom), mock.patch.object(soundfile, "SoundFile", boom)]
        except ImportError:
            pass
        for p in patches:
            p.start()
        try:
            soundlib.add_root(self.lib)
            self.assertEqual(soundlib.index()["entries"], 11)
            self.assertTrue(soundlib.search("window shatter"))
        finally:
            for p in patches:
                p.stop()


class Search(LibCase):
    def setUp(self):
        super().setUp()
        soundlib.add_root(self.lib)
        soundlib.index()

    def test_rank_category_and_length(self):
        hits = soundlib.search("window shatter")
        self.assertEqual(hits[0]["name"], "GLASBrk Window Shatter Large TEST")
        self.assertEqual(set(hits[0]) >= {"id", "name", "category", "duration", "source", "credit", "score", "cover"}, True)
        self.assertNotIn("path", hits[0])                                          # text only leaves the library
        hits = soundlib.search("glass", cat="GLASS")
        self.assertEqual({h["category"] for h in hits[:2]}, {"GLASS"})
        short = soundlib.search("glass", cat="GLASS", dur=0.5)[0]
        self.assertEqual(short["name"], "GLASBrk Bottle Smash TEST")               # 0.5 s beats 0.8 s
        self.assertEqual(soundlib.search("bubbles aquarium")[0]["category"], "WATER")
        self.assertEqual(soundlib.search("zzzz qqqq"), [])

    def test_customer_scope_sees_cc0_only(self):
        self.assertEqual(soundlib.search("window shatter", scope="cc0"), [])
        c = soundlib.connect()
        soundlib.put(c, {"id": "fs:7", "path": str(self.t / "x.ogg"), "size": 1, "mtime_ns": 1, "name": "window glass break",
                         "category": "", "subcategory": "", "description": "", "keywords": "glass", "duration": 1.0,
                         "rate": 44100, "channels": 1, "source": "freesound", "credit": "Freesound #7 by a", "url": "u",
                         "license": "cc0-1.0", "fetched_at": "t", "ok": 1, "root": ""})
        c.commit()
        c.close()
        self.assertEqual([h["id"] for h in soundlib.search("window shatter", scope="cc0")], ["fs:7"])
        sid = soundlib.search("window shatter")[0]["id"]
        with self.assertRaises(soundlib.LibraryError) as e:
            soundlib.get(sid, scope="cc0")
        self.assertEqual(e.exception.code, "scope")

    def test_licence_never_changes_after_it_came_in(self):
        sid = soundlib.search("window shatter")[0]["id"]
        row = soundlib.get(sid)
        row["license"] = "cc0-1.0"
        c = soundlib.connect()
        soundlib.put(c, row)
        c.commit()
        c.close()
        self.assertEqual(soundlib.get(sid)["license"], "sonniss-gdc-2.0")

    def test_find_stays_offline_without_a_key(self):
        with mock.patch.dict(os.environ, {"FREESOUND_API_KEY": ""}), \
             mock.patch("filmcheck.eleven.load_env", return_value={}):
            self.assertEqual(soundlib.find("aquarium fish tank pump")[0]["category"], "WATER")
            self.assertEqual(soundlib.find("spaceship laser"), [])

    def test_cache_copies_into_the_film(self):
        film = self.t / "films" / "f1"
        sid = soundlib.search("window shatter")[0]["id"]
        p = soundlib.cache(sid, film)
        self.assertEqual(p.parent, film / "sound" / "cache")
        self.assertEqual(p.name, sid.replace(":", "_") + ".wav")
        self.assertEqual(soundlib.cache(sid, film), p)                             # once


class Cli(LibCase):
    def run_cli(self, *argv):
        import io
        from contextlib import redirect_stderr, redirect_stdout
        from filmcheck import cli
        o, e = io.StringIO(), io.StringIO()
        with redirect_stdout(o), redirect_stderr(e):
            code = cli.main(list(argv))
        return code, o.getvalue() + e.getvalue()

    def test_lib_commands(self):
        code, out = self.run_cli("sound", "lib", "add", str(self.lib))
        self.assertEqual(code, 0, out)
        self.assertRegex(out, r"indexed 12 new · 0 changed · 0 gone · 1 broken · [\d.]+ s")
        code, out = self.run_cli("sound", "lib", "index")
        self.assertRegex(out, r"indexed 0 new · 0 changed · 0 gone · 1 broken")
        code, out = self.run_cli("sound", "lib", "search", "window shatter", "--cat", "GLASS")
        self.assertEqual(code, 0)
        self.assertIn("GLASBrk Window Shatter Large TEST", out.splitlines()[0])
        code, out = self.run_cli("sound", "lib", "add", str(self.t / "repo" / "references"))
        self.assertEqual(code, 3)
        with mock.patch.dict(os.environ, {"FREESOUND_API_KEY": "fs_secret_key_9999"}):
            code, out = self.run_cli("sound", "lib", "status")
        self.assertIn("Freesound key: yes", out)
        self.assertNotIn("fs_secret_key_9999", out)


class Ucs(unittest.TestCase):
    def test_names(self):
        self.assertEqual(ucs.parse_name("GLASBrk_Window Shatter_TEST")["category"], "GLASS")
        self.assertEqual(ucs.parse_name("FIREWRKBurst_Big_X")["category"], "FIREWORKS")
        self.assertEqual(ucs.parse_name("my bubbles take 3")["category"], "")
        self.assertTrue(ucs.match("GLAS", "GLASS") and ucs.match("glass", "GLASS") and not ucs.match("WATR", "GLASS"))


if __name__ == "__main__":
    unittest.main()
