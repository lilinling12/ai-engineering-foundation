"""G2.4 real synthetic Linux Guest boot with software-only QEMU TCG.

No KVM, no network, no model credentials, no user or model-supplied source.
A successful guest serial marker is FUNCTIONAL proof only for QEMU, NOT
Firecracker/Jailer/multi-tenant sandbox acceptance.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import signal
import subprocess
import sys
import tempfile
import time
import urllib.parse

from .__main__ import ROOT
from .g20_guest_serial import checked_boot_args, guest_marker_observed
from .g21_build_guest import build_guest, _sha256
from .g22_kernel_compat import inspect_kernel_config
from .g23_kernel_inventory import (
    _client, _read_bounded, BASE, KERNEL_KEY, MAX_BINARY, MAX_CONFIG, InventoryError,
)

RECEIPT = ROOT / "docs" / "g23-pinned-kernel-receipt.json"
BOOT_ARGS = "console=ttyS0 reboot=k panic=1 pci=off root=/dev/vda rootfstype=ext4 init=/sbin/init ro"
RUN_LIMIT_SECONDS = 100


class BootError(RuntimeError):
    pass


def fetch_pinned_kernel(base: Path, client=None) -> tuple[Path, dict]:
    """Download only bytes matching previously pinned SHA256, never run on host."""
    if not base.is_absolute() or base.is_symlink() or not base.is_dir():
        raise BootError("Unsafe asset workdir")
    data = json.loads(RECEIPT.read_text(encoding="utf-8"))
    key, config_key = data["kernelKey"], data["configKey"]
    if (not KERNEL_KEY.fullmatch(key) or config_key != key + ".config"
            or data["kernelBytes"] > MAX_BINARY
            or data["status"] != "candidate-hash-pinned-NOT-signed-NOT-approved"):
        raise BootError("Unreviewed kernel receipt")
    client = client if client is not None else _client()
    config_bytes = _read_bounded(
        client, BASE + "/" + urllib.parse.quote(config_key, safe="/"), MAX_CONFIG)
    if hashlib.sha256(config_bytes).hexdigest() != data["configSha256"]:
        raise BootError("Pinned Kconfig differs")
    if b"CONFIG_PVH=y\n" not in config_bytes:
        raise BootError("Direct ELF QEMU boot requires CONFIG_PVH=y")
    config = base / ".config"
    config.write_bytes(config_bytes)
    config.chmod(0o600)
    kernel = base / "vmlinux"
    kernel_url = BASE + "/" + urllib.parse.quote(key, safe="/")
    size = 0
    digest = hashlib.sha256()
    with client.open(kernel_url, timeout=90) as response:
        if response.geturl() != kernel_url or response.status != 200:
            raise BootError("Unexpected kernel URL")
        length = response.headers.get("Content-Length")
        if length and int(length) != data["kernelBytes"]:
            raise BootError("Changed kernel content length")
        with kernel.open("wb") as out:
            while True:
                chunk = response.read(min(1024 * 1024, MAX_BINARY - size + 1))
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BINARY:
                    raise BootError("Kernel larger than cap")
                out.write(chunk)
                digest.update(chunk)
    kernel.chmod(0o600)
    if size != data["kernelBytes"] or digest.hexdigest() != data["kernelSha256"]:
        raise BootError("Kernel fails exact pinned checksum")
    inspect_kernel_config(kernel, data["kernelSha256"], config, data["configSha256"])
    return kernel, data


def fixed_qemu_args(qemu: Path, kernel: Path, disk: Path,
                    serial: Path, nonce: str) -> tuple[str, ...]:
    if (any(not p.is_absolute() or not p.is_file() or p.is_symlink()
            for p in (qemu, kernel, disk))
            or not serial.is_absolute() or serial.exists() or serial.is_symlink()
            or not serial.parent.is_dir()
            or not re.fullmatch(r"[0-9a-f]{32}", nonce)):
        raise BootError("Unsafe fixed QEMU input")
    return (
        str(qemu), "-machine", "microvm", "-accel", "tcg,thread=single",
        "-cpu", "qemu64", "-m", "256M", "-smp", "1",
        "-kernel", str(kernel), "-append", checked_boot_args(BOOT_ARGS, nonce),
        "-drive", "file=" + str(disk) + ",if=none,format=raw,readonly=on,id=rootdisk",
        "-device", "virtio-blk-device,drive=rootdisk",
        "-nodefaults", "-no-user-config", "-display", "none",
        "-serial", "file:" + str(serial), "-monitor", "none",
        "-nic", "none", "-no-reboot",
        "-sandbox", "on,obsolete=deny,elevateprivileges=deny,spawn=deny,resourcecontrol=deny",
    )


def _terminate(proc: subprocess.Popen) -> bool:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except OSError:
        return False
    try:
        proc.wait(timeout=8)
        return True
    except (OSError, subprocess.TimeoutExpired):
        return False


def observe_guest(args: tuple[str, ...], serial: Path, nonce: str, *,
                  runner=subprocess.Popen, stopper=_terminate, limit=RUN_LIMIT_SECONDS):
    home = serial.parent / "qemu-home"
    home.mkdir(mode=0o700)
    proc = None
    seen = False
    clean = False
    reason = "start-failed"
    try:
        proc = runner(list(args), cwd=serial.parent, start_new_session=True,
                      stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL,
                      env={"PATH": "/usr/bin:/bin", "HOME": str(home), "LANG": "C"})
        deadline = time.monotonic() + limit
        while time.monotonic() < deadline:
            if guest_marker_observed(serial, nonce):
                seen = True
                reason = "real-qemu-guest-userspace-marker"
                break
            if proc.poll() is not None:
                reason = "qemu-exited-without-guest-marker"
                break
            time.sleep(0.25)
        else:
            reason = "guest-serial-timeout"
    except (OSError, ValueError, subprocess.SubprocessError):
        reason = "qemu-subprocess-error"
    finally:
        if proc is not None:
            clean = stopper(proc)
    return seen, clean, reason


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--github-hosted-synthetic-only", action="store_true")
    opts = parser.parse_args(argv)
    if (not opts.github_hosted_synthetic_only
            or os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"):
        print('{"result":"blocked","reason":"disposable-ci-required"}')
        return 3
    report = {
        "contract": "foundation.real-qemu-tcg-synthetic-guest/v0",
        "observedAt": datetime.now(timezone.utc).isoformat(),
        "assessment": "real-QEMU-TCG-guest-NOT-Firecracker-KVM-isolation",
        "hypervisor": "qemu-tcg",
        "firecrackerExecuted": False,
        "kvmUsed": False,
        "jailerUsed": False,
        "modelInvoked": False,
        "untrustedExternalCodeExecuted": False,
        "guestReadinessAttested": False,
        "productionIsolationValidated": False,
        "vmAdmissionAllowed": False,
        "guestMarkerObserved": False,
        "cleanupConfirmed": False,
        "result": "blocked",
        "reason": "preflight-unavailable",
    }
    output = ROOT / "artifacts" / "g24-qemu-tcg-guest-boot.json"
    output.parent.mkdir(exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="foundation-g24-") as td:
            root = Path(td)
            kernel, receipt = fetch_pinned_kernel(root)
            staging = root / "guest"
            manifest_path = build_guest(staging)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            disk = staging / "rootfs.ext4"
            if _sha256(disk) != manifest["rootfsSha256"]:
                raise BootError("Unexpected synthetic rootfs contents")
            qemu = Path("/usr/bin/qemu-system-x86_64")
            challenge = secrets.token_hex(16)
            serial = root / "serial.log"
            args = fixed_qemu_args(qemu, kernel, disk, serial, challenge)
            seen, cleaned, reason = observe_guest(args, serial, challenge)
            report.update({
                "kernelSha256": receipt["kernelSha256"],
                "rootfsSha256": manifest["rootfsSha256"],
                "guestMarkerObserved": seen,
                "cleanupConfirmed": cleaned,
                "result": "pass" if seen and cleaned else "blocked",
                "reason": reason if cleaned else "cleanup-unverified",
            })
    except (OSError, ValueError, BootError, InventoryError,
            subprocess.TimeoutExpired) as ex:
        report["reason"] = type(ex).__name__
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["result"], "reason": report["reason"],
                      "guestMarkerObserved": report["guestMarkerObserved"],
                      "firecrackerExecuted": False, "kvmUsed": False}))
    return 0 if report["result"] == "pass" else 3


if __name__ == "__main__":
    sys.exit(main())
