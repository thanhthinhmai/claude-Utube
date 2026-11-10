"""Claude accounts on the admin page, with the fake Claude Code (specs/008 T009, T016 — sign-in part)."""
import os
import stat
import threading
import time
import unittest

from helpers import FAKE_CLAUDE, PASSWORD, W, OnlineProject, sign_in

A = "/api/v1/admin/claude"


class Base(unittest.TestCase):
    """An online project with a signed-in admin and the fake Claude Code."""

    def setUp(self):
        self.p = OnlineProject()
        self.old = {k: os.environ.get(k) for k in ("STUDIO_CLAUDE_BIN", "STUDIO_CLAUDE_LOGIN_TTL", "ANTHROPIC_API_KEY")}
        os.environ["STUDIO_CLAUDE_BIN"] = str(FAKE_CLAUDE)
        os.environ.pop("ANTHROPIC_API_KEY", None)
        from studio import accounts
        accounts.signup("boss@example.com", PASSWORD, True, role="admin", verified=True)
        self.a = self.p.client()
        assert self.a.post("/api/v1/auth/login", json={"email": "boss@example.com", "password": PASSWORD},
                           headers=W).status_code == 200

    def tearDown(self):
        from studio import claude_plan
        claude_plan.cancel_login()
        for k, v in self.old.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.p.close()


