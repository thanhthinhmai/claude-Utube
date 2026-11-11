"""The topic picker (specs/013 T004–T006, T012): plumbing, the score tables on hand-checked numbers (SC-001), units
(SC-002), the queue rules (SC-003) and the key never showing (SC-004). A fake YouTube runs in this process."""
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
from filmcheck import topics  # noqa: E402

import samples  # noqa: E402
import youtube_samples as yt  # noqa: E402

TMP = Path(__file__).resolve().parent / ".tmp"
FAKE_CLAUDE = REPO / "tests" / "online" / "fake_claude"
SAMPLE = list(yt.EXPECTED)


class FakeYouTube:
    def __init__(self):
        self.calls, self.keys = [], []
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                u = urllib.parse.urlsplit(self.path)
                endpoint = u.path.rsplit("/", 1)[-1]
                params = dict(urllib.parse.parse_qsl(u.query))
                outer.calls.append(endpoint)
                if "[403]" in params.get("q", ""):
                    body = json.dumps({"error": {"code": 403, "message": f"bad request {self.path}"}}).encode()
                    self.send_response(403)
                else:
                    body = json.dumps(yt.answer(endpoint, params, outer.keys)).encode()
                    self.send_response(200)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}/youtube/v3"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()

    def units(self):
        return sum(topics.PRICE[c] for c in self.calls)


def fresh():
    TMP.mkdir(exist_ok=True)
    return Path(tempfile.mkdtemp(dir=TMP))


def fake_fit(channel, texts, suggest, videos=None):
    got = {t: {"score": 2 if "[fit-low]" in t else 7, "type": None, "reason": "r",
               "offtopic": [vid for vid, title in (videos or {}).get(t, []) if "squish" in title.lower()]} for t in texts}
    return got, (["how bees make honey"] if suggest else [])


class Plumbing(unittest.TestCase):
    def test_usage_by_day_and_limit(self):
        d = fresh()
        u = topics.Usage(d / "u.json", 150)
        self.assertEqual(u.charge("search"), 100)
        with self.assertRaises(topics.QuotaError):
            u.charge("search")
        (d / "u.json").write_text(json.dumps({"day": "2000-01-01", "units": 149}))
        self.assertEqual(u.today(), 0)                           # a new day starts again

    def test_cache_and_redact(self):
        c = topics.Cache(fresh() / "c")
        c.put("videos", {"id": "x"}, {"items": [1]})
        self.assertEqual(c.get("videos", {"id": "x"}), {"items": [1]})
        self.assertIsNone(c.get("videos", {"id": "y"}))
        k = yt.KEY
        self.assertNotIn(k, topics.redact(f"url?key={k}&q=1 and {k}", k))
        self.assertIn(k[-4:], topics.redact(k, k))


