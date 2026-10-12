# G2.3 — Official Firecracker CI kernel candidate discovery

Experimental data-only discovery to find a **real** x86_64 Linux 6.18
`vmlinux` and `.config` pair from the public Firecracker CI S3 area
documented in its upstream getting-started guide.

The credential-free CI job lists build prefixes, chooses an exact dated
object key, downloads the kernel in bounded chunks to **hash, not execute**
and downloads the companion config to check G2.2 built-in driver options.
Only metadata and SHA256 values enter an unsigned JSON artifact. The
ELF is never made executable, used with G1.9, packaged into rootfs, mounted,
or passed to KVM/Firecracker.

A date-stamped S3 key is **not immutable provenance**, SHA256 determined
by the same discovery process is **not an externally authenticated signature**,
and `.config` adjacency does not certify an exact kernel build relation.
The latest build might change or disappear, resulting in a blocked inventory.
Operator approval must bind independently reviewed source, release/toolchain,
kernel ELF, Kconfig, Firecracker binary and Guest rootfs before any boot.

The KVM runner and independent security review remain unavailable; Issue #8
and Issue #7 are still open. DO NOT treat a green discovery job as VM safety.

Official source: https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md

## Exact upstream candidate pinned after real CI discovery (2026-10-12)

Two independent push/PR CI discovery jobs identified the same official public
`vmlinux-6.18.51` (27,882,928 bytes), and a real ZIP artifact contained its
full pair of SHA-256s. The committed receipt is
`docs/g23-pinned-kernel-receipt.json`. GitHub Actions now runs
`python -m foundation.g23_kernel_inventory --pinned`, which fetches exactly
those two named S3 objects and refuses hash drift or missing drivers.

This is **data-integrity pinning only**. Both hashes were initially determined
by our own unsigned CI run and are not third-party signatures, build attestations
or independent review. No kernel ELF is persisted in this repo; no automatic
Firecracker guest trial, code execution, Jailer admission or external spend.
An operator must independently establish provenance and approve any actual
G1.9 boot experiment. Never substitute a new 'latest' kernel automatically.
