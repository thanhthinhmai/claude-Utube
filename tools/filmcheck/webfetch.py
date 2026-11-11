"""Open one web page safely and return its text (specs/010 R4). Used by `studio web fetch` locally and by the proxy.

Only http(s) on ports 80/443; the host is resolved first and private, loopback, link-local, multicast, reserved and
Docker addresses are refused, again after every redirect (at most 3). At most 2 MB and 15 s; only text-like types;
the text is cut at 8 000 characters."""
import html
import ipaddress
import re
import socket
import urllib.parse

import http.client

MAX_BYTES = 2_000_000
TIMEOUT = 15
MAX_REDIRECTS = 3
MAX_TEXT = 8_000            # text kept per page (first live run: 20 000 made the Script step too costly)
TYPES = ("text/html", "text/plain", "application/json", "application/xml", "text/xml", "application/xhtml+xml")
UA = "FilmStudio-SourceCheck/1.0"


class FetchError(Exception):
    def __init__(self, code: str, message: str, http: int):
        super().__init__(message)
        self.code, self.message, self.http = code, message, http


def resolve(host: str):
    """All addresses of a host (tests replace this)."""
    return [i[4][0] for i in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)]


def blocked(addr: str) -> bool:
    ip = ipaddress.ip_address(addr.split("%")[0])
    if ip.version == 6 and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved
            or ip.is_unspecified or not ip.is_global
            or (ip.version == 4 and ip in ipaddress.ip_network("100.64.0.0/10")))


def check_url(url: str):
    """(scheme, host, port, path, address) or FetchError."""
    u = urllib.parse.urlsplit(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise FetchError("blocked_address", "only http and https links can be opened", 400)
    port = u.port or (443 if u.scheme == "https" else 80)
    if port not in (80, 443):
        raise FetchError("blocked_address", "only ports 80 and 443 can be opened", 400)
    try:
        ipaddress.ip_address(u.hostname)
        addrs = [u.hostname]                   # an address written in the link is checked as it is
    except ValueError:
        addrs = None
    try:
        addrs = addrs or resolve(u.hostname)
    except OSError:
        raise FetchError("blocked_address", f"cannot resolve {u.hostname}", 400) from None
    if not addrs or any(blocked(a) for a in addrs):
        raise FetchError("blocked_address", f"{u.hostname} is not a public address", 400)
    path = (u.path or "/") + (f"?{u.query}" if u.query else "")
    return u.scheme, u.hostname, port, path, addrs[0]


class _Pinned(http.client.HTTPSConnection):
    """HTTPS to a checked address, with the certificate checked for the host name."""
    def __init__(self, host, addr, port, timeout):
        super().__init__(host, port, timeout=timeout)
        self._addr = addr

    def connect(self):
        sock = socket.create_connection((self._addr, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def _open(scheme, host, port, path, addr):
    if scheme == "https":
        c = _Pinned(host, addr, port, TIMEOUT)
    else:
        c = http.client.HTTPConnection(addr, port, timeout=TIMEOUT)
    c.request("GET", path, headers={"Host": host, "User-Agent": UA, "Accept": "text/html,text/plain,*/*;q=0.5"})
    return c, c.getresponse()


def text_of(body: bytes, ctype: str) -> str:
    charset = re.search(r"charset=([\w-]+)", ctype or "")
    s = body.decode(charset.group(1) if charset else "utf-8", errors="replace")
    if "html" in (ctype or "") or "xml" in (ctype or ""):
        s = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", s)
        s = re.sub(r"(?s)<!--.*?-->", " ", s)
        s = re.sub(r"(?i)<(br|p|div|li|h\d|tr)[^>]*>", "\n", s)
        s = re.sub(r"<[^>]+>", " ", s)
        s = html.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s).strip()
    return s[:MAX_TEXT]


def fetch(url: str) -> dict:
    """{status, final_url, content_type, text} or FetchError."""
    for _ in range(MAX_REDIRECTS + 1):
        scheme, host, port, path, addr = check_url(url)
        try:
            conn, r = _open(scheme, host, port, path, addr)
        except socket.timeout:
            raise FetchError("timeout", "the page took too long", 504) from None
        except OSError as e:
            raise FetchError("unreachable", f"cannot open the page: {e}", 502) from None
        try:
            if r.status in (301, 302, 303, 307, 308) and r.getheader("location"):
                url = urllib.parse.urljoin(url, r.getheader("location"))
                continue
            ctype = (r.getheader("content-type") or "").lower()
            if not any(ctype.startswith(t) for t in TYPES):
                raise FetchError("unsupported_type", f"pages of type {ctype or 'unknown'} are not opened", 415)
            n = r.getheader("content-length")
            if n and n.isdigit() and int(n) > MAX_BYTES:
                raise FetchError("too_large", "the page is larger than 2 MB", 413)
            try:
                body = r.read(MAX_BYTES + 1)
            except socket.timeout:
                raise FetchError("timeout", "the page took too long", 504) from None
            if len(body) > MAX_BYTES:
                raise FetchError("too_large", "the page is larger than 2 MB", 413)
            return {"status": r.status, "final_url": url, "content_type": ctype, "text": text_of(body, ctype)}
        finally:
            conn.close()
    raise FetchError("blocked_address", "too many redirects", 400)
