"""Script review and film checks (specs/010): sh bin/studio script|web|qc|config …

Runs the same way locally and inside an online job container. Never calls Claude except `script review`."""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))


def not_yet(a) -> int:
    print(f"✗ not built yet: {a.cmd}", file=sys.stderr)
    return 2


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="studio", description="Script review and film checks (specs/010)")
    sub = p.add_subparsers(dest="group", required=True)

    sc = sub.add_parser("script", help="score and review a film's SCRIPT.md").add_subparsers(dest="cmd", required=True)
    for name in ("check", "review", "status"):
        s = sc.add_parser(name)
        s.add_argument("film")
        s.add_argument("--json", action="store_true")
        if name == "review":
            s.add_argument("--customer-round", action="store_true", help="a round the customer asked for (FR-019)")
    s = sc.add_parser("skip")
    s.add_argument("film")
    s.add_argument("--reason", required=True)

    w = sub.add_parser("web", help="open a web page").add_subparsers(dest="cmd", required=True)
    s = w.add_parser("fetch")
    s.add_argument("url")
    s.add_argument("--film")

    q = sub.add_parser("qc", help="measure a finished film")
    q.add_argument("film")
    q.add_argument("--json", action="store_true")

    c = sub.add_parser("config", help="local settings").add_subparsers(dest="cmd", required=True)
    s = c.add_parser("editor-model")
    s.add_argument("value", choices=["inherit", "opus", "sonnet", "haiku"])
    return p


def main(argv=None) -> int:
    a = parser().parse_args(argv)
    if a.group == "qc":
        a.cmd = "qc"
    return not_yet(a)


if __name__ == "__main__":
    sys.exit(main())
