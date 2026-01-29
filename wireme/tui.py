from __future__ import annotations

import curses
import textwrap
import time
from pathlib import Path

from . import qr, util, wg

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


def draw_header(stdscr, title: str):
    _h, w = stdscr.getmaxyx()
    stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
    stdscr.addnstr(0, 0, f" wireme  •  {title}", w - 1)
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


def msg_any_key(stdscr, title: str, text: str):
    while True:
        stdscr.erase()
        draw_header(stdscr, title)
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


def confirm_typed(stdscr, title: str, text: str, expected: str) -> bool:
    msg_any_key(stdscr, title, text + f"\n\nType exactly: {expected}")
    typed = prompt(stdscr, "Confirm:", default="")
    return typed == expected


def menu(stdscr, title: str, items: list[str], subtitle: str | None = None):
    idx = 0
    while True:
        stdscr.erase()
        draw_header(stdscr, title)
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


# ---------- Screens ----------


def iface_overview_screen(stdscr, conf_path: Path):
    iface = conf_path.stem
    cfg, peers, _ = wg.parse_conf(conf_path)
    _, live = wg.live_dump(iface) or (None, {})
    net_str, server_ip = wg.iface_network_and_ip(cfg.get("Address") or "")

    while True:
        stdscr.erase()
        draw_header(stdscr, f"{iface} • Overview")
        h, w_ = stdscr.getmaxyx()

        draw_box(stdscr, 2, 2, 6, w_ - 4, title="Interface")
        y = 3
        stdscr.addnstr(y, 4, f"Config: {conf_path}", w_ - 8)
        y += 1
        stdscr.addnstr(y, 4, f"Address: {cfg.get('Address') or '-'}", w_ - 8)
        y += 1
        stdscr.addnstr(y, 4, f"ListenPort: {cfg.get('ListenPort') or '-'}", w_ - 8)
        y += 1
        stdscr.addnstr(
            y,
            4,
            f"Network: {net_str or '-'}   Server VPN IP: {server_ip or '-'}",
            w_ - 8,
        )

        box_y = 9
        box_h = h - box_y - 2
        draw_box(stdscr, box_y, 2, box_h, w_ - 4, title=f"Peers ({len(peers)})")

        header = "name            vpn-ip(s)           hs     rx/tx        endpoint"
        stdscr.attron(curses.A_DIM)
        stdscr.addnstr(box_y + 1, 4, header, w_ - 8)
        stdscr.attroff(curses.A_DIM)

        max_rows = box_h - 3
        for i in range(min(max_rows, len(peers))):
            p = peers[i]
            name = (p.get("name") or "unnamed")[:14].ljust(14)
            aips = (p.get("AllowedIPs") or "-")[:20].ljust(20)
            pub = p.get("PublicKey") or ""
            li = live.get(pub, {})
            hs = wg.format_hs(li.get("hs", "0"))
            rx_ = li.get("rx", "-")
            tx_ = li.get("tx", "-")
            ep = (p.get("Endpoint") or li.get("endpoint") or "-")[:22]

            row_y = box_y + 2 + i

            attr = curses.color_pair(4) if hs == "never" else curses.color_pair(2)
            stdscr.addnstr(row_y, 4, name, w_ - 8)
            stdscr.addnstr(row_y, 4 + 15, aips, w_ - 8)
            stdscr.attron(attr)
            stdscr.addnstr(row_y, 4 + 36, hs.ljust(6), 6)
            stdscr.attroff(attr)
            stdscr.addnstr(row_y, 4 + 43, f"{rx_}/{tx_}".ljust(12), 12)
            stdscr.addnstr(row_y, 4 + 56, ep, w_ - 60)

        stdscr.attron(curses.A_DIM)
        stdscr.addnstr(h - 1, 2, "Press Esc/Backspace to go back", w_ - 4)
        stdscr.attroff(curses.A_DIM)
        stdscr.refresh()

        k = stdscr.getch()
        if k in (ord("q"), 27, curses.KEY_BACKSPACE, 127):
            return


