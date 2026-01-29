from __future__ import annotations

import hashlib
import ipaddress
import re
import shlex
import time
from pathlib import Path

from . import util

WIREGUARD_DIR = Path("/etc/wireguard")
CLIENTS_DIR = Path("/etc/wireguard/clients")

META_PREFIX = "wireme-"
_META_RE = re.compile(r"#\s*wireme-([a-zA-Z0-9_-]+)\s*:\s*(.*)$")


def interfaces() -> list[Path]:
    if not WIREGUARD_DIR.exists():
        return []
    return sorted([p for p in WIREGUARD_DIR.glob("*.conf") if p.is_file()])


def live_dump(iface: str):
    rc, dump, _ = util.run(["wg", "show", iface, "dump"])
    if rc != 0 or not dump:
        return None, {}
    rows = dump.splitlines()
    live: dict[str, dict[str, str]] = {}
    for ln in rows[1:]:
        parts = ln.split("\t")
        if len(parts) >= 8:
            pub, _psk, ep, allowed, hs, rx, tx, keep = parts[:8]
            live[pub] = {
                "endpoint": ep,
                "allowed": allowed,
                "hs": hs,
                "rx": rx,
                "tx": tx,
                "keep": keep,
            }
    return rows[0], live


def parse_conf(conf_path: Path):
    txt = util.read_text(conf_path)
    lines = txt.splitlines(True)

    iface = {"Address": None, "ListenPort": None, "PrivateKey": None, "DNS": None}
    peers: list[dict] = []

    section = None
    current = None
    start_idx = None
    meta_pending: dict[str, str] = {}

    def flush_peer(end_idx: int):
        nonlocal current, start_idx
        if current is not None:
            current["start"] = start_idx
            current["end"] = end_idx
            peers.append(current)
        current = None
        start_idx = None

    for i, raw in enumerate(lines):
        ln = raw.strip()

        # metadata lines
        if ln.startswith("#") and META_PREFIX in ln:
            m = _META_RE.match(ln)
            if m:
                meta_pending[m.group(1)] = m.group(2).strip()
                continue

        if ln.startswith("[") and ln.endswith("]"):
            tag = ln.lower()
            if tag == "[interface]":
                flush_peer(i)
                section = "iface"
                meta_pending = {}
            elif tag == "[peer]":
                flush_peer(i)
                section = "peer"
                current = dict(meta_pending)
                for k in ["name", "created", "profile", "note"]:
                    current.setdefault(k, None)
                for k in [
                    "PublicKey",
                    "AllowedIPs",
                    "Endpoint",
                    "PresharedKey",
                    "PersistentKeepalive",
                ]:
                    current.setdefault(k, None)
                start_idx = i
                meta_pending = {}
            else:
                section = None
            continue

        if "=" in ln:
            k, v = [x.strip() for x in ln.split("=", 1)]
            if section == "iface" and k in iface:
                iface[k] = v
            elif section == "peer" and current is not None and k in current:
                current[k] = v

    flush_peer(len(lines))
    return iface, peers, lines


def pubkey_from_priv(priv: str):
    rc, out, _ = util.run(["wg", "pubkey"], input_text=(priv.strip() + "\n"))
    return out.strip() if rc == 0 else None


def backup(conf_path: Path) -> Path:
    ts = time.strftime("%Y%m%d-%H%M%S")
    b = conf_path.with_name(conf_path.name + f".bak-{ts}")
    b.write_bytes(conf_path.read_bytes())
    return b


def apply_now(iface: str):
    if not util.have("wg-quick"):
        return 1, "", "wg-quick missing"
    return util.bash(
        f"wg syncconf {shlex.quote(iface)} <(wg-quick strip {shlex.quote(iface)})",
        timeout=20,
    )


def guess_public_ipv4():
    rc, out, _ = util.bash("ip -4 -o addr show scope global | awk '{print $4}' || true")
    if rc == 0 and out:
        cands = out.splitlines()
        for c in cands:
            ip = c.split("/")[0]
            try:
                a = ipaddress.ip_address(ip)
                if not (a.is_private or a.is_loopback or a.is_link_local):
                    return ip
            except Exception:
                pass
        return cands[0].split("/")[0]
    return None


def iface_network_and_ip(addr_field: str):
    if not addr_field:
        return None, None
    first = addr_field.split(",")[0].strip()
    try:
        ii = ipaddress.ip_interface(first)
        return ii.network.with_prefixlen, str(ii.ip)
    except Exception:
        return None, None


def next_free_client_ip(addr_field: str, peers):
    net_str, server_ip = iface_network_and_ip(addr_field)
    if not net_str:
        return None
    net = ipaddress.ip_network(net_str, strict=False)
    used = set()
    if server_ip:
        used.add(ipaddress.ip_address(server_ip))
    for p in peers:
        a = (p.get("AllowedIPs") or "")
        for part in a.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                used.add(ipaddress.ip_interface(part).ip)
            except Exception:
                pass
    for host in net.hosts():
        if host not in used:
            return f"{host}/32"
    return None


def format_hs(hs: str):
    try:
        hs_i = int(hs)
        if hs_i == 0:
            return "never"
        age = int(time.time()) - hs_i
        if age < 60:
            return f"{age}s"
        if age < 3600:
            return f"{age//60}m"
        if age < 86400:
            return f"{age//3600}h"
        return f"{age//86400}d"
    except Exception:
        return "-"


def pub_fingerprint(pub: str) -> str:
    return hashlib.sha256(pub.encode("utf-8", errors="ignore")).hexdigest()[:8] if pub else "unknown"


def client_privkey_from_conf_text(text: str):
    # naive parse: first "PrivateKey = ..." under any section
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = [x.strip() for x in ln.split("=", 1)]
        if k == "PrivateKey" and v:
            return v
    return None


def client_pubkey_from_file(path: Path):
    txt = util.read_text(path)
    priv = client_privkey_from_conf_text(txt)
    if not priv:
        return None
    return pubkey_from_priv(priv)
