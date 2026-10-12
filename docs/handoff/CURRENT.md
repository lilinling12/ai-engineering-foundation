# CURRENT — Integration Audit / G0 reviewer handoff
Last observed: 2026-10-10. **This file is a checkpoint, not a live GitHub status API.**

## Product and branch
- Goal: MVP-2 Multi-Stack Engineering Platform (not yet a complete platform).
- This branch: `feat/g14-review-static-acceptance` / PR #6, stacked on PR #5.
- At the last GitHub check, PR #1 was Ready for review; PR #2–#6 were Draft.
- G0 through G1.4 are **NOT CLOSED**, and no PR was merged.
- `main` baseline: `838c875f0e6912612fee6f5aaa0a723549d47857`.
- Branch protection returned `protected=false`, repository Rulesets `[]`;
  Issue #7 remained Open and PR #1 had no submitted review.
- Always check live refs, status, reviews and exact-head checks before making
  claims. This checkpoint may become outdated at any time.

## Read authority in order
1. `docs/integration-audit-2026-10-09.md`: findings, corrected risk register, merge gates
2. `docs/governance/merge-gates.md`: proposed independent reviewer policy
3. `docs/mvp2-plan.md`: MVP-2 vertical slice scope and acceptance
4. `docs/security.md`, `docs/contracts.md`
5. Current affected Gate's own design (`docs/g14-review-static-acceptance.md`,
   `docs/g13-model-proposal.md`, `docs/g12-runtime.md` as needed)

## Latest engineering change
- G0 `foundation verify` requires `--trust-project-code`; not a sandbox.
- G0 verifier refuses untrusted staged marker and invalid scaffold versions.
- G0 verification evidence no longer persists raw subprocess output or exception text.
- Changes propagated through PR #1–#6 with preserved ancestry.
- Latest SHA and CI must be checked on GitHub; do not reuse older green evidence.