def wg_show_qr_saved(stdscr, iface: str):
    base = wg.CLIENTS_DIR / iface
    if not base.exists():
        msg_any_key(stdscr, "QR", f"No saved client configs at:\n{base}")
        return
    confs = sorted(base.glob("*.conf"))
    if not confs:
        msg_any_key(stdscr, "QR", f"No *.conf in:\n{base}")
        return
    act, idx = menu(stdscr, f"{iface}", [c.name for c in confs] + ["Back"], subtitle="Show QR (saved configs)")
    if act != "open" or idx == len(confs):
        return
    target = confs[idx]
    rc, out, err = qr.qr_from_text(util.read_text(target))
    if rc != 0 or not out:
        msg_any_key(stdscr, "QR", f"QR failed:\n{err or out}")
        return
    msg_any_key(stdscr, f"QR • {iface}/{target.stem}", out)


def wg_add_peer(stdscr, conf_path: Path):
    iface = conf_path.stem
    cfg, peers, raw_lines = wg.parse_conf(conf_path)

    smart = prompt(stdscr, "Is this for a smartphone? (y/N):", default="n").lower().startswith("y")
    profile = "smartphone" if smart else "desktop"

    name_raw = prompt(stdscr, "Peer name:", default="")
    name = util.sanitize_name(name_raw)
    if not name:
        msg_any_key(stdscr, "Add peer", "Cancelled (invalid name).")
        return

    suggested_ip = wg.next_free_client_ip(cfg.get("Address") or "", peers) or ""
    client_ip = prompt(
        stdscr,
        f"Client VPN IP (suggested {suggested_ip or '10.0.0.2/32'}):",
        default=suggested_ip,
    ).strip()
    if not client_ip:
        msg_any_key(stdscr, "Add peer", "Cancelled (no IP).")
        return
    if "/" not in client_ip:
        client_ip = client_ip + "/32"

    rc, priv, err = util.run(["wg", "genkey"])
    if rc != 0 or not priv:
        msg_any_key(stdscr, "Add peer", f"wg genkey failed:\n{err}")
        return
    pub = wg.pubkey_from_priv(priv)
    if not pub:
        msg_any_key(stdscr, "Add peer", "Failed to derive public key.")
        return
    rc, psk, _ = util.run(["wg", "genpsk"])
    psk = psk.strip() if rc == 0 else ""

    s_priv = cfg.get("PrivateKey")
    if not s_priv:
        msg_any_key(stdscr, "Add peer", "Interface PrivateKey not found in config.")
        return
    s_pub = wg.pubkey_from_priv(s_priv)
    if not s_pub:
        msg_any_key(stdscr, "Add peer", "Failed to derive server public key.")
        return

    listen_port = (cfg.get("ListenPort") or "51820").strip()
    pub_ip = wg.guess_public_ipv4()
    default_ep = f"{pub_ip}:{listen_port}" if pub_ip else f":{listen_port}"
    endpoint = prompt(stdscr, f"Endpoint host:port (default {default_ep}):", default=default_ep).strip()

    net_str, server_vpn_ip = wg.iface_network_and_ip(cfg.get("Address") or "")
    if smart:
        route_default = f"{net_str or '10.0.0.0/24'}, {pub_ip + '/32' if pub_ip else 'PUBLIC_IP/32'}"
        dns_default = "1.1.1.1"
    else:
        route_default = f"{server_vpn_ip}/32" if server_vpn_ip else ""
        dns_default = ""

    route = prompt(stdscr, f"Client AllowedIPs (default {route_default}):", default=route_default).strip()
    dns = prompt(stdscr, f"Client DNS (default {dns_default or '(empty)'}):", default=dns_default).strip()
    note = prompt(stdscr, "Note (optional):", default="").strip()

    backup = wg.backup(conf_path)
    created = util.now_utc_iso()

    block: list[str] = []
    block.append("\n")
    block.append(f"# wireme-name: {name}\n")
    block.append(f"# wireme-created: {created}\n")
    block.append(f"# wireme-profile: {profile}\n")
    if note:
        block.append(f"# wireme-note: {note}\n")
    block.append("[Peer]\n")
    block.append(f"PublicKey = {pub}\n")
    if psk:
        block.append(f"PresharedKey = {psk}\n")
    block.append(f"AllowedIPs = {client_ip}\n")

    conf_path.write_text("".join(raw_lines) + "".join(block))

    client_config: list[str] = []
    client_config.append(f"# name: {name}\n")
    client_config.append(f"# created: {created}\n")
    client_config.append(f"# profile: {profile}\n")
    client_config.append("[Interface]\n")
    client_config.append(f"PrivateKey = {priv.strip()}\n")
    client_config.append(f"Address = {client_ip}\n")
    if dns:
        client_config.append(f"DNS = {dns}\n")
    client_config.append("\n[Peer]\n")
    client_config.append(f"PublicKey = {s_pub}\n")
    if psk:
        client_config.append(f"PresharedKey = {psk}\n")
    client_config.append(f"Endpoint = {endpoint}\n")
    if route:
        client_config.append(f"AllowedIPs = {route}\n")
    client_config.append("PersistentKeepalive = 25\n")
    client_text = "".join(client_config)

    apply_now = prompt(stdscr, "Apply now (wg syncconf)? (y/N):", default="n").lower().startswith("y")
    if apply_now:
        rc, _, aerr = wg.apply_now(iface)
        if rc != 0:
            msg_any_key(
                stdscr,
                "Add peer",
                f"Saved, but apply failed.\n\nBackup: {backup}\n\nError:\n{aerr}",
            )
        else:
            msg_any_key(stdscr, "Add peer", f"Saved + applied.\n\nBackup: {backup}")
    else:
        msg_any_key(stdscr, "Add peer", f"Saved (not applied).\n\nBackup: {backup}")

    show_qr = prompt(stdscr, "Show QR now? (y/N):", default="n").lower().startswith("y")
    if show_qr:
        rc, out, qerr = qr.qr_from_text(client_text)
        if rc == 0 and out:
            msg_any_key(stdscr, f"QR • {iface}/{name}", out)
        else:
            msg_any_key(stdscr, "QR", f"QR failed:\n{qerr or out}")

    save = prompt(stdscr, "Save client config on disk? (y/N):", default="n").lower().startswith("y")
    if save:
        client_dir = wg.CLIENTS_DIR / iface
        client_dir.mkdir(parents=True, exist_ok=True)
        fp = wg.pub_fingerprint(pub)
        client_conf = client_dir / f"{name}--{fp}.conf"
        if client_conf.exists():
            client_conf = client_dir / f"{name}--{fp}--{int(time.time())}.conf"
        client_conf.write_text(client_text)
        client_conf.chmod(0o600)
        msg_any_key(stdscr, "Saved client config", f"Saved:\n{client_conf}")
    else:
        msg_any_key(stdscr, "Client config not saved", "Not saved on disk.\n(You can re-run add and choose to save next time.)")


