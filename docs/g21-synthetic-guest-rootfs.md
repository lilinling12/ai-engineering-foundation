# G2.1 — Static synthetic Guest rootfs build

**Status: actual ELF/ext4 build work; KVM Guest boot NOT verified.**

This adds a single-purpose C `/sbin/init` at `guest/synthetic-init.c`:
PID 1 mounts proc, reads the nonce from `/proc/cmdline`, writes the exact
G2.0 readiness line to `/dev/console`, then waits. It has no shell, services,
network, agent execution, SSH or credentials. Its `--self-test` mode tests
only the parser on the trusted build host.

The build command `python -m foundation.g21_build_guest --dest /absolute/new/directory`
requires GCC with static libc, readelf, mke2fs, debugfs and e2fsck. It compiles
a static ELF, rejects dynamic interpreter linkage, self-tests the nonce parser,
generates a 32 MiB ext4 rootfs without sudo/loop mount, creates device nodes,
checks required inodes and runs a read-only fsck. An unsigned manifest records
SHA-256 for the source, init and rootfs.

A dedicated credential-free GitHub CI job runs those REAL build tools and uploads
the rootfs plus manifest with short retention. Passing this build proves neither
a successful kernel boot nor binary provenance or hypervisor isolation.

The Guest kernel is NOT included. The trusted-host operator must independently
select and verify an architecture-compatible kernel with virtio-blk, ext4,
procfs and ttyS0 console support; use the previously reviewed Firecracker
binary and G1.9 `--require-guest-ready` trial on an authorized disposable host.
The PR-controlled CI artifact hash is **not** an independent authenticity proof.

No host is provisioned, no KVM permissions changed, no API calls made and
Issues #7 and #8 remain external blockers.

Authority: https://github.com/firecracker-microvm/firecracker/blob/main/docs/rootfs-and-kernel-setup.md
and https://man7.org/linux/man-pages/man8/mke2fs.8.html
