"""The studio's MCP server at /api/mcp (specs/009 FR-219, FR-220, contracts/mcp.md, research R5, R6).

Like neb-creative-tool: Streamable HTTP, stateless, JSON answers; a fresh server per request. Every tool is one call
to the studio's own REST API, in process, with the same API token the agent sent, so permissions, credits, rate,
content check and errors are exactly the REST ones and each tool call is one row of the token's log.
Tools follow the token's effective role: a Member token does not see the Owner tools.

Note: the session manager needs the low-level server, which mcp 2.3.0 only exposes as `_lowlevel_server`
(the version is pinned in tools/requirements-online.txt; tests/online/test_mcp.py fails if it changes)."""
import html
import json
import logging
import re
from typing import List, Optional

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError        # its message reaches the agent; other errors do not
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings

for _name in ("httpx", "mcp"):                     # one line per tool call would fill the web log; keep warnings only
    logging.getLogger(_name).setLevel(logging.WARNING)

INSTRUCTIONS = """Film Studio makes short films and learns visual styles. Every action uses the user's account.
- Ask the user before anything that uses a film or learn credit (make_film, revise_film, learn_style).
- Send an idempotency_key (any unique text) when you make a job, and the same one if you retry.
- Films take many minutes: call get_job again later instead of waiting.
- When a job waits for an answer (a question, a treatment, a style draft), show it to the user with get_review and
  answer with answer_review.
- To learn from the user's own videos: start_upload for each file, run the curl command it gives, then learn_style
  with the upload ids. To give the user a finished film: film_download_url, then run its curl command."""


def safe_path(path: str) -> str:
    """Only the studio's own API under /api/v1/; never the MCP server itself, no dot segments, no encoded slashes."""
    p = (path or "").strip()
    if not p.startswith("/api/v1/") or ".." in p or re.search(r"%2f|%5c", p, re.I) or "\\" in p:
        raise ToolError("path must be under /api/v1/ (no '..', no encoded slashes)")
    return p


