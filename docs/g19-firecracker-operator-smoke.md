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