class ClaudeLogin(Base):
    def test_sign_in_with_a_good_code_then_sign_out(self):
        r = self.a.get(A).json()
        self.assertEqual((r["ready"], r["api_key"], r["login"]), (False, False, None))
        self.assertEqual([(x["slot"], x["state"]) for x in r["accounts"]], [(1, "signed_out")])
        r = self.a.post(f"{A}/accounts/1/login", headers=W)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["url"].startswith("https://claude.com/cai/oauth/authorize?"))
        self.assertNotIn("\x1b", r.json()["url"])                     # the terminal hyperlink is stripped
        self.assertEqual(self.a.get(A).json()["login"]["slot"], 1)
        t = time.time()
        r = self.a.post(f"{A}/accounts/1/code", json={"code": "good-owner@x.test"}, headers=W)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertLess(time.time() - t, 10)                           # US1 #2
        self.assertEqual((r.json()["state"], r.json()["email"], r.json()["plan"]), ("signed_in", "owner@x.test", "max"))
        r = self.a.get(A).json()
        self.assertEqual((r["ready"], r["login"]), (True, None))
        d = self.p.data / "claude" / "slot-1"
        self.assertEqual(stat.S_IMODE(d.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(d.parent.stat().st_mode), 0o700)
        self.assertNotIn("tok-", self.a.get(A).text)                   # FR-104
        r = self.a.post(f"{A}/accounts/1/logout", headers=W)
        self.assertEqual((r.json()["state"], r.json()["email"]), ("signed_out", None))
        self.assertFalse((d / ".credentials.json").exists())
        self.assertFalse(self.a.get(A).json()["ready"])

    def test_bad_code_and_no_login(self):
        r = self.a.post(f"{A}/accounts/1/code", json={"code": "x"}, headers=W)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "no_login"))
        self.a.post(f"{A}/accounts/1/login", headers=W)
        r = self.a.post(f"{A}/accounts/1/code", json={"code": "wrong"}, headers=W)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (422, "bad_code"))
        self.assertEqual(self.a.get(A).json()["accounts"][0]["state"], "signed_out")
        self.assertEqual(self.a.post(f"{A}/accounts/1/login", headers=W).status_code, 200)   # can try again

    def test_unfinished_login_cancels_itself(self):
        os.environ["STUDIO_CLAUDE_LOGIN_TTL"] = "0.5"
        self.a.post(f"{A}/accounts/1/login", headers=W)
        time.sleep(1.2)
        self.assertIsNone(self.a.get(A).json()["login"])
        r = self.a.post(f"{A}/accounts/1/code", json={"code": "good-a@x.test"}, headers=W)
        self.assertEqual(r.status_code, 409)

    def test_only_one_login_waits(self):
        sign_in(self.a, 1, "one@x.test")
        self.assertEqual(self.a.post(f"{A}/accounts", headers=W).json()["slot"], 2)
        self.a.post(f"{A}/accounts/1/login", headers=W)
        self.a.post(f"{A}/accounts/2/login", headers=W)
        self.assertEqual(self.a.get(A).json()["login"]["slot"], 2)
        self.assertEqual(self.a.post(f"{A}/accounts/1/code", json={"code": "good-x@x.test"}, headers=W).status_code, 409)

    def test_add_remove_and_duplicates(self):
        sign_in(self.a, 1, "one@x.test")
        for n in (2, 3, 4, 5):
            self.assertEqual(self.a.post(f"{A}/accounts", headers=W).json()["slot"], n)
        r = self.a.post(f"{A}/accounts", headers=W)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "max_accounts"))
        sign_in(self.a, 2, "one@x.test")                               # same account twice
        os.environ["FAKE_CLAUDE_PLAN"] = "free"
        try:
            sign_in(self.a, 3, "free@x.test")
        finally:
            os.environ.pop("FAKE_CLAUDE_PLAN")
        acc = {x["slot"]: x for x in self.a.get(A).json()["accounts"]}
        self.assertEqual((acc[2]["same_as"], acc[1]["same_as"]), (1, None))
        self.assertEqual((acc[3]["plan_warning"], acc[1]["plan_warning"]), (True, False))
        from studio import claude_plan
        self.assertEqual(claude_plan.usable(), [1, 3])                 # slot 2 is a duplicate
        r = self.a.delete(f"{A}/accounts/1", headers=W)
        self.assertEqual((r.status_code, r.json()["error"]["code"]), (409, "first_account"))
        self.assertEqual(self.a.delete(f"{A}/accounts/2", headers=W).status_code, 204)
        self.assertFalse((self.p.data / "claude" / "slot-2").exists())
        self.assertEqual(self.a.delete(f"{A}/accounts/2", headers=W).status_code, 404)
        self.assertEqual(self.a.post(f"{A}/accounts", headers=W).json()["slot"], 2)       # smallest free slot

    def test_usable_order_and_rest(self):
        from studio import claude_plan, db, store
        sign_in(self.a, 1, "one@x.test")
        self.a.post(f"{A}/accounts", headers=W)
        sign_in(self.a, 2, "two@x.test")
        self.assertEqual(claude_plan.usable(), [1, 2])                 # equal: smaller slot first
        with db.tx() as con:
            con.execute("INSERT INTO call (via, tokens_in, at) VALUES ('plan:1', 500, ?)", (store.now_iso(),))
            con.execute("INSERT INTO call (via, tokens_in, at) VALUES ('plan:2', 9999, '2000-01-01T00:00:00+00:00')")
        self.assertEqual(claude_plan.usable(), [2, 1])                 # old calls fall out of the 5-hour window
        with db.tx() as con:
            con.execute("UPDATE claude_account SET state = 'limited', rest_until = ? WHERE slot = 2",
                        (claude_plan._iso(time.time() + 60),))
        self.assertEqual(claude_plan.usable(), [1])
        self.assertEqual(claude_plan.usable(time.time() + 120), [2, 1])

    def test_manual_order_and_move_to_top(self):                   # FR-120, like neb-creative-tool
        from studio import claude_plan, db, store
        sign_in(self.a, 1, "pro@x.test")
        self.a.post(f"{A}/accounts", headers=W)
        sign_in(self.a, 2, "max@x.test")
        self.a.post(f"{A}/accounts", headers=W)
        sign_in(self.a, 3, "three@x.test")
        with db.tx() as con:                                         # slot 2 used most, slot 3 least
            con.execute("INSERT INTO call (via, tokens_in, at) VALUES ('plan:2', 900, ?)", (store.now_iso(),))
            con.execute("INSERT INTO call (via, tokens_in, at) VALUES ('plan:1', 500, ?)", (store.now_iso(),))
        r = self.a.get(A).json()
        self.assertEqual((r["order"], [x["slot"] for x in r["accounts"]]), ("auto", [1, 2, 3]))
        self.assertEqual(claude_plan.usable(), [3, 1, 2])            # auto: least used first, as before
        r = self.a.post(f"{A}/accounts/2/top", headers=W).json()       # the Max account to the top
        self.assertEqual((r["order"], [x["slot"] for x in r["accounts"]]), ("manual", [2, 1, 3]))
        self.assertEqual(claude_plan.usable(), [2, 1, 3])            # manual: top first, though used most
        claude_plan.mark_limited(2, time.time() + 600)
        self.assertEqual(claude_plan.usable(), [1, 3])               # at its limit: the next one
        r = self.a.put(f"{A}/order", json={"mode": "auto"}, headers=W).json()
        self.assertEqual((r["order"], [x["slot"] for x in r["accounts"]]), ("auto", [2, 1, 3]))   # the list keeps its order
        self.assertEqual(claude_plan.usable(), [3, 1])
        self.assertEqual(self.a.put(f"{A}/order", json={"mode": "random"}, headers=W).status_code, 422)
        self.assertEqual(self.a.post(f"{A}/accounts/5/top", headers=W).status_code, 404)
        self.assertEqual(self.a.put("/api/v1/admin/settings", json={"claude_order": "x"}, headers=W).status_code, 422)
        self.a.post(f"{A}/accounts", headers=W)
        self.assertEqual([x["slot"] for x in self.a.get(A).json()["accounts"]][-1], 4)          # a new account goes last
        c = self.p.signup_verified("m@x.test")
        self.assertEqual(c.post(f"{A}/accounts/1/top", headers=W).status_code, 403)
        self.assertEqual(c.put(f"{A}/order", json={"mode": "auto"}, headers=W).status_code, 403)

    def test_backoff_without_a_reset_time(self):
        from studio import claude_plan
        sign_in(self.a, 1, "one@x.test")
        rests = []
        for _ in range(10):
            until = claude_plan.mark_limited(1)
            rests.append(round(claude_plan._ts(until) - time.time()))
        for got, want in zip(rests, [2, 4, 8, 16, 32, 64, 128, 256, 300, 300]):   # never more than 5 minutes
            self.assertAlmostEqual(got, want, delta=1)              # times are stored to the second
        claude_plan.mark_ok(1)
        acc = self.a.get(A).json()["accounts"][0]
        self.assertEqual((acc["state"], acc["rest_until"]), ("signed_in", None))
        self.assertAlmostEqual(claude_plan._ts(claude_plan.mark_limited(1)) - time.time(), 2, delta=1)   # starts over

    def test_status_notices_a_lost_sign_in(self):
        sign_in(self.a, 1, "one@x.test")
        (self.p.data / "claude" / "slot-1" / ".credentials.json").unlink()
        r = self.a.post(f"{A}/refresh", headers=W).json()
        self.assertEqual(r["accounts"][0]["state"], "needs_signin")
        self.assertFalse(r["ready"])
        self.a.post(f"{A}/refresh", headers=W)                         # checked again: still one mail (FR-109)
        mails = [p.read_text() for p in self.p.flush_mail() if "needs to sign in again" in p.read_text()]
        self.assertEqual(len(mails), 1)
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-x"
        self.assertTrue(self.a.get(A).json()["ready"])                # the fallback key alone is enough (FR-110)

    def test_commands_on_one_slot_never_overlap(self):
        from studio import claude_plan
        os.environ["FAKE_CLAUDE_SLEEP"] = "0.3"
        spans = []

        def go():
            t = time.time()
            claude_plan.run(1, ["auth", "status", "--json"])
            spans.append((t, time.time()))
        try:
            ts = [threading.Thread(target=go) for _ in range(3)]
            t0 = time.time()
            [t.start() for t in ts]
            [t.join() for t in ts]
        finally:
            os.environ.pop("FAKE_CLAUDE_SLEEP")
        self.assertGreaterEqual(time.time() - t0, 0.85)                # three runs of 0.3 s, one after another

    def test_members_are_kept_out(self):
        c = self.p.signup_verified("cust@example.com")
        for method, path in (("get", ""), ("post", "/refresh"), ("post", "/accounts"), ("delete", "/accounts/2"),
                             ("post", "/accounts/1/login"), ("post", "/accounts/1/code"), ("post", "/accounts/1/logout")):
            kw = {"headers": W}
            if path.endswith("/code"):
                kw["json"] = {"code": "x"}
            r = getattr(c, method)(A + path, **kw)
            self.assertEqual(r.status_code, 403, path)


