"""UCS (Universal Category System) names, as Sonniss GDC files use them (specs/037 research R2).

A UCS file name is `CatID_FX Name_Creator_Source…`; the CatID is the category code followed by the subcategory, e.g.
`GLASBrk` = GLASS / BREAK. Only names and text are read here, never audio (FR-013b). The table holds the main UCS
categories by code, plus a few codes some libraries use that are not in UCS (IMPC, BALL, CRTN)."""
import re

CATEGORIES = {
    "AIR": "AIR", "AERO": "AIRCRAFT", "ALRM": "ALARMS", "AMB": "AMBIENCE", "ANML": "ANIMALS", "ARCH": "ARCHIVED",
    "BEEP": "BEEPS", "BELL": "BELLS", "BIRD": "BIRDS", "BOAT": "BOATS", "BLLT": "BULLETS", "TOON": "CARTOON",
    "CERM": "CERAMICS", "CHAN": "CHAINS", "CHEM": "CHEMICALS", "CLOK": "CLOCKS", "CLOTH": "CLOTH", "COMM": "COMMUNICATIONS",
    "COMP": "COMPUTERS", "CREA": "CREATURES", "CRWD": "CROWDS", "DSGN": "DESIGNED", "DEST": "DESTRUCTION",
    "DIRT": "DIRT & SAND", "DOOR": "DOORS", "DRWR": "DRAWERS", "ELEC": "ELECTRICITY", "EQUIP": "EQUIPMENT",
    "EXPL": "EXPLOSIONS", "FART": "FARTS", "FGHT": "FIGHT", "FIRE": "FIRE", "FIREWRK": "FIREWORKS", "FOLY": "FOLEY",
    "FOOD": "FOOD & DRINK", "FEET": "FOOTSTEPS", "GAME": "GAMES", "GEOT": "GEOTHERMAL", "GLAS": "GLASS", "GORE": "GORE",
    "GUN": "GUNS", "HORN": "HORNS", "HMN": "HUMAN", "ICE": "ICE", "LASR": "LASERS", "LETH": "LEATHER",
    "LIQ": "LIQUID & MUD", "MACH": "MACHINES", "MAGC": "MAGIC", "MECH": "MECHANICAL", "METL": "METAL", "MOTR": "MOTORS",
    "MOVE": "MOVEMENT", "MUSC": "MUSICAL", "NTDST": "NATURAL DISASTER", "OBJ": "OBJECTS", "PAPR": "PAPER",
    "PLST": "PLASTIC", "RAIN": "RAIN", "ROBO": "ROBOTS", "ROCK": "ROCKS", "ROPE": "ROPE", "RUBR": "RUBBER",
    "SCI": "SCIFI", "SNOW": "SNOW", "SPRT": "SPORTS", "SWSH": "SWOOSHES", "TOOL": "TOOLS", "TOY": "TOYS",
    "TRAN": "TRAINS", "UI": "USER INTERFACE", "VEH": "VEHICLES", "VOX": "VOICES", "WATR": "WATER", "WEAP": "WEAPONS",
    "WHSH": "WHOOSHES", "WIND": "WIND", "WINDW": "WINDOWS", "WING": "WINGS", "WOOD": "WOOD", "WTHR": "WEATHER",
    # not UCS, seen in libraries
    "IMPC": "IMPACTS", "IMPT": "IMPACTS", "BALL": "BALLS", "CRTN": "CARTOON", "STEP": "FOOTSTEPS",
}

SUBS = {
    "Brk": "BREAK", "Shtr": "SHATTER", "Crsh": "CRASH", "Impt": "IMPACT", "Hit": "HIT", "Pop": "POP", "Bnce": "BOUNCE",
    "Bubl": "BUBBLES", "Cheer": "CHEER", "Aplse": "APPLAUSE", "Wlk": "WALK", "Run": "RUN", "Foot": "FOOTSTEPS",
    "Click": "CLICK", "Scrbl": "SCRIBBLE", "Hand": "HAND", "Misc": "MISC", "Open": "OPEN", "Close": "CLOSE",
    "Slam": "SLAM", "Drip": "DRIP", "Splsh": "SPLASH", "Flow": "FLOW", "Room": "ROOM", "Office": "OFFICE",
    "Metl": "METAL", "Wood": "WOOD", "Glas": "GLASS", "Swsh": "SWISH", "Fast": "FAST", "Slow": "SLOW",
}

_CATID = re.compile(r"^([A-Z]{2,7})([A-Z][a-z][A-Za-z]*)?$")


def category_of(code: str):
    """'GLAS' → 'GLASS', or None."""
    return CATEGORIES.get(code.upper())


def split_catid(token: str):
    """'GLASBrk' → ('GLAS', 'Brk'); ('', '') when it is no CatID. Longest known category code wins."""
    m = _CATID.match(token or "")
    if not m:
        return "", ""
    head, tail = m.group(1), m.group(2) or ""
    for n in range(len(head), 1, -1):              # 'FIREWRK' before 'FIRE'
        if head[:n] in CATEGORIES:
            rest = head[n:]
            return head[:n], rest + tail
    return "", ""


def parse_name(stem: str) -> dict:
    """A file name without extension → {cat_id, category, subcategory, descriptor}; empty strings when unknown."""
    parts = [p.strip() for p in stem.split("_")]
    code, sub = split_catid(parts[0]) if parts else ("", "")
    if not code:
        return {"cat_id": "", "category": "", "subcategory": "", "descriptor": stem.replace("_", " ").strip()}
    sub_name = SUBS.get(sub, sub.upper())
    descriptor = parts[1] if len(parts) > 1 else ""
    return {"cat_id": parts[0], "category": CATEGORIES[code], "subcategory": sub_name, "descriptor": descriptor}


def match(cat: str, category: str) -> bool:
    """Does a wanted category ('GLASS' or code 'GLAS') match an entry's category?"""
    if not cat or not category:
        return False
    want = cat.upper()
    return want == category.upper() or CATEGORIES.get(want, "") == category.upper()
