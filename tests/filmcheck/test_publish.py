"""The publish pack (specs/011): chapters, subtitles, description, every check rule (T004, T006, T018; SC-002, SC-003,
SC-006). No browser: thumbnails here are plain pictures with a hand-written thumbs.json (test_thumbs draws real ones)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import publish, report  # noqa: E402

import samples  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"


def studio(*args):
    return subprocess.run(["sh", str(REPO / "bin" / "studio"), *map(str, args)], capture_output=True, text=True,
                          env={**os.environ, "STUDIO_LIB": "/nonexistent"})


def made(root, name="honey", **kw):
    d = samples.make_publish_film(root, name, **kw)
    samples.fake_thumbs(d)
    publish.build(d, None, draw=False)
    return d


def codes(result):
    return sorted({p.split(":")[0] for p in result["problems"]})


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TMP.mkdir(exist_ok=True)
        cls.root = Path(tempfile.mkdtemp(dir=TMP))
        cls.good = made(cls.root)

    def copy(self, name):
        dst = self.root / "films" / name
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(self.good, dst)
        (dst / f"{self.good.name}.mp4").rename(dst / f"{name}.mp4")
        return dst


class Pack(Base):
    def test_files(self):
        pub = self.good / "publish"
        for f in ("thumbnail-1.png", "thumbnail-2.png", "thumbnail-3.png", "thumbs.json", "titles.md", "description.md",
                  "subtitles.srt", "PUBLISH.md"):
            self.assertTrue((pub / f).is_file(), f)

    def test_good_pack_passes(self):
        r = publish.check(self.good)
        self.assertEqual(r["problems"], [])
        self.assertEqual(r["applicable"], {"chapters": True, "subtitles": True})

    def test_chapters_from_paragraph_starts(self):
        r = publish.check(self.good)
        ch = r["measures"]["chapters"]
        self.assertEqual(len(ch), 3)
        self.assertEqual(ch[0]["at"], 0.0)
        nar = json.loads((self.good / "narration.json").read_text())
        p3 = next(x["at"] for x in nar["lines"] if x["para"] == "P03")
        self.assertAlmostEqual(ch[1]["at"], p3)
        self.assertTrue(all(c["length"] >= 10 for c in ch))
        desc = (self.good / "publish" / "description.md").read_text()
        self.assertIn("0:00 The tomb", desc)
        self.assertIn(f"{publish.stamp(p3)} Too dry for germs", desc)

    def test_short_film_has_no_chapters(self):
        d = made(self.root, "short", seconds=25)
        r = publish.check(d)
        self.assertFalse(r["applicable"]["chapters"])
        self.assertNotIn("chapters", codes(r))
        self.assertNotIn("0:00", (d / "publish" / "description.md").read_text())

    def test_subtitles_match_script_and_timing(self):
        cues = publish.read_srt(self.good / "publish" / "subtitles.srt")
        text = " ".join(" ".join(c["lines"]) for c in cues)
        script = " ".join(s for _, ss in samples.PUB_PARAS for s in ss)
        self.assertEqual(text, script)
        words = json.loads((self.good / "voices" / "words.json").read_text())
        nar = json.loads((self.good / "narration.json").read_text())
        starts = [ln["at"] + words[ln["id"]][0][1] for ln in nar["lines"]]
        for c in cues:      # every cue starts with the first word of a line, here one line is one sentence (SC-006)
            self.assertLessEqual(min(abs(c["start"] - s) for s in starts), 0.3)
            self.assertLessEqual(len(c["lines"]), 2)
            self.assertTrue(all(publish.units(x) <= 42 for x in c["lines"]))
            self.assertTrue(1.0 - 1e-3 <= c["end"] - c["start"] <= 7.0 + 1e-3)

    def test_long_sentence_is_split(self):
        words = [[f"w{i}", i * 0.4, i * 0.4 + 0.35] for i in range(30)]
        text = " ".join(f"word{i}," if i == 14 else f"word{i}" for i in range(30)) + "."
        cues = publish._cues_for_line(text, words)
        self.assertGreater(len(cues), 1)
        self.assertEqual(" ".join(" ".join(c["lines"]) for c in cues), text)
        self.assertTrue(all(c["end"] - c["start"] <= 7.0 + 1e-3 for c in cues))

    def test_description_order_and_sources(self):
        desc = (self.good / "publish" / "description.md").read_text()
        i = [desc.index(x) for x in ("Archaeologists found", "A short look", "0:00", "Sources:", "#honey")]
        self.assertEqual(i, sorted(i))
        self.assertEqual(desc.count("https://example.org/acid"), 1)       # one line per source

    def test_fiction_and_provided_not_listed(self):
        d = self.copy("fiction")
        (d / "SOURCES.md").write_text('- [P01] "a tomb": fiction\n- [P02] "notes": Notes, 2024, provided:notes.pdf\n')
        publish.build(d, None, draw=False)
        self.assertNotIn("Sources:", (d / "publish" / "description.md").read_text())

    def test_titles_and_publish_md(self):
        t = (self.good / "publish" / "titles.md").read_text()
        self.assertIn("**Curiosity:**", t)
        self.assertIn("thumbnail-3.png", t)
        p = (self.good / "publish" / "PUBLISH.md").read_text()
        self.assertIn("# Publish: Honey Never Spoils", p)
        self.assertEqual(p.count("| thumbnail-"), 3)
        self.assertNotIn("## Missing", p)

    def test_old_film_without_narration(self):
        d = made(self.root, "old", narration=False, script=False)
        r = publish.check(d)
        self.assertEqual(r["applicable"], {"chapters": False, "subtitles": False})
        self.assertFalse(r["measures"]["numbers_checked"])
        self.assertEqual(r["problems"], [])
        p = (d / "publish" / "PUBLISH.md").read_text()
        self.assertIn("## Missing", p)
        self.assertFalse((d / "publish" / "subtitles.srt").exists())

    def test_cli_exit_codes(self):
        r = studio("publish", self.good, "--check-only", "--json")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(json.loads(r.stdout)["pass"])
        d = self.copy("nopack")
        (d / "publish" / "pack.json").unlink()
        self.assertEqual(studio("publish", d).returncode, 2)

    def test_check_only_is_fast(self):
        d = made(self.root, "sixty", seconds=60)
        t0 = time.time()
        r = studio("publish", d, "--check-only")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertLess(time.time() - t0, 10)            # SC-003


class Report(Base):
    def test_publish_and_script_results_live_together(self):
        d = self.copy("report")
        r = studio("publish", d, "--check-only")
        self.assertEqual(r.returncode, 0, r.stdout)
        report.update(d, lambda x: x["script"].__setitem__("verdict", "pass"))
        data = report.load(d)
        self.assertTrue(data["publish"]["pass"])
        self.assertEqual(data["script"]["verdict"], "pass")
        self.assertIn("**Publish:** pass", (d / "CHECKS.md").read_text())
        studio("publish", d, "--check-only")
        self.assertEqual(report.load(d)["script"]["verdict"], "pass")


def _pack(d):
    return json.loads((d / "publish" / "pack.json").read_text())


def _save(d, pk):
    (d / "publish" / "pack.json").write_text(json.dumps(pk))


def _edit_srt(d, old, new):
    f = d / "publish" / "subtitles.srt"
    f.write_text(f.read_text().replace(old, new, 1))


def _set(path_fn):
    def go(d):
        pk = _pack(d)
        path_fn(pk)
        _save(d, pk)
        publish.build(d, None, draw=False)
    return go


def _thumbs(**row):
    return lambda d: samples.fake_thumbs(d, rows=[{}, row])


BAD = {   # code → how to break a good pack in exactly one way (contracts/cli.md)
    "files_missing": lambda d: (d / "publish" / "titles.md").unlink(),
    "thumb_size": lambda d: samples.fake_thumbs(d, size=(640, 360)),
    "thumb_text_words": _set(lambda pk: pk["titles"][1]["thumb"].__setitem__("text", "one two three four five six seven")),
    "thumb_text_height": _thumbs(text_height_ratio=0.05),
    "thumb_contrast": _thumbs(contrast=3.0),
    "thumb_glyphs": _thumbs(missing_glyphs=[{"char": "", "codepoint": "U+E000", "text": "x"}]),
    "thumb_font": _thumbs(font_loaded=False),
    "thumb_repeats_title": _set(lambda pk: pk["titles"][2]["thumb"].__setitem__("text", "Honey really last")),
    "thumb_same_time": _set(lambda pk: pk["titles"][1]["thumb"].__setitem__("t", 5.5)),
    "thumb_not_rendered": lambda d: (d / "publish" / "thumbs.json").write_text('{"error": "no browser"}'),
    "title_count": _set(lambda pk: pk["titles"].reverse()),
    "title_length": _set(lambda pk: pk["titles"][0].__setitem__("text", "Honey: " + "very " * 20 + "old")),
    "title_break": _set(lambda pk: pk["titles"][0].__setitem__("text", "Why honey found in an old Egyptian tomb was still good to eat today")),
    "hook_length": _set(lambda pk: pk.__setitem__("hook", ["Archaeologists found honey in an Egyptian tomb."])),
    "description_length": _set(lambda pk: pk.__setitem__("summary", "Honey keeps. " * 50)),
    "hashtags": _set(lambda pk: pk.__setitem__("hashtags", ["#honey", "#science"])),
    "angle_brackets": _set(lambda pk: pk.__setitem__("summary", "Honey resists germs <for a long time>.")),
    "number_unsourced": _set(lambda pk: pk["titles"][0].__setitem__("text", "Why 5,000 Jars of Honey Were Still Good")),
    "language": _set(lambda pk: pk.__setitem__("language", "vi")),
    "chapters": _set(lambda pk: pk.__setitem__("chapters", pk["chapters"][1:])),
    "subtitles_text": lambda d: _edit_srt(d, "Egyptian", "Roman"),
    "subtitles_cue": lambda d: _edit_srt(d, "Archaeologists found", "Archaeologists\nfound"),
}


class Rules(Base):
    def test_each_bad_pack_fails_one_rule(self):
        for code, breakit in BAD.items():
            with self.subTest(code=code):
                d = self.copy("bad-" + code.replace("_", "-"))
                breakit(d)
                r = publish.check(d)
                self.assertEqual(codes(r), [code], r["problems"])

    def test_every_rule_has_a_bad_pack(self):
        rules = set()
        for line in (REPO / "specs/011-publish-pack/contracts/cli.md").read_text().splitlines():
            if line.startswith("| `") and "`" in line[3:]:
                rules.add(line[3:line.index("`", 3)])
        self.assertEqual(rules - {"Mã lỗi"}, set(BAD))


if __name__ == "__main__":
    unittest.main()
