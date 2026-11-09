"""The MCP server at /api/mcp (specs/009 FR-219, FR-220, SC-207): a real MCP client, as an agent would use it.
Every tool is the REST API with the same token, so its rules and its log are the REST ones."""
import json
import unittest
from urllib.parse import urlsplit

from helpers import PASSWORD, W, McpAgent, Server, Studio, first_library_style


class McpBase(unittest.TestCase):
    def setUp(self):
        self.s = Studio()
        from studio import accounts, tokens
        from studio.server import create_app
        accounts.signup("boss@x.test", PASSWORD, True, role="admin", verified=True)
        self.boss = accounts.get(next(u["id"] for u in accounts.users() if u["email"] == "boss@x.test"))
        self.m = accounts.add_user("m@x.test", PASSWORD)
        self.member = accounts.get(self.m["id"])
        self.tok, self.secret = tokens.create(self.member, "agent", can_spend=True, rate_per_min=300)   # agents poll
        self.web = Server(create_app())
        self.agent = McpAgent(self.web.url, self.secret)

    def tearDown(self):
        self.web.close()
        self.s.close()

    def rest_rows(self, token_id):
        from studio import tokens
        return [x for x in tokens.log(token_id) if x["path"] != "/api/mcp"]

    def get(self, url):
        """A link the studio gave (https://studio.test/...), fetched with no cookie and no token."""
        c = self.s.client()
        c.cookies.clear()
        return c.get(urlsplit(url).path)


