from __future__ import annotations

import argparse
import sys

from . import __version__
from .tui import run as run_tui


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wireme",
        description="WireGuard TUI (add/delete peers, optional QR + optional save).",
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit.")
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return 0

    run_tui()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
