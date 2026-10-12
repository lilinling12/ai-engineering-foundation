"""G2.0 read-only synthetic Guest serial readiness observer.

The per-run random challenge binds one serial line to this operator VMM launch,
but it is not a secret or cryptographic proof; a malicious Guest can forge it.
This module never executes input, accepts network traffic or starts a Guest.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import stat

PREFIX = "FOUNDATION_GUEST_READY_V1"
NONCE = re.compile(r"^[0-9a-f]{32}$")
MAX_SERIAL_BYTES = 256 * 1024


def checked_boot_args(base: str, nonce: str) -> str:
    if not NONCE.fullmatch(nonce):
        raise ValueError("Invalid synthetic readiness challenge")
    # Passed via the kernel command line, readable inside the guest:
    # never use this for credentials/authentication.
    return base + " foundation.probe_token=" + nonce


def guest_marker_observed(serial_path: Path, nonce: str) -> bool:
    """Require an exact, standalone line in bounded local serial output."""
    if not NONCE.fullmatch(nonce) or not serial_path.is_absolute():
        return False
    try:
        st = serial_path.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_SERIAL_BYTES:
            return False
        with serial_path.open("rb") as fh:
            content = fh.read(MAX_SERIAL_BYTES + 1)
        if len(content) > MAX_SERIAL_BYTES:
            return False
        marker = (PREFIX + " " + nonce).encode("ascii")
        return any(line == marker for line in content.splitlines())
    except (OSError, ValueError):
        return False
