"""Who says each line and with which voice (specs/036 US2, research R5/R6, data-model).

Each line of lines.json may carry `speaker` (absent or "narrator" = the narrator), `role` for a side part, `emotion`
and `fx`. `resolve()` turns them into a voice setting per line, in this order:
  0. a `voice` written on the line by hand wins (films before 036 keep reading exactly as before);
  1. narrator → the film's `film.json → narrator`, else the channel's narrator (`channels/<slug>/VOICE.json`, else the
     channel's old `voice`/`speed`), else the old default (no voice: the library picks);
  2. a speaker in `film.json → voices` (or a cast character, specs/034, when cast/cast.json has one with a voice);
  3. a speaker with a `role` → the channel's voices for that role; the same side part keeps one voice for the whole
     film, and two speakers of one scene (`para`) never share a voice (key: provider, voice, pitch, speed);
  4. else an error naming the speaker.
The table is written to voices/speakers.json (the "fallback" entry of `voice make --provider kokoro` is kept)."""
import json
import re
from pathlib import Path

ROLES = ("boy", "girl", "woman", "man", "old_man", "old_woman")
EMOTIONS = ("neutral", "whisper", "shout", "laugh", "cry", "sarcastic")
FXS = ("none", "phone", "wall", "radio", "hall")
SPEAKER = re.compile(r"^[a-z0-9-]{1,32}$")
# research R6, changed 2026-11-25 after a listening test (own voices sound like other people, a pitched narrator does
# not): two Kokoro voices of their own per role, the second for a scene where the first is taken; the narrator pitched
# for the part is the last choice
DEFAULT_ROLES = {"boy": [{"mode": "own", "voice": "am_puck", "pitch": 3, "speed": 1.05},
                         {"mode": "own", "voice": "am_echo", "pitch": 3, "speed": 1.05},
                         {"mode": "narrator", "pitch": 4, "speed": 1.08}],
                 "girl": [{"mode": "own", "voice": "af_sky", "pitch": 2, "speed": 1.05},
                          {"mode": "own", "voice": "af_nova", "pitch": 2, "speed": 1.05},
                          {"mode": "narrator", "pitch": 5, "speed": 1.08}],
                 "woman": [{"mode": "own", "voice": "af_sarah"}, {"mode": "own", "voice": "af_nicole"},
                           {"mode": "narrator", "pitch": 3, "speed": 1.0}],
                 "man": [{"mode": "own", "voice": "am_onyx", "speed": 0.95}, {"mode": "own", "voice": "am_eric"},
                         {"mode": "narrator", "pitch": -2, "speed": 0.95}],
                 "old_man": [{"mode": "own", "voice": "bm_lewis", "pitch": -2, "speed": 0.9},
                             {"mode": "own", "voice": "bm_daniel", "pitch": -2, "speed": 0.9},
                             {"mode": "narrator", "pitch": -3, "speed": 0.9}],
                 "old_woman": [{"mode": "own", "voice": "bf_isabella", "speed": 0.92},
                               {"mode": "own", "voice": "bf_alice", "speed": 0.92},
                               {"mode": "narrator", "pitch": 2, "speed": 0.9}]}
SETTING_FIELDS = ("mode", "voice", "pitch", "formant", "speed", "emotion", "el", "cloned_ok")


class SpeakerError(Exception):
    pass


