from __future__ import annotations

import curses
import textwrap

HELP = "↑↓ move  •  Enter select  •  Esc/Backspace back  •  q quit"


def init_curses(stdscr):
    curses.curs_set(0)
    curses.use_default_colors()
    curses.start_color()
    try:
        curses.init_pair(1, curses.COLOR_CYAN, -1)  # title
        curses.init_pair(2, curses.COLOR_GREEN, -1)  # ok
        curses.init_pair(3, curses.COLOR_YELLOW, -1)  # warn
        curses.init_pair(4, curses.COLOR_RED, -1)  # bad
        curses.init_pair(5, curses.COLOR_WHITE, -1)  # normal
    except Exception:
        pass


def draw_header(stdscr, app_name: str, title: str):
    _h, w = stdscr.getmaxyx()
    stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
    stdscr.addnstr(0, 0, f" {app_name}  •  {title}", w - 1)
    stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

    stdscr.attron(curses.A_DIM)
    stdscr.addnstr(1, 0, " " * (w - 1), w - 1)
    stdscr.addnstr(1, 2, HELP, w - 4)
    stdscr.attroff(curses.A_DIM)


def draw_box(stdscr, y: int, x: int, h: int, w: int, title: str | None = None):
    if h < 3 or w < 4:
        return
    stdscr.attron(curses.A_DIM)
    stdscr.addch(y, x, "┌")
    stdscr.addch(y, x + w - 1, "┐")
    stdscr.addch(y + h - 1, x, "└")
    stdscr.addch(y + h - 1, x + w - 1, "┘")
    for i in range(1, w - 1):
        stdscr.addch(y, x + i, "─")
        stdscr.addch(y + h - 1, x + i, "─")
    for j in range(1, h - 1):
        stdscr.addch(y + j, x, "│")
        stdscr.addch(y + j, x + w - 1, "│")
    stdscr.attroff(curses.A_DIM)

    if title:
        t = f" {title} "
        stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        stdscr.addnstr(y, x + 2, t, max(0, w - 4))
        stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)


def wrap(text: str, width: int) -> list[str]:
    out: list[str] = []
    for ln in text.splitlines():
        if not ln:
            out.append("")
            continue
        out.extend(
            textwrap.wrap(
                ln,
                width=width,
                replace_whitespace=False,
                drop_whitespace=False,
            )
            or [""]
        )
    return out


def msg_any_key(stdscr, app_name: str, title: str, text: str):
    while True:
        stdscr.erase()
        draw_header(stdscr, app_name, title)
        h, w = stdscr.getmaxyx()
        box_h = h - 4
        box_w = w - 4
        draw_box(stdscr, 2, 2, box_h, box_w, title="Message")
        lines = wrap(text, max(20, box_w - 4))
        max_body = box_h - 4
        for i in range(min(max_body, len(lines))):
            stdscr.addnstr(3 + i, 4, lines[i], box_w - 6)
        stdscr.attron(curses.A_DIM)
        stdscr.addnstr(h - 1, 2, "Press any key to continue", w - 4)
        stdscr.attroff(curses.A_DIM)
        stdscr.refresh()
        stdscr.getch()
        return


def prompt(stdscr, prompt_text: str, default: str = "", secret: bool = False) -> str:
    curses.curs_set(1)
    h, w = stdscr.getmaxyx()
    stdscr.attron(curses.A_REVERSE)
    stdscr.addnstr(h - 1, 0, " " * (w - 1), w - 1)
    msg = f"{prompt_text} "
    stdscr.addnstr(h - 1, 0, msg, w - 1)
    stdscr.attroff(curses.A_REVERSE)
    stdscr.refresh()
    if secret:
        curses.noecho()
    else:
        curses.echo()
    maxlen = max(1, w - len(msg) - 2)
    try:
        val = (
            stdscr.getstr(h - 1, min(w - 2, len(msg)), maxlen)
            .decode("utf-8", errors="replace")
            .strip()
        )
    except Exception:
        val = ""
    curses.noecho()
    curses.curs_set(0)
    return val if val else default


def confirm_typed(stdscr, app_name: str, title: str, text: str, expected: str) -> bool:
    msg_any_key(stdscr, app_name, title, text + f"\n\nType exactly: {expected}")
    typed = prompt(stdscr, "Confirm:", default="")
    return typed == expected


def menu(stdscr, app_name: str, title: str, items: list[str], subtitle: str | None = None):
    idx = 0
    while True:
        stdscr.erase()
        draw_header(stdscr, app_name, title)
        h, w = stdscr.getmaxyx()
        box_h = h - 4
        box_w = w - 4
        draw_box(stdscr, 2, 2, box_h, box_w, title=subtitle or "Select")

        y0 = 4
        max_items = box_h - 4
        start = 0
        if idx >= max_items:
            start = idx - max_items + 1
        vis = items[start : start + max_items]

        for i, it in enumerate(vis):
            y = y0 + i
            if start + i == idx:
                stdscr.attron(curses.A_REVERSE)
                stdscr.addnstr(y, 4, it, box_w - 6)
                stdscr.attroff(curses.A_REVERSE)
            else:
                stdscr.addnstr(y, 4, it, box_w - 6)

        stdscr.refresh()
        k = stdscr.getch()
        if k == ord("q"):
            return "quit", None
        if k in (27, curses.KEY_BACKSPACE, 127):
            return "back", None
        if k in (curses.KEY_DOWN, ord("j")):
            idx = min(len(items) - 1, idx + 1)
        elif k in (curses.KEY_UP, ord("k")):
            idx = max(0, idx - 1)
        elif k in (curses.KEY_ENTER, 10, 13):
            return "open", idx

