"""A tiny fake YouTube for the topic picker (specs/013 T002). `answer(endpoint, params)` returns what the YouTube Data
API would, for four topics whose scores were worked out by hand from research R2 (dates are relative to now):

  "why honey never spoils"   demand 10 (median of top 10 = 1.1M → 8, +2: 5M > 3 × its channel's median 500k)
                             heat 10 (n30 = 10, n60 = 3 → r = 6.7; 8 of the 10 are 16–30 days old: cooling)
                             competition 8 (4 channels: 5k 0.5 + 50k 1 + 60k 1 + 500k 2 = 4.5)
                             overlap 10, fit 7 → 45 → PRIORITY
  "honey vs sugar"           demand 6 (median 400k; channel medians 300k: no outlier)
                             heat 10 (n30 = 6 spread evenly, n60 = 6 → r = 2.0; not cooling)
                             competition 6 (2M 3 + 200k 2 + 20k 1 = 6) · overlap 10 · fit 7 → 39 → GO
                             (a reference channel posted "Honey vs sugar: which is healthier" 9 days ago)
  "bee dances explained"     demand 8 (median 2M) · heat 0 (n30 = 0) · competition 10 (one 50k channel = 1)
                             overlap 10 · fit 7 → 35, but heat ≤ 3 → HOLD
  "royal jelly market [fit-low]"  demand 2 (median 5k) · heat 2 (n30 = 1, n60 = 4 → r = 0.5; views 300 → cap 5)
                             competition 4 (5 channels × 2M = 15) · overlap 10 · fit 2 → 20 → DROP"""
from datetime import datetime, timedelta, timezone

REF_CHANNEL = "UCreferencechannel0000001"[:24].ljust(24, "0")
KEY = "AIzaTEST-not-a-real-key-000000000000000"


