"""Craft rules of tier 1 (specs/027 FR-015, contracts/cli.md): from the page's window.CRAFT, the shares of shots with
people doing a real action (error under the style's minimum), and of outdoor shots, shots with an item in a hand and
over-the-shoulder shots (style warnings outside the style's range); acts that fell back on their own item warn too.
The counting is craftlabel.shares, the same as the reference set was measured with."""
from filmcheck import craftlabel

RULE_ACTION = "craft_action"
FIX_MAX = 8


def _issue(rule, measure, limit, text, fix, severity, ref="film", at=None):
    return {"tier": "plan", "ref": ref, "at": at, "rule": rule, "severity": severity, "measure": measure,
            "limit": limit, "text": text, "fix": fix, "excepted": None}


def rows_of(craft: list) -> list:
    out = []
    for r in craft or []:
        if not (isinstance(r, list) and len(r) >= 4 and isinstance(r[3], dict)):
            continue
        c = r[3]
        out.append({"id": str(r[2]), "t0": float(r[0]), "t1": float(r[1]), "card": bool(c.get("card")),
                    "people": int(c.get("people") or 0), "action": bool(c.get("action")),
                    "outdoor": bool(c.get("outdoor")), "prop": bool(c.get("prop")), "ots": c.get("cam") == "ots",
                    "item_default": list(c.get("item_default") or [])})
    return out


def rules(tpl, craft, exceptions=()) -> tuple:
    """(issues, measures, skipped). exceptions: qc-exceptions.json rows; a shot excepted for craft_action leaves the
    action share's count."""
    craft_tpl = (tpl or {}).get("craft")
    if not craft_tpl:
        return [], {}, ["craft: the style has no template.json → craft, skipped"]
    if craft is None:
        return [], {}, ["craft: the page has no window.CRAFT (kit v3), skipped"]
    rows = rows_of(craft)
    skip = {e.get("shot") for e in exceptions or () if e.get("rule") == RULE_ACTION}
    sh = craftlabel.shares(rows)
    act_rows = [r for r in rows if r["id"] not in skip]
    act = craftlabel.shares(act_rows)["action"]
    m = {"craft": {**sh, "action": act, "action_excepted": sorted(skip & {r["id"] for r in rows}),
                   "source": craft_tpl.get("source")}}
    issues = []
    a = craft_tpl.get("action") or {}
    if a.get("min") is not None and act is not None and act < a["min"]:
        idle = sorted((r for r in act_rows if not r["card"] and r["people"] > 0 and not r["action"]),
                      key=lambda r: r["t1"] - r["t0"], reverse=True)[:FIX_MAX]
        issues.append(_issue(RULE_ACTION, act, f">= {a['min']}",
                             f"{act:.0%} of the shots with people have someone doing a real action; the style needs "
                             f"at least {a['min']:.0%}",
                             "give these shots a body or pair act (run, jump, throw, carry, fall, push, type, give, "
                             "high-five), longest first: " + ", ".join(r["id"] for r in idle), "block"))
    for key in ("outdoor", "prop", "ots"):
        rng = (craft_tpl.get(key) or {}).get("range")
        v = sh.get(key)
        if rng and v is not None and not (rng[0] - 1e-9 <= v <= rng[1] + 1e-9):
            issues.append(_issue(f"craft_{key}", v, f"{rng[0]}–{rng[1]}",
                                 f"style: {v:.0%} of the shots are {key}; the style's range is {rng[0]:.0%}–{rng[1]:.0%}",
                                 "match the style, or accept with a reason (qc accept-style)", "warn"))
    for r in rows:
        if r["item_default"]:
            issues.append(_issue("craft_item_default", ", ".join(r["item_default"]), "an item named",
                                 f"{r['id']}: {', '.join(r['item_default'])} names no item; the act's own item is used",
                                 "name the item, e.g. throw:ball, give:keys@1", "warn", ref=r["id"], at=r["t0"]))
    return issues, m, []
