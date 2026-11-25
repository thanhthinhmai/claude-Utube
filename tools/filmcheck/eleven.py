"""ElevenLabs voices (specs/036 research R1, R3): the account, its voices, and one line read with per-character times.

Two ways in, never both:
- inside an app job (STUDIO_JOB_TOKEN and STUDIO_PROXY set): through the studio proxy, which alone holds the key
  (`POST /internal/tts/elevenlabs/…`, contracts/http.md); the job never sees the key;
- from the command line: ELEVENLABS_API_KEY / ELEVENLABS_MODEL from the environment, else from `.env` at the root.
The key is never printed, logged or written anywhere by this module. STUDIO_ELEVEN_URL points tests at a fake."""
import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.elevenlabs.io"
DEFAULT_MODEL = "eleven_multilingual_v2"
RATE = 24000                    # pcm_24000: the same 24 kHz mono as Kokoro
TIMEOUT = 60
MAX_CHARS = 1000                # one line; longer is refused (contracts/http.md)
_cache = {}                     # voices, 10 minutes (research R4)


class ElevenError(Exception):
    """code: no_key | invalid_key | quota | too_long | network | api."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


# ---------- where the key comes from ----------
def load_env(root: Path) -> dict:
    """KEY=VALUE lines of <root>/.env (quotes stripped, # comments skipped); {} when there is no file."""
    out = {}
    try:
        text = (Path(root) / ".env").read_text(encoding="utf-8")
    except OSError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip()
        if k.startswith("export "):
            k = k[7:].strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        elif " #" in v or "\t#" in v:                # an unquoted value ends at an inline comment
            v = v.replace("\t#", " #").split(" #", 1)[0].rstrip()
        out[k] = v
    return out


def root() -> Path:
    return Path(os.environ.get("STUDIO_ROOT") or Path(__file__).resolve().parents[2])


def setting(name: str, default=None):
    """The environment wins over .env."""
    v = os.environ.get(name)
    if v:
        return v
    return load_env(root()).get(name) or default


def via_proxy() -> bool:
    return bool(os.environ.get("STUDIO_JOB_TOKEN") and os.environ.get("STUDIO_PROXY"))


def model() -> str:
    return setting("ELEVENLABS_MODEL", DEFAULT_MODEL)


def _key() -> str:
    k = setting("ELEVENLABS_API_KEY")
    if not k:
        raise ElevenError("no_key", "no ElevenLabs key: set ELEVENLABS_API_KEY in .env or in the app's Settings")
    return k


def redact(text: str, key: str) -> str:
    return text.replace(key, "…" + key[-4:]) if key else text


# ---------- raw calls ----------
def _error(status: int, body: bytes, key: str = "") -> ElevenError:
    try:
        d = json.loads(body or b"{}")
    except ValueError:
        d = {}
    det = d.get("detail") if isinstance(d, dict) else None
    st = (det.get("status") if isinstance(det, dict) else "") or ""
    msg = (det.get("message") if isinstance(det, dict) else det if isinstance(det, str) else "") or f"HTTP {status}"
    msg = redact(str(msg), key)
    if st == "quota_exceeded" or status == 402:
        return ElevenError("quota", "not enough ElevenLabs characters left: " + msg)
    if status == 401 or st in ("invalid_api_key", "missing_permissions"):
        return ElevenError("invalid_key", "the ElevenLabs key does not work: " + msg)
    if status == 429:                      # too many lines at once for the plan, or ElevenLabs is busy: try again
        return ElevenError("busy", f"ElevenLabs is busy: {msg}")
    return ElevenError("api", f"ElevenLabs answered {status}: {msg}")


def direct(method: str, path: str, body=None, key: str = None, query: dict = None) -> dict:
    """One call to ElevenLabs with a key (the proxy uses this too). Returns the JSON answer."""
    return direct_with_headers(method, path, body, key, query)[0]


def direct_with_headers(method: str, path: str, body=None, key: str = None, query: dict = None):
    """(JSON answer, response headers) of one call."""
    key = key or _key()
    url = os.environ.get("STUDIO_ELEVEN_URL", API).rstrip("/") + path
    if query:
        url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"xi-api-key": key, "content-type": "application/json", "accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read() or b"{}"), r.headers
    except urllib.error.HTTPError as e:
        raise _error(e.code, e.read(), key) from None
    except (urllib.error.URLError, OSError) as e:
        raise ElevenError("network", f"ElevenLabs cannot be reached: {redact(str(e), key)}") from None


def _proxy(what: str, body: dict) -> dict:
    base = os.environ["STUDIO_PROXY"].rstrip("/")
    req = urllib.request.Request(f"{base}/internal/tts/elevenlabs/{what}", data=json.dumps(body).encode(), method="POST",
                                 headers={"content-type": "application/json",
                                          "authorization": f"Bearer {os.environ['STUDIO_JOB_TOKEN']}"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT + 10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read()).get("error") or {}
        except ValueError:
            err = {}
        if isinstance(err, str):
            err = {"code": err}
        raise ElevenError(err.get("code") or "api", err.get("message") or f"the studio answered {e.code}") from None
    except (urllib.error.URLError, OSError) as e:
        raise ElevenError("network", f"the studio proxy cannot be reached: {e}") from None


# ---------- what the studio uses ----------
def public_subscription(d: dict) -> dict:
    limit, used = int(d.get("character_limit") or 0), int(d.get("character_count") or 0)
    return {"tier": d.get("tier"), "limit": limit, "used": used, "left": max(0, limit - used),
            "reset_at": d.get("next_character_count_reset_unix")}


def subscription(key: str = None) -> dict:
    """{tier, limit, used, left, reset_at}."""
    if via_proxy() and not key:
        return _proxy("subscription", {})
    return public_subscription(direct("GET", "/v1/user/subscription", key=key))


def public_voice(v: dict) -> dict:
    lab = v.get("labels") or {}
    return {"id": "el:" + v["voice_id"], "provider": "elevenlabs", "name": v.get("name") or v["voice_id"],
            "gender": lab.get("gender"), "age": lab.get("age"), "accent": lab.get("accent"),
            "desc": lab.get("description") or v.get("description") or lab.get("use_case"),
            # a clone the account made itself; voices added from the shared library are "library", not clones
            "cloned": v.get("category") in ("cloned", "professional") and v.get("is_owner") is not False,
            "library": bool((v.get("sharing") or {}).get("original_voice_id")) and v.get("is_owner") is False,
            "category": v.get("category"),
            "preview": v.get("preview_url")}


def list_voices(key: str = None) -> list:
    """Every voice of the account (all pages of /v2/voices), as voicecat rows."""
    out, token = [], None
    for _ in range(50):
        d = direct("GET", "/v2/voices", key=key, query={"page_size": 100, "next_page_token": token})
        out += [public_voice(v) for v in d.get("voices") or [] if v.get("voice_id")]
        token = d.get("next_page_token")
        if not d.get("has_more") or not token:
            break
    return out


def voices(refresh: bool = False) -> list:
    hit = _cache.get("voices")
    if hit and not refresh and time.time() - hit[0] < 600:
        return hit[1]
    rows = _proxy("voices", {"refresh": refresh})["voices"] if via_proxy() else list_voices()
    _cache["voices"] = (time.time(), rows)
    return rows


def speak_body(text: str, model_id: str, settings: dict) -> dict:
    vs = {k: settings[k] for k in ("stability", "similarity_boost", "style", "use_speaker_boost") if k in settings}
    if settings.get("speed") is not None:
        vs["speed"] = max(0.7, min(1.2, float(settings["speed"])))
    body = {"text": text, "model_id": model_id}
    if vs:
        body["voice_settings"] = vs
    return body


def direct_speak(voice_id: str, text: str, model_id: str = None, settings: dict = None, key: str = None) -> dict:
    """{audio_base64, alignment, chars} for one line (the proxy calls this with the studio's key)."""
    if len(text) > MAX_CHARS:
        raise ElevenError("too_long", f"a line may have at most {MAX_CHARS} characters")
    d, h = direct_with_headers("POST", f"/v1/text-to-speech/{urllib.parse.quote(voice_id)}/with-timestamps",
                               speak_body(text, model_id or model(), settings or {}), key=key,
                               query={"output_format": f"pcm_{RATE}"})
    try:                                   # what the plan really charged (often less than the letters): the
        chars = int(h.get("character-cost"))   # estimate of `voice make` stays the ceiling
    except (TypeError, ValueError):
        chars = len(text)
    return {"audio_base64": d.get("audio_base64") or "", "alignment": d.get("alignment") or d.get("normalized_alignment"),
            "chars": chars}


def speak(voice_id: str, text: str, model_id: str = None, settings: dict = None):
    """(pcm16 bytes at 24 kHz mono, alignment or None, characters charged) for one line."""
    voice_id = voice_id[3:] if voice_id.startswith("el:") else voice_id
    body = {"voice_id": voice_id, "text": text, "model_id": model_id or model(), "voice_settings": settings or {}}
    d = _proxy("speak", body) if via_proxy() else direct_speak(voice_id, text, body["model_id"], settings)
    return base64.b64decode(d.get("audio_base64") or ""), d.get("alignment"), int(d.get("chars") or len(text))


def write_wav(path: Path, pcm: bytes, rate: int = RATE) -> float:
    """pcm16 mono → a .wav; returns the length in seconds."""
    import wave
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return len(pcm) / 2 / rate