NODE_MODULES = __import__("helpers").REPO / "lib" / "lemo-opuscar" / "node_modules"


@unittest.skipUnless(__import__("shutil").which("node") and (NODE_MODULES / "playwright-core").is_dir(),
                     "needs node and playwright-core (sh bin/studio setup)")
class ClaudeLoginBrowser(Base):
    """Sign in, add, remove and sign out on the Claude accounts page, at phone width."""

    def test_claude_page_in_a_browser(self):
        import json
        import subprocess
        from pathlib import Path
        from helpers import Server
        from studio.server import create_app
        web = Server(create_app())
        try:
            r = subprocess.run(["node", str(Path(__file__).with_name("browser_claude.cjs")), web.url, "boss@example.com",
                                PASSWORD, os.environ.get("CLAUDE_PAGE_SHOT", "")],
                               capture_output=True, text=True, timeout=90, env={**os.environ, "NODE_PATH": str(NODE_MODULES)})
            if r.returncode == 77:
                self.skipTest("cannot start a browser")
            self.assertEqual(r.returncode, 0, r.stderr)
            res = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertEqual(res["errors"], [])
            self.assertLessEqual(res["wide"], 360)                    # no sideways scrolling on a phone
        finally:
            web.close()


if __name__ == "__main__":
    unittest.main()
