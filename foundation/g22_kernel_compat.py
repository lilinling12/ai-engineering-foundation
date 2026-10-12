"""G2.2 synthetic x86_64 Firecracker guest-kernel *compatibility* preflight.

A trusted operator must independently bind the Kconfig to the actual kernel
build; matching a user-provided SHA256 does not certify source or provenance.
No KVM, network, downloads, shell commands or VM invocation occur here.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import stat

KCONFIG_LIMIT = 2 * 1024 * 1024
SHA256 = re.compile(r"^[a-f0-9]{64}$")
# This project supports the fixed x86_64 ACPI + VirtIO-MMIO + ext4 rootfs
# fixture only. Each needed driver must be built-in (=y), not a module (=m).
GUEST_REQUIRED = frozenset({
    "CONFIG_64BIT",
    "CONFIG_X86_64",
    "CONFIG_BINFMT_ELF",
    "CONFIG_BLOCK",
    "CONFIG_VIRTIO",
    "CONFIG_VIRTIO_MMIO",
    "CONFIG_VIRTIO_BLK",
    "CONFIG_EXT4_FS",
    "CONFIG_PROC_FS",
    "CONFIG_KVM_GUEST",
    "CONFIG_ACPI",
    "CONFIG_PCI",
    "CONFIG_SERIAL_8250",
    "CONFIG_SERIAL_8250_CONSOLE",
    "CONFIG_PRINTK",
})


@dataclass(frozen=True)
class KernelCompatibility:
    classification: str
    kernel_sha256: str
    config_sha256: str
    requirements: tuple[str, ...]
    config_is_kernel_authenticated: bool = False
    kernel_booted: bool = False


class KernelPreflightDenied(ValueError):
    pass


def _load_checked(path: Path, expected: str, *, limit: int) -> bytes:
    if (not isinstance(path, Path) or not path.is_absolute() or
            path.is_symlink() or ".." in path.parts or
            path.resolve(strict=True) != path or
            not SHA256.fullmatch(expected)):
        raise KernelPreflightDenied("Untrusted or noncanonical kernel artifact")
    st = path.stat()
    if (not stat.S_ISREG(st.st_mode) or st.st_size < 64 or
            st.st_size > limit or st.st_mode & 0o022):
        raise KernelPreflightDenied("Kernel artifact is oversized, writable or missing")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit or hashlib.sha256(data).hexdigest() != expected:
        raise KernelPreflightDenied("Kernel artifact SHA256 mismatch")
    return data


def inspect_kernel_config(
    kernel: Path, kernel_sha256: str,
    kconfig: Path, config_sha256: str,
) -> KernelCompatibility:
    """Require raw uncompressed little-endian x86_64 ELF and built-in drivers.

    Companion Kconfig is merely operator-claimed: this function cannot prove
    it was used to compile the kernel image.
    """
    header = _load_checked(kernel, kernel_sha256, limit=512 * 1024 * 1024)
    if (header[:4] != b"\x7fELF" or header[4] != 2 or header[5] != 1 or
            int.from_bytes(header[18:20], "little") != 62):
        raise KernelPreflightDenied("Only little-endian x86_64 ELF vmlinux is reviewed")
    text = _load_checked(kconfig, config_sha256, limit=KCONFIG_LIMIT)
    try:
        cfg = text.decode("ascii")
    except UnicodeDecodeError:
        raise KernelPreflightDenied("Kconfig must be ASCII") from None
    values: dict[str, str] = {}
    for line in cfg.splitlines():
        if not line.startswith("CONFIG_"):
            continue
        key, sep, value = line.partition("=")
        if not sep or key in values:
            raise KernelPreflightDenied("Ambiguous or malformed kernel configuration")
        values[key] = value
    missing = sorted(key for key in GUEST_REQUIRED if values.get(key) != "y")
    if missing:
        raise KernelPreflightDenied("Built-in kernel requirements missing: " + ",".join(missing))
    return KernelCompatibility(
        "x86_64-elf-built-in-config-claimed-NOT-booted",
        kernel_sha256, config_sha256, tuple(sorted(GUEST_REQUIRED)),
    )
