"""Terms page (specs/007 tasks T047): served at /terms, linked from the login page (008: no sign-up page)."""
import unittest

from helpers import REPO, OnlineProject


class Terms(unittest.TestCase):
    def test_terms_page(self):
        p = OnlineProject()
        try:
            r = p.client().get("/terms")
            self.assertEqual(r.status_code, 200)
            self.assertIn("text/html", r.headers["content-type"])
            self.assertIn("<h1>Terms of use</h1>", r.text)
            self.assertIn("deleted when learning ends", r.text)
            self.assertIn('href="/terms"', (REPO / "tools/studio/studio/web/app.js").read_text())
        finally:
            p.close()


if __name__ == "__main__":
    unittest.main()