def _read(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(p)


# ---------- settings ----------
def check_setting(s, where: str) -> list:
    """Errors of one VoiceSetting (data-model)."""
    if not isinstance(s, dict):
        return [f"{where}: a voice setting is an object"]
    errs = []
    mode = s.get("mode", "own")
    if mode not in ("own", "narrator"):
        errs.append(f"{where}: mode is own or narrator")
    if mode == "own":
        from filmcheck import channels
        if not s.get("voice") or not channels.voice_ok(s["voice"]):
            errs.append(f"{where}: choose a voice (kokoro name or el:<id>)")
    p = s.get("pitch", 0)
    if not isinstance(p, (int, float)) or isinstance(p, bool) or not -6 <= p <= 6 or abs(p * 2 - round(p * 2)) > 1e-9:
        errs.append(f"{where}: pitch is −6…+6 in half steps")
    sp = s.get("speed", 1)
    if not isinstance(sp, (int, float)) or isinstance(sp, bool) or not 0.5 <= sp <= 2:
        errs.append(f"{where}: speed is 0.5…2")
    if s.get("formant") not in (None, "shifted", "preserved"):
        errs.append(f"{where}: formant is shifted or preserved")
    if s.get("emotion", "neutral") not in EMOTIONS:
        errs.append(f"{where}: emotion is one of {', '.join(EMOTIONS)}")
    return errs


def clean(s: dict) -> dict:
    return {k: s[k] for k in SETTING_FIELDS if k in s and s[k] is not None}


# ---------- the channel's voices ----------
def channel_of(film_dir: Path):
    snap = _read(Path(film_dir) / "channel.json", {}) or {}
    return snap.get("channel") if isinstance(snap, dict) else None


def channel_file(root: Path, slug: str) -> Path:
    from filmcheck import channels
    return channels.channel_dir(root, slug) / "VOICE.json"


def channel_voice(root: Path, slug: str) -> dict:
    """{version, narrator, roles}: the defaults where VOICE.json says nothing. narrator None = not chosen yet; a channel
    from before 036 counts its `voice`/`speed` as the narrator."""
    doc = _read(channel_file(root, slug), {}) if slug else {}
    doc = doc if isinstance(doc, dict) else {}
    narr = doc.get("narrator")
    if not narr and slug:
        ch = _read(channel_file(root, slug).with_name("channel.json"), {}) or {}
        if ch.get("voice"):
            narr = {"mode": "own", "voice": ch["voice"], "speed": float(ch.get("speed") or 1), "from": "channel.json"}
    roles = {r: list((doc.get("roles") or {}).get(r) or DEFAULT_ROLES[r]) for r in ROLES}
    return {"version": 1, "narrator": narr, "roles": roles}


def save_channel_voice(root: Path, slug: str, narrator: dict = None, role: str = None, settings: list = None,
                       by: str = "local") -> dict:
    """Set the narrator, or the list of settings of one role (contracts/cli.md `voice channel`)."""
    from datetime import datetime, timezone
    p = channel_file(root, slug)
    if not p.with_name("channel.json").is_file():
        raise SpeakerError(f"no channel \"{slug}\"")
    doc = _read(p, {}) or {}
    if narrator is not None:
        narrator = dict(clean(narrator), mode="own")
        errs = check_setting(narrator, "narrator")
        if errs:
            raise SpeakerError("; ".join(errs))
        narrator["approved"] = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "by": by}
        doc["narrator"] = narrator
    if role is not None:
        if role not in ROLES:
            raise SpeakerError(f"role is one of {', '.join(ROLES)}")
        rows = [clean(s) for s in settings or []]
        errs = [e for i, s in enumerate(rows) for e in check_setting(s, f"{role}[{i}]")]
        if errs or not rows:
            raise SpeakerError("; ".join(errs) or "give at least one voice for the role")
        doc.setdefault("roles", {})[role] = rows
    doc["version"] = 1
    _write(p, doc)
    return channel_voice(root, slug)


# ---------- resolving ----------
def film_voices(film_dir: Path) -> dict:
    f = _read(Path(film_dir) / "film.json", {}) or {}
    return f if isinstance(f, dict) else {}


def cast_voices(film_dir: Path) -> dict:
    """Approved character voices of cast/cast.json (specs/034), when there are any."""
    c = _read(Path(film_dir) / "cast" / "cast.json", {}) or {}
    out = {}
    for ch in (c.get("characters") or []) if isinstance(c, dict) else []:
        if isinstance(ch, dict) and ch.get("id") and isinstance(ch.get("voice"), dict):
            out[ch["id"]] = ch["voice"]
    return out


