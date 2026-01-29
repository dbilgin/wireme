from __future__ import annotations

import argparse
import sys

from . import __version__
from .client_tui import run as run_tui


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wiremec",
        description="WireGuard client manager TUI (import config, up/down, status).",
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
