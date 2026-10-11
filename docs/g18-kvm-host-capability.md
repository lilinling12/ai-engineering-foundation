# G1.8 — Real KVM host capability assessment

Status: **KVM probing only / VM execution NOT VERIFIED**.

## Why this gate exists

Firecracker requires a Linux x86_64/aarch64 host with read/write access to
\`/dev/kvm\` and a working KVM API. CI success in a GitHub-hosted container
or Docker is **not** proof of a suitable microVM host.

## Executable preflight

\`python -m foundation.g18_kvm_probe\` checks the kernel *character device*
and opens /dev/kvm with O_RDWR/O_CLOEXEC/O_NOFOLLOW. It issues Linux ioctl
\`KVM_GET_API_VERSION\` (0xAE00) and accepts version 12 only. It closes
the device on all successful-open paths.

The \`g18-kvm-capability-probe\` GitHub job runs on a no-secret, read-only-token
Ubuntu runner, writes \`artifacts/g18-kvm-host-preflight.json\`, and uploads
it. A successful job means **observation was recorded**, NOT that KVM exists.
Read \`kvm.result\` and \`kvm.reason\` in the artifact.

The probe has no provisioned VM, no Firecracker executable, no kernel image,
no guest rootfs, no inference credentials, no network access, no test payload,
and **always records vmAdmissionAllowed=false**. Any later VM-admission
control MUST come from an independently verified, non-PR-controlled
provisioner and remain default-deny here.

## Next gate, only after actual KVM available

1. Select a dedicated, trusted KVM-capable host and verify /dev/kvm with
   the same ioctl. Do not blindly run Firecracker on GitHub-hosted CI.
2. Build or supply verified pinned Firecracker+jailer binaries, Linux kernel
   and read-only ext4 rootfs. Record immutable hashes and provenance.
3. Prove actual VM boot, in-guest isolated deterministic test, VM identity,
   0-Internet egress and termination (including descendant cleanup).
4. Run rejection/injection scenarios, guarantee no Docker fallback and ensure
   no model API key is ever passed into evaluator VM.
5. Publish independent signed evidence and get human security review.
6. Only then, with explicit approval, consider executing model-generated
   synthetic code, still without customer repositories.

No inference, paid call or microVM execution is performed by this check.

References:
- Firecracker getting started: https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md
- Firecracker production host: https://github.com/firecracker-microvm/firecracker/blob/main/docs/prod-host-setup.md
