from __future__ import annotations

import curses
from pathlib import Path

from . import util, wg
from .client_ops import install_client_conf, parse_iface_name_from_text, wg_quick_down, wg_quick_up, wg_show
from .ui import init_curses, menu, msg_any_key, prompt, draw_header, draw_box

APP_NAME = "wiremec"


def _pick_iface_from_existing(stdscr) -> str | None:
    confs = wg.interfaces()
    if not confs:
        return None
    items = [p.stem for p in confs] + ["Back"]
    act, idx = menu(stdscr, APP_NAME, "Pick interface", items, subtitle="Existing /etc/wireguard/*.conf")
    if act != "open" or idx is None or idx == len(items) - 1:
        return None
    return items[idx]


def _status_screen(stdscr, iface: str):
    rc, out, err = wg_show(iface)
    if rc != 0:
        msg_any_key(stdscr, APP_NAME, "Status", f"wg show failed for {iface}.\n\n{err or out}")
        return

    # Also show a quick up/down guess via dump.
    _, live = wg.live_dump(iface) or (None, {})
    status = "up" if live is not None else "down"
    msg_any_key(stdscr, APP_NAME, "Status", f"Interface: {iface}\nStatus: {status}\n\n{out}")


def _import_config_flow(stdscr):
    if not util.is_root():
        msg_any_key(stdscr, APP_NAME, "Import", "Run as root to write /etc/wireguard/*.conf and run wg-quick.")
        return

    method_items = [
        "Paste config",
        "Read config from file path",
        "Back",
    ]
    act, idx = menu(stdscr, APP_NAME, "Import client config", method_items, subtitle="Select input method")
    if act != "open" or idx is None or idx == 2:
        return

    conf_text = ""
    if idx == 0:
        msg_any_key(
            stdscr,
            APP_NAME,
            "Paste",
            "Paste the config at the prompt.\n\nTip: You can also include a line like:\n# iface: wg0\n\nThe paste prompt is one line; if you need multi-line, use the file path option.",
        )
        conf_text = prompt(stdscr, "Config (single line):", default="").strip()
    elif idx == 1:
        path_str = prompt(stdscr, "Path to client .conf:", default="").strip()
        if not path_str:
            msg_any_key(stdscr, APP_NAME, "Import", "Cancelled.")
            return
        p = Path(path_str)
        if not p.exists():
            msg_any_key(stdscr, APP_NAME, "Import", f"File not found:\n{p}")
            return
        conf_text = util.read_text(p)

    if not conf_text.strip():
        msg_any_key(stdscr, APP_NAME, "Import", "Empty config.")
        return

    suggested_iface = parse_iface_name_from_text(conf_text) or ""
    iface = prompt(stdscr, f"Interface name (e.g. wg0) (suggested {suggested_iface or 'wg0'}):", default=suggested_iface or "wg0").strip()
    ok, msg = install_client_conf(iface, conf_text)
    if not ok:
        msg_any_key(stdscr, APP_NAME, "Import", msg)
        return

    msg_any_key(stdscr, APP_NAME, "Import", msg)

    bring_up = prompt(stdscr, "Bring interface up now? (y/N):", default="n").lower().startswith("y")
    if bring_up:
        rc, out, err = wg_quick_up(iface)
        if rc != 0:
            msg_any_key(stdscr, APP_NAME, "wg-quick up", f"Failed.\n\n{err or out}")
        else:
            msg_any_key(stdscr, APP_NAME, "wg-quick up", out or "OK")


def _iface_actions(stdscr, iface: str):
    while True:
        items = [
            "Status (wg show)",
            "Bring up (wg-quick up)",
            "Bring down (wg-quick down)",
            "Back",
        ]
        act, idx = menu(stdscr, APP_NAME, iface, items, subtitle="Actions")
        if act == "quit":
            return "quit"
        if act in ("back",) or idx == 3:
            return "back"
        if act == "open":
            if idx == 0:
                _status_screen(stdscr, iface)
            elif idx == 1:
                if not util.is_root():
                    msg_any_key(stdscr, APP_NAME, "Up", "Run as root for wg-quick up.")
                    continue
                rc, out, err = wg_quick_up(iface)
                msg_any_key(stdscr, APP_NAME, "wg-quick up", out if rc == 0 else (err or out))
            elif idx == 2:
                if not util.is_root():
                    msg_any_key(stdscr, APP_NAME, "Down", "Run as root for wg-quick down.")
                    continue
                rc, out, err = wg_quick_down(iface)
                msg_any_key(stdscr, APP_NAME, "wg-quick down", out if rc == 0 else (err or out))


def _main(stdscr):
    init_curses(stdscr)

    if not util.have("wg"):
        msg_any_key(stdscr, APP_NAME, "WireGuard", "wg not installed.")
        return

    while True:
        stdscr.erase()
        draw_header(stdscr, APP_NAME, "Client")
        h, w_ = stdscr.getmaxyx()
        draw_box(stdscr, 2, 2, h - 4, w_ - 4, title=("root" if util.is_root() else "not root"))
        stdscr.refresh()

        items = [
            "Import client config",
            "Manage existing interface",
            "Quit",
        ]
        act, idx = menu(stdscr, APP_NAME, "wiremec", items, subtitle="Select")
        if act == "quit" or idx == 2:
            return
        if act == "open":
            if idx == 0:
                _import_config_flow(stdscr)
            elif idx == 1:
                iface = _pick_iface_from_existing(stdscr)
                if iface:
                    out = _iface_actions(stdscr, iface)
                    if out == "quit":
                        return


def run():
    curses.wrapper(_main)

