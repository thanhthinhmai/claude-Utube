"""specs/037 T008: Freesound fills gaps with CC0 sounds only, and the key never shows."""
import io
import logging
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
sys.path.insert(0, str(HERE))

from fake_freesound import FakeFreesound  # noqa: E402
from filmcheck import freesound, soundlib  # noqa: E402

KEY = "fs_live_abcdef0123456789K3Y9"


class Freesound(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fake = FakeFreesound(key=KEY).start()
        self.env = mock.patch.dict(os.environ, {"STUDIO_DATA": self.tmp.name, "STUDIO_ROOT": self.tmp.name,
                                                "STUDIO_FREESOUND_URL": self.fake.url, "FREESOUND_API_KEY": KEY})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.fake.stop()
        self.tmp.cleanup()

    def test_query_asks_for_cc0_and_drops_the_rest(self):
        res = freesound.search_cc0("bubbles")
        path, q, auth = self.fake.calls[-1]
        self.assertEqual(path, "/apiv2/search/text/")
        self.assertIn('license:"Creative Commons 0"', q["filter"])
        self.assertNotIn(KEY, q.get("token", "") + path)                          # the key is in the header only
        self.assertEqual(auth, f"Token {KEY}")
        self.assertEqual(sorted(r["id"] for r in res), [101, 103])                # 102 is CC BY: dropped

    def test_fetch_puts_a_cc0_entry_in_the_library(self):
        got = freesound.fill("aquarium bubbles", 3.0)
        self.assertEqual(got, 2)
        f = Path(self.tmp.name) / "sound" / "freesound" / "101.ogg"
        self.assertTrue(f.is_file())
        e = soundlib.get("fs:101")
        self.assertEqual((e["source"], e["license"], e["credit"], e["url"]),
                         ("freesound", "cc0-1.0", "Freesound #101 by alice", "https://freesound.org/s/101/"))
        self.assertTrue(e["fetched_at"])
        self.assertAlmostEqual(e["duration"], 4.0)
        self.assertEqual(freesound.fill("aquarium bubbles", 3.0), 0)               # already here
        with self.assertRaises(freesound.FreesoundError) as x:
            freesound.fetch(dict(self.fake.sounds[1], previews={"preview-hq-ogg": self.fake.url + "/previews/102-hq.ogg"}))
        self.assertEqual(x.exception.code, "not_cc0")

    def test_find_goes_to_freesound_when_the_library_lacks_it(self):
        hits = soundlib.find("aquarium bubbles", dur=2.0)
        self.assertTrue(hits)
        self.assertEqual(hits[0]["license"], "cc0-1.0")
        self.assertTrue(all(h["source"] == "freesound" for h in hits))

    def test_key_never_shows(self):
        self.fake.key = "something-else-entirely-0000"
        logs = []
        h = logging.Handler()
        h.emit = lambda rec: logs.append(rec.getMessage())
        logging.getLogger().addHandler(h)
        try:
            with self.assertRaises(freesound.FreesoundError) as e:
                freesound.search_cc0("bubbles")
        finally:
            logging.getLogger().removeHandler(h)
        self.assertEqual(e.exception.code, "invalid_key")
        self.assertNotIn(KEY, str(e.exception) + repr(e.exception) + "\n".join(logs))
        self.assertEqual(freesound.redact(f"x {KEY} y", KEY), "x …K3Y9 y")

    def test_no_key_is_a_clear_error(self):
        with mock.patch.dict(os.environ, {"FREESOUND_API_KEY": ""}), \
             mock.patch("filmcheck.eleven.load_env", return_value={}):
            with self.assertRaises(freesound.FreesoundError) as e:
                freesound.search_cc0("bubbles")
            self.assertEqual(e.exception.code, "no_key")
            self.assertIn("FREESOUND_API_KEY", e.exception.message)
            self.assertFalse(freesound.has_key())


if __name__ == "__main__":
    unittest.main()
