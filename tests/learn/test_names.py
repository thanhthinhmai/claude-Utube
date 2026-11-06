import unittest

from helpers import Project
from sl import names, refset


class Names(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        data = refset.new_set("names-set", "channel", ["https://example.invalid/@meoluoi"], deny=["Captain Nova"])
        data["videos"].append({"id": "v01", "file": "v01.mp4", "origin": "https://example.invalid/v/1",
                               "title": "Why bridges fall down", "channel": "Mèo Lười Studio", "handle": "@meoluoi",
                               "state": "transcribed"})
        refset.save("names-set", data)
        words = "the soldiers marched across the old iron bridge in perfect step".split()
        refset.write_json(refset.profile_dir("names-set", "v01") / "words.json",
                          {"language": "en", "words": [{"word": w, "start": i, "end": i + .5} for i, w in enumerate(words)]})
        self.f = self.p.dir / "STYLE.md"

    def tearDown(self):
        self.p.close()

    def check(self, text):
        self.f.write_text(text, encoding="utf-8")
        return names.check_files("names-set", [self.f])

    def test_clean_text_passes(self):
        self.assertEqual(self.check("# Style\nWarm palette, ink outlines, the camera glides.\n"), [])

    def test_channel_without_diacritics(self):
        v = self.check("line one\nInspired by meo luoi studio videos\n")
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0]["line"], 2)

    def test_handle_title_deny(self):
        self.assertTrue(self.check("see @meoluoi"))
        self.assertTrue(self.check("like 'Why bridges fall down'"))
        self.assertTrue(self.check("hero: captain nova"))

    def test_six_word_quote(self):  # SC-003
        self.assertTrue(self.check("Narration: The soldiers marched across the old iron gate."))
        self.assertEqual(self.check("They marched across the old iron gate."), [])   # only 5 words match

    def test_names_from_transcript(self):  # FR-015, T036
        words = "we met Alice at the harbour . Later Alice said Bob was late . Later we left".split()
        refset.write_json(refset.profile_dir("names-set", "v02") / "words.json",
                          {"words": [{"word": w, "start": i, "end": i + .5} for i, w in enumerate(words)]})
        self.assertTrue(self.check("A heroine like alice walks in."))     # twice, mid-sentence
        self.assertEqual(self.check("Bob style hats."), [])                # only once
        self.assertEqual(self.check("Later the camera rests."), [])        # sentence start, not a name

    def test_strings_and_cli_exit(self):
        self.assertTrue(names.check_strings("names-set", ["meo-luoi-studio"]))
        self.f.write_text("clean\n", encoding="utf-8")
        self.assertEqual(names.cli("names-set", [str(self.f)]), 0)
        self.f.write_text("by Mèo Lười Studio\n", encoding="utf-8")
        self.assertEqual(names.cli("names-set", [str(self.f)]), 1)


if __name__ == "__main__":
    unittest.main()
