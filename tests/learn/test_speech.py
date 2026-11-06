import unittest

import helpers  # noqa: F401  (sys.path)
from sl import speech


class Speech(unittest.TestCase):
    def test_rate_with_pause(self):  # SC-002: ≤ 10 %
        # 40 words over 10 s, with one 1 s pause between word 20 and 21
        words, t = [], 0.0
        for i in range(40):
            if i == 20:
                t += 1.0
            words.append({"word": f"w{i}", "start": t, "end": t + 0.2})
            t += 9.0 / 40
        r = speech.rate(words)
        expect = 40 / 9.0
        self.assertEqual(r["unit"], "words/s")
        self.assertLessEqual(abs(r["rate"] - expect) / expect, 0.10, r)
        self.assertAlmostEqual(r["pause_total"], 1.0, delta=0.1)

    def test_chinese_counts_characters(self):
        words = [{"word": "你好", "start": 0.0, "end": 0.4}, {"word": "世界", "start": 0.5, "end": 1.0}]
        r = speech.rate(words, language="zh")
        self.assertEqual(r["unit"], "chars/s")
        self.assertEqual(r["words"], 4)

    def test_empty(self):
        self.assertIsNone(speech.rate([]))


if __name__ == "__main__":
    unittest.main()
