# G1.7 — Production isolation decision and synthetic boundary hardening

**Status: implementation of synthetic guards only; strong isolation NOT deployed.**

A real Agent Runtime requires separate inference and evaluation trust domains. Codex may
need short-lived provider credentials and controlled HTTPS egress; the evaluator must
receive only a reviewed source artifact, have no model/API keys or GitHub credentials,
no outbound network by default, an independent immutable oracle, and hard CPU, memory,
PID and cancellation limits.

**Preferred VM evaluation candidate:** Firecracker microVM with jailer, KVM on dedicated
trusted host, network namespaces, seccomp/cgroups and pinned guest image. Evaluate
gVisor/runsc as a separately threat-modelled alternative. Neither is installed here,
and no silent downgrade to normal Docker is permitted for arbitrary AI-generated code.

The immediate GitHub-hosted CI patch remains synthetic-only: fixed candidate source
bytes, startup/sitecustomize injection checks, exact acceptance oracle, clean Docker
client environment, and negative tests. Existing G1.2 reviewed-fixture executor stays
unchanged. It does not prove host integrity against malicious PR contributors.

**Production exit criteria** (all pending): verified VM isolation; no credentials in
guest evaluator; permitted inference egress only; full descendant/VM cleanup; immutable
runtime images; independent signed provenance; authenticated patch review; real paid
model trial on approved synthetic data; and independent security review plus Issue #7
main branch protection/PR approval.

Sources:
- https://github.com/firecracker-microvm/firecracker/blob/main/docs/prod-host-setup.md
- https://gvisor.dev/docs/architecture_guide/intro/
- https://docs.github.com/en/actions/reference/security/secure-use
