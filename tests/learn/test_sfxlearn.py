"""specs/037 T032: learn sfx on synthetic layers with fake classifiers (no torch).

Each sound is a tone at its own frequency; the fake classifiers name a clip by its main frequency, so every rule of
R8 can be checked: agree (CLAP in AST top 5 / same level-2 ancestor), unsure, AST < 0.10, a missing classifier;
events in the vocals layer outside the narrator's words; nearest word; chosen silence; how sounds end at a cut.
"""
import json
import unittest

import numpy as np

import helpers  # noqa: F401
from sl import sfxlearn as sx

SR = sx.SR
DUR = 23.0
CUTS = [11.0, 14.0, 17.0, 20.0]
WORDS = [("the", 1.0, 1.4), ("window", 2.5, 2.9), ("people", 5.0, 5.5), ("cheer", 5.5, 5.9),
         ("goes", 7.2, 7.6), ("silent.", 7.6, 8.1), ("fish", 9.5, 9.9), ("then", 12.8, 13.1)]
# freq: (layer, t0, t1, ast top 5, clap top 1)
SOUNDS = {
    3000: ("fx", 3.0, 3.3, [("Shatter", .6), ("Glass", .3), ("Breaking", .2)], ("glass shattering", .7)),  # sure
    500: ("vocals", 6.0, 6.8, [("Cheering", .5), ("Crowd", .4)], ("crowd cheering", .8)),               # vocals off words
    1500: ("fx", 10.0, 10.6, [("Speech", .3), ("Gurgling", .05)], ("water bubbling", .6)),               # likely: support
    2200: ("fx", 12.0, 12.3, [("Dog", .5), ("Bark", .3)], ("car engine", .6)),                           # unsure: veto
    800: ("fx", 13.2, 14.0, [("Applause", .5), ("Clapping", .3)], ("people applauding", .6)),            # hard at 14.0
    1000: ("fx", 16.5, 17.0, [("Ding", .5)], ("ding", .6)),                                              # fade at 17.0
    1200: ("fx", 19.0, 21.5, [("Whoosh, swoosh, swish", .5)], ("whoosh", .6)),                           # over 20.0
    2600: ("fx", 22.0, 22.4, [("Speech", .4)], ("ball bouncing", .95)),                                  # likely: CLAP alone
}
BED = {220: ("fx", 9.0, None, [("Music", .8), ("Hum", .05)], ("background music", .5))}   # music back: never an effect


def tone(f, a, b, amp=0.3, decay=None):
    n = int(DUR * SR)
    x = np.zeros(n, np.float32)
    i, j = int(a * SR), int(b * SR)
    t = np.arange(j - i) / SR
    x[i:j] = amp * np.sin(2 * np.pi * f * t)
    if decay:                               # exponential tail of `decay` s losing 30 dB
        k = int(decay * SR)
        tt = np.arange(k) / SR
        x[j:j + k] = amp * np.sin(2 * np.pi * f * ((j - i) / SR + tt)) * 10 ** (-1.5 * tt / decay)
    return x


def build():
    rnd = np.random.default_rng(1)
    n = int(DUR * SR)
    fx = (rnd.normal(0, 1e-4, n)).astype(np.float32)
    voc = (rnd.normal(0, 1e-4, n)).astype(np.float32)
    for w, a, b in WORDS:                   # the narrator: band noise bursts
        i, j = int(a * SR), int(b * SR)
        s = np.fft.rfft(rnd.normal(0, 1, j - i))
        f = np.fft.rfftfreq(j - i, 1 / SR)
        s[(f < 300) | (f > 3000)] = 0
        y = np.fft.irfft(s, j - i)
        voc[i:j] += (0.2 * y / np.abs(y).max()).astype(np.float32)
    for f, (layer, a, b, _, _) in SOUNDS.items():
        x = tone(f, a, b, decay=0.4 if f == 1000 else None)
        if layer == "fx":
            fx += x
        else:
            voc += x
    bed = (0.03 * np.sin(2 * np.pi * 220 * np.arange(n) / SR)).astype(np.float32)   # music bed, −33 dBFS
    bed[int(8.2 * SR):int(8.9 * SR)] = 0                                            # "…goes silent."
    bed[int(8.9 * SR):int(9.4 * SR)] *= np.linspace(0, 1, int(9.4 * SR) - int(8.9 * SR))  # the music comes back softly
    fx += bed                                                                       # music is in the no-voice layer
    mix = fx + voc
    words = [{"word": w, "start": a, "end": b} for w, a, b in WORDS]
    return mix, {"fx": fx, "vocals": voc}, words