## Immediate next tasks
1. Confirm this branch's exact-head Python/TS/Docker CI, and all upstream PR heads.
2. Arrange **genuine independent review** for PR #1 and enable active `main` Ruleset
   via repository administrator (tracked in Issue #7). Do not self-approve or merge.
3. Keep G1 runtime trust domains separated: fixture-only Docker smoke is not
   arbitrary untrusted-code isolation; model proposals remain quarantined.
4. Once G0 is approved and protection verified, human-controlled integration may
   proceed through PR #1 → #6 in dependency order, with repeated head/base checks.

## Explicitly NOT achieved
No closed Gates, production adoption, authenticated human approval, general hostile-code
sandbox, Codex CLI / Claude Code runtime, or independent cryptographic attestations.

## 2026-10-10 G1.3 outbound credential boundary

- PR #5 inference transport rejects HTTP redirects and ambient proxies to avoid
  forwarding model credentials off the single approved HTTPS endpoint.
- G1.3 transport tests and source are synchronized into this PR's stacked ancestry.
- Recheck current SHA and exact-head checks after this change; no Gate is closed.

## G1.3 Codex CLI compatibility checkpoint (2026-10-10)

- PR #5 provides a proposal-only Codex CLI request builder with no process launch.
- The CI compatibility test installs the actual Codex binary from a frozen npm
  lockfile and verifies CLI flags with no credentials or live inference.
- Synced into this PR with preserved Git ancestry. Re-check exact-head checks
  and PR base/head on GitHub after this update.
- Issue #7 still requires independent approval and main ruleset for any merge.

## G1.5 Code proposal experiment (2026-10-10)

- `codex-propose` is now an explicit opt-in live CLI subprocess entrypoint, but only for a fixed synthetic task in an operator-provided disposable environment.
- `foundation/review_gate.py` supports quarantined `codex-cli` proposals and retains the local-unattested approval and static-only stage path.
- CI uses fake process tests and a credential-free real CLI interface check. No actual paid model inference or model-generated code execution verified.
- G0 through G1.5 remain OPEN. Issue #7 main branch protection and independent review remain blocking.

## 2026-10-11 G1.6 offline isolation proof (pending CI)

- PR #6 adds a *separate* synthetic-only offline evaluation runtime, without
  changing G1.2's fixed-fixture execution permission boundary.
- Uses quarantine → **synthetic test decision** → G1.4 static stage → Docker
  independent acceptance, plus negative wrong-answer and timeout experiments.
- No live model, no credentials, no arbitrary repository input or host-side source
  execution. Do NOT claim multi-tenant sandbox security or authentic human approval.
- Check exact-head CI and artifact before marking even the synthetic prototype verified.
- All Gates remain NOT CLOSED; Issue #7 still blocks main protection and independent review.

## G1.7 — synthetic boundary hardening (2026-10-12)

- Added `foundation/g17_boundary.py`: exact built-in synthetic candidate/oracle checks and explicit, minimal Docker-client process environment. G1.6 Python command disables `site` processing with `-S`.
- This guards existing Docker-only synthetic CI, not a genuine VM-grade multi-tenant runtime; no model output admitted. No actual Firecracker runtime provisioned.
- Check latest exact-head CI, then document independent reviewer and Issue #7 blockers. All Gates remain unclosed.

## 2026-10-12 G1.8 host capability probe (pending exact-head CI)

- Separate `g18-kvm-capability-probe` job checks actual /dev/kvm character device and Linux KVM_GET_API_VERSION ioctl rather than trusting environmental markers.
- Even when the job itself passes, the artifact is authoritative for `kvm.result`; KVM unavailable and microVM absent must be reported independently.
- No Firecracker/jailer installed and no KVM-backed guest boot attempted; vmAdmissionAllowed remains false. G1.8 not closed.
- Confirm artifact outcome and exact-head CI from GitHub; Issue #7 remains open and all PR merges require independent review.

## 2026-10-12 G1.8 exact-run outcome

- Actual GitHub-hosted KVM probe for f936b8cd: result=blocked, reason=kvm-permission-denied, apiVersion=null, microVmStarted=false.
- Both exact-head CI runs were green (12/12 tests): the diagnostic job completed, not the Firecracker acceptance Gate.
- Added --require-kvm operator mode which fails with code 3 when KVM is unavailable. No CI sudo/ACL permission widening performed.
- Need trusted KVM host and real guest boot; all Gates remain NOT CLOSED, Issue #7 still blocks independent review / main ruleset.

## 2026-10-12 G1.9 actual VMM boot probe implementation

- PR #6 now contains `foundation/g19_firecracker_smoke.py`: **operator-run only**, defaults deny, requires external trusted disposable Linux KVM host, explicit unjailed-experiment acknowledgment, operator-provided local Firecracker/kernel/ext4 images and SHA-256 digests.
- Uses fixed Firecracker Unix socket API calls: machine-config → boot-source → read-only rootfs → InstanceStart → GET status; always attempts process-group termination and reaping. No NIC/vsock configuration, model credentials or arbitrary generated code.
- `VMM API state=Running` is explicitly **not** guest readiness, successful independent acceptance, complete descendant cleanup or Jailer isolation. `vmAdmissionAllowed=false` remains unchanged.
- CI tests use injected subprocess/API mocks and MUST NOT run Firecracker on GitHub-hosted runners. G1.8 real KVM result remains `blocked/kvm-permission-denied`.
- Issue #8 is the separate KVM host and actual guest-boot blocker; Issue #7 is still the main Ruleset/independent review blocker. All Gates NOT CLOSED.

## G2.0 synthetic Guest readiness challenge (2026-10-12)

- PR #6 extends the operator-only G1.9 Firecracker VMM probe with
  `--require-guest-ready`: per-run random challenge appended to Guest kernel
  command line, bounded exact-line serial marker observation, and fail-closed
  readiness timeout/cleanup behavior.
- Tests use a fake VMM and synthetic serial output. No actual Guest boot on KVM.
- The challenge is **not authentication** and no Guest image/init has been
  independently built/provisioned. Guest boot attestation remains false.
- Reviewers must see exact-head CI for this change. Issue #8 trusted host and
  Issue #7 merge governance remain unresolved; no Gate closed.

## G2.1 minimal synthetic Guest image build (2026-10-12)

- Added `guest/synthetic-init.c` (static Linux PID1 nonce-to-serial readiness); host-only self-test is **not** Guest boot.
- `foundation/g21_build_guest.py` builds a real static ELF and no-root ext4 image using gcc/readelf/mke2fs/debugfs/e2fsck, and publishes SHA256 of source/init/rootfs. The CI artifact is unsigned and its toolchain unpinned.
- Dedicated G2.1 job must actually compile/init self-test/fsck; check latest exact-head CI. Guest kernel remains external; no KVM Guest boot, Jailer or attestation.
- Issue #8 KVM host and Issue #7 independent main Ruleset/review remain OPEN. No Gate closed.

## G2.2 kernel/rootfs boot compatibility checkpoint (2026-10-12)

- Added x86_64 ELF/sha256/Kconfig gate with required built-in ext4, virtio-blk,
  MMIO, procfs, ELF-init, KVM guest, ACPI/PCI and serial console support.
- Strict G1.9 Guest readiness operator path now requires separately supplied
  kernel companion Kconfig + SHA256, and boot args explicitly select ext4 and
  /sbin/init; default Guest start denies a missing config.
- Operator-supplied Kconfig is **not** authenticated as originating from
  vmlinux; real Guest boot and pinned kernel provenance remain external.
- Check exact-head CI. Issue #7 independent review and Issue #8 KVM host
  remain OPEN. No VM success or Gate closure.

## G2.3 official x86_64 Linux 6.18 kernel discovery (2026-10-12)

- Added `foundation/g23_kernel_inventory.py` and no-secret official S3 listing/download CI, retrieving actual candidate kernel and companion .config hashes from a dated Firecracker CI prefix.
- Candidate is **discovery-only**: S3 CI latest objects are not immutable release trust or verified matching kernel build provenance. The process never boots, executes or uploads the kernel ELF; only an unsigned inventory report is saved.
- G1.9 still requires separately operator-reviewed pinned binaries and KVM Guest readiness. Do not reinterpret green inventory as production-ready supply chain.
- Check exact-head G23 CI for actual candidate and repo Issue #8 for trusted host. Issue #7 review/protection still blocks merging. All Gates remain OPEN.

## G2.3 pinned official 6.18.51 kernel receipt (2026-10-12)

- Two actual G23 inventory runs identified the same Firecracker upstream CI S3
  x86_64 `vmlinux-6.18.51`; kernel SHA256 `946e164b5a50...`,
  config SHA256 `47194037099c...`. Full exact keys and sizes are committed
  in `docs/g23-pinned-kernel-receipt.json`.
- Latest G23 CI switches from 'discover latest build' to **verify exact
  receipt hashes**; changes to public upstream bytes cause the CI job to fail.
- This is NOT independently verified kernel provenance or an operational
  Guest boot. Issue #8 actual KVM host and Issue #7 main governance OPEN.
