from __future__ import annotations

import os
import re
from pathlib import Path

from . import util, wg


def parse_iface_name_from_text(conf_text: str) -> str | None:
    """
    Best-effort parse for interface name. WireGuard configs don't include iface name;
    we accept a comment like '# iface: wg0' if present.
    """
    for ln in conf_text.splitlines():
        m = re.match(r"#\s*iface\s*:\s*([a-zA-Z0-9_.-]+)\s*$", ln.strip())
        if m:
            return m.group(1)
    return None


def validate_client_conf_text(conf_text: str) -> tuple[bool, str]:
    txt = conf_text.strip()
    if not txt:
        return False, "Empty config."
    if "[Interface]" not in txt:
        return False, "Missing [Interface] section."
    if "PrivateKey" not in txt:
        return False, "Missing PrivateKey."
    if "[Peer]" not in txt:
        return False, "Missing [Peer] section."
    return True, "OK"


def install_client_conf(iface: str, conf_text: str) -> tuple[bool, str]:
    ok, msg = validate_client_conf_text(conf_text)
    if not ok:
        return False, msg

    if not iface or not re.match(r"^[a-zA-Z0-9_.-]{1,32}$", iface):
        return False, "Invalid interface name."

    target = wg.WIREGUARD_DIR / f"{iface}.conf"
    backup = None
    try:
        wg.WIREGUARD_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return False, f"Failed to create {wg.WIREGUARD_DIR}: {e}"

    if target.exists():
        try:
            backup = wg.backup(target)
        except Exception as e:
            return False, f"Failed to create backup: {e}"

    try:
        target.write_text(conf_text.rstrip() + "\n")
        os.chmod(target, 0o600)
    except Exception as e:
        return False, f"Failed to write {target}: {e}"

    if backup:
        return True, f"Installed {target}\nBackup: {backup}"
    return True, f"Installed {target}"


def wg_quick_up(iface: str):
    if not util.have("wg-quick"):
        return 1, "", "wg-quick missing"
    return util.run(["wg-quick", "up", iface], timeout=60)


def wg_quick_down(iface: str):
    if not util.have("wg-quick"):
        return 1, "", "wg-quick missing"
    return util.run(["wg-quick", "down", iface], timeout=60)


def wg_show(iface: str):
    return util.run(["wg", "show", iface], timeout=10)

