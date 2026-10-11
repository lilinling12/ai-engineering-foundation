"""G1.8 zero-secret Firecracker host preflight: KVM presence AND real ioctl.

This is a capability diagnostic only. It neither starts a VM nor attests
host identity. A successful CI *job* is not proof KVM is available.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import errno
import fcntl
import json
import os
from pathlib import Path
import platform
import stat
import sys
from typing import Callable

from .__main__ import ROOT

# Linux /usr/include/linux/kvm.h: _IO(KVMIO, 0x00), KVMIO = 0xAE
KVM_GET_API_VERSION = 0xAE00
EXPECTED_KVM_API_VERSION = 12
KVM_DEVICE = Path("/dev/kvm")

@dataclass(frozen=True)
class KvmCapability:
    result: str
    reason: str
    api_version: int | None
    device_is_char: bool

def probe_kvm(
    *,
    system: str | None = None,
    lstat_device: Callable = os.lstat,
    open_device: Callable = os.open,
    ioctl: Callable = fcntl.ioctl,
    fstat_device: Callable = os.fstat,
    close_device: Callable = os.close,
) -> KvmCapability:
    """Fail closed on permission, unexpected device identity, or ioctl errors.

    Injection hooks exist for unit testing; CLI has no device/command inputs.
    """
    if (system or platform.system()) != "Linux":
        return KvmCapability("blocked", "unsupported-operating-system", None, False)
    try:
        entry = lstat_device(KVM_DEVICE)
    except FileNotFoundError:
        return KvmCapability("blocked", "kvm-device-missing", None, False)
    except OSError:
        return KvmCapability("blocked", "kvm-device-stat-failed", None, False)
    if not stat.S_ISCHR(entry.st_mode):
        return KvmCapability("blocked", "kvm-not-character-device", None, False)
    flags = os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = open_device(KVM_DEVICE, flags)
    except OSError as exc:
        reason = "kvm-permission-denied" if exc.errno in (errno.EACCES, errno.EPERM) else "kvm-open-failed"
        return KvmCapability("blocked", reason, None, True)
    try:
        opened = fstat_device(fd)
        if not stat.S_ISCHR(opened.st_mode):
            return KvmCapability("blocked", "opened-device-not-character", None, True)
        try:
            version = ioctl(fd, KVM_GET_API_VERSION, 0)
        except OSError:
            return KvmCapability("blocked", "kvm-ioctl-failed", None, True)
        if type(version) is not int or version != EXPECTED_KVM_API_VERSION:
            return KvmCapability("blocked", "unsupported-kvm-api", version if type(version) is int else None, True)
        return KvmCapability("available", "kvm-api-version-confirmed", version, True)
    except OSError:
        return KvmCapability("blocked", "opened-device-stat-failed", None, True)
    finally:
        close_device(fd)

def write_preflight() -> Path:
    probe = probe_kvm()
    result = {
        "contract": "foundation.kvm-host-preflight/v0",
        "trustLevel": "github-ci-unattested",
        "assessment": "capability-probe-only-NOT-VM-isolation",
        "runner": "github-hosted-diagnostic-NOT-attested-host",
        "commit": os.environ.get("GITHUB_SHA"),
        "observedAt": datetime.now(timezone.utc).isoformat(),
        "architecture": platform.machine(),
        "kvm": asdict(probe),
        "microVmStarted": False,
        "firecrackerInstalled": False,
        "inferenceCredentialsUsed": False,
        "arbitraryAgentCodeExecuted": False,
        "vmAdmissionAllowed": False,
    }
    dest = ROOT / "artifacts" / "g18-kvm-host-preflight.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"kvmCapability": probe.result, "reason": probe.reason,
                      "apiVersion": probe.api_version, "vmStarted": False}))
    return dest

def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Probe Linux KVM capability without starting a VM")
    parser.add_argument("--require-kvm", action="store_true",
                        help="Exit nonzero unless /dev/kvm and KVM API are available")
    opts = parser.parse_args(argv)
    artifact = write_preflight()
    if not opts.require_kvm:
        # Green recording job is NOT proof a KVM host was admitted.
        return 0
    result = json.loads(artifact.read_text(encoding="utf-8"))
    return 0 if result["kvm"]["result"] == "available" else 3

if __name__ == "__main__":
    sys.exit(main())