class Fake:
    def __init__(self, ast=True, clap=True):
        if not ast:
            self.ast = None
        if not clap:
            self.clap = None

    @staticmethod
    def _freq(clip, sr):
        s = np.abs(np.fft.rfft(clip))
        f = np.fft.rfftfreq(len(clip), 1 / sr)[int(s.argmax())]
        return min({**SOUNDS, **BED}, key=lambda k: abs(k - f))

    def ast(self, clip, sr):
        return {**SOUNDS, **BED}[self._freq(clip, sr)][3]

    def clap(self, clip, sr, labels):
        lab = {**SOUNDS, **BED}[self._freq(clip, sr)][4]
        assert lab[0] in labels and "Speech" not in labels and "Music" not in labels
        return lab


class SfxLearn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mix, cls.stems, cls.words = build()
        cls.res = sx.analyze(cls.mix, cls.stems, cls.words, CUTS, Fake())

    def ev(self, t):
        hits = [e for e in self.res["events"] if abs(e["t"] - t) < 0.1]
        self.assertEqual(len(hits), 1, f"event at {t}: {[(e['t'], e['layer']) for e in self.res['events']]}")
        return hits[0]

    def test_events_found_once_each(self):
        ts = sorted(round(e["t"], 1) for e in self.res["events"])
        self.assertEqual(ts, sorted(v[1] for v in {**SOUNDS, **BED}.values()))
        self.assertFalse(self.ev(9.0)["agree"], "Music never names an effect")

    def test_agree_in_top5(self):
        e = self.ev(3.0)
        self.assertEqual(e["trust"], "sure")
        self.assertEqual(e["label"], "glass shattering")
        self.assertEqual(e["layer"], "fx")
        self.assertEqual(e["word"]["text"], "window")
        self.assertEqual(e["shot"], "S1")

    def test_crowd_in_vocals_off_words(self):
        e = self.ev(6.0)
        self.assertEqual(e["layer"], "vocal_off_words")
        self.assertTrue(e["agree"])
        self.assertEqual(e["word"]["text"], "cheer")
        self.assertFalse(any(e["layer"] == "vocal_off_words" and e["t"] < 5.95 for e in self.res["events"]),
                         "words of the narrator must be muted")

    def test_likely(self):
        e = self.ev(10.0)                               # CLAP, supported by a weak AST label of the same group
        self.assertEqual((e["trust"], e["label"]), ("likely", "water bubbling"))
        self.assertEqual(self.res["ontology"]["Gurgling"], ["Water"])
        e = self.ev(22.0)                               # CLAP alone, very sure, AST not against
        self.assertEqual((e["trust"], e["label"]), ("likely", "ball bouncing"))

    def test_unsure(self):
        self.assertFalse(self.ev(12.0)["agree"])
        self.assertIsNone(self.ev(12.0)["label"])

    def test_word_limit(self):
        self.assertNotIn("word", self.ev(19.0))      # no word within 1.0 s
        self.assertNotIn("word", self.ev(16.5))

    def test_cuts(self):
        self.assertEqual(self.ev(13.2)["cut"]["kind"], "hard")
        c = self.ev(16.5)["cut"]
        self.assertEqual(c["kind"], "fade")
        self.assertGreater(c["fade_s"], 0.1)
        self.assertEqual(self.ev(19.0)["cut"]["kind"], "over")
        self.assertNotIn("cut", self.ev(3.0))

    def test_silence(self):
        s = self.res["silences"]
        self.assertEqual(len(s), 1, s)
        self.assertEqual(s[0]["word"], "silent")
        self.assertAlmostEqual(s[0]["t"], 8.2, delta=0.05)
        self.assertGreaterEqual(s[0]["len"], 0.6)
        self.assertLessEqual(s[0]["db"], -50)

    def test_gain_vs_voice(self):
        self.assertIsNotNone(self.ev(3.0)["db_vs_voice"])

    def test_missing_classifier(self):
        for m in (Fake(ast=False), Fake(clap=False)):
            r = sx.analyze(self.mix, self.stems, self.words, CUTS, m)
            self.assertTrue(r["events"])
            self.assertFalse(any(e["agree"] for e in r["events"]))
            self.assertTrue(r["models"]["missing"])

    def test_summary_numbers_only(self):
        r = dict(self.res, video="v1")
        s = sx.sfx_summary([r])
        self.assertEqual({a["label"] for a in s["actions"]}, {"glass shattering", "crowd cheering", "water bubbling",
                                                               "people applauding", "ding", "whoosh", "ball bouncing"})
        self.assertEqual(next(a for a in s["actions"] if a["label"] == "ball bouncing")["trust"], "likely")
        glass = next(a for a in s["actions"] if a["label"] == "glass shattering")
        self.assertEqual(glass["trust"], "sure")
        self.assertEqual(glass["action"], "window")
        self.assertEqual(glass["evidence"][0][0], "v1")
        self.assertAlmostEqual(glass["evidence"][0][1], 3.0, delta=0.05)
        self.assertEqual(s["unsure_n"], 2)
        self.assertEqual(len(s["gain_db"]), 3)
        self.assertEqual(s["silences"]["evidence"][0][2], "silent")
        self.assertIn(s["cut"]["kind"], ("hard", "fade", "over"))

        def walk(x):
            if isinstance(x, list):
                self.assertLessEqual(len(x), 10, "no sample arrays in sound.sfx")
                for y in x:
                    walk(y)
            elif isinstance(x, dict):
                for y in x.values():
                    walk(y)
            else:
                self.assertIsInstance(x, (int, float, str, type(None)))
        walk(s)
        json.dumps(s)

    def test_write_style(self):
        p = helpers.Project()
        try:
            d = p.dir / "my-styles" / "demo"
            d.mkdir()
            (d / "template.json").write_text('{"set": "demo-set"}')
            (d / "STYLE.md").write_text("# Demo\n\n## Âm thanh\n\nold\n")
            s = sx.sfx_summary([dict(self.res, video="v1")])
            sx.write_style("demo", "demo-set", s, p.dir)
            sx.write_style("demo", "demo-set", s, p.dir)
            t = json.loads((d / "template.json").read_text())
            self.assertEqual(t["set"], "demo-set")
            self.assertEqual(t["sound"]["sfx"]["unsure_n"], 2)
            md = (d / "STYLE.md").read_text()
            self.assertEqual(md.count("<!-- sfx (learn sfx"), 1)
            self.assertIn("window → glass shattering", md)
            self.assertIn("(likely)", md)
        finally:
            p.close() if hasattr(p, "close") else None


