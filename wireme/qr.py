from __future__ import annotations

from . import util


def qr_from_text(config_text: str):
    if not util.have("qrencode"):
        return 1, "", "qrencode not installed"
    return util.run(["qrencode", "-t", "ansiutf8"], timeout=10, input_text=config_text)