def dup_key(s: dict) -> tuple:
    from filmcheck import voicecat
    prov, v = voicecat.parse(s.get("voice") or "")
    return (prov, v, round(float(s.get("pitch") or 0), 1), round(float(s.get("speed") or 1), 2))


def _real(s: dict, narr: dict) -> dict:
    """A setting with the narrator's voice put in when the narrator plays the part."""
    s = clean(s)
    if s.get("mode") == "narrator":
        if not narr:
            return dict(s)
        base = {k: v for k, v in clean(narr).items() if k in ("voice", "el", "speed")}
        s = {**base, **{k: v for k, v in s.items() if k != "voice"}}
    if s.get("formant") is None and float(s.get("pitch") or 0) > 0:
        s["formant"] = "shifted"
    return s


def resolve(film_dir: Path, rows: list, root: Path = None) -> dict:
    """{speakers: {speaker: {source, role?, setting, lines}}, lines: {id: setting}, errors: [..]}. Lines with a hand
    written `voice` are not in `lines` (they read as written)."""
    d = Path(film_dir)
    root = Path(root) if root else d.parent.parent
    film = film_voices(d)
    slug = channel_of(d)
    chan = channel_voice(root, slug) if slug else {"narrator": None, "roles": DEFAULT_ROLES}
    if not chan["narrator"] and slug:                  # the channel folder is not here (a job): the film's snapshot
        snap = (_read(d / "channel.json", {}) or {}).get("film") or {}
        if snap.get("voice"):
            chan["narrator"] = {"mode": "own", "voice": snap["voice"], "speed": float(snap.get("speed") or 1)}
    narr = film.get("narrator") if isinstance(film.get("narrator"), dict) else chan["narrator"]
    narr_src = "film" if isinstance(film.get("narrator"), dict) else "narrator"
    own = dict(film.get("voices") or {}) if isinstance(film.get("voices"), dict) else {}
    cast = cast_voices(d)
    prev = _read(d / "voices" / "speakers.json", {}) or {}
    speakers, lines, errors = {}, {}, []
    used_in = {}                                           # para -> {dup key: speaker}
    narr_real = _real(narr, None) if narr else None

    def take(sp, src, setting, role=None):
        e = speakers.setdefault(sp, {"source": src, "setting": setting, "lines": []})
        if role:
            e["role"] = role
        return e

    for r in rows:
        if not isinstance(r, dict) or not r.get("id"):
            continue
        sp = r.get("speaker") or "narrator"
        if r.get("voice"):                                 # 0. written by hand
            e = take(sp, "manual", {k: r[k] for k in ("voice", "speed", "pitch") if k in r})
            e["lines"].append(r["id"])
            continue
        if sp == "narrator":
            if narr_real is None:
                if slug:
                    errors.append(f"line {r['id']}: the channel \"{slug}\" has no narrator yet — choose a narrator voice "
                                  f"(sh bin/studio voice channel {slug} narrator --voice <id>)")
                continue                                   # no channel: the library's default, as before
            e = take(sp, narr_src, narr_real)
        elif sp in cast or sp in own:
            src = "cast" if sp in cast else "film"
            e = speakers.get(sp) or take(sp, src, _real(cast.get(sp) or own[sp], narr_real))
        elif r.get("role") in ROLES:
            e = speakers.get(sp)
            if e is None:
                e = take(sp, "role", _pick_role(r["role"], chan["roles"], narr_real, prev.get(sp), used_in.get(r.get("para"), {}),
                                                 sp), r["role"])
        else:
            errors.append(f"line {r['id']}: speaker \"{sp}\" has no voice — give it a voice in film.json → voices or a role "
                          f"({', '.join(ROLES)})")
            continue
        e["lines"].append(r["id"])
        s = dict(e["setting"])
        if r.get("emotion"):
            s["emotion"] = r["emotion"]
        lines[r["id"]] = s
        used_in.setdefault(r.get("para"), {}).setdefault(dup_key(e["setting"]), sp)
    # two speakers of one scene with the same voice (research R5): an error naming both and the scene
    for para in sorted({r.get("para") for r in rows if isinstance(r, dict)}, key=str):
        seen = {}
        for r in rows:
            if not isinstance(r, dict) or r.get("para") != para or r.get("id") not in lines:
                continue
            sp = r.get("speaker") or "narrator"
            k = dup_key(lines[r["id"]])
            if k in seen and seen[k] != sp:
                errors.append(f"scene {para}: {seen[k]} and {sp} have the same voice — change one of them")
                break
            seen.setdefault(k, sp)
    return {"speakers": speakers, "lines": lines, "errors": errors}


