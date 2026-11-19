"""The studio's real-person library (specs/028 US3; contracts/people-cli.md; data-model "Người thật").

people/<slug>/figure.js   the caricature (a role config, same format as the kit's generic roles)
people/<slug>/person.json name, role, reference photo source and licence, approval bound to the hash of figure.js
people/<slug>/.sheet/     model sheet and reference photo (not in git: third-party photo)

A film picks people by name: `people use <film> <slug…>` copies approved people into films/<film>/people/ (the page
server only reaches the film folder). Approval is the user's: the agent never runs `approve` on its own. Editing
figure.js changes its hash, so the person is back to "changed since approval" until approved again.
Standard library only.
"""
import hashlib
import json
import re
import shutil
import subprocess
import unicodedata
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SYMBOLS = re.compile(r"^[!?$…♪.\s]{1,3}$")
TEMPLATE = """// {name}: caricature for the studio's 2D films (specs/028). Head radius ≈ 165 at 0,0; body from y 148 to 470.
// Two or three signature features (hair, glasses, one garment). Lines and Bézier curves only (no arcs, no rx).
import {{ ovalHead }} from '../../kit/core.js';
import {{ ears, rearHair, BLAZER, HAIR }} from '../../kit/roles.js';

export default {{
  skin: '#ecc6a4', skinShade: '#cf9f7c', suit: '#2b303e', suitShade: '#1f2330', torso: BLAZER('#f1eee6', null),
  head: ovalHead(146, 168, 0.62), hairBack: ears(142, '#e8bf9c'), hair: HAIR.short('#3a2a20'), hairRear: rearHair('#3a2a20', -204),
}};
"""


class PeopleError(Exception):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def lib_dir(root: Path = ROOT) -> Path:
    return Path(root) / "people"


def pdir(slug: str, root: Path = ROOT) -> Path:
    if not SLUG.match(slug or ""):
        raise PeopleError(f"bad slug {slug!r}: lower case letters, digits and hyphens")
    return lib_dir(root) / slug


