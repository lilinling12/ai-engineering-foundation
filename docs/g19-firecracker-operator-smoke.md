# G1.9 — Trusted-host unjailed Firecracker VMM startup smoke (not production)

**Status: executable operator-only VMM diagnostic; guest health and security isolation NOT verified.**
The trusted-host KVM probe in G1.8 remains blocked on GitHub-hosted runners
(`kvm-permission-denied`). This experimental runner is intentionally **not**
added to GitHub Actions, and does not provision paid hosts.

## Why this is not a sandbox provider

This runner intentionally starts Firecracker **without Jailer** for a controlled,
operator-owned dedicated-host VMM API smoke test. It must NEVER execute code
from an AI, user upload, external PR, or customer repository. There is no guest
agent, vsock, TAP interface, external network, model credentials or production
secrets. The guest root filesystem is mounted read-only.

It requires explicit authorization via *both* environment and CLI flag, a genuine
KVM ioctl preflight, three operator-supplied absolute canonical local files,
matching SHA-256 digests, a Firecracker ELF binary, ELF guest kernel, ext4 rootfs,
a clean child-process environment, and a dedicated process group.

```bash
# ONLY in a dedicated disposable operator-controlled KVM Linux host:
export FOUNDATION_TRUSTED_DISPOSABLE_KVM_HOST=G19_UNJAILED_EXPERIMENT_ONLY
python -m foundation.g18_kvm_probe --require-kvm

python -m foundation.g19_firecracker_smoke \
  --firecracker /opt/reviewed/firecracker --firecracker-sha256 <64-hex> \
  --kernel /opt/reviewed/vmlinux --kernel-sha256 <64-hex> \
  --rootfs /opt/reviewed/rootfs.ext4 --rootfs-sha256 <64-hex> \
  --acknowledge-unjailed-experiment
```

You must review the binary/guest image provenance **independently**. Supplying
a SHA-256 you calculated from a malicious downloaded file does not establish
trust. The probe never downloads files, enables KVM ACLs, changes firewall
rules, configures TAP networking, or creates external resources.

## Actual requests

Uses a fresh Unix-socket Firecracker API: PUT `/machine-config` (1 vCPU,
128 MiB RAM), PUT `/boot-source` (fixed console/reboot arguments),
PUT `/drives/rootfs` (read-only ext4), PUT `/actions` InstanceStart,
then GET `/` for `state=Running`. Does NOT configure a guest NIC or vsock.

Process-group kill and wait run even when an API command fails. The unsigned
result artifact explicitly records `guestBootVerified=false`,
`jailerUsed=false`, `vmAdmissionAllowed=false`, `productionIsolationValidated=false`.
Positive `state=Running` is **VMM API startup**, not successful in-guest
test execution, VM security isolation, or complete descendant cleanup.

## Next acceptance, separately reviewed

- KVM-capable trusted host with independent evidence; pinned Firecracker and
  Jailer binaries + immutable guest rootfs/kernel from reviewed sources.
- Run actual VMM smoke and inspect run artifacts and API/host process lifecycle.
- Add separately operated Jailer, guest readiness/proof and termination tests.
- Prove network and credential isolation outside the guest and signed independent
  run evidence. Reject Docker fallback.
- Verify human approval / repository Ruleset (Issue #7) and close host blocker
  only with actual test evidence (Issue #8).

References: https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md
and https://github.com/firecracker-microvm/firecracker/blob/main/docs/api_requests/actions.md .

## G2.0 optional trusted-Guest serial readiness challenge (2026-10-12)

The operator-run command now accepts `--require-guest-ready` to **fail closed**
when the Firecracker VMM API reports `Running` but the trusted synthetic
Guest does not emit an exact per-boot readiness line within the deadline.

A cryptographically random 128-bit *correlation challenge* is appended to
the kernel boot arguments as `foundation.probe_token=<32 lowercase hex>`.
The **operator-owned, independently reviewed Guest init** must read
`/proc/cmdline`, finish its trusted userspace startup checks, then print the
exact following line by writing to the **serial console** (`/dev/console`
or `ttyS0`), followed by newline:

```text
FOUNDATION_GUEST_READY_V1 <the-32-hex-challenge>
```

Example operator command after independently preparing this synthetic Guest:

```bash
python -m foundation.g19_firecracker_smoke \
  --firecracker /opt/reviewed/firecracker --firecracker-sha256 <sha256> \
  --kernel /opt/reviewed/vmlinux --kernel-sha256 <sha256> \
  --rootfs /opt/reviewed/rootfs.ext4 --rootfs-sha256 <sha256> \
  --acknowledge-unjailed-experiment --require-guest-ready
```

The challenge is **not a secret or authentication**. A malicious Guest can echo
it, kernel command-line arguments can be read by the Guest, and the VMM or its
stdout can simulate output. The protocol is a useful synthetic readiness
correlation check only. The log remains in an automatically deleted private
directory, limited to 256 KiB; raw kernel/Guest output and the challenge
never enter the evidence artifact. The evidence records only
`guestReadinessMarkerObserved` and `guestReadinessAttested=false`.
`guestBootVerified=false` and `vmAdmissionAllowed=false` remain unchanged
even after the marker is observed.

This code **does not package or verify a working Guest image** and is not
executed against a KVM host in GitHub CI. It cannot replace a later jailed,
cryptographically attested independent Guest acceptance/termination test.
