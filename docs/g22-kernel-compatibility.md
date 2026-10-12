# G2.2 Kernel + rootfs compatibility gate (not a Guest boot)

The G2.1 real ext4 rootfs is now compiled. The missing kernel is a **separate,
operator-controlled artifact**. The Firecracker upstream policy (checked on
2026-10-12) includes 6.18 as a currently supported guest kernel generation,
but this repository does **not** assume any `vmlinux` file has suitable
compiled-in drivers just because it is ELF.

`foundation/g22_kernel_compat.py` checks a SHA-256-pinned, uncompressed,
64-bit little-endian x86_64 ELF vmlinux plus a separately pinned companion
ASCII Kconfig. This G2.1 fixture requires built-in (=y), not loadable modules,
for: x86_64, ELF init, block, virtio/MMIO/blk, ext4, procfs, KVM guest,
ACPI/PCI and 8250 serial console/printk. Other kernel image formats and
platforms are intentionally outside this one synthetic test profile.

`--require-guest-ready` in G1.9 will require a separately supplied
`--kernel-config` and `--kernel-config-sha256` before starting Firecracker.
`--kernel` and `--kernel-sha256` continue to be mandatory.

**Critical limitation:** The supplied `.config` file is not cryptographically
bound to the kernel that was built. A checksum of both files is insufficient
to authenticate source, toolchain, or build relation. Acceptance requires
independent reviewed provenance and a real guest boot on an operator-owned
trusted KVM host. This check does not use network, KVM or install anything.

Boot parameters explicitly select `root=/dev/vda rootfstype=ext4
init=/sbin/init ro console=ttyS0`; Firecracker's no-PCI MMIO mode is still
a fixed scope, not a generic kernel launcher. The actual Guest user-mode
readiness marker remains unsigned and forgeable.

Official references:
- https://github.com/firecracker-microvm/firecracker/blob/main/docs/kernel-policy.md
- https://github.com/firecracker-microvm/firecracker/blob/main/docs/rootfs-and-kernel-setup.md

Gate status: **NOT CLOSED**. Issues #7 and #8 remain.