class Mcp(McpBase):
    def test_only_tokens_open_the_mcp_server(self):
        import httpx
        body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        h = {"accept": "application/json, text/event-stream"}
        self.assertEqual(httpx.post(self.web.url + "/api/mcp", json=body, headers=h).status_code, 401)
        c = self.s.client()                                                   # a signed-in browser: still no
        self.assertEqual(c.post("/api/v1/auth/login", json={"email": "m@x.test", "password": PASSWORD}, headers=W).status_code, 200)
        r = c.post("/api/mcp", json=body, headers={**h, **W})
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (401, "bad_token"))
        bad = McpAgent(self.web.url, "fs_" + "x" * 43)
        with self.assertRaises(Exception):
            bad.tools()

    def test_tools_follow_the_role(self):
        from studio import tokens
        member_tools = self.agent.tools()
        for t in ("list_styles", "make_film", "revise_film", "start_upload", "learn_style", "list_jobs", "get_job",
                  "get_review", "answer_review", "film_download_url", "list_operations", "describe_operation",
                  "api_request"):
            self.assertIn(t, member_tools)
        self.assertNotIn("worker_status", member_tools)
        self.assertNotIn("usage", member_tools)
        _, owner_secret = tokens.create(self.boss, "ops", role="admin")
        owner = McpAgent(self.web.url, owner_secret)
        self.assertIn("worker_status", owner.tools())
        self.assertEqual(owner.ok("worker_status")["counts"]["queued"], 0)
        self.assertIn("days", owner.ok("usage"))
        _, member_of_owner = tokens.create(self.boss, "member-level")                 # an Owner's Member token
        self.assertNotIn("usage", McpAgent(self.web.url, member_of_owner).tools())

    def test_make_film_with_idempotency_then_download_once(self):
        from studio import tokens
        style = first_library_style()
        styles = self.agent.ok("list_styles", {"query": style})
        self.assertIn(style, [x["slug"] for x in styles["library"]])
        args = {"style": style, "idea": "A small fox finds a lantern", "seconds": 20, "idempotency_key": "fox-1"}
        a = self.agent.ok("make_film", args)
        b = self.agent.ok("make_film", args)                                       # a retry: the same job
        self.assertEqual(a["job_id"], b["job_id"])
        err, text = self.agent.call("make_film", {**args, "idea": "Another idea"})
        self.assertTrue(err)
        self.assertIn("idempotency_conflict", text)
        from studio import jobs, quotas  # noqa: F401
        self.assertEqual(jobs.load(a["job_id"])["owner"], self.member["id"])       # the token's owner
        self.assertEqual(quotas.used(self.member["id"], "film"), 1)
        self.assertEqual([x["id"] for x in self.agent.ok("list_jobs")["jobs"]], [a["job_id"]])
        self.s.start()
        self.assertEqual(self.s.wait(a["job_id"])["status"], "done")
        j = self.agent.ok("get_job", {"job_id": a["job_id"]})
        self.assertEqual((j["status"], j["waiting_reviews"]), ("done", []))
        d = self.agent.ok("film_download_url", {"film": a["film"]})
        self.assertIn(urlsplit(d["download_url"]).path, d["curl"])
        r = self.get(d["download_url"])
        self.assertEqual((r.status_code, r.headers["content-type"]), (200, "video/mp4"))
        self.assertEqual(self.get(d["download_url"]).status_code, 404)              # once only
        err, text = self.agent.call("film_download_url", {"film": "not-a-film"})
        self.assertTrue(err)
        self.assertIn("404", text)
        _, reader = tokens.create(self.member, "reader")                           # no spending right
        err, text = McpAgent(self.web.url, reader).call("make_film", {**args, "idempotency_key": "x"})
        self.assertTrue(err)
        self.assertIn("spend_not_allowed", text)

    def test_api_request_keeps_the_rest_rules(self):
        ok = self.agent.ok("api_request", {"method": "GET", "path": "/api/v1/jobs"})
        self.assertEqual(ok["jobs"], [])
        for path, word in (("/api/v1/admin/usage", "403 forbidden"), ("/api/v1/me/tokens", "token_forbidden"),
                           ("/api/v1/admin/users", "token_forbidden")):
            err, text = self.agent.call("api_request", {"method": "GET", "path": path})
            self.assertTrue(err, path)
            self.assertIn(word, text, path)
        for path in ("/api/mcp", "/api/v1/../mcp", "/api/v1/films/a%2F..%2Fb", "/api/v1\\x", "https://evil.test/api/v1/x",
                     "/api/v1/jobs/..%2fme"):
            err, text = self.agent.call("api_request", {"method": "GET", "path": path})
            self.assertTrue(err, path)
            self.assertIn("/api/v1/", text, path)
        err, text = self.agent.call("api_request", {"method": "PUT", "path": "/api/v1/me", "body": {"email_notify": False}})
        self.assertIn("token_forbidden", text)
        ops = self.agent.ok("list_operations")["operations"]
        paths = {o["path"] for o in ops}
        self.assertIn("/api/v1/jobs", paths)
        self.assertFalse(any(p.startswith(("/api/v1/me/tokens", "/api/v1/admin/users", "/api/v1/admin/claude",
                                           "/api/v1/admin/tokens")) for p in paths))
        self.assertIn("requestBody", self.agent.ok("describe_operation", {"method": "post", "path": "/api/v1/jobs"})["operation"])
        spec = json.loads(self.agent.resource("film-studio://openapi"))
        self.assertNotIn("/api/v1/me/tokens", spec["paths"])

    def test_one_log_row_per_tool_call(self):                                     # SC-207
        before = len(self.rest_rows(self.tok["id"]))
        self.agent.ok("list_jobs")
        self.agent.call("api_request", {"method": "GET", "path": "/api/v1/admin/usage"})
        self.agent.call("api_request", {"method": "GET", "path": "/api/v1/../x"})   # refused before any call
        rows = self.rest_rows(self.tok["id"])
        self.assertEqual(len(rows) - before, 2)
        from studio import tokens
        self.assertFalse([x for x in tokens.log(self.tok["id"]) if x["path"] == "/api/mcp"])   # the protocol is not logged
        self.assertEqual([(x["path"], x["outcome"]) for x in rows[:2]],
                         [("/api/v1/admin/usage", "forbidden"), ("/api/v1/jobs", "allowed")])


    def test_the_protocol_does_not_eat_the_rate(self):
        """A token of 10 a minute still makes 10 tool calls in a minute (each is 3 MCP messages and one REST call);
        the 11th is refused like REST."""
        from studio import tokens
        t, secret = tokens.create(self.member, "slow", rate_per_min=10)
        agent = McpAgent(self.web.url, secret)
        for _ in range(10):
            agent.ok("list_jobs")
        err, text = agent.call("list_jobs")
        self.assertTrue(err)
        self.assertIn("429", text)
        self.assertEqual([x["outcome"] for x in tokens.log(t["id"])][:2], ["rate_limit", "allowed"])


if __name__ == "__main__":
    unittest.main()