class Scores(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.yt = FakeYouTube()

    @classmethod
    def tearDownClass(cls):
        cls.yt.close()

    def fetcher(self, root, limit=9000):
        return topics.Fetcher.local(yt.KEY, topics.Usage(root / "u.json", limit), topics.Cache(root / "cache"), self.yt.url)

    def test_tables_at_their_edges(self):
        self.assertEqual([topics._step(v, topics.DEMAND) for v in (999, 1000, 299_999, 300_000, 10_000_000)], [0, 2, 5, 6, 10])
        self.assertEqual([topics._step(v, topics.HEAT) for v in (0.39, 0.4, 1.0, 1.99, 2.0)], [1, 2, 6, 8, 10])
        self.assertEqual(topics.score_overlap("honey vs sugar", []), (10, None))
        self.assertEqual(topics.score_overlap("honey vs sugar", [{"name": "f", "text": "honey vs sugar"}])[0], 0)
        self.assertEqual(topics.verdict({"demand": 10, "heat": 10, "competition": 10, "overlap": 10, "fit": 3}), "HOLD")
        self.assertEqual(topics.verdict({"demand": 5, "heat": 5, "competition": 5, "overlap": 5, "fit": 4}), "DROP")

    def test_sample_topics_match_the_hand_checks(self):                # SC-001
        root = fresh()
        ch = {"slug": "honey", "language": "en", "name": "Honey"}
        f = self.fetcher(root)
        r = topics.score_batch(root, "honey", ch, SAMPLE, f, fit=fake_fit, made=[])
        data = r["data"]
        for text, (scores, verdict) in yt.EXPECTED.items():
            t = next(x for x in data["topics"] if x["text"] == text)
            self.assertEqual((t["scores"], t["verdict"]), (scores, verdict), text)
            again = topics.score_raw(text, t["raw"], [], t["scores"]["fit"])      # same numbers, same result
            self.assertEqual((again["scores"], again["verdict"]), (scores, verdict))
            self.assertTrue(t["evidence"]["top_video"]["url"].startswith("https://www.youtube.com/watch?v="))
        self.assertLessEqual(r["units"] / len(SAMPLE), 400)          # SC-002
        units = r["units"]
        r2 = topics.score_batch(root, "honey", ch, SAMPLE, self.fetcher(root), fit=fake_fit, made=[])
        self.assertEqual(r2["units"], 0)                             # within 24 hours: from the cache
        self.assertGreater(units, 0)

    def test_overlap_names_the_film(self):
        root = fresh()
        made = [{"name": "honey-forever", "text": "Why honey never spoils, ever"}]
        r = topics.score_batch(root, "honey", {"language": "en"}, ["why honey never spoils"], self.fetcher(root),
                               fit=fake_fit, made=made)
        t = r["data"]["topics"][0]
        self.assertLess(t["scores"]["overlap"], 3)
        self.assertEqual(t["evidence"]["closest_film"]["name"], "honey-forever")

    def test_reference_channel_blocks(self):
        root = fresh()
        r = topics.score_batch(root, "honey", {"language": "en"}, SAMPLE, self.fetcher(root), fit=fake_fit, made=[],
                               refs=[yt.REF_CHANNEL])
        st = {t["text"]: t["status"] for t in r["data"]["topics"]}
        self.assertEqual(st["honey vs sugar"], "blocked_reference")
        self.assertEqual(st["bee dances explained"], "queued")       # the reference video is 40 days old

    def test_quota_stops_and_keeps(self):
        root = fresh()
        r = topics.score_batch(root, "honey", {"language": "en"}, SAMPLE, self.fetcher(root, limit=450), fit=fake_fit, made=[])
        st = [t["status"] for t in r["data"]["topics"]]
        self.assertTrue(r["stopped"])
        self.assertIn("unscored", st)
        self.assertTrue(any(s != "unscored" for s in st))

    def test_cli(self):
        root = fresh()
        samples.make_channel(root, "honey")
        env = {**os.environ, "STUDIO_ROOT": str(root), "STUDIO_YOUTUBE_URL": self.yt.url, "STUDIO_CLAUDE_BIN": str(FAKE_CLAUDE),
               "HOME": str(root)}
        env.pop("YOUTUBE_API_KEY", None)
        run = lambda *a, **kw: subprocess.run(["sh", str(REPO / "bin" / "studio"), *a], capture_output=True, text=True,  # noqa: E731
                                              env={**env, **kw})
        r = run("topics", "score", "honey", "why honey never spoils")
        self.assertEqual(r.returncode, 2)
        self.assertIn("config youtube-key", r.stderr)
        r = run("topics", "score", "honey", *SAMPLE, "--suggest", YOUTUBE_API_KEY=yt.KEY)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("PRIORITY", r.stdout)
        data = json.loads((root / "channels" / "honey" / "topics.json").read_text())
        self.assertTrue(any(t["source"] == "suggested" for t in data["topics"]))
        self.assertIn("## Queue", (root / "channels" / "honey" / "TOPICS.md").read_text())
        r = run("topics", "fit", "honey", "3", "1", YOUTUBE_API_KEY=yt.KEY)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("HOLD", r.stdout)                              # bee dances: fit set to 1 by hand
        self.assertEqual(run("topics", "score", "honey", "a brand new honey topic", YOUTUBE_API_KEY=yt.KEY,
                             STUDIO_YOUTUBE_DAILY="50").returncode, 3)


class Relevance(unittest.TestCase):                                  # T025: off-topic and other-script videos
    @classmethod
    def setUpClass(cls):
        cls.yt = FakeYouTube()

    @classmethod
    def tearDownClass(cls):
        cls.yt.close()

    def fetcher(self, root):
        return topics.Fetcher.local(yt.KEY, topics.Usage(root / "u.json", 9000), topics.Cache(root / "cache"), self.yt.url)

    def test_script(self):
        self.assertFalse(topics.script_ok("🐈பயந்தாங்கொல்லி பூனை! |  Why do cats purr?🐱", "en"))
        self.assertFalse(topics.script_ok("蜜蜂如何制造蜂蜡 bees make wax", "vi"))
        self.assertTrue(topics.script_ok("Vì sao mật ong không hỏng? 🍯", "vi"))
        self.assertTrue(topics.script_ok("蜜蜂如何制造蜂蜡 bees make wax", "zh"))
        self.assertFalse(topics.script_ok("How bees make wax", "ja"))
        self.assertTrue(topics.script_ok("2024 !!! 🐝", "en"))

    def test_other_scripts_are_not_counted(self):
        root = fresh()
        r = topics.score_batch(root, "c", {"language": "en"}, ["how do bees make wax"], self.fetcher(root), fit=None, made=[])
        titles = [v["title"] for v in r["data"]["topics"][0]["raw"]["y365"]]
        self.assertFalse(any("தேனீ" in x or "蜜蜂" in x for x in titles))
        r = topics.score_batch(fresh(), "c", {"language": "zh"}, ["how do bees make wax"], self.fetcher(fresh()), fit=None, made=[])
        self.assertTrue(any("蜜蜂" in v["title"] for v in r["data"]["topics"][0]["raw"]["y365"]))

    def test_offtopic_hit_is_dropped(self):
        root = fresh()
        r = topics.score_batch(root, "c", {"language": "en"}, ["how do bees make wax"], self.fetcher(root), fit=fake_fit, made=[])
        t = r["data"]["topics"][0]
        self.assertEqual(t["raw"]["offtopic"], ["v5020"])
        self.assertNotIn("squishies", t["evidence"]["top_video"]["title"])
        self.assertEqual(t["evidence"]["top_video"]["views"], 200_000)
        self.assertEqual(t["scores"]["demand"], 5)                   # median 200k; the off-topic 10.7M does not count
        again = topics.score_raw(t["text"], t["raw"], [], t["scores"]["fit"])
        self.assertEqual(again["evidence"]["top_video"]["views"], 200_000)
        root2 = fresh()                                               # no Claude: nothing is dropped
        r = topics.score_batch(root2, "c", {"language": "en"}, ["how do bees make wax"], self.fetcher(root2), fit=None, made=[])
        self.assertIn("squishies", r["data"]["topics"][0]["evidence"]["top_video"]["title"])

    def test_cli_with_fake_claude_drops_it(self):
        root = fresh()
        samples.make_channel(root, "honey")
        env = {**os.environ, "STUDIO_ROOT": str(root), "STUDIO_YOUTUBE_URL": self.yt.url, "STUDIO_CLAUDE_BIN": str(FAKE_CLAUDE),
               "HOME": str(root), "YOUTUBE_API_KEY": yt.KEY}
        p = subprocess.run(["sh", str(REPO / "bin" / "studio"), "topics", "score", "honey", "how do bees make wax"],
                           capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("squishies", p.stdout)


class Secret(unittest.TestCase):                                     # SC-004
    def test_the_key_never_shows(self):
        y = FakeYouTube()
        try:
            root = fresh()
            samples.make_channel(root, "honey")
            env = {**os.environ, "STUDIO_ROOT": str(root), "STUDIO_YOUTUBE_URL": y.url, "STUDIO_CLAUDE_BIN": str(FAKE_CLAUDE),
                   "HOME": str(root), "YOUTUBE_API_KEY": yt.KEY}
            outs = []
            for args in (["topics", "score", "honey", "why honey never spoils", "--json"],
                         ["topics", "score", "honey", "honey [403] bad"], ["topics", "queue", "honey", "--all"],
                         ["topics", "usage"], ["topics", "take", "honey"]):
                p = subprocess.run(["sh", str(REPO / "bin" / "studio"), *args], capture_output=True, text=True, env=env)
                outs.append(p.stdout + p.stderr)
            self.assertIn(yt.KEY, y.keys)                            # the key really went to YouTube
            self.assertTrue(any("refused" in o for o in outs), outs)
            files = [f.read_text(errors="replace") for f in root.rglob("*") if f.is_file() and f.suffix in (".json", ".md")]
            for blob in outs + files:
                self.assertNotIn(yt.KEY, blob)
        finally:
            y.close()


class Queue(unittest.TestCase):
    def data(self):
        now = datetime.now(timezone.utc)
        fresh_at = topics.iso(now - timedelta(days=1))

        def t(n, verdict, total, kind, status="queued", scored=fresh_at, taken=None):
            return {"n": n, "text": f"topic {n}", "type": kind, "status": status, "verdict": verdict, "total": total,
                    "scored_at": scored, "taken_at": taken, "film": None, "scores": {}}
        return {"topics": [t(1, "HOLD", 28, "list"), t(2, "GO", 36, "comparison"), t(3, "GO", 40, "explainer"),
                           t(4, "PRIORITY", 41, "explainer"), t(5, "DROP", 20, "list", status="dropped"),
                           t(6, "GO", 35, "list", scored=topics.iso(now - timedelta(days=20)))]}

    def test_order(self):
        self.assertEqual(topics.queue(self.data()), [4, 3, 2, 6, 1])

    def test_take_skips_the_last_two_types_and_stale(self):
        d = self.data()
        now = datetime.now(timezone.utc)
        d["topics"] += [{"n": 7, "text": "old a", "type": "explainer", "status": "made", "verdict": "GO", "total": 33,
                         "taken_at": topics.iso(now - timedelta(days=3)), "scored_at": None, "film": "a"},
                        {"n": 8, "text": "old b", "type": "explainer", "status": "made", "verdict": "GO", "total": 33,
                         "taken_at": topics.iso(now - timedelta(days=2)), "scored_at": None, "film": "b"}]
        t, skipped = topics.take(d, "film-x")
        self.assertEqual(t["n"], 2)                                  # 4 and 3 are explainers like the last 2 films
        self.assertEqual([s["n"] for s in skipped], [4, 3])
        self.assertEqual((t["status"], t["film"]), ("in_progress", "film-x"))
        topics.mark_made(d, 2)
        t, skipped = topics.take(d)                                  # last two: comparison, explainer → no rule
        self.assertEqual(t["n"], 4)

    def test_stale_needs_permission(self):
        d = {"topics": [t for t in self.data()["topics"] if t["n"] == 6]}
        t, skipped = topics.take(d)
        self.assertIsNone(t)
        self.assertIn("days ago", skipped[0]["reason"])
        self.assertEqual(topics.take(d, allow_stale=True)[0]["n"], 6)

    def test_refs_and_cli_take(self):
        root = fresh()
        samples.make_channel(root, "honey")
        with self.assertRaises(topics.TopicError):
            topics.save_refs(root, "honey", ["not-a-channel"])
        topics.save_refs(root, "honey", [yt.REF_CHANNEL])
        self.assertEqual([r["id"] for r in topics.load_refs(root, "honey")], [yt.REF_CHANNEL])
        topics.save(root, "honey", self.data())
        env = {**os.environ, "STUDIO_ROOT": str(root)}
        p = subprocess.run(["sh", str(REPO / "bin" / "studio"), "topics", "take", "honey", "--film", "f1"],
                           capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("topic #4", p.stdout)
        empty = fresh()
        samples.make_channel(empty, "honey")
        p = subprocess.run(["sh", str(REPO / "bin" / "studio"), "topics", "take", "honey"], capture_output=True, text=True,
                           env={**os.environ, "STUDIO_ROOT": str(empty)})
        self.assertEqual(p.returncode, 1)

    def test_publish_marks_the_topic_made(self):
        root = fresh()
        samples.make_channel(root, "honey-facts")
        topics.save(root, "honey-facts", self.data())
        d = samples.make_publish_film(root, "made-film")
        samples.fake_thumbs(d)
        from filmcheck import channels
        channels.attach(root, d, "honey-facts", topic=4)
        pk = json.loads((d / "publish" / "pack.json").read_text())
        (d / "publish" / "pack.json").write_text(json.dumps(pk))
        data = topics.load(root, "honey-facts")
        topics.find(data, 4)["status"] = "in_progress"
        topics.save(root, "honey-facts", data)
        p = subprocess.run(["sh", str(REPO / "bin" / "studio"), "publish", str(d), "--no-draw"], capture_output=True,
                           text=True, env={**os.environ, "STUDIO_ROOT": str(root), "STUDIO_LIB": "/nonexistent"})
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(topics.find(topics.load(root, "honey-facts"), 4)["status"], "made")


if __name__ == "__main__":
    unittest.main()