def _iso(days):
    return (datetime.now(timezone.utc) - timedelta(days=days, hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _vid(topic_n, i, title, chan, ctitle, days, views):
    return {"id": f"v{topic_n}{i:03d}", "title": title, "channel_id": chan, "channel": ctitle, "days": days, "views": views}


def _topics():
    t = {}
    # 1. why honey never spoils
    y = [_vid(1, i, f"Why honey never spoils part {i}", ch, ch.title(), 100 + i, v) for i, (v, ch) in enumerate(
        [(5_000_000, "UCbigsci"), (3_000_000, "UCmid1"), (2_000_000, "UCmid1"), (1_500_000, "UCmid1"),
         (1_200_000, "UCmid2"), (1_000_000, "UCmid2"), (900_000, "UCmid2"), (800_000, "UCmid2"),
         (700_000, "UCmid2"), (600_000, "UCmid2")])]
    n_ch = ["UCsmall", "UCmid1", "UCmid3", "UCbigsci"]
    n = [_vid(1, 100 + i, f"Honey never spoils: why {i}", n_ch[i % 4], n_ch[i % 4].title(), d, 50_000)
         for i, d in enumerate([3, 10, 17, 18, 20, 21, 23, 25, 27, 29, 40, 60, 80])]
    t["why honey never spoils"] = {"y": y, "n": n, "subs": {"UCsmall": 5_000, "UCmid1": 50_000, "UCmid3": 60_000,
                                                            "UCbigsci": 500_000, "UCmid2": 40_000},
                                   "median": {"UCbigsci": 500_000, "UCmid1": 2_000_000, "UCmid2": 900_000}}
    # 2. honey vs sugar
    chs = ["UCtwoM", "UCtwohundred", "UCtwenty"]
    y = [_vid(2, i, f"Honey vs sugar test {i}", chs[i % 3], chs[i % 3], 120 + i, 400_000) for i in range(10)]
    n = [_vid(2, 100 + i, f"Honey vs sugar round {i}", chs[i % 3], chs[i % 3], d, 20_000)
         for i, d in enumerate([2, 7, 12, 17, 22, 27, 35, 45, 55, 65, 75, 85])]
    t["honey vs sugar"] = {"y": y, "n": n, "subs": {"UCtwoM": 2_000_000, "UCtwohundred": 200_000, "UCtwenty": 20_000},
                           "median": {c: 300_000 for c in chs}}
    # 3. bee dances explained
    y = [_vid(3, i, f"Bee dances explained {i}", "UCbees", "Bees", 150 + i, 2_000_000) for i in range(10)]
    n = [_vid(3, 100 + i, f"Bee dances explained again {i}", "UCbees", "Bees", d, 30_000) for i, d in enumerate([40, 50, 70, 85])]
    t["bee dances explained"] = {"y": y, "n": n, "subs": {"UCbees": 50_000}, "median": {"UCbees": 2_000_000}}
    # 4. royal jelly market
    chs = [f"UCjelly{i}" for i in range(5)]
    y = [_vid(4, i, f"Royal jelly market report {i}", chs[i % 5], chs[i % 5], 200 + i, 5_000) for i in range(10)]
    n = [_vid(4, 100 + i, f"Royal jelly market today {i}", chs[i], chs[i], d, 300) for i, d in enumerate([5, 40, 50, 60, 70])]
    t["royal jelly market [fit-low]"] = {"y": y, "n": n, "subs": {c: 2_000_000 for c in chs}, "median": {c: 5_000 for c in chs}}
    return t


TOPICS = _topics()
EXPECTED = {
    "why honey never spoils": ({"demand": 10, "heat": 10, "competition": 8, "overlap": 10, "fit": 7}, "PRIORITY"),
    "honey vs sugar": ({"demand": 6, "heat": 10, "competition": 6, "overlap": 10, "fit": 7}, "GO"),
    "bee dances explained": ({"demand": 8, "heat": 0, "competition": 10, "overlap": 10, "fit": 7}, "HOLD"),
    "royal jelly market [fit-low]": ({"demand": 2, "heat": 2, "competition": 4, "overlap": 10, "fit": 2}, "DROP"),
}
REF_VIDEOS = [{"id": "vref1", "title": "Honey vs sugar: which is healthier", "days": 9},
              {"id": "vref2", "title": "Why bees dance", "days": 40}]


def _all_videos():
    out = {}
    for d in TOPICS.values():
        for v in d["y"] + d["n"]:
            out[v["id"]] = v
    return out


def _snippet(v):
    return {"title": v["title"], "channelId": v["channel_id"], "channelTitle": v["channel"], "publishedAt": _iso(v["days"])}


def answer(endpoint, params, seen_keys=None):
    if seen_keys is not None and params.get("key"):
        seen_keys.append(params["key"])
    if endpoint == "search":
        d = TOPICS.get(params.get("q", ""), {"y": [], "n": []})
        vs = d["y"] if params.get("order") == "viewCount" else d["n"]
        return {"items": [{"id": {"kind": "youtube#video", "videoId": v["id"]}, "snippet": _snippet(v)} for v in vs]}
    if endpoint == "videos":
        allv, items = _all_videos(), []
        for vid in params.get("id", "").split(","):
            if vid in allv:
                items.append({"id": vid, "snippet": _snippet(allv[vid]), "statistics": {"viewCount": str(allv[vid]["views"])}})
            elif vid.startswith("u_"):                   # a channel's own upload, for its median
                cid, views = vid[2:].rsplit("_", 1)
                items.append({"id": vid, "snippet": {"title": "x", "channelId": cid, "channelTitle": cid,
                                                     "publishedAt": _iso(200)}, "statistics": {"viewCount": views}})
        return {"items": items}
    if endpoint == "channels":
        subs, items = {}, []
        for d in TOPICS.values():
            subs.update(d["subs"])
        for cid in params.get("id", "").split(","):
            if cid == REF_CHANNEL:
                items.append({"id": cid, "statistics": {"subscriberCount": "100000"},
                              "contentDetails": {"relatedPlaylists": {"uploads": "UUref"}}})
            elif cid in subs:
                items.append({"id": cid, "statistics": {"subscriberCount": str(subs[cid])},
                              "contentDetails": {"relatedPlaylists": {"uploads": "UU" + cid}}})
        return {"items": items}
    if endpoint == "playlistItems":
        pl = params.get("playlistId", "")
        if pl == "UUref":
            return {"items": [{"contentDetails": {"videoId": v["id"], "videoPublishedAt": _iso(v["days"])},
                               "snippet": {"title": v["title"], "publishedAt": _iso(v["days"])}} for v in REF_VIDEOS]}
        cid = pl[2:]
        med = next((d["median"][cid] for d in TOPICS.values() if cid in d["median"]), None)
        if med is None:
            return {"items": []}
        views = [med] * 25 + [med // 2] * 12 + [med * 2] * 12      # median = med (49 videos)
        return {"items": [{"contentDetails": {"videoId": f"u_{cid}_{v}", "videoPublishedAt": _iso(200)},
                           "snippet": {"title": "x", "publishedAt": _iso(200)}} for v in views]}
    return {"items": []}