class Score(unittest.TestCase):
    def test_expect_file_and_score(self):
        exp = json.loads((helpers.REPO / "tests" / "learn" / "data" / "voicecheck_expect.json").read_text())
        self.assertEqual(len(exp["events"]), 5)
        res = {"events": [{"t": 4.0, "agree": True, "label": "glass shattering"}, {"t": 165.0, "agree": True, "label": "Cheering"},
                          {"t": 23.0, "agree": False, "label": None}],
               "silences": [{"t": 8.2, "len": 0.7, "db": -57.0, "word": "silent"}]}
        sc = sx.score(res, exp)
        self.assertEqual(sc["found"], 3)
        self.assertEqual([e["found"] for e in sc["events"]], [True, True, False, False, True])


class Inputs(unittest.TestCase):
    def test_words_from_sentences(self):
        w = sx.load_words([{"t": 2.0, "d": 1.0, "text": "the window breaks"}, {"t": 0.0, "d": 0.5, "text": "so"}])
        self.assertEqual([x["word"] for x in w], ["so", "the", "window", "breaks"])
        self.assertAlmostEqual(w[2]["start"], 2.333, places=2)
        self.assertEqual(sx.load_words({"words": [{"word": "a", "start": 1, "end": 2}]})[0]["end"], 2.0)

    def test_cuts(self):
        self.assertEqual(sx.load_cuts({"shots": [{"t0": 0, "t1": 2}, {"t0": 2, "t1": 5}]}), [2.0])
        self.assertEqual(sx.load_cuts([[0, 2, "", "S1"], [2, 4, "", "S2"]]), [2.0])
        self.assertEqual(sx.load_cuts([3.0, 1.0]), [1.0, 3.0])
        self.assertEqual(sx.shot_of(2.5, [2.0, 4.0]), "S2")

    def test_agree_rule(self):
        A = sx.agree
        self.assertEqual(A([("Shatter", .5)], ("window breaking", .4)), ("sure", "window breaking"))
        self.assertEqual(A([("Shatter", .5)], ("Chink, clink", .9)), ("sure", "Chink, clink"))      # same group
        self.assertEqual(A([("Liquid", .04)], ("water bubbling", .6)), ("likely", "water bubbling"))
        self.assertEqual(A([("Pant", .1)], ("ball bouncing", .94)), ("likely", "ball bouncing"))
        self.assertEqual(A([("Pant", .3)], ("ball bouncing", .94)), (None, None))                    # AST veto
        self.assertEqual(A([("Smash, crash", .18)], ("whistle", .3)), ("likely", "Smash, crash"))    # AST alone
        self.assertEqual(A([("Smash, crash", .18)], ("coins dropping", .84)), (None, None))          # CLAP veto
        self.assertEqual(A([("Glass", .09)], ("glass shattering", .5)), ("likely", "glass shattering"))   # < AST_MIN
        self.assertEqual(A([("Music", .9)], ("background music", .9)), (None, None))
        self.assertEqual(A([("Speech", .9)], ("a man talking", .99)), (None, None))
        self.assertEqual(A([], None), (None, None))


if __name__ == "__main__":
    unittest.main()
