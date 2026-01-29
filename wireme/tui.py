from __future__ import annotations

import curses
import time
from pathlib import Path

from . import qr, util, wg
from .ui import confirm_typed, draw_box, init_curses, menu, msg_any_key, prompt, draw_header

APP_NAME = "wireme"


# ---------- Screens ----------


def iface_overview_screen(stdscr, conf_path: Path):
    iface = conf_path.stem
    cfg, peers, _ = wg.parse_conf(conf_path)
    _, live = wg.live_dump(iface) or (None, {})
    net_str, server_ip = wg.iface_network_and_ip(cfg.get("Address") or "")

    while True:
        stdscr.erase()
        draw_header(stdscr, APP_NAME, f"{iface} • Overview")
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
        msg_any_key(stdscr, APP_NAME, "QR", f"No saved client configs at:\n{base}")
        return
    confs = sorted(base.glob("*.conf"))
    if not confs:
        msg_any_key(stdscr, APP_NAME, "QR", f"No *.conf in:\n{base}")
        return
    act, idx = menu(stdscr, APP_NAME, f"{iface}", [c.name for c in confs] + ["Back"], subtitle="Show QR (saved configs)")
    if act != "open" or idx == len(confs):
        return
    target = confs[idx]
    rc, out, err = qr.qr_from_text(util.read_text(target))
    if rc != 0 or not out:
        msg_any_key(stdscr, APP_NAME, "QR", f"QR failed:\n{err or out}")
        return
    msg_any_key(stdscr, APP_NAME, f"QR • {iface}/{target.stem}", out)


def wg_add_peer(stdscr, conf_path: Path):
    iface = conf_path.stem
    cfg, peers, raw_lines = wg.parse_conf(conf_path)

    smart = prompt(stdscr, "Is this for a smartphone? (y/N):", default="n").lower().startswith("y")
    profile = "smartphone" if smart else "desktop"

    name_raw = prompt(stdscr, "Peer name:", default="")
    name = util.sanitize_name(name_raw)
    if not name:
        msg_any_key(stdscr, APP_NAME, "Add peer", "Cancelled (invalid name).")
        return

    suggested_ip = wg.next_free_client_ip(cfg.get("Address") or "", peers) or ""
    client_ip = prompt(
        stdscr,
        f"Client VPN IP (suggested {suggested_ip or '10.0.0.2/32'}):",
        default=suggested_ip,
    ).strip()
    if not client_ip:
        msg_any_key(stdscr, APP_NAME, "Add peer", "Cancelled (no IP).")
        return
    if "/" not in client_ip:
        client_ip = client_ip + "/32"

    rc, priv, err = util.run(["wg", "genkey"])
    if rc != 0 or not priv:
        msg_any_key(stdscr, APP_NAME, "Add peer", f"wg genkey failed:\n{err}")
        return
    pub = wg.pubkey_from_priv(priv)
    if not pub:
        msg_any_key(stdscr, APP_NAME, "Add peer", "Failed to derive public key.")
        return
    rc, psk, _ = util.run(["wg", "genpsk"])
    psk = psk.strip() if rc == 0 else ""

    s_priv = cfg.get("PrivateKey")
    if not s_priv:
        msg_any_key(stdscr, APP_NAME, "Add peer", "Interface PrivateKey not found in config.")
        return
    s_pub = wg.pubkey_from_priv(s_priv)
    if not s_pub:
        msg_any_key(stdscr, APP_NAME, "Add peer", "Failed to derive server public key.")
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
                APP_NAME,
                "Add peer",
                f"Saved, but apply failed.\n\nBackup: {backup}\n\nError:\n{aerr}",
            )
        else:
            msg_any_key(stdscr, APP_NAME, "Add peer", f"Saved + applied.\n\nBackup: {backup}")
    else:
        msg_any_key(stdscr, APP_NAME, "Add peer", f"Saved (not applied).\n\nBackup: {backup}")

    show_qr = prompt(stdscr, "Show QR now? (y/N):", default="n").lower().startswith("y")
    if show_qr:
        rc, out, qerr = qr.qr_from_text(client_text)
        if rc == 0 and out:
            msg_any_key(stdscr, APP_NAME, f"QR • {iface}/{name}", out)
        else:
            msg_any_key(stdscr, APP_NAME, "QR", f"QR failed:\n{qerr or out}")

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
        msg_any_key(stdscr, APP_NAME, "Saved client config", f"Saved:\n{client_conf}")
    else:
        msg_any_key(stdscr, APP_NAME, "Client config not saved", "Not saved on disk.\n(You can re-run add and choose to save next time.)")


def wg_delete_peer(stdscr, conf_path: Path):
    iface = conf_path.stem
    _, peers, raw_lines = wg.parse_conf(conf_path)
    if not peers:
        msg_any_key(stdscr, APP_NAME, "Delete peer", "No peers in config.")
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

    act, idx = menu(stdscr, APP_NAME, f"{iface}", labels + ["Back"], subtitle="Delete peer")
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
        APP_NAME,
        "Confirm delete",
        f"Remove peer from {conf_path}:\n\nName: {name}\nPublicKey: {pub}\nAllowedIPs: {aips}\n\nBackups will be created.{extra}",
        expected=confirm_str,
    )
    if not ok:
        msg_any_key(stdscr, APP_NAME, "Delete peer", "Cancelled.")
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
                APP_NAME,
                "Delete peer",
                f"Removed from config, but apply failed.\n\nBackup: {backup}\n\nError:\n{aerr}",
            )
            return

    msg = f"Removed peer.\n\nBackup: {backup}"
    if deleted_files:
        msg += "\n\nDeleted matching client config(s):\n" + "\n".join(deleted_files)
    if delete_errors:
        msg += "\n\nFailed to delete some files:\n" + "\n".join(delete_errors)
    msg_any_key(stdscr, APP_NAME, "Delete peer", msg)


def _main(stdscr):
    init_curses(stdscr)

    if not util.have("wg"):
        msg_any_key(stdscr, APP_NAME, "WireGuard", "wg not installed.")
        return

    confs = wg.interfaces()
    if not confs:
        msg_any_key(stdscr, APP_NAME, "WireGuard", "No /etc/wireguard/*.conf found.")
        return

    while True:
        items: list[str] = []
        for c in confs:
            iface = c.stem
            _, live = wg.live_dump(iface) or (None, {})
            status = "up" if live is not None else "down"
            items.append(f"{iface}  •  {status}  •  {c}")
        items.append("Quit")

        act, idx = menu(stdscr, APP_NAME, "WireGuard", items, subtitle=("root" if util.is_root() else "not root"))
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
                act2, j = menu(stdscr, APP_NAME, iface, choices, subtitle="Actions")
                if act2 == "quit":
                    return
                if act2 == "back":
                    break
                if act2 == "open":
                    if j == 0:
                        iface_overview_screen(stdscr, conf_path)
                    elif j == 1:
                        if not util.is_root():
                            msg_any_key(stdscr, APP_NAME, "Add peer", "Run as root for add peer.")
                        else:
                            wg_add_peer(stdscr, conf_path)
                    elif j == 2:
                        wg_show_qr_saved(stdscr, iface)
                    elif j == 3:
                        if not util.is_root():
                            msg_any_key(stdscr, APP_NAME, "Delete peer", "Run as root for delete peer.")
                        else:
                            wg_delete_peer(stdscr, conf_path)
                    elif j == 4:
                        break


def run():
    curses.wrapper(_main)