def _pick_role(role, roles, narr, before, used, sp):
    """A side part's voice: the one it had before in this film, else the first choice of its role not used in the scene
    by another speaker; none left → the narrator pitched one more semitone (research R5)."""
    opts = [_real(s, narr) for s in roles.get(role) or DEFAULT_ROLES[role]]
    if isinstance(before, dict) and before.get("source") == "role" and before.get("setting") in opts:
        return before["setting"]
    taken = {k for k, who in used.items() if who != sp}
    if narr:
        taken.add(dup_key(narr))
    for s in opts:
        if dup_key(s) not in taken:
            return s
    s = dict(opts[0])
    for step in (1, -1, 2, -2, 3, -3):
        s["pitch"] = max(-6, min(6, float(opts[0].get("pitch") or 0) + step))
        if dup_key(s) not in taken:
            break
    return _real(s, None)


def line_errors(r: dict) -> list:
    """The new fields of one line (data-model "Line")."""
    errs = []
    sp = r.get("speaker")
    if sp is not None and sp != "narrator" and not (isinstance(sp, str) and SPEAKER.match(sp)):
        errs.append(f"speaker \"{sp}\" is narrator or 1–32 lowercase letters, digits or dashes")
    if r.get("role") is not None and r["role"] not in ROLES:
        errs.append(f"role is one of {', '.join(ROLES)}")
    if r.get("emotion") is not None and r["emotion"] not in EMOTIONS:
        errs.append(f"emotion is one of {', '.join(EMOTIONS)}")
    if r.get("fx") is not None and r["fx"] not in FXS:
        errs.append(f"fx is one of {', '.join(FXS)}")
    return errs


def apply(film_dir: Path, rows: list, root: Path = None, write: bool = True) -> list:
    """The rows `voice make` reads: each resolved line gets voice, speed, pitch, formant, emotion and el from its
    speaker (the line's own emotion and fx stay). Raises SpeakerError with every problem. Writes speakers.json."""
    bad = [f"line {r['id']}: {e}" for r in rows if isinstance(r, dict) and r.get("id") for e in line_errors(r)]
    res = resolve(film_dir, rows, root)
    if bad or res["errors"]:
        raise SpeakerError("\n".join(bad + res["errors"]))
    out = []
    for r in rows:
        s = res["lines"].get(r.get("id")) if isinstance(r, dict) else None
        if s:
            r = dict(r)
            for k in ("voice", "speed", "pitch", "formant", "el"):
                if s.get(k) is not None:
                    r[k] = s[k]
            if s.get("emotion") and not r.get("emotion"):
                r["emotion"] = s["emotion"]
        out.append(r)
    if write and res["speakers"]:
        p = Path(film_dir) / "voices" / "speakers.json"
        old = _read(p, {}) or {}
        table = dict(res["speakers"])
        if "fallback" in old:
            table["fallback"] = old["fallback"]
        _write(p, table)
    return out


def estimate_chars(rows: list) -> int:
    """Characters ElevenLabs would read for these (resolved) rows."""
    from filmcheck import voicecat
    return sum(len(r.get("say") or r.get("text") or "") for r in rows
               if isinstance(r, dict) and voicecat.parse(r.get("voice") or "")[0] == "elevenlabs")
