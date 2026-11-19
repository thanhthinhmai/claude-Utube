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


def cmd_refetch(a):
    from sl import fetch
    return fetch.refetch(a.set, a.videos)


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
        path = refset.video_path(a.set, v)
        again = v.get("state") == "transcribed" and path.exists() and \
            not (refset.profile_dir(a.set, v["id"]) / "words.json").exists()      # refetched after clean (specs/023)
        if v.get("state") != "measured" and not again:
            continue
        meta = probe.probe(path)
        print(f"… chép lời {v['id']}")
        tr = speech.transcribe(path, meta, v["segments"], a.model, None if a.lang == "auto" else a.lang)
        out = refset.profile_dir(a.set, v["id"])
        refset.write_json(out / "words.json", tr)
        prof = refset.read_json(out / "video.json")
        r = speech.rate(tr["words"], tr["language"])
        if r:
            r["first_word_t"] = tr["words"][0]["start"]
            r["language"] = tr["language"]
        else:      # music or noise only: Whisper's language guess means nothing here
            r = {"words": 0, "rate": None, "unit": None, "language": None,
                 "note": tr.get("note") or "không phát hiện lời nói"}
        prof["speech"] = r
        refset.write_json(out / "video.json", prof)
        v["state"] = "transcribed"
        refset.save(a.set, data)
        n += 1
    print(f"Đã chép lời {n} video.")
    return 0


def cmd_shots(a):
    from sl import shots
    done = shots.shots_set(a.set, a.only)
    print(f"Shots: {len(done)} video(s) split (already split ones skipped).")
    return 0


def cmd_label(a):
    from sl import shots
    from filmcheck import labeler
    if a.set_label:
        for item in a.set_label:
            ref, *pairs = item.split()
            row = shots.set_label(a.set, ref, pairs)
            print(f"✓ {ref}: {row.get('scale')} · {row.get('angle')} (edited by the user)")
        return 0
    try:
        if a.pass_ == 2:
            shots.second_pass(a.set, a.sample)
        else:
            shots.label_set(a.set)
    except labeler.LabelError as e:
        raise StepError(str(e)) from None
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
    if a.clip:
        return compare.clip_cli(a.set, a.clip)
    if not (a.ref and a.ours):
        raise UsageError("cần --ref và --ours (khung chứng minh), hoặc --clip (đoạn video, specs/023)")
    return compare.cli(a.set, a.ref, a.ours, a.round)


def cmd_save(a):
    from sl import save
    return save.save(a.set, a.slug, a.en, a.cn, a.based_on, a.accept_proof, a.update)


def cmd_template_check(a):
    from sl import template
    return template.cli(a.slug, a.partial)


def cmd_craft_summary(a):
    from sl import template
    s = template.craft_summary(a.set, a.parts)
    template.print_summary(s)
    return 0


def cmd_craft(a):
    from sl import craft
    try:
        return craft.craft_set(a.set, a.only, a.strips)
    except craft.CraftError as e:
        raise StepError(str(e))


def cmd_evidence(a):
    from sl import craft
    print(craft.evidence(a.set, a.vid, a.t, a.name))
    return 0


def cmd_sound(a):
    from sl import soundcraft
    return soundcraft.sound_set(a.set, a.only)


def cmd_beats(a):
    from sl import timesummary
    probs = timesummary.check_beats(a.set)
    for x in probs:
        print(f"✗ {x}")
    if not probs:
        print("✓ beats.json đạt")
    return 1 if probs else 0