def figure_hash(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def load(slug: str, root: Path = ROOT) -> dict:
    p = pdir(slug, root) / "person.json"
    if not p.is_file():
        raise PeopleError(f"no person {slug!r} in people/")
    return json.loads(p.read_text(encoding="utf-8"))


def save(slug: str, data: dict, root: Path = ROOT) -> None:
    (pdir(slug, root) / "person.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def status(slug: str, root: Path = ROOT) -> str:
    """approved | not approved | changed since approval"""
    d = load(slug, root)
    cur = figure_hash(pdir(slug, root) / "figure.js")
    ap = d.get("approved")
    if not ap:
        return "not approved"
    return "approved" if ap.get("hash") == cur else "changed since approval"


def listing(root: Path = ROOT) -> list:
    out = []
    for p in sorted(lib_dir(root).glob("*/person.json")):
        slug = p.parent.name
        d = json.loads(p.read_text(encoding="utf-8"))
        out.append({"slug": slug, "name": d.get("name", ""), "role": d.get("role", ""), "status": status(slug, root)})
    return out


def new(slug: str, name: str, role: str = "", ref_url: str = "", license_: str = "", author: str = "",
        from_file: str = "", root: Path = ROOT, fetch=True, ref_file: str = "") -> Path:
    d = pdir(slug, root)
    if (d / "person.json").exists():
        raise PeopleError(f"{slug!r} is already in people/")
    d.mkdir(parents=True, exist_ok=True)
    fig = d / "figure.js"
    if from_file:
        shutil.copyfile(from_file, fig)
    else:
        fig.write_text(TEMPLATE.format(name=name), encoding="utf-8")
    ref = {"url": ref_url, "source": "", "license": license_, "author": author} if ref_url else None
    if ref_url:
        ref["source"] = ref_url.split("/")[2] if "://" in ref_url else ""
    if ref_url and fetch:
        (d / ".sheet").mkdir(exist_ok=True)
        ext = (Path(ref_url.split("?")[0]).suffix or ".jpg").lower()[:5]
        req = urllib.request.Request(ref_url, headers={"User-Agent": "studio-ref-fetch/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r, open(d / ".sheet" / ("ref" + ext), "wb") as f:
                f.write(r.read())
        except OSError as e:                 # a failed download leaves no half-made person
            shutil.rmtree(d, ignore_errors=True)
            raise PeopleError(f"the reference photo could not be fetched ({e}); try later or give the photo by hand") from None
    if ref_file:                              # a photo already on the machine (given by the user, or fetched earlier)
        (d / ".sheet").mkdir(exist_ok=True)
        shutil.copyfile(ref_file, d / ".sheet" / ("ref" + (Path(ref_file).suffix.lower() if Path(ref_file).suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") else ".jpg")))
    save(slug, {"slug": slug, "name": name, "role": role, "ref": ref, "figure_hash": figure_hash(fig), "approved": None, "history": []}, root)
    return d


def approve(slug: str, note: str = "", source: str = "chat", root: Path = ROOT) -> dict:
    """Record the user's approval of the current figure.js. Only after the user approved the model sheet."""
    d = load(slug, root)
    cur = figure_hash(pdir(slug, root) / "figure.js")
    if d.get("approved"):
        d.setdefault("history", []).append(d["approved"])
    d["figure_hash"] = cur
    d["approved"] = {"hash": cur, "at": now(), "by": source, "note": note}
    save(slug, d, root)
    return d["approved"]


def use(film: str, slugs: list, root: Path = ROOT) -> Path:
    fd = Path(root) / "films" / film
    if not fd.is_dir():
        raise PeopleError(f"films/{film} is not there")
    blocked = [f"{s}: {status(s, root)}" for s in slugs if status(s, root) != "approved"]
    if blocked:
        raise PeopleError("not approved: " + "; ".join(blocked))
    out = fd / "people"
    out.mkdir(exist_ok=True)
    idx_p = out / "index.json"
    idx = json.loads(idx_p.read_text(encoding="utf-8")) if idx_p.is_file() else {"people": []}
    keep = [p for p in idx.get("people", []) if p["slug"] not in slugs]
    for s in slugs:
        (out / s).mkdir(exist_ok=True)
        shutil.copyfile(pdir(s, root) / "figure.js", out / s / "figure.js")
        keep.append({"slug": s, "hash": figure_hash(out / s / "figure.js"), "copied_at": now()})
    idx_p.write_text(json.dumps({"people": sorted(keep, key=lambda p: p["slug"])}, indent=1) + "\n", encoding="utf-8")
    return out


def check_film(film_dir: Path, page_people=None, root: Path = ROOT) -> list:
    """Problems with the real people of a film: [{slug, problem}] (tier 1 rule person_unapproved)."""
    fd = Path(film_dir)
    idx_p = fd / "people" / "index.json"
    copied = json.loads(idx_p.read_text(encoding="utf-8")).get("people", []) if idx_p.is_file() else []
    slugs = {p["slug"] for p in copied} | {p.get("slug") for p in (page_people or []) if p.get("slug")}
    out = []
    for s in sorted(slugs):
        try:
            d = load(s, root)
        except PeopleError:
            out.append({"slug": s, "problem": "not in the people library"})
            continue
        ap = d.get("approved")
        copy = fd / "people" / s / "figure.js"
        if not ap:
            out.append({"slug": s, "problem": "not approved"})
        elif status(s, root) != "approved":
            out.append({"slug": s, "problem": "changed since approval"})
        elif not copy.is_file() or figure_hash(copy) != ap["hash"]:
            out.append({"slug": s, "problem": "the film's copy differs from the approved drawing (run people use again)"})
    return out


# ---------- words of real people (tier 1 rule person_words) ----------
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", s))


def quotes(film_dir: Path) -> list:
    """Quoted passages in the film's SOURCES.md (specs/010 contract: verbatim quotes in quote marks)."""
    p = Path(film_dir) / "SOURCES.md"
    if not p.is_file():
        return []
    text = p.read_text(encoding="utf-8")
    return [_norm(m) for m in re.findall(r"[\"“]([^\"”]{3,})[\"”]", text)]


def words_ok(text: str, qs: list) -> bool:
    if SYMBOLS.match(text or ""):
        return True
    n = _norm(text)
    return bool(n) and any(n in q for q in qs)


def sheet(slug: str, lib, root: Path = ROOT) -> Path:
    """Draw the model sheet: front, 3/4, back and four expressions, beside the reference photo if there is one."""
    d = pdir(slug, root)
    load(slug, root)
    kit = Path(root) / "my-styles" / "sketch-explainer" / "kit"
    work = d / ".sheet" / "page"
    if work.exists():
        shutil.rmtree(work)
    (work / "people" / slug).mkdir(parents=True)
    shutil.copytree(kit, work / "kit")
    shutil.copyfile(d / "figure.js", work / "people" / slug / "figure.js")
    (work / "people" / "index.json").write_text(json.dumps({"people": [{"slug": slug, "hash": figure_hash(d / "figure.js")}]}), encoding="utf-8")
    ref = next(iter(sorted((d / ".sheet").glob("ref.*"))), None)
    if ref:
        shutil.copyfile(ref, work / ("ref" + ref.suffix))
    page = (kit / "tools" / "sheet.html").read_text(encoding="utf-8").replace("__SLUG__", slug).replace("__REF__", ("ref" + ref.suffix) if ref else "")
    (work / "index.html").write_text(page, encoding="utf-8")
    out = d / ".sheet" / "sheet.jpg"
    p = subprocess.run(["node", str(kit / "tools" / "sheet.mjs"), str(work), str(lib), str(out)], capture_output=True, text=True, timeout=300)
    if p.returncode != 0 or not out.is_file():
        raise PeopleError(f"the sheet could not be drawn: {(p.stderr or p.stdout).strip()[-300:]}")
    return out
