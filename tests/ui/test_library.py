"""Style library API (004): list, detail, poster, safety, my styles linking to the library."""
import json
import shutil
import time
import unittest

from helpers import Project, client


class Library(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.c = client()
        self.lib = self.p.dir / "lib" / "lemo-opuscar"

    def tearDown(self):
        self.p.close()

    def test_list(self):  # FR-005, FR-006, data-model
        r = self.c.get("/api/v1/library").json()
        self.assertTrue(r["installed"])
        self.assertEqual(r["version"], Project.SHA[:7])
        self.assertEqual([s["slug"] for s in r["styles"]], ["woodcut", "art-deco"])     # by num: 7, 18
        self.assertEqual(r["skipped"], 2)                                                 # broken, BadName
        self.assertEqual(r["posters"], {"have": 1, "total": 2})
        self.assertEqual(r["groups"], [{"name": "Print & Printmaking", "count": 1}, {"name": "Graphic & Type", "count": 1}])
        deco = r["styles"][1]
        self.assertEqual(set(deco), {"slug", "num", "en", "cn", "film", "line", "uses", "dur", "category", "has_poster", "github_url"})
        self.assertEqual((deco["category"], deco["uses"], deco["has_poster"]), ("Graphic & Type", ["Galas", "Invitations"], True))
        self.assertEqual(deco["github_url"], f"https://github.com/lemomo-ai/lemo-opuscar/tree/{Project.SHA}/styles/art-deco")

    def test_github_link_follows_library_version(self):  # edge case: library.lock changes
        new = "a" * 40
        (self.lib / ".git" / "HEAD").write_text(new + "\n")
        self.assertIn(f"/tree/{new}/styles/", self.c.get("/api/v1/library").json()["styles"][0]["github_url"])
        (self.p.dir / "library.lock").write_text("LIB_REPO=https://gitlab.example/x/y.git\n")
        self.assertIsNone(self.c.get("/api/v1/library").json()["styles"][0]["github_url"])

    def test_detail_and_poster(self):  # FR-009
        d = self.c.get("/api/v1/library/styles/art-deco").json()
        self.assertIn("<h1>art-deco</h1>", d["style_html"])
        self.assertNotIn("<script>", d["style_html"])
        r = self.c.get("/api/v1/library/styles/art-deco/poster")
        self.assertEqual((r.status_code, r.headers["content-type"]), (200, "image/jpeg"))
        self.assertEqual(r.headers["cache-control"], "max-age=86400")
        self.assertIn("etag", r.headers)
        self.assertEqual(self.c.get("/api/v1/library/styles/woodcut/poster").status_code, 404)    # no poster
        self.assertEqual(self.c.get("/api/v1/library/styles/nope").status_code, 404)

    def test_refuses_anything_else(self):  # FR-015, SC-006
        for path in ("/api/v1/library/styles/_template", "/api/v1/library/styles/broken",
                     "/api/v1/library/styles/BadName", "/api/v1/library/styles/BadName/poster",
                     "/api/v1/library/styles/..%2f..%2fAGENTS.md", "/api/v1/library/styles/..%2fAGENTS.md/poster",
                     "/api/v1/library/styles/a%2fb", "/api/v1/library/styles/%2e%2e/poster"):
            r = self.c.get(path)
            self.assertIn(r.status_code, (400, 404), path)
            self.assertNotIn(b"secret library file", r.content, path)
            self.assertNotIn(b"do not serve", r.content, path)

    def test_not_installed(self):  # edge case: no library yet
        shutil.rmtree(self.p.dir / "lib")
        r = self.c.get("/api/v1/library").json()
        self.assertEqual((r["installed"], r["styles"], r["posters"]), (False, [], {"have": 0, "total": 0}))
        self.assertEqual(self.c.get("/api/v1/library/styles/art-deco").status_code, 404)

    def test_66_styles_fast(self):  # SC-003
        src = self.lib / "styles" / "art-deco"
        for i in range(64):
            d = self.lib / "styles" / f"s{i:02d}"
            shutil.copytree(src, d)
            meta = json.loads((d / "style.json").read_text())
            (d / "style.json").write_text(json.dumps({**meta, "num": str(20 + i)}))
        t = time.time()
        r = self.c.get("/api/v1/library").json()
        self.assertLess(time.time() - t, 0.5)
        self.assertEqual(len(r["styles"]), 66)

    def test_ui_files_are_revalidated(self):  # an old cached app.js once hid the Library page
        for path in ("/", "/app.js", "/style.css"):
            r = self.c.get(path)
            self.assertEqual((r.status_code, r.headers.get("cache-control")), (200, "no-cache"), path)
            again = self.c.get(path, headers={"If-None-Match": r.headers["etag"]})
            self.assertEqual(again.status_code, 304, path)

    def test_my_styles_link_to_library(self):  # FR-013
        self.assertTrue(self.c.get("/api/v1/styles").json()["styles"][0]["based_on_in_library"])
        self.assertTrue(self.c.get("/api/v1/styles/demo-style").json()["based_on_in_library"])
        f = self.p.dir / "my-styles" / "demo-style" / "style.json"
        f.write_text(json.dumps({**json.loads(f.read_text()), "based_on": "khong-co"}))
        self.assertFalse(self.c.get("/api/v1/styles/demo-style").json()["based_on_in_library"])


if __name__ == "__main__":
    unittest.main()
