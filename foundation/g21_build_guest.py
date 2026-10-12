"""Create a real synthetic static-ELF init and ext4 Guest rootfs (NO KVM).

No sudo, loop device, Docker, network access, downloaded dependencies or
AI-generated source. Host GCC/e2fsprogs supply chain is not pinned, so build
evidence remains unsigned and requires an independent operator review.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from .__main__ import ROOT

SOURCE = ROOT / "guest" / "synthetic-init.c"
FS_UUID = "4cda8845-f4d5-47f1-90ac-ef001d210001"
ROOTFS_BYTES = 32 * 1024 * 1024
TEST_NONCE = "a" * 32
TEST_MARKER = b"FOUNDATION_GUEST_READY_V1 " + TEST_NONCE.encode() + b"\n"


class GuestBuildError(RuntimeError):
    pass


def _invoke(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        timeout=90, check=False,
        env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "C", "HOME": "/nonexistent"},
    )


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def build_guest(destination: Path) -> Path:
    if (not isinstance(destination, Path) or not destination.is_absolute() or
            ".." in destination.parts or destination.exists() or
            destination.is_symlink() or not destination.parent.is_dir() or
            destination.parent.is_symlink()):
        raise GuestBuildError("Destination must be a new absolute directory")
    if not SOURCE.is_file() or SOURCE.is_symlink():
        raise GuestBuildError("Built-in synthetic init missing")
    for tool in ("gcc", "readelf", "mke2fs", "debugfs", "e2fsck"):
        if not shutil.which(tool):
            raise GuestBuildError("Required host build tool unavailable: " + tool)
    with tempfile.TemporaryDirectory(prefix="foundation-g21-") as temp:
        base = Path(temp)
        root = base / "root"
        for name in ("sbin", "proc", "dev"):
            (root / name).mkdir(parents=True)
        init = root / "sbin" / "init"
        cmd = ["gcc", "-static", "-O2", "-Wall", "-Wextra", "-Werror",
               "-o", str(init), str(SOURCE)]
        if _invoke(cmd).returncode:
            raise GuestBuildError("Static init compilation failed")
        init.chmod(0o755)
        if init.read_bytes()[:4] != b"\x7fELF":
            raise GuestBuildError("Guest init not ELF")
        elf = _invoke(["readelf", "-l", str(init)])
        if elf.returncode or b"INTERP" in elf.stdout:
            raise GuestBuildError("Guest ELF has dynamic interpreter")
        args = "console=ttyS0 foundation.probe_token=" + TEST_NONCE
        valid = _invoke([str(init), "--self-test", args])
        if valid.returncode or valid.stdout != TEST_MARKER:
            raise GuestBuildError("Guest init readiness parser self-test failed")
        duplicate = _invoke([str(init), "--self-test",
                             args + " foundation.probe_token=" + TEST_NONCE])
        if duplicate.returncode == 0:
            raise GuestBuildError("Guest init accepted duplicated token")
        image = base / "rootfs.ext4"
        with image.open("wb") as fh:
            fh.truncate(ROOTFS_BYTES)
        if _invoke(["mke2fs", "-q", "-F", "-t", "ext4", "-b", "4096",
                    "-U", FS_UUID, "-d", str(root), str(image)]).returncode:
            raise GuestBuildError("Rootfs construction failed")
        commands = base / "debugfs.commands"
        commands.write_text("cd /dev\nmknod console c 5 1\nmknod null c 1 3\n",
                            encoding="ascii")
        if _invoke(["debugfs", "-w", "-f", str(commands), str(image)]).returncode:
            raise GuestBuildError("Rootfs special device creation failed")
        for path in ("/sbin/init", "/dev/console", "/dev/null"):
            response = _invoke(["debugfs", "-R", "stat " + path, str(image)])
            if response.returncode or b"Inode:" not in response.stdout:
                raise GuestBuildError("Rootfs inode missing: " + path)
        if _invoke(["e2fsck", "-fn", str(image)]).returncode not in (0, 1):
            raise GuestBuildError("Rootfs integrity check failed")
        manifest = {
            "contract": "foundation.synthetic-guest-assets/v0",
            "assessment": "built-and-fsck-checked-NOT-booted",
            "guestSourceSha256": _sha256(SOURCE),
            "guestInitSha256": _sha256(init),
            "rootfsSha256": _sha256(image),
            "rootfsBytes": image.stat().st_size,
            "guestInitPath": "/sbin/init",
            "kernelIncluded": False,
            "jailerIncluded": False,
            "modelInvoked": False,
            "guestBootVerified": False,
            "vmAdmissionAllowed": False,
        }
        destination.mkdir(mode=0o700)
        shutil.copyfile(image, destination / "rootfs.ext4")
        m = destination / "manifest.json"
        m.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return m


def main() -> int:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--dest", type=Path, required=True)
    args = p.parse_args()
    try:
        output = build_guest(args.dest)
        print(json.dumps({"result": "rootfs-built-not-booted", "manifest": str(output)}))
        return 0
    except (GuestBuildError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"result": "blocked", "reason": str(exc) if isinstance(exc, GuestBuildError) else type(exc).__name__}))
        return 3


if __name__ == "__main__":
    sys.exit(main())
