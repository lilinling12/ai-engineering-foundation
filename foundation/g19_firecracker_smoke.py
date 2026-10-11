"""G1.9 trusted-host Firecracker VMM boot probe; never executes generated code.

Default DENY. Even a positive VMM API state does NOT prove guest health, jailer
isolation, safe egress, hostile-source containment or production approval.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
from typing import Callable

from .__main__ import ROOT
from .g18_kvm_probe import probe_kvm, KvmCapability

HEX = re.compile(r"^[0-9a-f]{64}$")
OPERATOR_FLAG = "FOUNDATION_TRUSTED_DISPOSABLE_KVM_HOST"
OPERATOR_VALUE = "G19_UNJAILED_EXPERIMENT_ONLY"
BOOT_ARGS = "console=ttyS0 reboot=k panic=1 pci=off root=/dev/vda ro"
POLL_SECONDS = 0.1

@dataclass(frozen=True)
class Assets:
    firecracker: Path
    kernel: Path
    rootfs: Path
    firecracker_sha256: str
    kernel_sha256: str
    rootfs_sha256: str

@dataclass(frozen=True)
class Trial:
    status: str
    reason: str
    kvm_api_version: int | None
    vmm_api_running: bool
    guest_boot_verified: bool
    process_reaped: bool
    process_group_kill_issued: bool


class TrialDenied(ValueError):
    pass


def _verify_file(path: Path, digest: str, kind: str) -> None:
    if (not isinstance(path, Path) or not path.is_absolute()
            or path.is_symlink() or not path.is_file()
            or path.resolve(strict=True) != path
            or not HEX.fullmatch(digest)):
        raise TrialDenied("Noncanonical or unpinned " + kind)
    st = path.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_size < 128 or st.st_mode & 0o022:
        raise TrialDenied("Missing or writable " + kind)
    if kind == "firecracker" and not os.access(path, os.X_OK):
        raise TrialDenied("Firecracker binary must be executable")
    if kind in {"firecracker", "kernel"}:
        with path.open("rb") as fh:
            if fh.read(4) != b"\x7fELF":
                raise TrialDenied("Expected uncompressed ELF " + kind)
    if kind == "rootfs":
        with path.open("rb") as fh:
            fh.seek(1080)
            if fh.read(2) != b"\x53\xef":
                raise TrialDenied("Expected ext4 rootfs")
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            hasher.update(block)
    if hasher.hexdigest() != digest:
        raise TrialDenied("Pinned SHA256 mismatch for " + kind)


def validate_assets(assets: Assets) -> None:
    _verify_file(assets.firecracker, assets.firecracker_sha256, "firecracker")
    _verify_file(assets.kernel, assets.kernel_sha256, "kernel")
    _verify_file(assets.rootfs, assets.rootfs_sha256, "rootfs")
    if len({str(assets.firecracker), str(assets.kernel), str(assets.rootfs)}) != 3:
        raise TrialDenied("Assets must be distinct")


def _clean_env(home: Path) -> dict[str, str]:
    # No model/CI/cloud credentials, proxies, existing Firecracker socket hints
    # or inherited dynamic-loader variables.
    return {"PATH": os.defpath, "HOME": str(home), "LANG": "C.UTF-8"}


class _UnixConnection(http.client.HTTPConnection):
    def __init__(self, sock_path: Path):
        super().__init__("localhost", timeout=3)
        self.sock_path = sock_path

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(3)
        self.sock.connect(str(self.sock_path))


def firecracker_api(sock_path: Path, method: str, resource: str,
                    payload: dict | None) -> dict | None:
    if method not in {"PUT", "GET"} or resource not in {
        "/machine-config", "/boot-source", "/drives/rootfs", "/actions", "/"
    }:
        raise TrialDenied("Unreviewed Firecracker API action")
    conn = _UnixConnection(sock_path)
    try:
        body = json.dumps(payload, separators=(",", ":")) if payload is not None else None
        conn.request(method, resource, body=body,
                     headers={"Content-Type": "application/json"} if body else {})
        resp = conn.getresponse()
        raw = resp.read(8193)
        if len(raw) > 8192:
            raise TrialDenied("Oversized VMM API response")
        expected = 200 if method == "GET" else 204
        if resp.status != expected:
            raise TrialDenied("Firecracker API rejected reviewed request")
        return json.loads(raw) if method == "GET" else None
    finally:
        conn.close()


def _stop_group(proc: subprocess.Popen) -> tuple[bool, bool]:
    """Kill dedicated VMM process group; reaping parent is NOT descendant proof."""
    signalled = False
    try:
        os.killpg(proc.pid, signal.SIGKILL)
        signalled = True
    except ProcessLookupError:
        signalled = True  # Group already absent.
    except OSError:
        pass
    try:
        proc.wait(timeout=5)
        return (signalled, True)
    except (OSError, subprocess.TimeoutExpired):
        return (signalled, False)


def run_probe(
    assets: Assets, *, explicit: bool,
    runner: Callable = subprocess.Popen,
    request: Callable = firecracker_api,
    capability: Callable[[], KvmCapability] = probe_kvm,
    stopper: Callable = _stop_group,
) -> Trial:
    if not explicit or os.environ.get(OPERATOR_FLAG) != OPERATOR_VALUE:
        return Trial("blocked", "operator-authorization-required", None, False, False, True, False)
    host = capability()
    if host.result != "available" or host.api_version != 12:
        return Trial("blocked", "kvm-host-unavailable", host.api_version, False, False, True, False)
    try:
        validate_assets(assets)
    except (TrialDenied, OSError, UnicodeError):
        return Trial("blocked", "untrusted-or-invalid-assets", 12, False, False, True, False)

    vmm_running = False
    reason = "vmm-launch-failed"
    started = False
    terminated = False
    reaped = True
    with tempfile.TemporaryDirectory(prefix="g19-fc-") as td:
        root = Path(td)
        (root / "home").mkdir(mode=0o700)
        sock = root / "firecracker.sock"
        if len(os.fsencode(sock)) >= 106:
            return Trial("blocked", "socket-path-too-long", 12, False, False, True, False)
        proc = None
        try:
            proc = runner(
                [str(assets.firecracker), "--api-sock", str(sock)],
                env=_clean_env(root / "home"), cwd=root,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, start_new_session=True,
            )
            deadline = time.monotonic() + 8
            while not sock.exists() and time.monotonic() < deadline:
                if proc.poll() is not None:
                    raise TrialDenied("VMM terminated before socket ready")
                time.sleep(POLL_SECONDS)
            if not sock.exists() or not sock.is_socket():
                raise TrialDenied("VMM socket unavailable")
            sequence = (
                ("PUT", "/machine-config", {"vcpu_count": 1, "mem_size_mib": 128, "smt": False}),
                ("PUT", "/boot-source", {"kernel_image_path": str(assets.kernel),
                                        "boot_args": BOOT_ARGS}),
                ("PUT", "/drives/rootfs", {"drive_id": "rootfs",
                                          "path_on_host": str(assets.rootfs),
                                          "is_root_device": True, "is_read_only": True}),
                ("PUT", "/actions", {"action_type": "InstanceStart"}),
            )
            for method, resource, payload in sequence:
                request(sock, method, resource, payload)
            started = True
            if proc.poll() is not None:
                raise TrialDenied("VMM terminated on boot")
            info = request(sock, "GET", "/", None)
            vmm_running = isinstance(info, dict) and info.get("state") == "Running"
            reason = "vmm-api-running-guest-unverified" if vmm_running else "vmm-api-not-running"
        except (OSError, ValueError, http.client.HTTPException, TimeoutError):
            reason = "vmm-api-or-boot-error"
        finally:
            if proc is not None:
                terminated, reaped = stopper(proc)
    status = "vmm-start-observed" if vmm_running and terminated and reaped else "blocked"
    if not terminated or not reaped:
        reason = "cleanup-unverified"
    return Trial(status, reason, 12, vmm_running, False, reaped, terminated)


def write_report(assets: Assets, result: Trial) -> Path:
    data = {
        "contract": "foundation.firecracker-vmm-smoke/v0",
        "trustLevel": "operator-local-unattested",
        "observedAt": datetime.now(timezone.utc).isoformat(),
        "result": asdict(result),
        "pinnedAssetSha256": {
            "firecracker": assets.firecracker_sha256,
            "kernel": assets.kernel_sha256, "rootfs": assets.rootfs_sha256,
        },
        "networkInterfacesConfigured": False,
        "modelInvoked": False,
        "generatedCodeExecuted": False,
        "jailerUsed": False,
        "vmAdmissionAllowed": False,
        "guestBootVerified": False,
        "productionIsolationValidated": False,
    }
    dest = ROOT / "artifacts" / "g19-firecracker-vmm-smoke.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    for key in ("firecracker", "kernel", "rootfs"):
        parser.add_argument("--" + key, type=Path, required=True)
        parser.add_argument("--" + key + "-sha256", required=True)
    parser.add_argument("--acknowledge-unjailed-experiment", action="store_true")
    opts = parser.parse_args(argv)
    assets = Assets(*(getattr(opts, key) for key in (
        "firecracker", "kernel", "rootfs", "firecracker_sha256",
        "kernel_sha256", "rootfs_sha256",
    )))
    result = run_probe(assets, explicit=opts.acknowledge_unjailed_experiment)
    report = write_report(assets, result)
    print(json.dumps({"status": result.status, "reason": result.reason,
                      "guestBootVerified": False, "report": str(report)}))
    return 0 if result.status == "vmm-start-observed" else 3

if __name__ == "__main__":
    sys.exit(main())
