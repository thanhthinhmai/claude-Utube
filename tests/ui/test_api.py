import re
import time
import unittest
from pathlib import Path

from helpers import W, Project, client, jpg
from studio import jobs, reviews

CONTRACT = Path(__file__).resolve().parents[2] / "specs" / "003-studio-ui" / "contracts" / "api-v1.md"


class Api(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.c = client()

    def tearDown(self):
        self.p.close()

    # ---------- US1 ----------
    def test_jobs_list_filter_detail(self):  # FR-001..004
        a = jobs.create("learn", "a", {"set": "demo-set"})
        time.sleep(1.1)
        b = jobs.create("film", "b", {"film": "demo-film"})
        js = self.c.get("/api/v1/jobs").json()["jobs"]
        self.assertEqual([j["id"] for j in js], [b["id"], a["id"]])           # newest first
        self.assertEqual([j["id"] for j in self.c.get("/api/v1/jobs?kind=film").json()["jobs"]], [b["id"]])
        self.assertEqual(self.c.get("/api/v1/jobs?status=done").json()["jobs"], [])
        d = self.c.get(f"/api/v1/jobs/{a['id']}").json()
        self.assertEqual(d["reviews"], [])
        r = self.c.get("/api/v1/jobs/j-20990101-000000-ffff")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["error"]["code"], "not_found")

    def test_fifty_jobs_under_two_seconds(self):  # SC-008
        for i in range(50):
            jobs.create("learn", f"job {i}")
        t = time.time()
        self.assertEqual(len(self.c.get("/api/v1/jobs").json()["jobs"]), 50)
        self.assertLess(time.time() - t, 2.0)

    # ---------- US2 ----------
    def test_review_flow(self):  # FR-006..010
        j = jobs.create("learn", "demo", {"set": "demo-set"})
        r1 = reviews.create(j["id"], "style-1", "demo-set", "# Bản chất\n**10 luật**")
        pend = self.c.get("/api/v1/reviews?status=pending").json()["reviews"]
        self.assertEqual([r["id"] for r in pend], [r1["id"]])
        got = self.c.get(f"/api/v1/reviews/{r1['id']}").json()
        self.assertIn("<strong>10 luật</strong>", got["summary_html"])
        self.assertIsNone(got["decision"])
        url = f"/api/v1/reviews/{r1['id']}/decision"
        self.assertEqual(self.c.post(url, json={"value": "revise"}, headers=W).json()["error"]["code"], "note_required")
        self.assertEqual(self.c.post(url, json={"value": "stop"}, headers=W).json()["error"]["code"], "value_not_allowed")
        self.assertEqual(self.c.post(url, json={"value": "nope"}, headers=W).status_code, 422)
        ok = self.c.post(url, json={"value": "approve"}, headers=W)
        self.assertEqual(ok.status_code, 201)
        self.assertEqual(ok.json()["source"], "ui")
        again = self.c.post(url, json={"value": "approve"}, headers=W)
        self.assertEqual((again.status_code, again.json()["error"]["code"]), (409, "already_decided"))
        r2 = reviews.create(j["id"], "style-2", "demo-set", "Tay nhân vật bị che", final_round=True)
        g2 = self.c.get(f"/api/v1/reviews/{r2['id']}").json()
        self.assertEqual(g2["compare"]["luma_diff"], .03)
        self.assertTrue(g2["final_round"])
        self.assertEqual(self.c.get("/api/v1/sets/demo-set/proof/ref.jpg").status_code, 200)
        d = self.c.get(f"/api/v1/jobs/{j['id']}").json()
        self.assertEqual(len(d["reviews"]), 2)

    # ---------- US3 ----------
    def test_films(self):  # FR-012
        fs = {f["name"]: f for f in self.c.get("/api/v1/films").json()["films"]}
        self.assertTrue(fs["demo-film"]["has_video"] and fs["demo-film"]["has_subtitles"])
        self.assertTrue(fs["half-done"]["rendering"])
        f = self.c.get("/api/v1/films/demo-film").json()
        self.assertIn("Baloo", f["credits"])
        v = self.c.get("/api/v1/films/demo-film/video", headers={"Range": "bytes=0-99"})
        self.assertEqual(v.status_code, 206)
        self.assertEqual(len(v.content), 100)
        self.assertEqual(self.c.get("/api/v1/films/demo-film/poster").headers["content-type"], "image/jpeg")
        vtt = self.c.get("/api/v1/films/demo-film/subtitles.vtt").text
        self.assertTrue(vtt.startswith("WEBVTT"))
        self.assertIn("00:00:00.000 --> 00:00:01.000", vtt)
        self.assertEqual(self.c.get("/api/v1/films/half-done/video").json()["error"]["code"], "not_found")

    def test_film_tiers(self):  # specs/020 T051: the QC tiers on the film and job pages
        import json
        self.assertIsNone(self.c.get("/api/v1/films/demo-film").json()["tiers"])
        bad = {"ref": "P27.2", "rule": "cut_in_sentence", "severity": "block", "measure": 0.6, "limit": 0.0,
               "fix": "move the cut to ≥ 314.06 s", "excepted": None}
        warn = {"ref": "film", "rule": "style_luma", "severity": "warn", "measure": 0.18, "limit": "0.198–0.299"}
        (self.p.dir / "films" / "demo-film" / "checks.json").write_text(json.dumps({"tiers": {
            "plan": {"pass": False, "at": "t", "issues": [bad]},
            "shots": {"pass": True, "at": "t", "issues": [warn], "style_accept": {"reason": "night film"}}}}))
        t = self.c.get("/api/v1/films/demo-film").json()["tiers"]
        rows = {r["tier"]: r for r in t["rows"]}
        self.assertEqual([r["tier"] for r in t["rows"]], ["voice", "plan", "shots", "render", "final"])
        self.assertFalse(rows["voice"]["ran"])
        self.assertEqual((rows["plan"]["pass"], rows["plan"]["problems"]), (False, 1))
        self.assertEqual((rows["shots"]["warnings"], rows["shots"]["style_accepted"]), (1, "night film"))
        self.assertEqual(t["open"][0]["ref"], "P27.2")
        self.assertIn("tiersHtml(f.tiers)", (Path(__file__).resolve().parents[2] / "tools/studio/studio/web/app.js").read_text())

    def test_publish_pack(self):  # specs/011 contracts/api.md
        import io
        import json
        import zipfile
        pub = self.p.dir / "films" / "demo-film" / "publish"
        pub.mkdir()
        jpg(pub / "thumbnail-1.png")
        (pub / "pack.json").write_text(json.dumps({"titles": [{"angle": "curiosity", "text": "A <b> title",
                                                               "thumb": {"t": 0.5, "text": "Look"}}]}), encoding="utf-8")
        (pub / "description.md").write_text("Line one.\nLine two.\n", encoding="utf-8")
        (pub / "subtitles.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")
        (pub / "PUBLISH.md").write_text("# Publish\n", encoding="utf-8")
        (pub / "thumbs.json").write_text("[]", encoding="utf-8")
        v = self.c.get("/api/v1/films/demo-film/publish").json()
        self.assertEqual(v["titles"][0], {"angle": "curiosity", "text": "A <b> title", "thumbnail": "thumbnail-1.png",
                                          "thumb_text": "Look"})
        self.assertEqual((v["description"], v["subtitles"]), ("Line one.\nLine two.\n", "subtitles.srt"))
        self.assertNotIn("pack.json", v["files"])
        r = self.c.get("/api/v1/films/demo-film/publish/subtitles.srt")
        self.assertIn("demo-film.srt", r.headers["content-disposition"])
        for bad in ("pack.json", "thumbs.json", "..%2Fdemo-film.mp4"):
            self.assertEqual(self.c.get(f"/api/v1/films/demo-film/publish/{bad}").status_code, 404, bad)
        z = zipfile.ZipFile(io.BytesIO(self.c.get("/api/v1/films/demo-film/publish.zip").content))
        self.assertEqual(sorted(z.namelist()), ["PUBLISH.md", "demo-film.srt", "description.md", "subtitles.srt",
                                                "thumbnail-1.png"])
        self.assertEqual(self.c.get("/api/v1/films/half-done/publish").status_code, 404)

    def test_sets_and_styles(self):  # FR-013, FR-014
        self.assertEqual(self.c.get("/api/v1/sets").json()["sets"][0]["set"], "demo-set")
        s = self.c.get("/api/v1/sets/demo-set").json()
        self.assertEqual(s["summary"]["videos_measured"], 1)
        self.assertEqual(s["videos"][0]["palette"][0]["hex"], "#102030")
        self.assertEqual(self.c.get("/api/v1/sets/demo-set/sheets").json(), {"removed": False, "sheets": {"v01": ["v01_0000.jpg"]}})
        self.assertEqual(self.c.get("/api/v1/sets/demo-set/sheets/v01_0000.jpg").status_code, 200)
        import shutil
        shutil.rmtree(self.p.dir / "references" / "demo-set" / "profile" / "v01" / "sheets")
        self.assertTrue(self.c.get("/api/v1/sets/demo-set/sheets").json()["removed"])
        st = self.c.get("/api/v1/styles").json()["styles"]
        self.assertEqual((st[0]["slug"], st[0]["has_styleframe"]), ("demo-style", True))
        self.assertEqual(self.c.get("/api/v1/styles/demo-style/styleframe").status_code, 200)
        self.assertEqual(self.c.get("/api/v1/styles/nope").status_code, 404)

    # ---------- SC-007 ----------
    def test_every_api_path_versioned_documented_and_tested(self):
        spec = self.c.get("/api/v1/openapi.json").json()
        paths = set(spec["paths"])
        self.assertTrue(all(p.startswith("/api/v1/") for p in paths), paths)
        contract = CONTRACT.read_text(encoding="utf-8")
        tests = "".join(p.read_text(encoding="utf-8") for p in Path(__file__).parent.glob("test_*.py"))
        for p in paths:
            short = p[len("/api/v1"):]
            pattern = re.escape(short).replace(r"\{", "{").replace(r"\}", "}")
            pattern = re.sub(r"\{[a-z_]+\}", "[^/` ]+", pattern)
            self.assertRegex(contract, pattern, f"{p} thiếu trong contracts/api-v1.md")
            self.assertRegex(tests, r"/api/v1" + pattern, f"{p} chưa có test nào gọi")


if __name__ == "__main__":
    unittest.main()