def wg_delete_peer(stdscr, conf_path: Path):
    iface = conf_path.stem
    _, peers, raw_lines = wg.parse_conf(conf_path)
    if not peers:
        msg_any_key(stdscr, "Delete peer", "No peers in config.")
        return

    labels: list[str] = []
    for p in peers:
        name = p.get("name") or "(unnamed)"
        created = p.get("created") or "unknown"
        prof = p.get("profile") or "-"
        aips = p.get("AllowedIPs") or "-"
        pub = p.get("PublicKey") or ""
        fp = wg.pub_fingerprint(pub)
        labels.append(f"{name}  •  {aips}  •  {prof}  •  {created}  •  {fp}")

    act, idx = menu(stdscr, f"{iface}", labels + ["Back"], subtitle="Delete peer")
    if act != "open" or idx == len(labels):
        return
    peer = peers[idx]

    name = peer.get("name") or "(unnamed)"
    pub = peer.get("PublicKey") or ""
    aips = peer.get("AllowedIPs") or "-"
    start = peer["start"]
    end = peer["end"]

    remove_start = start
    i = start - 1
    while i >= 0:
        ln = raw_lines[i].strip()
        if ln.startswith(f"# {wg.META_PREFIX}") or ln == "":
            remove_start = i
            i -= 1
            continue
        break

    # find matching saved client configs by pubkey derived from PrivateKey in file
    matches: list[Path] = []
    base = wg.CLIENTS_DIR / iface
    if base.exists():
        for f in sorted(base.glob("*.conf")):
            cpub = wg.client_pubkey_from_file(f)
            if cpub and pub and cpub == pub:
                matches.append(f)

    extra = ""
    if matches:
        extra = "\n\nMatching saved client config(s) to delete (pubkey match):\n" + "\n".join(f" - {m}" for m in matches)

    confirm_str = f"delete {name}"
    ok = confirm_typed(
        stdscr,
        "Confirm delete",
        f"Remove peer from {conf_path}:\n\nName: {name}\nPublicKey: {pub}\nAllowedIPs: {aips}\n\nBackups will be created.{extra}",
        expected=confirm_str,
    )
    if not ok:
        msg_any_key(stdscr, "Delete peer", "Cancelled.")
        return

    backup = wg.backup(conf_path)
    new_lines = raw_lines[:remove_start] + raw_lines[end:]
    conf_path.write_text("".join(new_lines))

    deleted_files: list[str] = []
    delete_errors: list[str] = []
    for m in matches:
        try:
            m.unlink()
            deleted_files.append(str(m))
        except Exception as e:
            delete_errors.append(f"{m}: {e}")

    apply_now = prompt(stdscr, "Apply now (wg syncconf)? (y/N):", default="n").lower().startswith("y")
    if apply_now:
        rc, _, aerr = wg.apply_now(iface)
        if rc != 0:
            msg_any_key(
                stdscr,
                "Delete peer",
                f"Removed from config, but apply failed.\n\nBackup: {backup}\n\nError:\n{aerr}",
            )
            return

    msg = f"Removed peer.\n\nBackup: {backup}"
    if deleted_files:
        msg += "\n\nDeleted matching client config(s):\n" + "\n".join(deleted_files)
    if delete_errors:
        msg += "\n\nFailed to delete some files:\n" + "\n".join(delete_errors)
    msg_any_key(stdscr, "Delete peer", msg)