def text_of(html_text: str) -> str:
    """Plain text of a review's summary (the API gives HTML), one block per line."""
    t = re.sub(r"<(br|/p|/li|/h\d|/tr)\s*/?>", "\n", html_text or "", flags=re.I)
    t = re.sub(r"<li[^>]*>", "- ", t, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def build(app, auth: str, role: str, ip: str = "127.0.0.1") -> MCPServer:
    """A server for one request: its tools call the REST API with the caller's own token."""
    server = MCPServer(name="film-studio", instructions=INSTRUCTIONS)

    async def api(method: str, path: str, body=None, params=None, idempotency_key: str = None, raw: bool = False):
        headers = {"Authorization": auth}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        # client=(ip, 0): the inner REST call logs the agent's IP, not 127.0.0.1
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=(ip, 0)), base_url="http://studio.mcp",
                                     timeout=600) as c:
            r = await c.request(method, path, json=body, params=params, headers=headers)
        ctype = r.headers.get("content-type", "")
        if r.status_code >= 400:
            try:
                e = r.json()["error"]
                raise ToolError(f"{r.status_code} {e.get('code')}: {e.get('message')}"
                                + (f" ({e['reason']})" if e.get("reason") else ""))
            except (ValueError, KeyError, TypeError):
                raise ToolError(f"{r.status_code}: {r.text[:300]}") from None
        if raw:
            return r
        if "json" in ctype:
            return r.json() if r.content else {}
        if ctype.startswith("text/"):
            return {"text": r.text[:20000]}
        return {"note": "Binary content, not included. Use film_download_url to get a film.",
                "content_type": ctype, "bytes": len(r.content)}

    # ---------- tools for every token ----------
    @server.tool(description="List styles to make films with: the library and the user's own learned styles.")
    async def list_styles(query: str = "") -> dict:
        lib = await api("GET", "/api/v1/library")
        mine = await api("GET", "/api/v1/styles")
        q = query.lower().strip()
        keep = lambda s: not q or q in json.dumps(s).lower()          # noqa: E731
        return {"library": [{"slug": s["slug"], "name": s.get("en"), "category": s.get("category"), "about": s.get("line")}
                            for s in lib.get("styles", []) if keep(s)],
                "mine": [{"slug": s.get("slug"), "name": s.get("en") or s.get("name")} for s in mine.get("styles", []) if keep(s)]}

    @server.tool(description="Make a film (uses one film credit: ask the user first). Returns the job; check it with get_job.")
    async def make_film(style: str, idea: str, seconds: int, review_treatment: bool = False,
                        idempotency_key: Optional[str] = None) -> dict:
        j = await api("POST", "/api/v1/jobs", {"kind": "film", "style": style, "idea": idea, "seconds": seconds,
                                               "review_treatment": review_treatment}, idempotency_key=idempotency_key)
        return {"job_id": j["id"], "status": j["status"], "film": j.get("links", {}).get("film")}

    @server.tool(description="Make a changed version of a finished film from a note (uses one film credit: ask first).")
    async def revise_film(film: str, note: str, idempotency_key: Optional[str] = None) -> dict:
        j = await api("POST", "/api/v1/jobs", {"kind": "film", "revise_of": film, "note": note},
                      idempotency_key=idempotency_key)
        return {"job_id": j["id"], "status": j["status"], "film": j.get("links", {}).get("film")}

    @server.tool(description="Get a one-time link (30 minutes) to upload one of the user's videos for learning a style. "
                             "Run the returned curl command with the real file path; it prints the upload_id.")
    async def start_upload(filename: str, size_bytes: int) -> dict:
        return await api("POST", "/api/v1/uploads/tickets", {"filename": filename, "size_bytes": size_bytes})

    @server.tool(description="Learn a visual style (uses one learn credit: ask first). source='youtube' with a channel URL "
                             "and rights_confirmed=true (the user confirms the right to use its videos for style study), "
                             "or source='upload' with upload_ids from start_upload.")
    async def learn_style(source: str, channel: Optional[str] = None, count: Optional[int] = None,
                          upload_ids: Optional[List[str]] = None, rights_confirmed: bool = False,
                          idempotency_key: Optional[str] = None) -> dict:
        body = {"kind": "learn", "source": source, "channel": channel, "count": count, "uploads": upload_ids,
                "rights_confirmed": rights_confirmed}
        j = await api("POST", "/api/v1/jobs", {k: v for k, v in body.items() if v is not None},
                      idempotency_key=idempotency_key)
        return {"job_id": j["id"], "status": j["status"]}

    @server.tool(description="List the user's jobs (films and learned styles), newest first.")
    async def list_jobs(status: str = "") -> dict:
        r = await api("GET", "/api/v1/jobs", params={"status": status} if status else None)
        return {"jobs": [{"id": j["id"], "kind": j["kind"], "name": j["name"], "status": j["status"], "step": j.get("step"),
                          "error": j.get("error"), "film": j.get("links", {}).get("film")} for j in r.get("jobs", [])]}

    @server.tool(description="One job: status, step, last log lines, reviews waiting for an answer, the film when done.")
    async def get_job(job_id: str) -> dict:
        j = await api("GET", f"/api/v1/jobs/{job_id}")
        waiting = [{"review_id": r["id"], "kind": r["kind"]} for r in j.get("reviews", []) if not r.get("decision")]
        return {"id": j["id"], "kind": j["kind"], "name": j["name"], "status": j["status"], "step": j.get("step"),
                "error": j.get("error"), "log": [x["line"] for x in j.get("log", [])[-10:]], "waiting_reviews": waiting,
                "links": j.get("links"), "tokens": j.get("tokens")}

    @server.tool(description="What a review asks (Markdown) and the answers allowed.")
    async def get_review(review_id: str) -> dict:
        r = await api("GET", f"/api/v1/reviews/{review_id}")
        if r["kind"] == "question":
            allowed = ["approve (note = the user's answer)"]
        else:                                                          # the rules of reviews.decide
            allowed = ["approve", "revise (note = the changes wanted, 3+ characters)"]
            if r.get("final_round"):
                allowed += ["accept_anyway", "stop"]
        return {"id": r["id"], "kind": r["kind"], "job_id": r.get("job_id"), "summary": text_of(r.get("summary_html")),
                "compare": r.get("compare"), "allowed": allowed, "decision": r.get("decision")}

    @server.tool(description="Answer a review: value is one of the allowed answers (e.g. approve, revise, stop); "
                             "note carries the user's words (an answer to a question, or the changes wanted).")
    async def answer_review(review_id: str, value: str, note: str = "") -> dict:
        return await api("POST", f"/api/v1/reviews/{review_id}/decision", {"value": value, "note": note or None})

    @server.tool(description="A one-time link (30 minutes) to download a finished film; run the returned curl command.")
    async def film_download_url(film: str) -> dict:
        return await api("POST", f"/api/v1/films/{film}/tickets")

    # ---------- general tools, like neb ----------
    def spec() -> dict:
        return app.openapi()

    @server.tool(description="List the studio's API operations usable with this token (method, path, summary).")
    async def list_operations(query: str = "") -> dict:
        q = query.lower().strip()
        ops = [{"method": m.upper(), "path": p, "summary": op.get("summary", "")}
               for p, item in spec().get("paths", {}).items() for m, op in item.items()]
        return {"operations": [o for o in ops if not q or q in json.dumps(o).lower()]}

    @server.tool(description="Parameters, request body and responses of one API operation.")
    async def describe_operation(method: str, path: str) -> dict:
        op = spec().get("paths", {}).get(path, {}).get(method.lower())
        if not op:
            raise ToolError("no such operation; see list_operations")
        return {"method": method.upper(), "path": path, "operation": op,
                "schemas": spec().get("components", {}).get("schemas", {})}

    @server.tool(description="Call any studio API under /api/v1/ with this token (same rules as the REST API).")
    async def api_request(method: str, path: str, query: Optional[dict] = None, body: Optional[dict] = None,
                          idempotency_key: Optional[str] = None) -> dict:
        return await api(method.upper(), safe_path(path), body, query, idempotency_key)

    @server.resource("film-studio://openapi", name="openapi", description="The studio's OpenAPI, as usable with a token",
                     mime_type="application/json")
    def openapi_resource() -> str:
        return json.dumps(spec())

    # ---------- Owner tools (read only) ----------
    if role == "admin":
        @server.tool(description="Owner: the worker processes, the queue counts and the latest jobs of everyone.")
        async def worker_status() -> dict:
            return await api("GET", "/api/v1/admin/worker")

        @server.tool(description="Owner: Claude calls and tokens per day, per member and per Claude account.")
        async def usage(start: str = "", end: str = "") -> dict:
            params = {k: v for k, v in (("from", start), ("to", end)) if v}
            return await api("GET", "/api/v1/admin/usage", params=params or None)
    return server


class Endpoint:
    """The ASGI app routed at /api/mcp. online_guard has already checked the token (cookies are refused there).
    A class, not a function, so Starlette's Route passes it the raw ASGI call."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        account = (scope.get("state") or {}).get("account") or {}
        headers = dict((k.decode().lower(), v.decode()) for k, v in scope.get("headers", []))
        ip = (scope.get("client") or ("127.0.0.1", 0))[0]
        server = build(self.app, headers.get("authorization", ""), account.get("role", "customer"), ip)
        manager = StreamableHTTPSessionManager(
            app=server._lowlevel_server, json_response=True, stateless=True,
            security_settings=TransportSecuritySettings(enable_dns_rebinding_protection=False))
        async with manager.run():
            await manager.handle_request(scope, receive, send)
