from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from shutil import which


def have(cmd: str) -> bool:
    return which(cmd) is not None


def run(cmd, timeout: int = 20, check: bool = False, input_text: str | None = None):
    try:
        p = subprocess.run(
            cmd,
            text=True,
            input=input_text,
            capture_output=True,
            timeout=timeout,
            check=check,
        )
        return p.returncode, (p.stdout or "").rstrip("\n"), (p.stderr or "").rstrip("\n")
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except FileNotFoundError:
        return 127, "", "not found"
    except subprocess.CalledProcessError as e:
        return e.returncode, (e.stdout or "").rstrip("\n"), (e.stderr or "").rstrip("\n")


def bash(cmd: str, timeout: int = 20):
    return run(["bash", "-lc", cmd], timeout=timeout)


def read_text(path: Path, max_bytes: int = 2_000_000) -> str:
    try:
        data = path.read_bytes()
        if len(data) > max_bytes:
            data = data[:max_bytes] + b"\n\n[truncated]\n"
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_root() -> bool:
    return os.geteuid() == 0


def sanitize_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"[^a-zA-Z0-9._-]", "", name)
    name = name.strip("._-")
    return name[:64] if name else ""
