"""SC-204: after making and using tokens (REST, MCP, tickets, a job run by the worker), the full token is nowhere:
not in any file of the data folder (the database and its WAL, job folders, logs), not in any log record, not in any
answer of the token lists, the worker tab or the OpenAPI."""
import logging
import unittest

from helpers import PASSWORD, TMP, W, McpAgent, Server, Studio, first_library_style


class Capture(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.lines = []

    def emit(self, record):
        try:
            self.lines.append(record.getMessage() + " " + str(record.args or ""))
        except Exception:                                   # noqa: BLE001
            self.lines.append(str(record.msg))


class TokenSecrets(unittest.TestCase):
    def setUp(self):
        self.s = Studio()
        self.log = Capture()
        root = logging.getLogger()
        self.old_level = root.level
        root.addHandler(self.log)
        root.setLevel(logging.DEBUG)
        for name in ("httpx", "mcp", "uvicorn", "uvicorn.access", "uvicorn.error"):
            logging.getLogger(name).setLevel(logging.DEBUG)

    def tearDown(self):
        root = logging.getLogger()
        root.removeHandler(self.log)
        root.setLevel(self.old_level)
        self.s.close()

    def test_the_full_token_is_never_kept_or_shown(self):
        from studio import accounts
        from studio.server import create_app
        accounts.signup("boss@x.test", PASSWORD, True, role="admin", verified=True)
        accounts.add_user("m@x.test", PASSWORD)
        member, boss = self.s.client(), self.s.client()
        member.post("/api/v1/auth/login", json={"email": "m@x.test", "password": PASSWORD}, headers=W)
        boss.post("/api/v1/auth/login", json={"email": "boss@x.test", "password": PASSWORD}, headers=W)
        made = member.post("/api/v1/me/tokens", json={"name": "agent", "can_spend": True, "rate_per_min": 300}, headers=W)
        self.assertEqual(made.status_code, 201)
        secret = made.json()["secret"]
        owner_secret = boss.post("/api/v1/me/tokens", json={"name": "ops", "role": "admin"}, headers=W).json()["secret"]
        secrets = (secret, owner_secret)

        # use them: REST, MCP (a film made, run by the worker, and downloaded), an upload by ticket
        web = Server(create_app())
        try:
            agent = McpAgent(web.url, secret)
            job = agent.ok("make_film", {"style": first_library_style(), "idea": "A fox", "seconds": 20})
            self.s.start()
            self.assertEqual(self.s.wait(job["job_id"])["status"], "done")
            link = agent.ok("film_download_url", {"film": job["film"]})["download_url"]
            plain = self.s.client()
            plain.cookies.clear()
            self.assertEqual(plain.get(link.replace("https://studio.test", "")).status_code, 200)
            video = (TMP / "good.mp4").read_bytes()
            up = agent.ok("start_upload", {"filename": "c.mp4", "size_bytes": len(video)})["upload_url"]
            self.assertEqual(plain.put(up.replace("https://studio.test", ""), content=video).status_code, 201)
            McpAgent(web.url, owner_secret).ok("worker_status")
            agent.call("api_request", {"method": "GET", "path": "/api/v1/admin/usage"})
            answers = [member.get("/api/v1/me/tokens").text, boss.get("/api/v1/admin/tokens").text,
                       boss.get("/api/v1/admin/worker").text, member.get("/api/v1/openapi.json").text,
                       member.get("/api/v1/me").text, agent.resource("film-studio://openapi")]
            for tid in (made.json()["token"]["id"],):
                answers.append(member.get(f"/api/v1/me/tokens/{tid}/log").text)
                answers.append(boss.get(f"/api/v1/admin/tokens/{tid}/log").text)
        finally:
            web.close()

        for s in secrets:
            hidden = s[8:]                                     # the prefix (first 8) is shown on purpose
            for text in answers:
                self.assertNotIn(hidden, text)
            for line in self.log.lines:
                self.assertNotIn(hidden, line)
            for f in self.s.data.rglob("*"):
                if f.is_file():
                    self.assertNotIn(hidden.encode(), f.read_bytes(), str(f))
        self.assertGreater(len(self.log.lines), 0)            # the capture did see the log


if __name__ == "__main__":
    unittest.main()
