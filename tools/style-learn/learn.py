"""Style learning CLI. Called by: sh bin/studio learn <command> …   (contracts/learn-cli.md)
Exit codes: 0 done · 1 a step failed / check not passed · 2 bad usage."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sl import refset  # noqa: E402
from sl.refset import StepError, UsageError  # noqa: E402


def cmd_fetch(a):
    from sl import fetch
    deny = a.deny or []
    if a.files:
        fetch.fetch_files(a.set, a.files, a.max_seconds, deny)
    elif a.channel:
        fetch.check_count(a.count)
        fetch.fetch_urls(a.set, "channel", [a.channel], a.count, a.max_seconds, deny)
    elif a.videos:
        fetch.fetch_urls(a.set, "videos", a.videos, len(a.videos), a.max_seconds, deny)
    else:
        raise UsageError("cần một trong: --channel URL, --videos URL…, --files PATH…")
    return 0


def cmd_measure(a):
    from sl import measure
    done = measure.measure_set(a.set, a.only)
    data = refset.load(a.set)
    ok = [v for v in data["videos"] if v.get("state") in ("measured", "transcribed")]
    print(f"Đã đo mới {len(done)} video; tổng {len(ok)}/{len(data['videos'])} video có hồ sơ đo.")
    return 0 if ok else 1


def cmd_transcribe(a):
    from sl import probe, speech
    data = refset.load(a.set)
    n = 0
    for v in data["videos"]:
        if v.get("state") != "measured":
            continue
        path = refset.video_path(a.set, v)
        meta = probe.probe(path)
        print(f"… chép lời {v['id']}")
        tr = speech.transcribe(path, meta, v["segments"], a.model, None if a.lang == "auto" else a.lang)
        out = refset.profile_dir(a.set, v["id"])
        refset.write_json(out / "words.json", tr)
        prof = refset.read_json(out / "video.json")
        r = speech.rate(tr["words"], tr["language"])
        if r and tr["words"]:
            r["first_word_t"] = tr["words"][0]["start"]
            r["language"] = tr["language"]
        prof["speech"] = r
        refset.write_json(out / "video.json", prof)
        v["state"] = "transcribed"
        refset.save(a.set, data)
        n += 1
    print(f"Đã chép lời {n} video.")
    return 0


def cmd_summary(a):
    from sl import summary
    s = summary.build(a.set)
    print((refset.set_dir(a.set) / "profile" / "summary.md").read_text(encoding="utf-8"))
    return 0 if s["videos_measured"] else 1


def cmd_check_names(a):
    from sl import names
    return names.cli(a.set, a.files)


def cmd_compare(a):
    from sl import compare
    return compare.cli(a.set, a.ref, a.ours, a.round)


def cmd_save(a):
    from sl import save
    return save.save(a.set, a.slug, a.en, a.cn, a.based_on, a.accept_proof)


def cmd_clean(a):
    from sl import save
    return save.clean(a.set, a.keep)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="sh bin/studio learn", description="Học phong cách từ video tham chiếu")
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="nhận video tham chiếu")
    f.add_argument("set")
    g = f.add_mutually_exclusive_group()
    g.add_argument("--channel")
    g.add_argument("--videos", nargs="+")
    g.add_argument("--files", nargs="+")
    f.add_argument("--count", type=int, default=12)
    f.add_argument("--max-seconds", type=float, default=180)
    f.add_argument("--deny", nargs="*")
    f.set_defaults(fn=cmd_fetch)

    m = sub.add_parser("measure", help="đo mọi khung của phần được đo")
    m.add_argument("set"); m.add_argument("--only", nargs="*")
    m.set_defaults(fn=cmd_measure)

    t = sub.add_parser("transcribe", help="chép lời (cần deps learn --extra)")
    t.add_argument("set"); t.add_argument("--model", default="small"); t.add_argument("--lang", default="auto")
    t.set_defaults(fn=cmd_transcribe)

    s = sub.add_parser("summary", help="tổng hợp cả bộ")
    s.add_argument("set"); s.set_defaults(fn=cmd_summary)

    c = sub.add_parser("check-names", help="chặn tên kênh và câu thoại nguyên văn")
    c.add_argument("set"); c.add_argument("files", nargs="+"); c.set_defaults(fn=cmd_check_names)

    k = sub.add_parser("compare", help="so khung chứng minh với khung gốc")
    k.add_argument("set"); k.add_argument("--ref", required=True); k.add_argument("--ours", required=True)
    k.add_argument("--round", type=int, default=1); k.set_defaults(fn=cmd_compare)

    v = sub.add_parser("save", help="lưu phong cách vào my-styles/")
    v.add_argument("set"); v.add_argument("--slug", required=True); v.add_argument("--en", required=True)
    v.add_argument("--cn", default=""); v.add_argument("--based-on", required=True)
    v.add_argument("--accept-proof", action="store_true", help="người dùng đã chấp nhận khung chứng minh chưa đạt ngưỡng")
    v.set_defaults(fn=cmd_save)

    d = sub.add_parser("clean", help="xoá video và âm thanh tham chiếu của bộ")
    d.add_argument("set"); d.add_argument("--keep", action="store_true"); d.set_defaults(fn=cmd_clean)

    a = p.parse_args(argv)
    try:
        return a.fn(a)
    except UsageError as e:
        print(f"✗ {e}", file=sys.stderr); return 2
    except StepError as e:
        print(f"✗ {e}", file=sys.stderr); return 1
    except BrokenPipeError:                      # output piped into head/less and closed early
        sys.stderr.close(); return 0


if __name__ == "__main__":
    sys.exit(main())