def cmd_pairs(a):
    from sl import pairs
    return pairs.cli(a.set, a.batch, a.component, a.ours, a.ref, a.notes, a.clip, a.ref_strip, a.ref_seconds)


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

    rf = sub.add_parser("refetch", help="tải lại video của một bộ đã học, vào đúng vNN cũ (specs/023)")
    rf.add_argument("set"); rf.add_argument("--videos", nargs="+", required=True); rf.set_defaults(fn=cmd_refetch)

    m = sub.add_parser("measure", help="đo mọi khung của phần được đo")
    m.add_argument("set"); m.add_argument("--only", nargs="*")
    m.set_defaults(fn=cmd_measure)

    t = sub.add_parser("transcribe", help="chép lời (cần deps learn --extra)")
    t.add_argument("set"); t.add_argument("--model", default=None, help="default: the studio's model in tools/asr.json"); t.add_argument("--lang", default="auto")
    t.set_defaults(fn=cmd_transcribe)

    sh = sub.add_parser("shots", help="tách cảnh, khung giữa cảnh, độ nét, bối cảnh (specs/021)")
    sh.add_argument("set"); sh.add_argument("--only", nargs="*"); sh.set_defaults(fn=cmd_shots)

    lb = sub.add_parser("label", help="gán nhãn cỡ cảnh và góc máy bằng một lượt Claude độc lập (specs/021)")
    lb.add_argument("set"); lb.add_argument("--pass", dest="pass_", type=int, default=1, choices=(1, 2))
    lb.add_argument("--sample", type=int, default=40)
    lb.add_argument("--set", dest="set_label", action="append", metavar="'vNN:Sxxx key=value …'",
                    help="sửa tay một nhãn, ví dụ --set 'v03:S014 scale=huge angle=top'")
    lb.set_defaults(fn=cmd_label)

    s = sub.add_parser("summary", help="tổng hợp cả bộ")
    s.add_argument("set"); s.set_defaults(fn=cmd_summary)

    c = sub.add_parser("check-names", help="chặn tên kênh và câu thoại nguyên văn")
    c.add_argument("set"); c.add_argument("files", nargs="+"); c.set_defaults(fn=cmd_check_names)

    k = sub.add_parser("compare", help="so khung chứng minh với khung gốc")
    k.add_argument("set"); k.add_argument("--ref"); k.add_argument("--ours")
    k.add_argument("--clip", help="đoạn video của khung chứng minh: so số đo chuyển động với kênh mẫu (specs/023)")
    k.add_argument("--round", type=int, default=1); k.set_defaults(fn=cmd_compare)

    v = sub.add_parser("save", help="lưu phong cách vào my-styles/")
    v.add_argument("set"); v.add_argument("--slug", required=True); v.add_argument("--en", required=True)
    v.add_argument("--cn", default=""); v.add_argument("--based-on", required=True)
    v.add_argument("--accept-proof", action="store_true", help="người dùng đã chấp nhận khung chứng minh chưa đạt ngưỡng")
    v.add_argument("--update", action="store_true", help="học lại một phong cách riêng đã có (giữ nhật ký sửa và phim mẫu)")
    v.set_defaults(fn=cmd_save)

    tc = sub.add_parser("template-check", help="kiểm TEMPLATE.md, template.json và nhãn luật của STYLE.md (specs/023)")
    tc.add_argument("slug"); tc.add_argument("--partial", metavar="a-b", help="chỉ kiểm mục a–b, bỏ công thức nhịp")
    tc.set_defaults(fn=cmd_template_check)

    cr = sub.add_parser("craft", help="đo máy, cử động trong cảnh, chuyển cảnh; cắt dải khung (specs/023)")
    cr.add_argument("set"); cr.add_argument("--only", nargs="*"); cr.add_argument("--strips", type=int, default=80)
    cr.set_defaults(fn=cmd_craft)

    ev = sub.add_parser("evidence", help="trích một khung 640 px làm bằng chứng (video phải còn)")
    ev.add_argument("set"); ev.add_argument("vid"); ev.add_argument("t", type=float); ev.add_argument("--name", required=True)
    ev.set_defaults(fn=cmd_evidence)

    so = sub.add_parser("sound", help="nhịp đọc, nhạc, tiếng động (cần learn transcribe trước; specs/023)")
    so.add_argument("set"); so.add_argument("--only", nargs="*"); so.set_defaults(fn=cmd_sound)

    bt = sub.add_parser("beats", help="kiểm profile/beats.json (specs/023)")
    bt.add_argument("set"); bt.add_argument("--check", action="store_true", required=True); bt.set_defaults(fn=cmd_beats)

    pr = sub.add_parser("pairs", help="bảng so bộ dựng | kênh mẫu (specs/023)")
    pr.add_argument("set"); pr.add_argument("--batch", type=int, required=True, choices=(1, 2, 3, 4))
    pr.add_argument("--component", required=True); pr.add_argument("--ours", nargs="+", required=True)
    pr.add_argument("--ref", nargs="+", required=True); pr.add_argument("--notes", default="")
    pr.add_argument("--clip"); pr.add_argument("--ref-strip"); pr.add_argument("--ref-seconds", type=float)
    pr.set_defaults(fn=cmd_pairs)

    cs = sub.add_parser("craft-summary", help="gom số tay nghề của bộ: bố cục, độ sâu, ánh sáng; theo thời gian (specs/023)")
    cs.add_argument("set"); cs.add_argument("--parts", nargs="+", default=["look"], choices=("look", "time"))
    cs.set_defaults(fn=cmd_craft_summary)

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
    except OSError as e:
        print(f"✗ lỗi đọc/ghi file: {e}", file=sys.stderr); return 1


if __name__ == "__main__":
    sys.exit(main())
