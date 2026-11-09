"""One-time links to upload and download (specs/009 research R6, FR-220) and SC-208: an agent learns a style from the
user's videos and makes a film with it, with MCP tools only."""
import time
import unittest
from urllib.parse import urlsplit

from helpers import TMP, McpAgent
from test_mcp import McpBase


class Tickets(McpBase):
    def put(self, url, data: bytes):
        c = self.s.client()
        c.cookies.clear()
        return c.put(urlsplit(url).path, content=data)                   # no cookie, no token, no X-Studio

    def test_upload_ticket(self):
        from studio import db, quotas
        video = (TMP / "good.mp4").read_bytes()
        t = self.agent.ok("start_upload", {"filename": "clip.mp4", "size_bytes": len(video)})
        self.assertIn(urlsplit(t["upload_url"]).path, t["curl"])
        self.assertTrue(t["curl"].startswith('curl -T "clip.mp4"'))
        r = self.put(t["upload_url"], video)
        self.assertEqual(r.status_code, 201, r.text)
        self.assertAlmostEqual(r.json()["seconds"], 3, delta=0.2)
        self.assertEqual(self.put(t["upload_url"], video).status_code, 404)                # once only
        self.assertTrue((self.s.data / "uploads" / self.member["id"] / f"{r.json()['upload_id']}.json").is_file())
        err, text = self.agent.call("start_upload", {"filename": "notes.txt", "size_bytes": 10})
        self.assertTrue(err)
        self.assertIn("422", text)
        quotas.update_settings({"upload_max_mb": 1})
        err, text = self.agent.call("start_upload", {"filename": "big.mp4", "size_bytes": 2 * 1024 * 1024})
        self.assertIn("413", text)
        t = self.agent.ok("start_upload", {"filename": "clip.mp4", "size_bytes": 1000})       # declared small, sent big
        self.assertEqual(self.put(t["upload_url"], video + b"\0" * (1024 * 1024)).status_code, 413)
        t = self.agent.ok("start_upload", {"filename": "clip.mp4", "size_bytes": len(video)})
        with db.tx() as con:
            con.execute("UPDATE ticket SET expires_at = '2000-01-01T00:00:00+00:00'")
        self.assertEqual(self.put(t["upload_url"], video).status_code, 404)                 # expired
        self.assertEqual(self.put("https://studio.test/api/v1/uploads/t/made-up", video).status_code, 404)
        made = [x for x in self.rest_rows(self.tok["id"]) if x["path"] == "/api/v1/uploads/tickets"]
        self.assertEqual(len(made), 5)                                     # each ticket is one row of the log

    def test_download_ticket_is_for_own_films_only(self):
        from studio import accounts, db, tokens
        other = accounts.add_user("o@x.test", "correct horse battery")
        _, osecret = tokens.create(accounts.get(other["id"]), "theirs")
        err, text = McpAgent(self.web.url, osecret).call("film_download_url", {"film": "anything"})
        self.assertIn("404", text)
        with db.read() as con:
            self.assertEqual(con.execute("SELECT count(*) FROM ticket").fetchone()[0], 0)

    def test_sc208_learn_a_style_and_use_it_with_mcp_only(self):
        a = self.agent
        err, text = a.call("learn_style", {"source": "youtube", "channel": "@some-channel", "count": 3})
        self.assertTrue(err)
        self.assertIn("rights_required", text)                                              # as on the web
        video = (TMP / "good.mp4").read_bytes()
        ids = []
        for i in range(3):
            t = a.ok("start_upload", {"filename": f"clip{i}.mp4", "size_bytes": len(video)})
            r = self.put(t["upload_url"], video)                                            # the agent's curl -T
            self.assertEqual(r.status_code, 201, r.text)
            ids.append(r.json()["upload_id"])
        job = a.ok("learn_style", {"source": "upload", "upload_ids": ids, "idempotency_key": "learn-1"})
        self.s.start()
        for n in (1, 2):                                                                    # two reviews
            j = self.wait_review(job["job_id"], n)
            rid = j["waiting_reviews"][0]["review_id"]
            review = a.ok("get_review", {"review_id": rid})
            self.assertEqual(review["kind"], f"style-{n}")
            self.assertTrue(review["summary"])
            a.ok("answer_review", {"review_id": rid, "value": "approve"})
        j = self.s.wait(job["job_id"])
        self.assertEqual(j["status"], "done", j["log"][-5:])
        slug = a.ok("get_job", {"job_id": job["job_id"]})["links"]["style"]
        self.assertIn(slug, [x["slug"] for x in a.ok("list_styles")["mine"]])
        film = a.ok("make_film", {"style": slug, "idea": "A fox learns to paint", "seconds": 20})
        self.assertEqual(self.s.wait(film["job_id"])["status"], "done")

    def wait_review(self, job_id, n, timeout=60):
        end = time.time() + timeout
        while time.time() < end:
            j = self.agent.ok("get_job", {"job_id": job_id})
            if j["status"] == "failed":
                self.fail(j["log"])
            if j["status"] == "waiting_review" and j["waiting_reviews"]:
                from studio import jobs
                if len(jobs.load(job_id)["review_ids"]) >= n:
                    return j
            time.sleep(0.2)
        self.fail(f"no review {n}")


if __name__ == "__main__":
    unittest.main()
