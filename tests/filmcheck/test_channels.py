"""Channel profiles and lessons (specs/012 T004–T006, T012, T015; SC-002, SC-003, SC-006)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import channels, editor, publish, qc, script  # noqa: E402

import samples  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"


def studio(root, *args):
    return subprocess.run(["sh", str(REPO / "bin" / "studio"), *map(str, args)], capture_output=True, text=True,
                          env={**os.environ, "STUDIO_ROOT": str(root), "STUDIO_LIB": "/nonexistent"})


def fresh():
    TMP.mkdir(exist_ok=True)
    return Path(tempfile.mkdtemp(dir=TMP))


def good_film(root, name="honey", slug="honey-facts", **kw):
    """A film with a passing script (010 rules apart from editor), a passing pack and the channel attached."""
    d = samples.make_publish_film(root, name, **kw)
    samples.write_script(d, (d / "SCRIPT.md").read_text(), (d / "SOURCES.md").read_text(),
                         opened=[{"url": u, "final_url": u, "status": 200} for u in
                                 ("https://example.org/honey", "https://example.org/acid")])
    samples.fake_thumbs(d)
    if not (Path(root) / "channels" / slug / "channel.json").exists():
        samples.make_channel(root, slug)
    channels.attach(root, d, slug)
    publish.build(d, None, draw=False)
    return d


def hard_fails(d):
    r = script.check(d)
    return sorted(k for k, ok in r["hard"].items() if not ok), r


def pub_codes(d):
    return sorted({p.split(":")[0] for p in publish.check(d)["problems"]})


class Store(unittest.TestCase):
    def setUp(self):
        self.root = fresh()

    def test_save_and_read_back(self):
        ch = samples.make_channel(self.root)
        self.assertEqual(channels.load(self.root, "honey-facts")["hashtags"], ["#honey"])
        self.assertIn("Honey Facts", (self.root / "channels" / "honey-facts" / "CHANNEL.md").read_text())
        self.assertIn("| honey-facts | Honey Facts |", (self.root / "channels" / "README.md").read_text())
        self.assertTrue(ch["updated"])

    def test_bad_profiles_are_refused(self):
        samples.make_channel(self.root)
        cases = {"slug": {"slug": "Bad Slug"}, "exists": {}, "tag banned": {"slug": "b", "hashtags": ["#shocking"]},
                 "voice file": {"slug": "c", "voice": "/home/me/clone.wav"}, "style": {"slug": "d", "style": "nope"},
                 "seconds": {"slug": "e", "seconds": 2}}
        for why, over in cases.items():
            with self.subTest(why):
                with self.assertRaises(channels.ChannelError):
                    ch = channels.load(self.root, "honey-facts")
                    ch.update(over)
                    channels.save(self.root, ch, new=True)

    def test_banned_matches_whole_words(self):
        self.assertEqual(channels.find_banned("Nhà bị sốt cao", ["sốc"]), [])
        self.assertEqual(len(channels.find_banned("Thật SỐC!", ["sốc"])), 1)
        self.assertEqual(len(channels.find_banned("这真是震惊的事", ["震惊"])), 1)

    def test_cli(self):
        r = studio(self.root, "channel", "list", "--json")
        self.assertEqual(json.loads(r.stdout)["channels"], [])
        samples.make_channel(self.root)                   # also writes my-styles/test-style
        self.assertEqual(studio(self.root, "channel", "new", "tea", "--name", "Tea", "--language", "en", "--seconds", "40",
                                "--style", "test-style").returncode, 0)
        self.assertEqual(studio(self.root, "channel", "new", "tea", "--name", "Tea", "--language", "en", "--seconds", "40",
                                "--style", "test-style").returncode, 2)
        self.assertEqual(studio(self.root, "channel", "set", "tea", "banned", "--add", "awful").returncode, 0)
        self.assertEqual(studio(self.root, "channel", "decide", "tea", "Short titles only").returncode, 0)
        ch = channels.load(self.root, "tea")
        self.assertEqual((ch["banned"], ch["decisions"][0]["text"]), (["awful"], "Short titles only"))
        self.assertEqual(studio(self.root, "channel", "show", "tea").returncode, 0)


class Snapshot(unittest.TestCase):
    def setUp(self):
        self.root = fresh()
        samples.make_channel(self.root)
        self.film = self.root / "films" / "f"
        self.film.mkdir(parents=True)

    def test_film_values_win(self):
        s = channels.attach(self.root, self.film, "honey-facts", seconds=30, voice="af_sky")["snapshot"]
        self.assertEqual((s["film"]["seconds"], s["film"]["voice"]), (30, "af_sky"))
        self.assertTrue(s["rules"]["voice_override"])
        s = channels.attach(self.root, self.film, "honey-facts")["snapshot"]
        self.assertFalse(s["rules"]["voice_override"])
        self.assertIn("No songs with lyrics.", (self.film / "CHANNEL_BRIEF.md").read_text())

    def test_only_active_valid_rules(self):
        samples.make_lesson(self.root, "honey-facts", "phrase:you won't believe")
        samples.make_lesson(self.root, "honey-facts", "phrase:draft only", status="draft")
        samples.make_lesson(self.root, "honey-facts", "regex:.*")
        samples.make_lesson(self.root, "shared", "max_title_chars:60")
        s = channels.attach(self.root, self.film, "honey-facts")["snapshot"]
        self.assertEqual([(x["n"], x["scope"]) for x in s["lessons"]], [(1, "channel"), (1, "shared")])

    def test_brief_is_short(self):
        for i in range(200):
            samples.make_lesson(self.root, "honey-facts", "phrase:bad words" if i == 199 else None,
                                what="A long mistake " * 15, stop="A long way to stop it " * 10)
        r = channels.attach(self.root, self.film, "honey-facts")
        text = (self.film / "CHANNEL_BRIEF.md").read_text()
        self.assertLessEqual(len(text), channels.BRIEF_MAX)
        self.assertIn("lessons not shown", text.splitlines()[-1])
        self.assertIn("#200", text)                     # the lesson with a rule comes first
        self.assertTrue(r["warning"])

    def test_missing_style_is_refused(self):
        with self.assertRaises(channels.ChannelError):
            channels.attach(self.root, self.film, "honey-facts", style="gone")


class Rules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = fresh()
        cls.good = good_film(cls.root)

    def copy(self, name):
        dst = self.root / "films" / name
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(self.good, dst)
        (dst / f"{self.good.name}.mp4").rename(dst / f"{name}.mp4")
        return dst

    def test_good_film_passes(self):
        fails, r = hard_fails(self.good)
        self.assertEqual(fails, [], r["issues"])
        self.assertEqual(pub_codes(self.good), [])
        self.assertNotIn("channel_voice", " ".join(qc.measure(self.good)["problems"]))

    def test_channel_language(self):
        d = self.copy("lang")
        (d / "SCRIPT.md").write_text((d / "SCRIPT.md").read_text().replace("Language: en", "Language: vi"))
        self.assertEqual(hard_fails(d)[0], ["channel_language"])

    def test_banned_word(self):
        d = self.copy("banned")
        (d / "SCRIPT.md").write_text((d / "SCRIPT.md").read_text().replace("Germs need water", "Shocking: germs need water"))
        fails, r = hard_fails(d)
        self.assertEqual(fails, ["banned_word"])
        bad = [i for i in r["issues"] if i["rule"] == "banned_word"]
        self.assertEqual((bad[0]["para"], bad[0]["sentence"]), ("P03", 1))

    def _pack(self, d, fn):
        pk = json.loads((d / "publish" / "pack.json").read_text())
        fn(pk)
        (d / "publish" / "pack.json").write_text(json.dumps(pk))
        publish.build(d, None, draw=False)

    def test_channel_hashtags(self):
        d = self.copy("tags")
        self._pack(d, lambda pk: pk.__setitem__("hashtags", ["#science", "#food", "#bees"]))
        self.assertEqual(pub_codes(d), ["channel_hashtags"])

    def test_channel_banned(self):
        d = self.copy("pbanned")
        self._pack(d, lambda pk: pk["titles"][2]["thumb"].__setitem__("text", "Shocking food"))
        self.assertEqual(pub_codes(d), ["channel_banned"])

    def test_channel_title_max(self):
        d = self.copy("tmax")
        self._pack(d, lambda pk: pk["titles"][0].__setitem__("text", "Why Honey From a Tomb Was Still Good to Eat: The Surprising Chemistry Behind It"))
        self.assertEqual(pub_codes(d), ["channel_title_max"])

    def test_channel_voice(self):
        d = self.copy("voice")
        rows = json.loads((d / "lines.json").read_text())
        rows[2]["voice"] = "am_adam"
        (d / "lines.json").write_text(json.dumps(rows))
        problems = qc.measure(d)["problems"]
        self.assertEqual([p.split(":")[0] for p in problems if p.startswith("channel_")], ["channel_voice"])
        channels.attach(self.root, d, "honey-facts", voice="am_adam")     # chosen for this film: allowed
        self.assertFalse(any(p.startswith("channel_voice") for p in qc.measure(d)["problems"]))

    def test_no_snapshot_no_change(self):                               # SC-006
        d = self.copy("plain")
        (d / "channel.json").unlink()
        (d / "CHANNEL_BRIEF.md").unlink()
        r = script.check(d)
        self.assertEqual(set(r["hard"]), {"format", "sources", "length", "unchanged"})
        self.assertNotIn("lessons_repeated", json.dumps([p for p in publish.check(d)["problems"]]))
        self.assertNotIn("channel_voice_bad", qc.measure(d)["measures"])

    def test_editor_reads_the_brief(self):                               # T012
        self.assertIn("CHANNEL_BRIEF.md", editor.prompt(self.good))
        self.assertIn("CHANNEL_BRIEF.md", editor.SYSTEM)
        d = self.copy("nobrief")
        (d / "CHANNEL_BRIEF.md").unlink()
        self.assertNotIn("CHANNEL_BRIEF.md", editor.prompt(d))


class Lessons(unittest.TestCase):
    def setUp(self):
        self.root = fresh()
        self.a = good_film(self.root, "a", "chan-a")
        samples.make_channel(self.root, "chan-b")
        self.b = good_film(self.root, "b", "chan-b")

    def reattach(self):
        channels.attach(self.root, self.a, "chan-a")
        channels.attach(self.root, self.b, "chan-b")

    def say(self, d, words):
        (d / "SCRIPT.md").write_text((d / "SCRIPT.md").read_text().replace("Germs need water to live.", words))

    def test_numbers_and_states(self):
        p = channels.lessons_file(self.root, "chan-a")
        x = channels.add_lesson(p, what="w", why="y", stop="s")
        self.assertEqual((x["n"], x["status"]), (1, "draft"))
        channels.approve(p, 1)
        channels.retire(p, 1)
        with self.assertRaises(channels.ChannelError):
            channels.approve(p, 1)
        self.assertEqual(channels.add_lesson(p, what="w", why="y", stop="s")["n"], 2)
        bad = channels.add_lesson(p, what="w", why="y", stop="s", rule="sound:loud")
        self.assertFalse(bad["rule_valid"])
        self.assertIn("(invalid)", p.with_name("LESSONS.md").read_text())

    def test_channel_lesson_blocks_only_its_channel(self):
        samples.make_lesson(self.root, "chan-a", "phrase:you won't believe")
        self.reattach()
        for d in (self.a, self.b):
            self.say(d, "You won't believe what germs need.")
        fails, r = hard_fails(self.a)
        self.assertEqual(fails, ["lesson_rule"])
        self.assertEqual([i["lesson"] for i in r["issues"] if i["rule"] == "lesson_rule"], [1])      # SC-003
        self.assertEqual(hard_fails(self.b)[0], [])

    def test_shared_lesson_blocks_every_channel(self):
        samples.make_lesson(self.root, "shared", "max_sentence_words:8")
        self.reattach()
        self.assertEqual(hard_fails(self.a)[0], ["lesson_rule"])
        self.assertEqual(hard_fails(self.b)[0], ["lesson_rule"])

    def test_draft_and_retired_do_not_block(self):
        samples.make_lesson(self.root, "chan-a", "phrase:germs", status="draft")
        x = samples.make_lesson(self.root, "chan-a", "phrase:water")
        channels.retire(channels.lessons_file(self.root, "chan-a"), x["n"])
        self.reattach()
        self.assertEqual(hard_fails(self.a)[0], [])

    def test_publish_lesson_rule_and_warning(self):
        samples.make_lesson(self.root, "chan-a", "phrase:last forever")
        samples.make_lesson(self.root, "shared", "max_title_chars:45")
        self.reattach()
        r = subprocess.run(["sh", str(REPO / "bin" / "studio"), "publish", str(self.a), "--no-draw"], capture_output=True,
                           text=True, env={**os.environ, "STUDIO_LIB": "/nonexistent"})
        self.assertEqual(r.returncode, 1, r.stdout)
        res = publish.check(self.a)
        self.assertEqual(sorted({p.split(":")[0] for p in res["problems"]}), ["lesson_rule"])
        self.assertEqual(res["measures"]["lessons_repeated"], [1])
        self.assertTrue(all("lesson #1" in p for p in res["problems"]))
        md = (self.a / "publish" / "PUBLISH.md").read_text().splitlines()
        self.assertTrue(md[2].startswith("⚠ Do not publish yet: repeats lesson #1"), md[:4])

    def test_lesson_cli(self):
        r = studio(self.root, "lesson", "draft", "chan-a", "--what", "w", "--why", "y", "--stop", "s", "--rule", "phrase:x y")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("lesson approve chan-a 1", r.stdout)
        self.assertEqual(studio(self.root, "lesson", "approve", "chan-a", "1").returncode, 0)
        self.assertEqual(studio(self.root, "lesson", "add", "shared", "--what", "w", "--why", "y", "--stop", "s").returncode, 0)
        rows = json.loads(studio(self.root, "lesson", "list", "chan-a", "--json").stdout)["lessons"]
        self.assertEqual([x["status"] for x in rows], ["active"])
        self.assertEqual(studio(self.root, "lesson", "list", "nope").returncode, 2)


if __name__ == "__main__":
    unittest.main()