def _main(stdscr):
    init_curses(stdscr)

    if not util.have("wg"):
        msg_any_key(stdscr, "WireGuard", "wg not installed.")
        return

    confs = wg.interfaces()
    if not confs:
        msg_any_key(stdscr, "WireGuard", "No /etc/wireguard/*.conf found.")
        return

    while True:
        items: list[str] = []
        for c in confs:
            iface = c.stem
            _, live = wg.live_dump(iface) or (None, {})
            status = "up" if live is not None else "down"
            items.append(f"{iface}  •  {status}  •  {c}")
        items.append("Quit")

        act, idx = menu(stdscr, "WireGuard", items, subtitle=("root" if util.is_root() else "not root"))
        if act in ("quit",):
            return
        if act == "open":
            if idx == len(confs):
                return
            conf_path = confs[idx]
            iface = conf_path.stem

            while True:
                choices = [
                    "Overview",
                    "Add peer (QR + optional save)",
                    "Show QR (saved configs)",
                    "Delete peer (typed confirmation + deletes matching saved config)",
                    "Back",
                ]
                act2, j = menu(stdscr, iface, choices, subtitle="Actions")
                if act2 == "quit":
                    return
                if act2 == "back":
                    break
                if act2 == "open":
                    if j == 0:
                        iface_overview_screen(stdscr, conf_path)
                    elif j == 1:
                        if not util.is_root():
                            msg_any_key(stdscr, "Add peer", "Run as root for add peer.")
                        else:
                            wg_add_peer(stdscr, conf_path)
                    elif j == 2:
                        wg_show_qr_saved(stdscr, iface)
                    elif j == 3:
                        if not util.is_root():
                            msg_any_key(stdscr, "Delete peer", "Run as root for delete peer.")
                        else:
                            wg_delete_peer(stdscr, conf_path)
                    elif j == 4:
                        break


def run():
    curses.wrapper(_main)
